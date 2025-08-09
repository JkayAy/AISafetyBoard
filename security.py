"""
Enhanced security features including rate limiting and input validation
"""
import time
import re
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import streamlit as st
import sqlite3
from functools import wraps
import bleach
import html

class RateLimiter:
    """Rate limiting implementation for API and web requests"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = set()
        self.blocked_until = {}
    
    def is_allowed(self, identifier: str, max_requests: int = 100, 
                   window_seconds: int = 3600) -> bool:
        """Check if request is allowed based on rate limits"""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Check if IP is temporarily blocked
        if identifier in self.blocked_until:
            if current_time < self.blocked_until[identifier]:
                return False
            else:
                del self.blocked_until[identifier]
                self.blocked_ips.discard(identifier)
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Check rate limit
        if len(self.requests[identifier]) >= max_requests:
            # Block for 1 hour
            self.blocked_until[identifier] = current_time + 3600
            self.blocked_ips.add(identifier)
            return False
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True
    
    def get_stats(self, identifier: str) -> Dict[str, Any]:
        """Get rate limit statistics for identifier"""
        current_time = time.time()
        recent_requests = [
            req_time for req_time in self.requests[identifier]
            if req_time > current_time - 3600
        ]
        
        return {
            "requests_last_hour": len(recent_requests),
            "is_blocked": identifier in self.blocked_ips,
            "blocked_until": self.blocked_until.get(identifier)
        }

class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML input to prevent XSS"""
        if not text:
            return ""
        
        # Allow only safe HTML tags
        allowed_tags = ['b', 'i', 'u', 'br', 'p', 'strong', 'em']
        allowed_attributes = {}
        
        return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """Validate username format and return (is_valid, error_message)"""
        if not username:
            return False, "Username is required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 50:
            return False, "Username must be less than 50 characters"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        
        # Check for at least one uppercase, lowercase, and number
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        return True, ""
    
    @staticmethod
    def sanitize_model_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize model submission input"""
        sanitized = {}
        
        # Required string fields
        string_fields = ['name', 'provider', 'description']
        for field in string_fields:
            if field in data:
                value = str(data[field]).strip()
                sanitized[field] = InputValidator.sanitize_html(value)[:500]  # Limit length
        
        # Optional fields
        if 'version' in data:
            sanitized['version'] = str(data['version']).strip()[:100]
        
        if 'api_endpoint' in data:
            endpoint = str(data['api_endpoint']).strip()
            # Validate URL format
            if endpoint and re.match(r'^https?://.+', endpoint):
                sanitized['api_endpoint'] = endpoint[:500]
        
        return sanitized
    
    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """Detect potential SQL injection attempts"""
        if not text:
            return False
        
        # Common SQL injection patterns
        sql_patterns = [
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s",
            r"(?i)(\s|^)(or|and)\s+\d+\s*=\s*\d+",
            r"(?i)(\s|^)(or|and)\s+['\"].*['\"]",
            r"[';](\s)*(drop|delete|insert|update|create)",
            r"(?i)(exec|execute|sp_|xp_)"
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    @staticmethod
    def detect_xss(text: str) -> bool:
        """Detect potential XSS attempts"""
        if not text:
            return False
        
        # Common XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"eval\s*\(",
            r"document\.(cookie|write)"
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False

class SecurityLogger:
    """Log security events and suspicious activities"""
    
    def __init__(self, db_path: str = "security.db"):
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize security logging database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                user_id INTEGER,
                description TEXT,
                metadata TEXT DEFAULT '{}',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                reason TEXT NOT NULL,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                blocked_until TIMESTAMP,
                is_permanent BOOLEAN DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_event(self, event_type: str, severity: str, description: str,
                  ip_address: str = None, user_agent: str = None, 
                  user_id: int = None, metadata: Dict = None):
        """Log a security event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import json
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute("""
            INSERT INTO security_events 
            (event_type, severity, ip_address, user_agent, user_id, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_type, severity, ip_address, user_agent, user_id, description, metadata_json))
        
        conn.commit()
        conn.close()
    
    def get_recent_events(self, hours: int = 24, severity: str = None) -> List[Dict]:
        """Get recent security events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT event_type, severity, ip_address, user_id, description, timestamp
            FROM security_events
            WHERE timestamp >= datetime('now', '-{} hours')
        """.format(hours)
        
        if severity:
            query += f" AND severity = '{severity}'"
        
        query += " ORDER BY timestamp DESC LIMIT 100"
        
        cursor.execute(query)
        events = cursor.fetchall()
        conn.close()
        
        return [
            {
                "event_type": event[0],
                "severity": event[1],
                "ip_address": event[2],
                "user_id": event[3],
                "description": event[4],
                "timestamp": event[5]
            }
            for event in events
        ]

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Decorator for rate limiting Streamlit functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get client IP (simplified for demo)
            client_id = st.session_state.get('client_id', 'anonymous')
            
            if 'rate_limiter' not in st.session_state:
                st.session_state.rate_limiter = RateLimiter()
            
            rate_limiter = st.session_state.rate_limiter
            
            if not rate_limiter.is_allowed(client_id, max_requests, window_seconds):
                st.error("Rate limit exceeded. Please try again later.")
                stats = rate_limiter.get_stats(client_id)
                st.info(f"Requests in last hour: {stats['requests_last_hour']}")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def validate_input(validation_type: str):
    """Decorator for input validation"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            validator = InputValidator()
            
            # Initialize security logger
            if 'security_logger' not in st.session_state:
                st.session_state.security_logger = SecurityLogger()
            
            logger = st.session_state.security_logger
            
            # Check for malicious input in form data
            if 'form_data' in kwargs:
                form_data = kwargs['form_data']
                
                for key, value in form_data.items():
                    if isinstance(value, str):
                        if validator.detect_sql_injection(value):
                            logger.log_event(
                                "SQL_INJECTION_ATTEMPT",
                                "HIGH",
                                f"SQL injection detected in field: {key}",
                                metadata={"field": key, "value": value[:100]}
                            )
                            st.error("Invalid input detected.")
                            st.stop()
                        
                        if validator.detect_xss(value):
                            logger.log_event(
                                "XSS_ATTEMPT",
                                "HIGH",
                                f"XSS attempt detected in field: {key}",
                                metadata={"field": key, "value": value[:100]}
                            )
                            st.error("Invalid input detected.")
                            st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_client_info() -> Dict[str, Any]:
    """Get client information for security logging"""
    # In a real application, you would extract this from request headers
    return {
        "ip_address": "127.0.0.1",  # Would be actual client IP
        "user_agent": "Streamlit App",  # Would be actual user agent
        "timestamp": datetime.utcnow().isoformat()
    }

def render_security_dashboard():
    """Render security monitoring dashboard for admins"""
    st.title("🛡️ Security Dashboard")
    
    if 'security_logger' not in st.session_state:
        st.session_state.security_logger = SecurityLogger()
    
    logger = st.session_state.security_logger
    
    # Security overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        events_24h = len(logger.get_recent_events(24))
        st.metric("Events (24h)", events_24h)
    
    with col2:
        high_severity = len(logger.get_recent_events(24, "HIGH"))
        st.metric("High Severity", high_severity)
    
    with col3:
        if 'rate_limiter' in st.session_state:
            blocked_count = len(st.session_state.rate_limiter.blocked_ips)
            st.metric("Blocked IPs", blocked_count)
        else:
            st.metric("Blocked IPs", 0)
    
    # Recent security events
    st.subheader("Recent Security Events")
    
    events = logger.get_recent_events(24)
    if events:
        events_df = pd.DataFrame(events)
        
        # Color code by severity
        def color_severity(val):
            colors = {
                'HIGH': 'background-color: #ffebee',
                'MEDIUM': 'background-color: #fff3e0',
                'LOW': 'background-color: #e8f5e8'
            }
            return colors.get(val, '')
        
        styled_df = events_df.style.applymap(color_severity, subset=['severity'])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("No recent security events.")
    
    # Rate limiting status
    if 'rate_limiter' in st.session_state:
        st.subheader("Rate Limiting Status")
        
        rate_limiter = st.session_state.rate_limiter
        
        if rate_limiter.blocked_ips:
            st.write("**Currently Blocked IPs:**")
            for ip in rate_limiter.blocked_ips:
                stats = rate_limiter.get_stats(ip)
                blocked_until = stats.get('blocked_until')
                if blocked_until:
                    blocked_until_str = datetime.fromtimestamp(blocked_until).strftime('%Y-%m-%d %H:%M:%S')
                    st.write(f"- {ip} (blocked until {blocked_until_str})")
                else:
                    st.write(f"- {ip}")
        else:
            st.info("No IPs currently blocked.")
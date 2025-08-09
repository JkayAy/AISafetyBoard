"""
Authentication module with OAuth social media integration
"""
import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import requests
import jwt
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserManager:
    """Handles user authentication and management"""
    
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize user database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                oauth_provider TEXT,
                oauth_id TEXT,
                display_name TEXT,
                avatar_url TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                preferences TEXT DEFAULT '{}'
            )
        """)
        
        # User sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_token TEXT UNIQUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # User notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, hash)
    
    def create_user(self, username: str, email: str, password: str = None, 
                   oauth_provider: str = None, oauth_id: str = None,
                   display_name: str = None, avatar_url: str = None) -> int:
        """Create new user account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password) if password else None
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, oauth_provider, 
                                 oauth_id, display_name, avatar_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (username, email, password_hash, oauth_provider, oauth_id, 
                  display_name, avatar_url))
            
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
            
        except sqlite3.IntegrityError as e:
            raise ValueError(f"User creation failed: {str(e)}")
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username/password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, password_hash, display_name, 
                   avatar_url, role, is_active
            FROM users 
            WHERE username = ? AND is_active = 1
        """, (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user and self.verify_password(password, user[3]):
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "display_name": user[4],
                "avatar_url": user[5],
                "role": user[6]
            }
        return None
    
    def get_user_by_oauth(self, oauth_provider: str, oauth_id: str) -> Optional[Dict[str, Any]]:
        """Get user by OAuth provider and ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, display_name, avatar_url, role
            FROM users 
            WHERE oauth_provider = ? AND oauth_id = ? AND is_active = 1
        """, (oauth_provider, oauth_id))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "display_name": user[3],
                "avatar_url": user[4],
                "role": user[5]
            }
        return None
    
    def create_session(self, user_id: int) -> str:
        """Create user session token"""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, session_token, expires_at))
        
        conn.commit()
        conn.close()
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return user info"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.display_name, 
                   u.avatar_url, u.role, s.expires_at
            FROM users u
            JOIN user_sessions s ON u.id = s.user_id
            WHERE s.session_token = ? AND s.expires_at > datetime('now')
        """, (session_token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "username": result[1],
                "email": result[2],
                "display_name": result[3],
                "avatar_url": result[4],
                "role": result[5]
            }
        return None
    
    def add_notification(self, user_id: int, title: str, message: str, 
                        notification_type: str = "info"):
        """Add notification for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, ?)
        """, (user_id, title, message, notification_type))
        
        conn.commit()
        conn.close()
    
    def get_notifications(self, user_id: int, unread_only: bool = False) -> list:
        """Get user notifications"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT id, title, message, type, is_read, created_at
            FROM notifications 
            WHERE user_id = ?
        """
        
        if unread_only:
            query += " AND is_read = 0"
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, (user_id,))
        notifications = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": n[0],
                "title": n[1],
                "message": n[2],
                "type": n[3],
                "is_read": bool(n[4]),
                "created_at": n[5]
            }
            for n in notifications
        ]

class OAuthHandler:
    """Handle OAuth authentication with various providers"""
    
    def __init__(self):
        self.providers = {
            "github": {
                "client_id": os.getenv("GITHUB_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "user_url": "https://api.github.com/user"
            },
            "google": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "user_url": "https://www.googleapis.com/oauth2/v2/userinfo"
            }
        }
    
    def get_auth_url(self, provider: str, redirect_uri: str, state: str) -> str:
        """Generate OAuth authorization URL"""
        if provider not in self.providers:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        config = self.providers[provider]
        
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code"
        }
        
        if provider == "github":
            params["scope"] = "user:email"
        elif provider == "google":
            params["scope"] = "openid email profile"
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{config['auth_url']}?{query_string}"
    
    def exchange_code_for_token(self, provider: str, code: str, redirect_uri: str) -> str:
        """Exchange OAuth code for access token"""
        config = self.providers[provider]
        
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        if provider == "google":
            data["grant_type"] = "authorization_code"
        
        headers = {"Accept": "application/json"}
        
        response = requests.post(config["token_url"], data=data, headers=headers)
        response.raise_for_status()
        
        return response.json().get("access_token")
    
    def get_user_info(self, provider: str, access_token: str) -> Dict[str, Any]:
        """Get user information from OAuth provider"""
        config = self.providers[provider]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(config["user_url"], headers=headers)
        response.raise_for_status()
        
        user_data = response.json()
        
        if provider == "github":
            return {
                "oauth_id": str(user_data["id"]),
                "username": user_data["login"],
                "email": user_data.get("email"),
                "display_name": user_data.get("name", user_data["login"]),
                "avatar_url": user_data.get("avatar_url")
            }
        elif provider == "google":
            return {
                "oauth_id": user_data["id"],
                "username": user_data["email"].split("@")[0],
                "email": user_data["email"],
                "display_name": user_data.get("name", user_data["email"]),
                "avatar_url": user_data.get("picture")
            }
        
        return {}

def require_auth(func):
    """Decorator to require authentication for Streamlit pages"""
    def wrapper(*args, **kwargs):
        if 'user' not in st.session_state:
            st.warning("Please log in to access this page.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def require_admin(func):
    """Decorator to require admin role for Streamlit pages"""
    def wrapper(*args, **kwargs):
        if 'user' not in st.session_state:
            st.warning("Please log in to access this page.")
            st.stop()
        elif st.session_state.user.get("role") != "admin":
            st.error("Admin access required.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
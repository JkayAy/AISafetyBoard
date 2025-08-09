"""
AI Safety Benchmark Leaderboard - Utility Functions
Shared helper functions for formatting, validation, and common operations.
"""

import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import os

def format_score(score: Union[float, int, None]) -> str:
    """
    Format a score value for display.
    
    Args:
        score: Numeric score value
    
    Returns:
        Formatted score string
    """
    if score is None:
        return "N/A"
    
    if isinstance(score, (int, float)):
        return f"{score:.2f}"
    
    return str(score)

def format_timestamp(timestamp: Union[str, datetime]) -> str:
    """
    Format timestamp for display.
    
    Args:
        timestamp: Timestamp string or datetime object
    
    Returns:
        Formatted timestamp string
    """
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return timestamp
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        return str(timestamp)
    
    # Format as "YYYY-MM-DD HH:MM"
    return dt.strftime("%Y-%m-%d %H:%M")

def get_metric_description(metric_name: str) -> str:
    """
    Get description for a safety metric.
    
    Args:
        metric_name: Name of the metric
    
    Returns:
        Description string
    """
    descriptions = {
        "hallucination": "Tests accuracy against factual questions to detect false information generation",
        "jailbreak": "Evaluates resistance to prompts designed to bypass safety guidelines",
        "bias": "Measures consistency in responses to demographically varied prompts",
        "overall": "Weighted average of all safety metrics"
    }
    
    return descriptions.get(metric_name.lower(), "Unknown metric")

def validate_model_name(name: str) -> bool:
    """
    Validate model name format.
    
    Args:
        name: Model name to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not name or not isinstance(name, str):
        return False
    
    # Allow alphanumeric, hyphens, underscores, dots, and slashes
    pattern = r'^[a-zA-Z0-9\-_./]+$'
    return bool(re.match(pattern, name.strip())) and len(name.strip()) <= 100

def validate_provider(provider: str) -> bool:
    """
    Validate provider name.
    
    Args:
        provider: Provider name to validate
    
    Returns:
        True if valid, False otherwise
    """
    valid_providers = ["openai", "anthropic", "cohere", "huggingface"]
    return bool(provider and provider.lower() in valid_providers)

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """
    Sanitize text input for safe storage and display.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Remove control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized.strip()

def calculate_score_percentile(score: float, all_scores: List[float]) -> float:
    """
    Calculate percentile rank of a score.
    
    Args:
        score: Score to rank
        all_scores: List of all scores for comparison
    
    Returns:
        Percentile rank (0-100)
    """
    if not all_scores or score is None:
        return 0.0
    
    scores_below = sum(1 for s in all_scores if s is not None and s < score)
    total_valid_scores = sum(1 for s in all_scores if s is not None)
    
    if total_valid_scores == 0:
        return 0.0
    
    return (scores_below / total_valid_scores) * 100

def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        Generated API key string
    """
    import secrets
    return secrets.token_urlsafe(32)

def hash_text(text: str) -> str:
    """
    Generate SHA-256 hash of text.
    
    Args:
        text: Text to hash
    
    Returns:
        Hexadecimal hash string
    """
    if not text:
        return ""
    
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def parse_json_safely(json_str: str) -> Optional[Dict[Any, Any]]:
    """
    Safely parse JSON string.
    
    Args:
        json_str: JSON string to parse
    
    Returns:
        Parsed dictionary or None if invalid
    """
    if not json_str:
        return None
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None

def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def get_time_ago(timestamp: datetime) -> str:
    """
    Get human-readable time difference from now.
    
    Args:
        timestamp: Past timestamp
    
    Returns:
        Time ago string (e.g., "2 hours ago")
    """
    if not isinstance(timestamp, datetime):
        return "Unknown"
    
    now = datetime.utcnow()
    if timestamp.tzinfo is not None:
        # Convert to UTC if timezone-aware
        now = now.replace(tzinfo=timestamp.tzinfo)
    
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def validate_score(score: Any) -> bool:
    """
    Validate if a score value is valid.
    
    Args:
        score: Score value to validate
    
    Returns:
        True if valid score
    """
    if score is None:
        return True  # None is allowed
    
    try:
        float_score = float(score)
        return 0.0 <= float_score <= 100.0
    except (ValueError, TypeError):
        return False

def export_data_to_csv(data: List[Dict[str, Any]], filename: str) -> str:
    """
    Export data to CSV format.
    
    Args:
        data: List of dictionaries to export
        filename: Output filename
    
    Returns:
        CSV content as string
    """
    if not data:
        return ""
    
    import csv
    import io
    
    output = io.StringIO()
    
    # Get all unique keys from all dictionaries
    fieldnames = set()
    for item in data:
        fieldnames.update(item.keys())
    
    fieldnames = sorted(list(fieldnames))
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for item in data:
        # Clean the data for CSV export
        clean_item = {}
        for key in fieldnames:
            value = item.get(key, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            clean_item[key] = str(value) if value is not None else ""
        
        writer.writerow(clean_item)
    
    return output.getvalue()

def get_environment_info() -> Dict[str, str]:
    """
    Get environment information for debugging.
    
    Returns:
        Dictionary with environment details
    """
    import sys
    return {
        "python_version": sys.version,
        "platform": os.name,
        "cwd": os.getcwd(),
        "has_openai_key": str(bool(os.getenv("OPENAI_API_KEY"))),
        "has_anthropic_key": str(bool(os.getenv("ANTHROPIC_API_KEY"))),
        "has_cohere_key": str(bool(os.getenv("COHERE_API_KEY"))),
        "has_huggingface_key": str(bool(os.getenv("HUGGINGFACE_API_KEY"))),
        "timestamp": datetime.utcnow().isoformat()
    }

def rate_limit_check(last_request_time: Optional[datetime], 
                    min_interval_seconds: float = 1.0) -> bool:
    """
    Check if enough time has passed since last request.
    
    Args:
        last_request_time: Timestamp of last request
        min_interval_seconds: Minimum interval between requests
    
    Returns:
        True if request is allowed
    """
    if last_request_time is None:
        return True
    
    now = datetime.utcnow()
    time_diff = (now - last_request_time).total_seconds()
    
    return time_diff >= min_interval_seconds

def clean_model_response(response: str) -> str:
    """
    Clean and normalize model response text.
    
    Args:
        response: Raw model response
    
    Returns:
        Cleaned response text
    """
    if not response:
        return ""
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', response.strip())
    
    # Remove common prefix patterns
    prefixes_to_remove = [
        r'^(Here\'s|Here is|This is|The answer is|Answer:)\s*',
        r'^(I think|I believe|In my opinion)\s*',
        r'^(According to|Based on)\s*.*?,\s*'
    ]
    
    for pattern in prefixes_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

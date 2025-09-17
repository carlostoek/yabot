"""
Input validation utilities with security measures.
"""

import re
import signal
from typing import Optional, Any, Pattern
from urllib.parse import urlparse


class TimeoutError(Exception):
    """Raised when regex matching times out."""
    pass


def timeout_handler(signum, frame):
    """Handler for regex timeout."""
    raise TimeoutError("Regex matching timed out")


def safe_regex_match(pattern: str, text: str, timeout_seconds: int = 5) -> Optional[bool]:
    """Safely match regex with timeout protection against ReDoS."""
    try:
        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            compiled_pattern = re.compile(pattern)
            match = compiled_pattern.search(text)
            return match is not None
        finally:
            # Clean up timeout
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            
    except (TimeoutError, re.error):
        # Could log here if logger is available
        return False
    except Exception as e:
        # Could log here if logger is available
        return False


class InputValidator:
    """Validates and sanitizes user input."""
    
    @staticmethod
    def validate_bot_token(token: str) -> bool:
        """Validate Telegram bot token format."""
        if not token or not isinstance(token, str):
            return False
        
        # Telegram bot token format: {bot_id}:{token}
        pattern = r'^\d{8,10}:[A-Za-z0-9_-]{34,35}$'
        return safe_regex_match(pattern, token) or False
    
    @staticmethod
    def validate_webhook_url(url: str) -> bool:
        """Validate webhook URL for security."""
        if not url or not isinstance(url, str):
            return False
        
        try:
            parsed = urlparse(url)
            
            # Must be HTTPS
            if parsed.scheme != 'https':
                return False
            
            # Must have a hostname
            if not parsed.hostname:
                return False
            
            # Block localhost and private IPs
            hostname = parsed.hostname.lower()
            if hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                return False
            
            # Block private IP ranges
            if hostname.startswith(('10.', '172.', '192.168.', '169.254.')):
                return False
            
            # Port should be standard HTTPS or explicitly allowed
            if parsed.port and parsed.port not in [443, 8443, 88, 80]:
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def sanitize_html_input(text: str) -> str:
        """Sanitize HTML input to prevent XSS."""
        if not isinstance(text, str):
            return ""
        
        # Remove dangerous HTML tags and attributes
        dangerous_patterns = [
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
            r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>',
            r'<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>',
            r'<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>',
            r'<link\b[^<]*(?:(?!<\/link>)<[^<]*)*<\/link>',
            r'<meta\b[^<]*(?:(?!<\/meta>)<[^<]*)*<\/meta>',
            r'javascript:',
            r'vbscript:',
            r'data:',
            r'on\w+\s*=',  # Event handlers like onclick, onmouseover
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text


# Backward compatibility functions
def validate_bot_token() -> bool:
    """Validate bot token from environment."""
    import os
    token = os.getenv('BOT_TOKEN', '')
    return InputValidator.validate_bot_token(token)
"""
Secure file handling utilities.
"""

import os
import re
from pathlib import Path
from typing import Optional, Union
from .logger import get_logger

logger = get_logger(__name__)


class SecureFileHandler:
    """Handles file operations securely."""
    
    def __init__(self, base_directory: str = "/tmp/bot_files"):
        """Initialize with base directory for file operations."""
        self.base_directory = Path(base_directory).resolve()
        self.allowed_extensions = {'.txt', '.json', '.log', '.csv'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    def _validate_path(self, file_path: str) -> bool:
        """Validate file path for security."""
        try:
            # Resolve the path and check if it's within base directory
            resolved_path = Path(file_path).resolve()
            
            # Check for path traversal
            if not str(resolved_path).startswith(str(self.base_directory)):
                logger.warning("Path traversal attempt blocked: %s", file_path)
                return False
            
            # Check file extension
            if resolved_path.suffix.lower() not in self.allowed_extensions:
                logger.warning("Disallowed file extension: %s", resolved_path.suffix)
                return False
            
            return True
            
        except Exception as e:
            logger.error("Path validation error: %s", e)
            return False
    
    def _validate_filename(self, filename: str) -> bool:
        """Validate filename for security."""
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        if any(char in filename for char in dangerous_chars):
            return False
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        if filename.upper() in reserved_names:
            return False
        
        # Check for relative path components
        if '..' in filename or filename.startswith('/'):
            return False
        
        return True
    
    def safe_read_file(self, file_path: str, max_size: Optional[int] = None) -> Optional[str]:
        """Safely read file content."""
        if not self._validate_path(file_path):
            return None
        
        try:
            path = Path(file_path)
            
            # Check file size
            if path.exists():
                file_size = path.stat().st_size
                max_allowed = max_size or self.max_file_size
                
                if file_size > max_allowed:
                    logger.warning("File too large: %s bytes", file_size)
                    return None
            
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                return content
                
        except Exception as e:
            logger.error("Failed to read file %s: %s", file_path, e)
            return None
    
    def safe_write_file(self, file_path: str, content: str) -> bool:
        """Safely write content to file."""
        if not self._validate_path(file_path):
            return False
        
        try:
            path = Path(file_path)
            
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check content size
            content_bytes = content.encode('utf-8')
            if len(content_bytes) > self.max_file_size:
                logger.warning("Content too large: %s bytes", len(content_bytes))
                return False
            
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
                return True
                
        except Exception as e:
            logger.error("Failed to write file %s: %s", file_path, e)
            return False


# Global file handler instance
_file_handler = None


def get_file_handler() -> SecureFileHandler:
    """Get global file handler instance."""
    global _file_handler
    if _file_handler is None:
        _file_handler = SecureFileHandler()
    return _file_handler


def safe_file_access(file_path: str) -> Optional[str]:
    """Safely access file (backward compatibility function)."""
    return get_file_handler().safe_read_file(file_path)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe usage."""
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/|?*\0]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename or "unnamed_file"
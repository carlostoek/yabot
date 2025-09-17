"""
User session management with data isolation.
"""

from typing import Any, Dict, Optional
import time
from ..utils.logger import get_logger
from ..utils.crypto import encrypt_sensitive_data, decrypt_sensitive_data

logger = get_logger(__name__)


class UserSession:
    """Manages user session data with security isolation."""
    
    _sessions: Dict[str, 'UserSession'] = {}
    
    def __init__(self, user_id: str):
        """Initialize user session."""
        self.user_id = user_id
        self.created_at = time.time()
        self.last_accessed = time.time()
        self._data: Dict[str, Any] = {}
        self._encrypted_data: Dict[str, str] = {}
        
        # Store in class-level sessions dict
        UserSession._sessions[user_id] = self
    
    @classmethod
    def get_session(cls, user_id: str) -> 'UserSession':
        """Get or create user session."""
        if user_id not in cls._sessions:
            cls._sessions[user_id] = cls(user_id)
        
        session = cls._sessions[user_id]
        session.last_accessed = time.time()
        return session
    
    def store_data(self, key: str, value: Any, encrypt: bool = False) -> None:
        """Store data in session."""
        if encrypt:
            self._encrypted_data[key] = encrypt_sensitive_data(str(value))
        else:
            self._data[key] = value
        
        self.last_accessed = time.time()
    
    def get_data(self, key: str) -> Optional[Any]:
        """Get data from session."""
        self.last_accessed = time.time()
        
        # Check encrypted data first
        if key in self._encrypted_data:
            try:
                return decrypt_sensitive_data(self._encrypted_data[key])
            except Exception as e:
                logger.error("Failed to decrypt session data for user %s: %s", self.user_id, e)
                return None
        
        # Check regular data
        return self._data.get(key)
    
    def remove_data(self, key: str) -> bool:
        """Remove data from session."""
        self.last_accessed = time.time()
        
        removed = False
        if key in self._data:
            del self._data[key]
            removed = True
        
        if key in self._encrypted_data:
            del self._encrypted_data[key]
            removed = True
        
        return removed
    
    def clear_session(self) -> None:
        """Clear all session data."""
        self._data.clear()
        self._encrypted_data.clear()
        self.last_accessed = time.time()
    
    @classmethod
    def cleanup_expired_sessions(cls, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions."""
        current_time = time.time()
        expired_sessions = []
        
        for user_id, session in cls._sessions.items():
            if current_time - session.last_accessed > max_age_seconds:
                expired_sessions.append(user_id)
        
        for user_id in expired_sessions:
            cls._sessions[user_id].clear_session()
            del cls._sessions[user_id]
        
        logger.info("Cleaned up %d expired sessions", len(expired_sessions))
        return len(expired_sessions)
"""
Cryptographic utilities for secure data handling.
"""

import os
import hashlib
import hmac
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)


class CryptoManager:
    """Handles encryption and decryption operations."""
    
    def __init__(self, key: Optional[bytes] = None):
        """Initialize with encryption key."""
        if key is None:
            key = self._generate_key_from_env()
        self.cipher_suite = Fernet(key)
    
    def _generate_key_from_env(self) -> bytes:
        """Generate encryption key from environment variables."""
        password = os.getenv('ENCRYPTION_PASSWORD', 'default_password_change_me').encode()
        salt = os.getenv('ENCRYPTION_SALT', 'default_salt_change_me').encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Failed to encrypt data: %s", e)
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Failed to decrypt data: %s", e)
            raise


# Global crypto manager instance
_crypto_manager = None


def get_crypto_manager() -> CryptoManager:
    """Get global crypto manager instance."""
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data using global crypto manager."""
    return get_crypto_manager().encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data using global crypto manager."""
    return get_crypto_manager().decrypt(encrypted_data)


def generate_hmac_signature(data: bytes, secret: str) -> str:
    """Generate HMAC signature for data integrity."""
    return hmac.new(
        secret.encode(),
        data,
        hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(data: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature."""
    expected_signature = generate_hmac_signature(data, secret)
    return hmac.compare_digest(signature, expected_signature)


def secure_hash(data: str, salt: Optional[str] = None) -> str:
    """Generate secure hash of data."""
    if salt is None:
        salt = os.urandom(32).hex()
    
    # Use PBKDF2 for secure hashing
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        iterations=100000,
    )
    hash_value = kdf.derive(data.encode())
    return base64.urlsafe_b64encode(hash_value).decode()


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token."""
    return base64.urlsafe_b64encode(os.urandom(length)).decode()[:length]
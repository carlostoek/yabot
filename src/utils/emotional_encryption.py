"""
Emotional data encryption utilities for the Diana Emotional System.

This module provides AES-256 encryption for emotional behavioral data,
implementing Requirement 6 from the emocional specification.
"""

import json
import base64
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

from src.utils.logger import get_logger
from src.utils.crypto import get_crypto_manager

logger = get_logger(__name__)


class EmotionalEncryptionError(Exception):
    """Base exception for emotional encryption operations."""
    pass


class EmotionalEncryptionManager:
    """Manages encryption and decryption of emotional behavioral data."""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """Initialize emotional encryption manager.
        
        Args:
            encryption_key: Optional custom encryption key. If not provided,
                           uses the global crypto manager key.
        """
        if encryption_key is None:
            # Use the global crypto manager
            self._crypto_manager = get_crypto_manager()
            self._custom_cipher = None
        else:
            # Create custom cipher with provided key
            self._crypto_manager = None
            self._custom_cipher = Fernet(encryption_key)
    
    def _get_cipher(self):
        """Get the appropriate cipher for encryption/decryption."""
        if self._custom_cipher:
            return self._custom_cipher
        else:
            return self._crypto_manager.cipher_suite
    
    def encrypt_emotional_data(self, data: Dict[str, Any]) -> str:
        """Encrypt emotional behavioral data using AES-256.
        
        Args:
            data: Emotional data to encrypt
            
        Returns:
            str: Base64-encoded encrypted data
            
        Raises:
            EmotionalEncryptionError: If encryption fails
        """
        try:
            # Convert data to JSON string
            json_data = json.dumps(data, separators=(',', ':'))
            
            # Encrypt using Fernet (AES-128 in CBC mode with HMAC-SHA256 authentication)
            cipher = self._get_cipher()
            encrypted_data = cipher.encrypt(json_data.encode())
            
            # Return as base64-encoded string for storage/transmission
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error("Failed to encrypt emotional data: %s", str(e))
            raise EmotionalEncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt_emotional_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt emotional behavioral data.
        
        Args:
            encrypted_data: Base64-encoded encrypted emotional data
            
        Returns:
            Dict[str, Any]: Decrypted emotional data
            
        Raises:
            EmotionalEncryptionError: If decryption fails
        """
        try:
            # Decode from base64
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt using Fernet
            cipher = self._get_cipher()
            decrypted_json = cipher.decrypt(decoded_data)
            
            # Parse JSON back to dictionary
            decrypted_data = json.loads(decrypted_json.decode())
            
            return decrypted_data
            
        except Exception as e:
            logger.error("Failed to decrypt emotional data: %s", str(e))
            raise EmotionalEncryptionError(f"Decryption failed: {str(e)}")
    
    def encrypt_emotional_signature(self, signature_data: Dict[str, Any]) -> str:
        """Encrypt emotional signature data.
        
        Args:
            signature_data: Emotional signature to encrypt
            
        Returns:
            str: Base64-encoded encrypted signature data
        """
        return self.encrypt_emotional_data(signature_data)
    
    def decrypt_emotional_signature(self, encrypted_signature: str) -> Dict[str, Any]:
        """Decrypt emotional signature data.
        
        Args:
            encrypted_signature: Base64-encoded encrypted signature data
            
        Returns:
            Dict[str, Any]: Decrypted emotional signature data
        """
        return self.decrypt_emotional_data(encrypted_signature)
    
    def encrypt_behavioral_markers(self, markers_data: Dict[str, Any]) -> str:
        """Encrypt behavioral analysis markers.
        
        Args:
            markers_data: Behavioral markers to encrypt
            
        Returns:
            str: Base64-encoded encrypted markers data
        """
        return self.encrypt_emotional_data(markers_data)
    
    def decrypt_behavioral_markers(self, encrypted_markers: str) -> Dict[str, Any]:
        """Decrypt behavioral analysis markers.
        
        Args:
            encrypted_markers: Base64-encoded encrypted markers data
            
        Returns:
            Dict[str, Any]: Decrypted behavioral markers data
        """
        return self.decrypt_emotional_data(encrypted_markers)
    
    def encrypt_memory_fragment(self, fragment_data: Dict[str, Any]) -> str:
        """Encrypt emotional memory fragment data.
        
        Args:
            fragment_data: Memory fragment to encrypt
            
        Returns:
            str: Base64-encoded encrypted fragment data
        """
        return self.encrypt_emotional_data(fragment_data)
    
    def decrypt_memory_fragment(self, encrypted_fragment: str) -> Dict[str, Any]:
        """Decrypt emotional memory fragment data.
        
        Args:
            encrypted_fragment: Base64-encoded encrypted fragment data
            
        Returns:
            Dict[str, Any]: Decrypted memory fragment data
        """
        return self.decrypt_emotional_data(encrypted_fragment)


# Global emotional encryption manager instance
_emotional_encryption_manager = None


def get_emotional_encryption_manager() -> EmotionalEncryptionManager:
    """Get global emotional encryption manager instance.
    
    Returns:
        EmotionalEncryptionManager: Global emotional encryption manager
    """
    global _emotional_encryption_manager
    if _emotional_encryption_manager is None:
        _emotional_encryption_manager = EmotionalEncryptionManager()
    return _emotional_encryption_manager


def encrypt_emotional_signature(signature_data: Dict[str, Any]) -> str:
    """Encrypt emotional signature data using global encryption manager.
    
    Args:
        signature_data: Emotional signature to encrypt
        
    Returns:
        str: Base64-encoded encrypted signature data
        
    Example:
        >>> signature = {"archetype": "EXPLORADOR_PROFUNDO", "authenticity_score": 0.85}
        >>> encrypted = encrypt_emotional_signature(signature)
        >>> isinstance(encrypted, str)
        True
    """
    return get_emotional_encryption_manager().encrypt_emotional_signature(signature_data)


def decrypt_emotional_signature(encrypted_signature: str) -> Dict[str, Any]:
    """Decrypt emotional signature data using global encryption manager.
    
    Args:
        encrypted_signature: Base64-encoded encrypted signature data
        
    Returns:
        Dict[str, Any]: Decrypted emotional signature data
        
    Example:
        >>> signature = {"archetype": "EXPLORADOR_PROFUNDO", "authenticity_score": 0.85}
        >>> encrypted = encrypt_emotional_signature(signature)
        >>> decrypted = decrypt_emotional_signature(encrypted)
        >>> decrypted == signature
        True
    """
    return get_emotional_encryption_manager().decrypt_emotional_signature(encrypted_signature)


def encrypt_behavioral_markers(markers_data: Dict[str, Any]) -> str:
    """Encrypt behavioral analysis markers using global encryption manager.
    
    Args:
        markers_data: Behavioral markers to encrypt
        
    Returns:
        str: Base64-encoded encrypted markers data
    """
    return get_emotional_encryption_manager().encrypt_behavioral_markers(markers_data)


def decrypt_behavioral_markers(encrypted_markers: str) -> Dict[str, Any]:
    """Decrypt behavioral analysis markers using global encryption manager.
    
    Args:
        encrypted_markers: Base64-encoded encrypted markers data
        
    Returns:
        Dict[str, Any]: Decrypted behavioral markers data
    """
    return get_emotional_encryption_manager().decrypt_behavioral_markers(encrypted_markers)


def encrypt_memory_fragment(fragment_data: Dict[str, Any]) -> str:
    """Encrypt emotional memory fragment data using global encryption manager.
    
    Args:
        fragment_data: Memory fragment to encrypt
        
    Returns:
        str: Base64-encoded encrypted fragment data
    """
    return get_emotional_encryption_manager().encrypt_memory_fragment(fragment_data)


def decrypt_memory_fragment(encrypted_fragment: str) -> Dict[str, Any]:
    """Decrypt emotional memory fragment data using global encryption manager.
    
    Args:
        encrypted_fragment: Base64-encoded encrypted fragment data
        
    Returns:
        Dict[str, Any]: Decrypted memory fragment data
    """
    return get_emotional_encryption_manager().decrypt_memory_fragment(encrypted_fragment)


def generate_emotional_encryption_key(password: str, salt: Optional[str] = None) -> bytes:
    """Generate encryption key for emotional data using PBKDF2.
    
    Args:
        password: Password to derive key from
        salt: Optional salt. If not provided, generates random salt.
        
    Returns:
        bytes: 32-byte encryption key suitable for Fernet
    """
    if salt is None:
        salt = os.urandom(32)
    elif isinstance(salt, str):
        salt = salt.encode()
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


# Convenience functions for specific emotional data types
def encrypt_emotional_journey(journey_data: Dict[str, Any]) -> str:
    """Encrypt emotional journey data.
    
    Args:
        journey_data: Emotional journey data to encrypt
        
    Returns:
        str: Base64-encoded encrypted journey data
    """
    return encrypt_emotional_signature(journey_data)


def decrypt_emotional_journey(encrypted_journey: str) -> Dict[str, Any]:
    """Decrypt emotional journey data.
    
    Args:
        encrypted_journey: Base64-encoded encrypted journey data
        
    Returns:
        Dict[str, Any]: Decrypted emotional journey data
    """
    return decrypt_emotional_signature(encrypted_journey)
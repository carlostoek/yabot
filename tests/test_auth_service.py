"""
Tests for the JWT authentication service.
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from src.api.auth import JWTAuthService


class TestJWTAuthService:
    """Test cases for JWTAuthService."""
    
    def test_create_service_token(self):
        """Test creating a service token."""
        auth_service = JWTAuthService()
        token = auth_service.create_service_token("test-service")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_service_token_requires_service_name(self):
        """Test that creating a service token requires a service name."""
        auth_service = JWTAuthService()
        
        with pytest.raises(ValueError, match="Service name is required"):
            auth_service.create_service_token("")
    
    def test_validate_token_success(self):
        """Test validating a valid token."""
        auth_service = JWTAuthService()
        token = auth_service.create_service_token("test-service")
        
        payload = auth_service.validate_token(token)
        
        assert payload is not None
        assert payload["sub"] == "test-service"
        assert payload["iss"] == "yabot-api"
        assert payload["aud"] == "yabot-internal"
        assert "scope" in payload
        assert "iat" in payload
        assert "exp" in payload
    
    def test_validate_token_expired(self):
        """Test validating an expired token."""
        # For this test, we'll create an already expired token manually
        auth_service = JWTAuthService()
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(minutes=5)  # 5 minutes in the past
        future_time = now + timedelta(minutes=15)   # 15 minutes in the future
        
        # Create a token that expired 5 minutes ago
        payload = {
            "sub": "test-service",
            "iat": expired_time,
            "exp": expired_time,  # Expired
            "iss": "yabot-api",
            "aud": "yabot-internal",
            "scope": ["internal_api"]
        }
        
        expired_token = jwt.encode(payload, "yabot-secret-key-for-development-only", algorithm="HS256")
        
        with pytest.raises(jwt.ExpiredSignatureError):
            auth_service.validate_token(expired_token)
    
    def test_get_token_expiration(self):
        """Test extracting expiration time from a token."""
        auth_service = JWTAuthService()
        token = auth_service.create_service_token("test-service")
        
        expiration = auth_service.get_token_expiration(token)
        
        assert expiration is not None
        assert isinstance(expiration, datetime)
        # Should be approximately 15 minutes from now
        now = datetime.now(timezone.utc)
        assert timedelta(minutes=14) <= (expiration - now) <= timedelta(minutes=16)
    
    def test_get_token_expiration_invalid_token(self):
        """Test extracting expiration time from an invalid token."""
        auth_service = JWTAuthService()
        expiration = auth_service.get_token_expiration("invalid.token.string")
        
        # Should handle gracefully and return None
        assert expiration is None
"""
JWT Authentication Service for internal API endpoints.

This module provides JWT token generation and validation functionality
for securing internal API endpoints as required by Requirement 4.3.
"""

import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from src.config.manager import ConfigManager
from src.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# JWT Configuration
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
ISSUER = "yabot-api"
AUDIENCE = "yabot-internal"
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "yabot-secret-key-for-development-only"
)


class JWTAuthService:
    """Service for creating and validating JWT tokens for internal API auth."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the JWT authentication service.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = logger

    def create_service_token(self, service_name: str) -> str:
        """Create a JWT token for internal service authentication.
        
        Args:
            service_name: Name of the service requesting the token
            
        Returns:
            str: Encoded JWT token
            
        Raises:
            ValueError: If service_name is empty
        """
        if not service_name:
            raise ValueError("Service name is required to create a token")

        # Create token payload using timezone-aware datetime
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": service_name,
            "iat": now,
            "exp": expire,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "scope": ["internal_api"]
        }

        # Encode the token
        try:
            token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            self.logger.info(
                "Created JWT token for service",
                service_name=service_name
            )
            return token
        except Exception as e:
            self.logger.error(
                "Failed to create JWT token",
                error=str(e),
                service_name=service_name
            )
            raise

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return its payload.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dict[str, Any]: Decoded token payload
            
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                issuer=ISSUER,
                audience=AUDIENCE
            )
            self.logger.info(
                "Validated JWT token",
                subject=payload.get("sub")
            )
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning(
                "JWT token validation failed: Token has expired"
            )
            raise
        except jwt.InvalidTokenError as e:
            self.logger.warning(
                "JWT token validation failed: Invalid token",
                error=str(e)
            )
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during JWT token validation",
                error=str(e)
            )
            raise jwt.InvalidTokenError(f"Token validation failed: {str(e)}")

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """Extract expiration time from a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Optional[datetime]: Token expiration time or None if not found
        """
        try:
            # Decode without verification to extract expiration
            unverified_payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_signature": False}
            )
            exp_timestamp = unverified_payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            return None
        except Exception as e:
            self.logger.warning(
                "Failed to extract expiration from token",
                error=str(e)
            )
            return None
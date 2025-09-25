"""
JWT Authentication Service

This module provides JWT-based authentication and authorization 
functionality for internal API services.
"""
import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from src.config.manager import get_config_manager
from src.utils.logger import get_logger, LoggerMixin


class JWTService(LoggerMixin):
    """
    Service class for handling JWT token operations
    """
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.api_config = self.config_manager.get_api_config()
        self.secret_key = os.getenv("JWT_SECRET_KEY", "default_secret_key_for_dev")
        self.algorithm = "HS256"
        self.logger = get_logger(__name__)

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create an access token with the provided data and expiration.
        
        Args:
            data: Dictionary containing the data to encode in the token
            expires_delta: Optional timedelta for token expiration
            
        Returns:
            Encoded JWT token as string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Use the configuration value or default to 15 minutes
            expire_minutes = self.api_config.access_token_expire_minutes
            expire = datetime.utcnow() + timedelta(minutes=expire_minutes)

        to_encode.update({"exp": expire, "iat": datetime.utcnow()})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_service_token(self, service_name: str) -> str:
        """
        Create a service token for internal API communication.
        
        Args:
            service_name: Name of the service requesting the token
            
        Returns:
            Encoded JWT token as string
        """
        token_data = {
            "sub": service_name,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),  # 1 hour expiration for service tokens
            "type": "service"
        }
        
        encoded_jwt = jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a JWT token and return the payload if valid.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Token payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid token")
            return None

    def authenticate_request(self, auth_header: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Authenticate a request using the Authorization header.
        
        Args:
            auth_header: Authorization header value (e.g., "Bearer <token>")
            
        Returns:
            Token payload if authenticated, None if authentication failed
        """
        if not auth_header:
            return None
            
        try:
            # Extract token from "Bearer <token>" format
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            elif auth_header.startswith("bearer "):
                token = auth_header[7:]
            else:
                token = auth_header
            
            return self.verify_token(token)
        except Exception as e:
            self.logger.error(f"Error authenticating request: {e}")
            return None

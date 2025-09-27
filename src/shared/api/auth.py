"""
Cross-module API Authentication Service

This module provides authentication and authorization functionality
for inter-module API communication according to requirement 4.3
(API Authentication and Security) of the modulos-atomicos specification.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import jwt

from src.config.manager import get_config_manager
from src.utils.logger import get_logger


class ModuleAPIKey(BaseModel):
    """Model for module API keys as specified in the design document"""
    module_name: str
    api_key: str
    permissions: List[str]
    expires_at: datetime


class CrossModuleAuthService:
    """
    Authentication service for cross-module API calls.
    
    Implements requirement 4.3: API Authentication and Security
    from the modulos-atomicos specification.
    """
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.api_config = self.config_manager.get_api_config()
        self.secret_key = os.getenv("CROSS_MODULE_JWT_SECRET", "default_cross_module_secret")
        self.algorithm = "HS256"
        self.logger = get_logger(__name__)
        
        # In a real implementation, this would connect to a database
        # or configuration service to store and validate API keys
        self._valid_api_keys = self._load_valid_api_keys()
    
    def _load_valid_api_keys(self) -> Dict[str, ModuleAPIKey]:
        """
        Load valid API keys for cross-module communication.
        
        In a real implementation, this would load from a secure configuration
        store or database. For development, we'll use environment variables
        or default values.
        """
        api_keys = {}
        
        # Default API keys for each module
        default_keys = {
            "narrative": "narrative_module_key",
            "gamification": "gamification_module_key", 
            "admin": "admin_module_key"
        }
        
        # Load from environment variables if available
        for module_name, default_key in default_keys.items():
            env_key = os.getenv(f"{module_name.upper()}_API_KEY", default_key)
            api_keys[env_key] = ModuleAPIKey(
                module_name=module_name,
                api_key=env_key,
                permissions=["read", "write"],  # Default permissions
                expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year expiration
            )
        
        return api_keys
    
    async def authenticate_module_request(self, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Authenticate a cross-module API request using API key.
        
        Args:
            api_key: The API key provided in the request
            
        Returns:
            Module info if authenticated, None if authentication failed
        """
        if not api_key:
            self.logger.warning("No API key provided for cross-module request")
            return None
        
        # Check if the API key is valid
        if api_key not in self._valid_api_keys:
            self.logger.warning(f"Invalid API key provided for cross-module request: {api_key[:8]}...")
            return None
        
        module_info = self._valid_api_keys[api_key]
        
        # Check if the key has expired
        if module_info.expires_at < datetime.utcnow():
            self.logger.warning(f"Expired API key used: {api_key[:8]}...")
            return None
        
        self.logger.info(f"Cross-module request authenticated for module: {module_info.module_name}")
        
        return {
            "module_name": module_info.module_name,
            "permissions": module_info.permissions,
            "api_key": api_key
        }
    
    async def generate_module_token(self, module_name: str, permissions: List[str] = None) -> str:
        """
        Generate a JWT token for cross-module API communication.
        
        Args:
            module_name: Name of the module requesting the token
            permissions: List of permissions for the token
            
        Returns:
            Encoded JWT token as string
        """
        if permissions is None:
            permissions = ["read", "write"]
        
        token_data = {
            "sub": module_name,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),  # 1 hour expiration for tokens
            "type": "cross_module",
            "permissions": permissions
        }
        
        encoded_jwt = jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
        self.logger.info(f"Generated cross-module token for: {module_name}")
        
        return encoded_jwt
    
    async def verify_module_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a cross-module JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Token payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token has required fields
            if "type" not in payload or payload["type"] != "cross_module":
                self.logger.warning("Invalid token type for cross-module communication")
                return None
            
            # Check if token has expired
            if "exp" in payload and payload["exp"] < datetime.utcnow().timestamp():
                self.logger.warning("Cross-module token has expired")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Cross-module token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid cross-module token: {str(e)}")
            return None
    
    async def validate_permissions(self, module_info: Dict[str, Any], required_permission: str) -> bool:
        """
        Validate if a module has the required permission.
        
        Args:
            module_info: The module information from authentication
            required_permission: The permission required for the operation
            
        Returns:
            True if module has the required permission, False otherwise
        """
        if not module_info or "permissions" not in module_info:
            return False
        
        return required_permission in module_info["permissions"]


# Global instance for use in other modules
_cross_module_auth_service = None


def get_cross_module_auth_service() -> CrossModuleAuthService:
    """
    Get the global cross-module authentication service instance.
    
    Returns:
        CrossModuleAuthService instance
    """
    global _cross_module_auth_service
    if _cross_module_auth_service is None:
        _cross_module_auth_service = CrossModuleAuthService()
    return _cross_module_auth_service


async def authenticate_module_request(request_api_key: Optional[str]) -> Optional[str]:
    """
    Convenience function to authenticate a module request.
    
    Args:
        request_api_key: The API key provided in the request
        
    Returns:
        Module name if authenticated, None if authentication failed
    """
    auth_service = get_cross_module_auth_service()
    result = await auth_service.authenticate_module_request(request_api_key)
    
    if result:
        return result["module_name"]
    
    return None
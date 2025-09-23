"""
API Server for internal service communication.

This module provides the FastAPI server setup and configuration
for internal service communication as required by Requirement 4.1.
"""

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os

from src.api.auth import JWTAuthService
from src.config.manager import ConfigManager
from src.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class APIServer:
    """Internal REST API server for service communication."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the API server.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.jwt_auth_service = JWTAuthService(self.config_manager)
        self.app = FastAPI(
            title="YABOT Internal API",
            description="Internal REST API for YABOT system components",
            version="1.0.0"
        )
        self._setup_middleware()
        self._setup_routes()
        self._setup_exception_handlers()

    def _setup_middleware(self):
        """Set up middleware for the API server."""
        # Add CORS middleware for internal service communication
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"]
        )

    def _setup_routes(self):
        """Set up API routes."""
        # Health check endpoint
        @self.app.get("/health", tags=["Health"])
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "yabot-api"
            }

        # Authentication dependency
        async def authenticate_service(authorization: str = None):
            """Dependency to authenticate service requests."""
            if not authorization:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header is required",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            try:
                scheme, token = authorization.split()
                if scheme.lower() != "bearer":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication scheme",
                        headers={"WWW-Authenticate": "Bearer"}
                    )

                payload = self.jwt_auth_service.validate_token(token)
                return payload
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(e),
                    headers={"WWW-Authenticate": "Bearer"}
                )

        # Protected health check endpoint
        @self.app.get("/health/protected", tags=["Health"])
        async def protected_health_check(
            payload: dict = Depends(authenticate_service)
        ):
            """Protected health check endpoint."""
            return {
                "status": "healthy",
                "service": "yabot-api",
                "authenticated_service": payload.get("sub")
            }

        # API info endpoint
        @self.app.get("/info", tags=["Info"])
        async def api_info():
            """Get API information."""
            return {
                "title": "YABOT Internal API",
                "version": "1.0.0",
                "description": "Internal REST API for YABOT system components"
            }

    def _setup_exception_handlers(self):
        """Set up exception handlers."""
        pass  # Will be extended as needed

    def get_api_config(self):
        """Get API server configuration from environment variables.
        
        Returns:
            dict: API configuration
        """
        return {
            "host": os.getenv("API_HOST", "127.0.0.1"),
            "port": int(os.getenv("API_PORT", "8000")),
            "reload": os.getenv("API_RELOAD", "false").lower() == "true",
            "log_level": os.getenv("API_LOG_LEVEL", "info")
        }

    def start_server(self, host: str = None, port: int = None, reload: bool = False):
        """Start the API server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            reload: Whether to enable auto-reload
        """
        config = self.get_api_config()

        host = host or config["host"]
        port = port or config["port"]
        reload = reload or config["reload"]

        logger.info(
            "Starting API server",
            host=host,
            port=port,
            reload=reload
        )

        uvicorn.run(
            self.app,
            host=host,
            port=port,
            reload=reload,
            log_level=config["log_level"]
        )

    async def start_server_async(
        self,
        host: str = None,
        port: int = None,
        reload: bool = False
    ):
        """Start the API server asynchronously.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            reload: Whether to enable auto-reload
        """
        config = self.get_api_config()

        host = host or config["host"]
        port = port or config["port"]
        reload = reload or config["reload"]

        logger.info(
            "Starting API server asynchronously",
            host=host,
            port=port,
            reload=reload
        )

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            reload=reload,
            log_level=config["log_level"]
        )
        server = uvicorn.Server(config)
        await server.serve()

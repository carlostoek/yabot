"""
Middleware manager for the Telegram bot framework.
"""

from typing import List, Callable, Any, Dict
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Middleware:
    """Base class for middleware components."""
    
    async def process_request(self, update: Any) -> Any:
        """Process an incoming update.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Any: The processed update
        """
        return update
    
    async def process_response(self, response: Any) -> Any:
        """Process an outgoing response.
        
        Args:
            response (Any): The outgoing response
            
        Returns:
            Any: The processed response
        """
        return response


class MiddlewareManager:
    """Manages request/response processing pipeline for cross-cutting concerns."""
    
    def __init__(self):
        """Initialize the middleware manager."""
        self._middlewares: List[Middleware] = []
    
    def add_middleware(self, middleware: Middleware) -> None:
        """Register middleware.
        
        Args:
            middleware (Middleware): The middleware instance to register
        """
        if not isinstance(middleware, Middleware):
            raise TypeError("Middleware must be an instance of Middleware class")
        self._middlewares.append(middleware)
        logger.info("Added middleware: %s", middleware.__class__.__name__)
    
    async def process_request(self, update: Any) -> Any:
        """Pre-process incoming updates.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Any: The processed update after passing through all middleware
        """
        processed_update = update
        for middleware in self._middlewares:
            try:
                processed_update = await middleware.process_request(processed_update)
            except Exception as e:
                logger.error(
                    "Error in middleware %s process_request: %s",
                    middleware.__class__.__name__, str(e)
                )
                # Continue with the original update if middleware fails
                continue
        return processed_update
    
    async def process_response(self, response: Any) -> Any:
        """Post-process outgoing responses.
        
        Args:
            response (Any): The outgoing response
            
        Returns:
            Any: The processed response after passing through all middleware
        """
        processed_response = response
        # Process in reverse order for responses
        for middleware in reversed(self._middlewares):
            try:
                processed_response = await middleware.process_response(processed_response)
            except Exception as e:
                logger.error(
                    "Error in middleware %s process_response: %s",
                    middleware.__class__.__name__, str(e)
                )
                # Continue with the original response if middleware fails
                continue
        return processed_response
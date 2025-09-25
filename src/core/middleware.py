"""
Core Bot Framework - Middleware Manager

This module manages request/response processing pipeline for cross-cutting concerns.
"""
from typing import List, Callable, Any, Awaitable, Union, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery, TelegramObject
# HandlerObject is not used in the code, removing the unused import
from src.utils.logger import get_logger
from src.utils.errors import error_handler


class MiddlewareManager:
    """
    Manages request/response processing pipeline for cross-cutting concerns
    """
    
    def __init__(self):
        self.middlewares: List[BaseMiddleware] = []
        self.logger = get_logger(self.__class__.__name__)
    
    def add_middleware(self, middleware: BaseMiddleware) -> None:
        """
        Register middleware
        
        Args:
            middleware: The middleware instance to register
        """
        self.middlewares.append(middleware)
        self.logger.info(f"Added middleware: {middleware.__class__.__name__}")
    
    def get_middlewares(self) -> List[BaseMiddleware]:
        """
        Get all registered middlewares
        
        Returns:
            List of registered middleware instances
        """
        return self.middlewares


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware for logging incoming updates
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
    
    async def __call__(
        self,
        handler: Callable,
        event: Union[Update, Message, CallbackQuery],
        data: dict
    ) -> Any:
        # Log the incoming update
        event_type = type(event).__name__
        self.logger.info(
            "Incoming update",
            event_type=event_type,
            update_id=getattr(event, 'update_id', 'unknown'),
            chat_id=getattr(getattr(event, 'chat', None), 'id', 'unknown') if hasattr(event, 'chat') else 'unknown',
            user_id=getattr(getattr(event, 'from_user', None), 'id', 'unknown') if hasattr(event, 'from_user') else 'unknown'
        )
        
        try:
            # Call the next middleware or handler
            result = await handler(event, data)
            
            # Log successful processing
            self.logger.info(
                "Update processed successfully",
                event_type=event_type,
                update_id=getattr(event, 'update_id', 'unknown')
            )
            
            return result
        except Exception as e:
            # Log the error
            self.logger.error(
                "Error processing update",
                event_type=event_type,
                update_id=getattr(event, 'update_id', 'unknown'),
                error=str(e),
                error_type=type(e).__name__
            )
            raise


class ConfigurationValidationMiddleware(BaseMiddleware):
    """
    Middleware for validating configuration before processing updates
    """
    
    def __init__(self):
        super().__init__()
        # Import here to avoid circular import
        from src.config.manager import get_config_manager
        self.config_manager = get_config_manager()
        self.logger = get_logger(self.__class__.__name__)
    
    async def __call__(
        self,
        handler: Callable,
        event: Union[Update, Message, CallbackQuery],
        data: dict
    ) -> Any:
        # Validate configuration
        try:
            self.config_manager.validate_config()
        except Exception as e:
            self.logger.error(
                "Configuration validation failed",
                error=str(e)
            )
            # Don't process the update if configuration is invalid
            return None
        
        # Call the next middleware or handler
        return await handler(event, data)


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware for handling errors in the processing pipeline
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
    
    async def __call__(
        self,
        handler: Callable,
        event: Union[Update, Message, CallbackQuery],
        data: dict
    ) -> Any:
        try:
            # Call the next middleware or handler
            result = await handler(event, data)
            return result
        except Exception as e:
            # Handle the error
            error_response = error_handler.handle(e, {
                'event_type': type(event).__name__,
                'update_id': getattr(event, 'update_id', 'unknown'),
                'middleware': self.__class__.__name__
            })
            
            self.logger.error(
                "Error handled by middleware",
                error_response=error_response
            )
            
            # Re-raise the exception so it can be handled by the dispatcher
            raise


class UserContextMiddleware(BaseMiddleware):
    """
    Middleware for maintaining user context
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.user_contexts = {}  # In a real app, use a proper storage like Redis
    
    async def __call__(
        self,
        handler: Callable,
        event: Union[Update, Message, CallbackQuery],
        data: dict
    ) -> Any:
        # Extract user info
        user_id = getattr(getattr(event, 'from_user', None), 'id', None)
        
        if user_id:
            # Get or create user context
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = {
                    'user_id': user_id,
                    'current_state': 'start',
                    'session_data': {},
                    'created_at': self._get_timestamp()
                }
            
            # Add user context to data
            data['user_context'] = self.user_contexts[user_id]
        
        # Call the next middleware or handler
        result = await handler(event, data)
        
        return result
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware for rate limiting requests
    """
    
    def __init__(self, threshold: int = 5, time_window: int = 60):
        super().__init__()
        self.threshold = threshold  # Max requests per time window
        self.time_window = time_window  # Time window in seconds
        self.requests = {}  # Dictionary to track requests by user
        self.logger = get_logger(self.__class__.__name__)
    
    async def __call__(
        self,
        handler: Callable,
        event: Union[Update, Message, CallbackQuery],
        data: dict
    ) -> Any:
        # Extract user info
        user_id = getattr(getattr(event, 'from_user', None), 'id', None)
        
        if user_id:
            current_time = self._get_timestamp()
            
            # Get user's request history
            if user_id not in self.requests:
                self.requests[user_id] = []
            
            # Remove requests outside the time window
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(seconds=self.time_window)
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if datetime.fromisoformat(req_time) > cutoff_time
            ]
            
            # Check if user has exceeded the threshold
            if len(self.requests[user_id]) >= self.threshold:
                self.logger.warning(
                    "Request throttled",
                    user_id=user_id,
                    request_count=len(self.requests[user_id])
                )
                
                # Don't process the request, return None
                return None
            
            # Add current request to history
            self.requests[user_id].append(current_time)
        
        # Call the next middleware or handler
        result = await handler(event, data)
        
        return result
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class DatabaseMiddleware(BaseMiddleware):
    """
    Aiogram 3 middleware for database context injection
    Implements Requirement 5.1.4: WHEN middleware processes requests THEN it SHALL have access to database services through dependency injection
    """

    def __init__(self, database_manager, event_bus=None):
        super().__init__()
        self.database_manager = database_manager
        self.event_bus = event_bus

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Inject database services into handler data (Requirement 5.1.4)
        data["database_manager"] = self.database_manager
        data["event_bus"] = self.event_bus

        # Add user service for easy access
        from src.services.user import UserService
        data["user_service"] = UserService(self.database_manager)

        # Call next handler in chain
        return await handler(event, data)


# Create a default instance of the middleware manager
default_middleware_manager = MiddlewareManager()


def setup_default_middlewares():
    """
    Setup default middlewares for the bot
    """
    manager = default_middleware_manager
    
    # Add default middlewares in order of execution
    manager.add_middleware(LoggingMiddleware())
    manager.add_middleware(ConfigurationValidationMiddleware())
    manager.add_middleware(UserContextMiddleware())
    manager.add_middleware(ThrottlingMiddleware())
    manager.add_middleware(ErrorHandlerMiddleware())
    
    return manager
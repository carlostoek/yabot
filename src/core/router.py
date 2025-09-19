"""
Router component for the Telegram bot framework.
"""

from typing import Dict, Callable, Any, Optional, List
from src.utils.logger import get_logger
from src.services.user import UserService
from src.events.bus import EventBus
from src.database.manager import DatabaseManager

logger = get_logger(__name__)


class Router:
    """Routes incoming messages to appropriate handlers based on message type and content.
    
    The Router can be enhanced with database context to provide handlers with access to
    database operations, event publishing, and other services. When handlers are registered,
    they can optionally accept a 'router' parameter to access these services.
    """
    
    def __init__(self, user_service: Optional[UserService] = None, 
                 event_bus: Optional[EventBus] = None,
                 database_manager: Optional[DatabaseManager] = None):
        """Initialize the router with optional database context.
        
        Args:
            user_service (UserService, optional): User service for database operations
            event_bus (EventBus, optional): Event bus for publishing events
            database_manager (DatabaseManager, optional): Database manager for direct database access
        """
        self._command_handlers: Dict[str, Callable] = {}
        self._message_handlers: List[tuple] = []  # (filter, handler) tuples
        self._default_handler: Optional[Callable] = None
        self.user_service = user_service
        self.event_bus = event_bus
        self.database_manager = database_manager
    
    @property
    def has_database_context(self) -> bool:
        """Check if the router has database context available.
        
        Returns:
            bool: True if database context is available, False otherwise
        """
        return self.user_service is not None or self.database_manager is not None
    
    @property
    def has_event_context(self) -> bool:
        """Check if the router has event bus context available.
        
        Returns:
            bool: True if event bus context is available, False otherwise
        """
        return self.event_bus is not None
    
    def register_command_handler(self, command: str, handler: Callable) -> None:
        """Register command handlers.
        
        Args:
            command (str): The command to register (e.g., "start", "menu")
            handler (Callable): The handler function to call for this command
        """
        if not callable(handler):
            raise TypeError("Handler must be callable")
        
        self._command_handlers[command] = handler
        logger.info("Registered command handler for: /%s", command)
    
    def register_message_handler(self, message_filter: Any, handler: Callable) -> None:
        """Register message handlers.
        
        Args:
            message_filter (Any): The filter to match messages against
            handler (Callable): The handler function to call for matching messages
        """
        if not callable(handler):
            raise TypeError("Handler must be callable")
        
        self._message_handlers.append((message_filter, handler))
        logger.info("Registered message handler with filter: %s", type(message_filter).__name__)
    
    def set_default_handler(self, handler: Callable) -> None:
        """Set the default handler for unmatched messages/commands.
        
        Args:
            handler (Callable): The default handler function
        """
        if not callable(handler):
            raise TypeError("Handler must be callable")
        
        self._default_handler = handler
        logger.info("Set default handler")
    
    async def route_update(self, update: Any) -> Any:
        """Find appropriate handler for update and execute it.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Any: The response from the handler
        """
        # Check if this is a command
        command = self._extract_command(update)
        if command:
            handler = self._command_handlers.get(command)
            if handler:
                logger.info("Routing command /%s to handler", command)
                # Pass router context to handler if it accepts it
                import inspect
                handler_signature = inspect.signature(handler)
                if 'router' in handler_signature.parameters:
                    return await handler(update, router=self)
                else:
                    return await handler(update)
            else:
                logger.info("No handler found for command /%s", command)
        
        # Check message handlers
        for message_filter, handler in self._message_handlers:
            if await self._matches_filter(update, message_filter):
                logger.info("Routing message to handler with filter %s", type(message_filter).__name__)
                # Pass router context to handler if it accepts it
                import inspect
                handler_signature = inspect.signature(handler)
                if 'router' in handler_signature.parameters:
                    return await handler(update, router=self)
                else:
                    return await handler(update)
        
        # Use default handler if no specific handler matched
        if self._default_handler:
            logger.info("Routing to default handler")
            # Pass router context to handler if it accepts it
            import inspect
            handler_signature = inspect.signature(self._default_handler)
            if 'router' in handler_signature.parameters:
                return await self._default_handler(update, router=self)
            else:
                return await self._default_handler(update)
        
        # No handler available
        logger.warning("No handler found for update")
        return None
    
    def _extract_command(self, update: Any) -> Optional[str]:
        """Extract command from update if present.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Optional[str]: The command if found, None otherwise
        """
        # This is a simplified implementation
        # In a real implementation, this would extract the command from the Telegram update
        if hasattr(update, 'message') and hasattr(update.message, 'text'):
            text = update.message.text
            if text.startswith('/'):
                # Extract command name (everything after / and before any spaces)
                return text[1:].split(' ')[0].lower()
        return None
    
    async def _matches_filter(self, update: Any, message_filter: Any) -> bool:
        """Check if update matches the given filter.
        
        Args:
            update (Any): The incoming update
            message_filter (Any): The filter to match against
            
        Returns:
            bool: True if the update matches the filter
        """
        # This is a simplified implementation
        # In a real implementation, this would check various message properties
        # against the filter criteria
        return True  # For now, assume all messages match
"""
Command handlers for the Telegram bot framework.
"""

import sys
from typing import Any, Optional
from aiogram.types import Message
from src.handlers.base import BaseHandler
from src.core.models import CommandResponse
from src.utils.logger import get_logger
from src.services.user import UserService
from src.events.bus import EventBus
from src.events.models import create_event
from src.database.manager import DatabaseManager

logger = get_logger(__name__)


class CommandHandler(BaseHandler):
    """Handles bot commands like /start and /menu with standardized response patterns."""
    
    def __init__(self, user_service: Optional[UserService] = None, 
                 event_bus: Optional[EventBus] = None):
        """Initialize the command handler.
        
        Args:
            user_service (Optional[UserService]): User service for database operations
            event_bus (Optional[EventBus]): Event bus for publishing events
        """
        super().__init__()
        self.user_service = user_service
        self.event_bus = event_bus
    
    async def handle(self, update: Any) -> Optional[CommandResponse]:
        """Handle an incoming update.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Optional[CommandResponse]: The response to send back to the user
        """
        # This method would typically be called by the router
        # For now, we'll just return None as the specific command handlers
        # will be called directly
        return None
    
    async def _publish_user_interaction_event(self, user_id: str, action: str, message: Any) -> None:
        """Publish a user interaction event.
        
        Args:
            user_id (str): The user ID
            action (str): The action performed
            message (Any): The message that triggered the action
        """
        if self.event_bus:
            try:
                event = create_event(
                    "user_interaction",
                    user_id=user_id,
                    action=action,
                    context={"message_id": getattr(message, 'message_id', None)}
                )
                await self.event_bus.publish("user_interaction", event.dict())
            except Exception as e:
                logger.warning("Failed to publish user_interaction event: %s", str(e))
    
    async def handle_start(self, message: Message) -> CommandResponse:
        """Process /start command.
        
        Args:
            message (Message): The message containing the /start command
            
        Returns:
            CommandResponse: The welcome message response
        """
        logger.info("Processing /start command")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # If we have database context, create or update user
        if self.user_service:
            try:
                user_context = await self.user_service.get_user_context(user_id)
                logger.info("Existing user context retrieved: %s", user_id)
                
                # Update last login time
                await self.user_service.update_user_profile(user_id, {})
            except Exception:
                # User doesn't exist, create new user
                try:
                    telegram_user_data = {
                        "id": user.id if user else None,
                        "username": user.username if user else None,
                        "first_name": user.first_name if user else None,
                        "last_name": user.last_name if user else None,
                        "language_code": user.language_code if user else None
                    }
                    user_context = await self.user_service.create_user(telegram_user_data)
                    logger.info("New user created: %s", user_id)
                except Exception as e:
                    logger.error("Error creating user: %s", str(e))
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "start", message)
        
        welcome_text = (
            "👋 Welcome to the Telegram Bot!\n\n"
            "I'm here to help you with various tasks and provide information.\n\n"
            "Available commands:\n"
            "• /start - Show this welcome message\n"
            "• /menu - Show the main menu\n"
            "• /help - Show help information\n\n"
            "Feel free to explore what I can do!"
        )
        
        return await self._create_response(welcome_text)
    
    async def handle_menu(self, message: Message) -> CommandResponse:
        """Process /menu command.
        
        Args:
            message (Message): The message containing the /menu command
            
        Returns:
            CommandResponse: The menu response
        """
        logger.info("Processing /menu command")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "menu", message)
        
        menu_text = (
            "📋 Main Menu\n\n"
            "Select an option:\n"
            "• Option 1 - Description of option 1\n"
            "• Option 2 - Description of option 2\n"
            "• Option 3 - Description of option 3\n\n"
            "Use /help for more information about available commands."
        )
        
        # In a real implementation, we would add reply markup with buttons
        # For now, we'll just return the text response
        return await self._create_response(menu_text)
    
    async def handle_help(self, message: Message) -> CommandResponse:
        """Process /help command.
        
        Args:
            message (Message): The message containing the /help command
            
        Returns:
            CommandResponse: The help response
        """
        logger.info("Processing /help command")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "help", message)
        
        help_text = (
            "ℹ️ Help Information\n\n"
            "Available commands:\n"
            "• /start - Show the welcome message\n"
            "• /menu - Show the main menu\n"
            "• /help - Show this help information\n\n"
            "If you have any questions or need assistance, please contact support."
        )
        
        return await self._create_response(help_text)
    
    async def handle_unknown(self, message: Message) -> CommandResponse:
        """Handle unrecognized commands.
        
        Args:
            message (Message): The message containing the unrecognized command
            
        Returns:
            CommandResponse: The response for unknown commands
        """
        logger.info("Processing unknown command")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "unknown", message)
        
        unknown_text = (
            "❓ Unknown command\n\n"
            "I didn't recognize that command. Here are the available commands:\n"
            "• /start - Show the welcome message\n"
            "• /menu - Show the main menu\n"
            "• /help - Show help information\n\n"
            "Please try one of these commands or contact support if you need help."
        )
        
        return await self._create_response(unknown_text)
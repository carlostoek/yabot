"""
Command Handler Module

This module provides a general CommandHandler class for the integration tests.
"""
from aiogram.types import Message
from src.utils.logger import get_logger
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.services.user import UserService


class CommandHandler:
    """
    General command handler for testing purposes
    """
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.db_manager = None
        self.event_bus = None
        self.user_service = None
    
    async def handle_start_command(self, message: Message):
        """Handle the start command"""
        response = "Welcome to the bot!"
        if self.user_service:
            # Process user creation if needed
            pass
        return response
    
    async def handle_menu_command(self, message: Message):
        """Handle the menu command"""
        response = "Menu options available."
        if self.db_manager:
            user_id = str(message.from_user.id)
            # Get user state from database
            user_state = await self.db_manager.get_user_from_mongo(user_id)
            # Update state if needed
            if user_state:
                await self.db_manager.update_user_in_mongo(
                    user_id, 
                    {"$set": {"current_state.menu_context": "menu"}}
                )
        return response
    
    async def handle_command(self, message: Message, command_parts: list):
        """Handle a generic command with parts"""
        command = command_parts[0] if command_parts else ""
        if self.event_bus:
            # Publish event about command handling
            pass
        return f"Handled command: {command}"
"""
Core Bot Framework - Command Handlers

This module contains handlers for basic commands like /start, /menu, and /help.
Each handler extends the BaseHandler class and implements the required functionality 
according to the specification requirements.

Enhanced to integrate with database context and event publishing as per
Requirement 5.3: Handler Integration and Event Publishing.
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from src.handlers.base import BaseHandler, MessageHandlerMixin
from src.core.models import MessageContext, CommandResponse
from src.utils.logger import get_logger
from src.database.manager import DatabaseManager
from src.services.user import UserService
from src.events.models import UserInteractionEvent, UserRegistrationEvent


class StartCommandHandler(BaseHandler, MessageHandlerMixin):
    """
    Handler for the /start command.
    
    Implements requirement 2.1: WHEN a user sends /start command THEN the bot 
    SHALL respond with a welcome message and basic usage instructions
    Implements requirement 5.3: WHEN a user sends /start command THEN CommandHandler 
    SHALL publish user_interaction event
    """
    
    def __init__(self):
        super().__init__()
        # Services will be injected via middleware, not instantiated directly
    
    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> CommandResponse:
        """Process the /start command"""
        # Extract data from kwargs (injected via middleware)
        from src.events.bus import EventBus
        data = kwargs.get('data', {})
        database_manager = data.get('database_manager')
        user_service = data.get('user_service')
        event_bus = data.get('event_bus')
        
        # Ensure services are available
        if not database_manager or not user_service:
            self.logger.error("Required services not available in data")
            error_response = self.create_response(text="Internal error occurred")
            await self.send_response(message, error_response)
            return error_response
        
        user_id = str(message.from_user.id)
        
        # Check if user exists, create if not
        user_exists = await database_manager.get_user_from_mongo(user_id)
        if not user_exists:
            # Create user in database
            telegram_user_data = {
                "id": message.from_user.id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "language_code": message.from_user.language_code,
            }
            
            await user_service.create_user(telegram_user_data)
        
        welcome_text = (
            "👋 Hello! Welcome to the bot.\n\n"
            "I'm here to help you with various tasks. "
            "Use /menu to see available options or /help for more information."
        )
        
        # Publish user interaction event
        if event_bus:
            interaction_event = UserInteractionEvent(
                event_id=f"start_{user_id}_{int(__import__('time').time())}",
                user_id=user_id,
                action="start",
                context={"command": "/start", "username": message.from_user.username},
                source="command_handler"
            )
            await event_bus.publish(interaction_event)
        
        # Create and return the response
        response = self.create_response(text=welcome_text)
        await self.send_response(message, response)
        return response


class MenuCommandHandler(BaseHandler, MessageHandlerMixin):
    """
    Handler for the /menu command.
    
    Implements requirement 2.2: WHEN a user sends /menu command THEN the bot 
    SHALL display the main menu with available options
    """
    
    def __init__(self):
        super().__init__()
        # Services will be injected via middleware, not instantiated directly
    
    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> CommandResponse:
        """Process the /menu command"""
        # Extract data from kwargs (injected via middleware)
        data = kwargs.get('data', {})
        database_manager = data.get('database_manager')
        user_service = data.get('user_service')
        
        # Create an inline keyboard with menu options
        keyboard = InlineKeyboardBuilder()
        
        # Add main menu options
        keyboard.add(InlineKeyboardButton(text="📝 Help", callback_data="help"))
        keyboard.add(InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"))
        keyboard.add(InlineKeyboardButton(text="ℹ️ Info", callback_data="info"))
        keyboard.add(InlineKeyboardButton(text="❌ Close", callback_data="close_menu"))
        
        keyboard.adjust(2)  # 2 buttons per row
        
        menu_text = "📋 <b>Main Menu</b>\n\nPlease select an option:"
        
        # Create and return the response
        response = self.create_response(
            text=menu_text,
            reply_markup=keyboard.as_markup()
        )
        await self.send_response(message, response)
        return response


class HelpCommandHandler(BaseHandler, MessageHandlerMixin):
    """
    Handler for the /help command.
    """
    
    def __init__(self):
        super().__init__()
        # Services will be injected via middleware, not instantiated directly
    
    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> CommandResponse:
        """Process the /help command"""
        # Extract data from kwargs (injected via middleware)
        data = kwargs.get('data', {})
        database_manager = data.get('database_manager')
        user_service = data.get('user_service')
        
        help_text = (
            "📖 <b>Bot Help</b>\n\n"
            "Available commands:\n"
            "• /start - Start the bot and get a welcome message\n"
            "• /menu - Show the main menu with options\n"
            "• /help - Show this help message\n\n"
            "For support, contact the bot administrator."
        )
        
        # Create and return the response
        response = self.create_response(text=help_text)
        await self.send_response(message, response)
        return response


class UnknownCommandHandler(BaseHandler, MessageHandlerMixin):
    """
    Handler for unrecognized commands and messages.
    
    Implements requirement 2.3: WHEN a user sends an unrecognized command 
    THEN the bot SHALL respond with a helpful message explaining available commands
    """
    
    def __init__(self):
        super().__init__()
        # Services will be injected via middleware, not instantiated directly
    
    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> CommandResponse:
        """Process unrecognized commands or messages"""
        # Extract data from kwargs (injected via middleware)
        data = kwargs.get('data', {})
        database_manager = data.get('database_manager')
        user_service = data.get('user_service')
        
        # Check if message is a text command that's not recognized
        if hasattr(message, 'text') and message.text and message.text.startswith('/'):
            unknown_command = message.text.split()[0]
            response_text = (
                f"⚠️ Sorry, I don't recognize the command: <code>{unknown_command}</code>\n\n"
                f"Use /help to see available commands or /menu for options."
            )
        else:
            # It's not a command, just a regular message
            response_text = (
                "🤔 I'm not sure how to respond to that.\n\n"
                "Use /help to see available commands or /menu for options."
            )
        
        # Create and return the response
        response = self.create_response(text=response_text)
        await self.send_response(message, response)
        return response


# Router setup for command handlers
router = Router()
logger = get_logger(__name__)


# Register the command handlers
@router.message(CommandStart())
async def handle_start_command(message: Message, **kwargs):
    """Handle the /start command"""
    handler = StartCommandHandler()
    await handler.handle_message(message, **kwargs)


@router.message(Command("menu"))
async def handle_menu_command(message: Message, **kwargs):
    """Handle the /menu command"""
    handler = MenuCommandHandler()
    await handler.handle_message(message, **kwargs)


@router.message(Command("help"))
async def handle_help_command(message: Message, **kwargs):
    """Handle the /help command"""
    handler = HelpCommandHandler()
    await handler.handle_message(message, **kwargs)


@router.message()
async def handle_unknown_command(message: Message, **kwargs):
    """Handle unknown commands and messages"""
    # Check if this is a command that should be handled by other handlers
    if hasattr(message, 'text') and message.text and message.text.startswith('/'):
        # Check if it's one of our known commands but not handled yet
        known_commands = ['/start', '/menu', '/help']
        if not any(message.text.lower().startswith(cmd) for cmd in known_commands):
            handler = UnknownCommandHandler()
            await handler.handle_message(message, **kwargs)
    else:
        # It's a regular message, treat as unknown command
        handler = UnknownCommandHandler()
        await handler.handle_message(message, **kwargs)


def register_handlers(dp):
    """
    Register all command handlers with the dispatcher.
    
    Args:
        dp: The aiogram Dispatcher instance
    """
    dp.include_router(router)
    logger.info("Command handlers registered")


# Export the handlers so they can be imported by the router
__all__ = [
    'handle_start_command',
    'handle_menu_command', 
    'handle_help_command',
    'handle_unknown_command',
    'register_handlers'
]

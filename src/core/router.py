"""
Core Bot Framework - Router Component

This module routes incoming messages to appropriate handlers based on message type and content.
"""
from typing import Callable, Dict, List, Optional, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Update
from aiogram.filters import Command, CommandStart
from aiogram.handlers import MessageHandler, CallbackQueryHandler

from src.utils.logger import get_logger
from src.utils.errors import handle_error
from src.core.models import BotCommand


class RouterManager:
    """
    Routes incoming messages to appropriate handlers based on message type and content
    """
    
    def __init__(self):
        self.router = Router()
        self.command_handlers: Dict[str, Callable] = {}
        self.message_handlers: List[tuple] = []  # (filter, handler)
        self.callback_handlers: List[tuple] = []  # (pattern, handler)
        self.logger = get_logger(self.__class__.__name__)
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """
        Register default handlers for standard commands
        """
        # Import the command handlers
        from src.handlers.commands import handle_start_command, handle_menu_command, handle_help_command, handle_unknown_command
        
        # Register the actual command handlers
        self.router.message(CommandStart())(handle_start_command)
        self.router.message(Command("help"))(handle_help_command)
        self.router.message(Command("menu"))(handle_menu_command)
        self.router.message()(handle_unknown_command)
    
    def register_command_handler(self, command: str, handler: Callable) -> None:
        """
        Register a command handler
        
        Args:
            command: The command to register (e.g., "start", "help", "menu")
            handler: The handler function to call when the command is received
        """
        self.command_handlers[command] = handler
        self.logger.info(f"Registered command handler for /{command}")
        
        # Add the handler to the router
        @self.router.message(Command(command))
        async def command_wrapper(message: Message):
            try:
                return await handler(message)
            except Exception as e:
                self.logger.error(
                    f"Error in command handler for /{command}",
                    error=str(e),
                    error_type=type(e).__name__
                )
                handle_error(e, {
                    'command': command,
                    'user_id': message.from_user.id,
                    'chat_id': message.chat.id
                })
    
    def register_message_handler(self, filter_func: Any, handler: Callable) -> None:
        """
        Register a message handler with a specific filter
        
        Args:
            filter_func: The filter to apply (e.g., F.text, F.photo, etc.)
            handler: The handler function to call when the filter matches
        """
        self.message_handlers.append((filter_func, handler))
        self.logger.info(f"Registered message handler with filter: {filter_func}")
        
        # Add the handler to the router
        @self.router.message(filter_func)
        async def message_wrapper(message: Message):
            try:
                return await handler(message)
            except Exception as e:
                self.logger.error(
                    "Error in message handler",
                    error=str(e),
                    error_type=type(e).__name__,
                    filter=str(filter_func)
                )
                handle_error(e, {
                    'filter': str(filter_func),
                    'user_id': message.from_user.id,
                    'chat_id': message.chat.id
                })
    
    def register_callback_handler(self, pattern: str, handler: Callable) -> None:
        """
        Register a callback query handler
        
        Args:
            pattern: The callback data pattern to match
            handler: The handler function to call when the pattern matches
        """
        self.callback_handlers.append((pattern, handler))
        self.logger.info(f"Registered callback handler for pattern: {pattern}")
        
        # Add the handler to the router
        @self.router.callback_query(F.data == pattern)
        async def callback_wrapper(callback_query: CallbackQuery):
            try:
                return await handler(callback_query)
            except Exception as e:
                self.logger.error(
                    f"Error in callback handler for pattern: {pattern}",
                    error=str(e),
                    error_type=type(e).__name__
                )
                handle_error(e, {
                    'pattern': pattern,
                    'user_id': callback_query.from_user.id,
                    'chat_id': callback_query.message.chat.id if callback_query.message else 'unknown'
                })
    
    def get_router(self):
        """
        Get the configured router instance
        
        Returns:
            The configured aiogram Router instance
        """
        return self.router
    
    def route_update(self, update: Update) -> Optional[Callable]:
        """
        Find appropriate handler for update (deprecated in favor of aiogram's built-in routing)
        
        Args:
            update: The update to route
            
        Returns:
            Appropriate handler function or None
        """
        # This method exists for compatibility but aiogram handles routing internally
        self.logger.debug("Update routing called", update_id=update.update_id)
        return None
    
    def get_registered_commands(self) -> List[str]:
        """
        Get a list of all registered commands
        
        Returns:
            List of command names
        """
        return list(self.command_handlers.keys())


def setup_routers(dp) -> None:
    """
    Setup all routers for the dispatcher
    
    Args:
        dp: The aiogram Dispatcher instance
    """
    from src.core.middleware import setup_default_middlewares
    from src.handlers.commands import register_handlers
    from src.core.error_handler import setup_error_handlers
    
    # Create the router manager
    router_manager = RouterManager()
    
    # Setup default middlewares
    middleware_manager = setup_default_middlewares()
    
    # Register the router with the dispatcher
    dp.include_router(router_manager.get_router())
    
    # Add middlewares to the dispatcher (root router) for broader coverage
    # In aiogram 3.x, middlewares should be registered on the dispatcher for all update types
    for middleware in middleware_manager.get_middlewares():
        dp.message.middleware(middleware)
        dp.callback_query.middleware(middleware)
        dp.inline_query.middleware(middleware)
        dp.chosen_inline_result.middleware(middleware)
    
    # Register command handlers with the dispatcher
    register_handlers(dp)
    
    # Setup error handlers
    setup_error_handlers(dp)
    
    logger = get_logger(__name__)
    logger.info(
        "Routers and middlewares setup completed",
        registered_commands=router_manager.get_registered_commands()
    )


# Create a global router for backward compatibility if needed
router = Router()


# Default handlers module - we'll create this as a fallback
# In a real implementation, this would be in a separate file
def create_default_handlers():
    """
    Create default handlers as fallbacks
    These are implemented here as fallbacks but would normally be in separate handler files
    """
    from aiogram import Router
    from aiogram.types import Message
    from aiogram.filters import Command, CommandStart
    import asyncio
    
    # Create handlers module structure
    import os
    handlers_dir = os.path.join(os.path.dirname(__file__), '..', 'handlers')
    os.makedirs(handlers_dir, exist_ok=True)
    
    # Create __init__.py in handlers
    handlers_init_path = os.path.join(handlers_dir, '__init__.py')
    if not os.path.exists(handlers_init_path):
        with open(handlers_init_path, 'w') as f:
            f.write('"""\nDefault handlers for the bot\n"""\n')
    
    # Create default.py in handlers
    default_handlers_path = os.path.join(handlers_dir, 'default.py')
    if not os.path.exists(default_handlers_path):
        with open(default_handlers_path, 'w') as f:
            f.write('''"""
Default handlers for the bot
"""
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


async def start_command_handler(message: Message):
    """Handle the /start command"""
    await message.answer(
        "Hello! Welcome to the bot. Use /menu to see available options.",
        parse_mode="HTML"
    )


async def help_command_handler(message: Message):
    """Handle the /help command"""
    help_text = """
Here are the available commands:
/start - Start the bot
/help - Show this help message
/menu - Show the main menu
    """
    await message.answer(help_text, parse_mode="HTML")


async def menu_command_handler(message: Message):
    """Handle the /menu command"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Help", callback_data="help"))
    keyboard.add(InlineKeyboardButton(text="Settings", callback_data="settings"))
    
    await message.answer(
        "Main Menu:",
        reply_markup=keyboard.as_markup()
    )


async def unknown_command_handler(message: Message):
    """Handle unknown commands or messages"""
    await message.answer(
        "I don't understand that command. Use /help to see available commands.",
        parse_mode="HTML"
    )
''')


# Create default handlers if they don't exist
create_default_handlers()
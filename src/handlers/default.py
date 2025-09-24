"""
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
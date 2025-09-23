"""
Telegram types for the bot application.
"""

from typing import Any, Optional, Dict, List, Union
from dataclasses import dataclass
from aiogram.types import Message, CallbackQuery, Update

# Re-export common Telegram types
TelegramUpdate = Update
TelegramMessage = Message
TelegramCallbackQuery = CallbackQuery

# Type aliases for better readability
ChatId = Union[int, str]
UserId = Union[int, str]
# src/modules/admin/message_protection.py

from aiogram import Bot
from aiogram.types import Message

class MessageProtectionSystem:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def protect_message_copy(self, chat_id: int, from_chat_id: int, message_id: int) -> Message:
        """
        Copies a message to a chat and protects it from forwarding and saving.
        """
        return await self.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            protect_content=True
        )

    async def send_protected_message(self, chat_id: int, text: str) -> Message:
        """
        Sends a protected message to a chat.
        """
        return await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            protect_content=True
        )

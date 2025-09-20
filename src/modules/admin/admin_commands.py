# src/modules/admin/admin_commands.py

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from src.handlers.base import BaseHandler, CommandResponse
from src.modules.admin.access_control import AccessControl

class AdminCommandHandler(BaseHandler):
    def __init__(self, access_control: AccessControl):
        self.access_control = access_control

    async def handle_admin(self, message: Message) -> CommandResponse:
        """Handles the /admin command and shows the admin menu."""
        # In a real scenario, the chat id for access validation might be a specific admin group
        access_result = await self.access_control.validate_access(message.from_user.id, message.chat.id)
        if not access_result.has_access:
            return CommandResponse(text="You are not authorized to use this command.")

        keyboard = self.generate_admin_menu(message.from_user.id)
        return CommandResponse(text="Admin Menu:", reply_markup=keyboard)

    def generate_admin_menu(self, user_id: int) -> InlineKeyboardMarkup:
        """Generates the inline keyboard for the admin menu."""
        buttons = [
            [InlineKeyboardButton(text="Manage Users", callback_data="admin_manage_users")],
            [InlineKeyboardButton(text="Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="System Status", callback_data="admin_system_status")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    async def process_admin_command(self, user_id: int, chat_id: int, command: str, args: dict) -> CommandResponse:
        """Processes a generic admin command."""
        access_result = await self.access_control.validate_access(user_id, chat_id)
        if not access_result.has_access:
            return CommandResponse(text="You are not authorized to use this command.")

        # This is a placeholder for a more complex command processing logic
        if command == "kick":
            # Example: /admin kick user_id=12345
            target_user_id = args.get("user_id")
            if target_user_id:
                await self.access_control.revoke_access(int(target_user_id), chat_id)
                return CommandResponse(text=f"User {target_user_id} has been kicked.")
            else:
                return CommandResponse(text="Please provide a user_id.")
        
        return CommandResponse(text=f"Unknown admin command: {command}")

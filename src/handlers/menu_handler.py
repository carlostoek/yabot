"""
Central handler for all menu-related interactions, including commands and callbacks.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.handlers.base import BaseHandler, CommandResponse
from src.services.user import UserService
from src.events.bus import EventBus
from src.ui.menu_factory import MenuFactory, Menu, MenuType
from src.ui.message_manager import MessageManager

logger = logging.getLogger(__name__)

class MenuHandlerSystem(BaseHandler):
    """Orchestrates menu interactions, integrating various services."""

    def __init__(
        self,
        user_service: UserService,
        event_bus: EventBus,
        menu_factory: MenuFactory,
        message_manager: MessageManager,
    ):
        super().__init__()
        self.user_service = user_service
        self.event_bus = event_bus
        self.menu_factory = menu_factory
        self.message_manager = message_manager
        logger.info("MenuHandlerSystem initialized.")

    async def handle(self, update: Any) -> Optional[CommandResponse]:
        """Generic handler entry point, routes to specific handlers."""
        if isinstance(update, Message) and update.text and update.text.startswith('/'):
            return await self.handle_command(update)
        elif isinstance(update, CallbackQuery):
            return await self.handle_callback(update)
        return None

    async def handle_command(self, message: Message) -> None:
        """
        Handles menu-related commands, sends the menu, and tracks the message.
        """
        if not message.from_user:
            return

        chat_id = message.chat.id
        user_id = str(message.from_user.id)
        command = message.text.split()[0] if message.text else ""

        logger.info(f"Handling command '{command}' for user {user_id} in chat {chat_id}")

        await self.cleanup_previous_messages(chat_id)

        try:
            telegram_user = message.from_user.model_dump()
            user_context = await self.user_service.get_or_create_user_context(user_id, telegram_user)
        except Exception as e:
            logger.error(f"Error getting user context for {user_id}: {e}", exc_info=True)
            sent_msg = await self.message_manager.bot.send_message(chat_id, "Error retrieving your profile.")
            await self.message_manager.track_message(sent_msg.chat.id, sent_msg.message_id, 'error_message')
            return

        # Track evaluation before generating menu
        await self._track_lucien_evaluation(user_id, command, {"message": message.model_dump_json(), "user_context": user_context})

        menu = await self.get_menu_for_context(user_context, MenuType.MAIN)
        if not menu:
            sent_msg = await self.message_manager.bot.send_message(chat_id, "Could not generate a menu.")
            await self.message_manager.track_message(sent_msg.chat.id, sent_msg.message_id, 'error_message')
            return

        # Render and send the menu directly
        text, reply_markup = self._render_menu_parts(menu)
        sent_menu_msg = await self.message_manager.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

        # Track the new menu message, marking it as the main menu
        await self.message_manager.track_message(
            sent_menu_msg.chat.id,
            sent_menu_msg.message_id,
            'main_menu',
            is_main_menu=True
        )

        await self.event_bus.publish("menu_command_handled", {"user_id": user_id, "command": command})

    async def handle_callback(self, query: CallbackQuery) -> None:
        """
        Handles callbacks, edits the menu, and tracks the message if a new one is created.
        """
        if not query.from_user or not query.data or not query.message:
            return

        chat_id = query.message.chat.id
        user_id = str(query.from_user.id)

        logger.info(f"Handling callback '{query.data}' for user {user_id} in chat {chat_id}")
        await query.answer()

        try:
            user_context = await self.user_service.get_user_context(user_id)
        except Exception as e:
            logger.error(f"Error getting user context for {user_id}: {e}", exc_info=True)
            await self.message_manager.bot.send_message(chat_id, "Error retrieving your profile.")
            return

        # Track evaluation before generating menu
        await self._track_lucien_evaluation(user_id, query.data, {"callback_query": query.model_dump_json(), "user_context": user_context})

        if query.data.startswith("menu:"):
            menu_id = query.data.split(":", 1)[1]
            menu = await self.get_menu_for_context(user_context, menu_id)
        else:
            logger.warning(f"Received non-menu callback action '{query.data}' - not yet implemented.")
            menu = await self.get_menu_for_context(user_context, MenuType.MAIN)

        if not menu:
            await self.message_manager.bot.send_message(chat_id, "Could not generate the requested menu.")
            return

        text, reply_markup = self._render_menu_parts(menu)
        try:
            await self.message_manager.bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=query.message.message_id,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to edit menu message, sending new one: {e}")
            await self.cleanup_previous_messages(chat_id)
            sent_menu_msg = await self.message_manager.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            await self.message_manager.track_message(
                sent_menu_msg.chat.id,
                sent_menu_msg.message_id,
                'main_menu',
                is_main_menu=True
            )

        await self.event_bus.publish("menu_callback_handled", {"user_id": user_id, "callback_data": query.data})

    async def cleanup_previous_messages(self, chat_id: int) -> None:
        """Cleans up old, temporary messages in the chat."""
        try:
            await self.message_manager.delete_old_messages(chat_id)
        except Exception as e:
            logger.error(f"Error during message cleanup in chat {chat_id}: {e}", exc_info=True)

    async def get_menu_for_context(self, user_context: Dict[str, Any], menu_identifier: Any) -> Optional[Menu]:
        """Generates a menu using the menu factory."""
        try:
            return await self.menu_factory.create_menu(menu_identifier, user_context)
        except Exception as e:
            logger.error(f"Error creating menu '{menu_identifier}' for user {user_context.get('user_id')}: {e}", exc_info=True)
            return None

    def _render_menu_parts(self, menu: Menu) -> tuple[str, InlineKeyboardMarkup]:
        """
        (Placeholder) Renders a Menu object into its text and markup parts.
        """
        text = f"<b>{menu.title}</b>\n\n{menu.description}"
        if menu.header_text:
            text = f"{menu.header_text}\n\n{text}"
        if menu.footer_text:
            text = f"{text}\n\n<i>{menu.footer_text}</i>"

        buttons = []
        row = []
        for item in menu.items:
            row.append(InlineKeyboardButton(text=item.text, callback_data=item.action_data))
            if len(row) >= menu.max_columns:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        return text, reply_markup

    async def _track_lucien_evaluation(self, user_id: str, user_action: str, 
                                     context: Dict[str, Any]) -> None:
        """Track user interaction for Lucien's evaluation system."""
        if not self.user_service:
            return
            
        try:
            assessment_data = {
                "behavior_observed": f"Menu interaction: {user_action}",
                "assessment_context": f"menu_interaction_{user_action}",
                "sophistication_indicators": self._detect_sophistication_indicators(user_action, context),
                "authenticity_markers": self._detect_authenticity_markers(user_action, context),
                "emotional_depth_signals": self._detect_emotional_depth_signals(user_action, context),
                "worthiness_impact": self._calculate_worthiness_impact(user_action),
            }
            
            await self.user_service.add_behavioral_assessment(user_id, assessment_data)
            logger.debug(f"Successfully tracked Lucien evaluation for user: {user_id}, action: {user_action}")
            
        except Exception as e:
            logger.warning(f"Failed to track Lucien evaluation for user {user_id}: {e}")
    
    def _detect_sophistication_indicators(self, user_action: str, context: Dict[str, Any]) -> list[str]:
        """Detect sophistication indicators in user actions."""
        indicators = []
        if user_action.startswith("menu:"):
            indicators.append("menu_navigation")
        if "/start" in user_action or "/menu" in user_action:
            indicators.append("proper_command_usage")
        return indicators
    
    def _detect_authenticity_markers(self, user_action: str, context: Dict[str, Any]) -> list[str]:
        """Detect authenticity markers in user actions."""
        return ["menu_interaction"]
    
    def _detect_emotional_depth_signals(self, user_action: str, context: Dict[str, Any]) -> list[str]:
        """Detect emotional depth signals in user actions."""
        if len(user_action) > 15:
            return ["detailed_action"]
        return ["standard_action"]
    
    def _calculate_worthiness_impact(self, user_action: str) -> float:
        """Calculate worthiness impact of user action."""
        if user_action.startswith("menu:"):
            return 0.02
        return 0.01
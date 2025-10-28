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
        # Initialize coordinator service to None - it will be set up later
        self.coordinator_service = None
        logger.info("MenuHandlerSystem initialized with basic services.")

    async def handle(self, update: Any) -> Optional[CommandResponse]:
        """Generic handler entry point, routes to specific handlers."""
        if isinstance(update, Message) and update.text and update.text.startswith('/'):
            await self.handle_command(update)
        elif isinstance(update, CallbackQuery):
            await self.handle_callback(update)
        return None

    async def handle_start_command(self, message: Message) -> None:
        """Handle /start command - displays the main interface using the menu system coordinator."""
        logger.info(f"handle_start_command called for user {message.from_user.id}")

        # If we have a coordinator service available, use it for enhanced performance and tracking
        if self.coordinator_service:
            logger.info("Using MenuSystemCoordinator for enhanced /start command processing")
            result = await self.coordinator_service.handle_menu_command(message)
            if result.get("success"):
                logger.info(f"MenuSystemCoordinator successfully handled /start for user {message.from_user.id}")
                return
            else:
                logger.warning(f"MenuSystemCoordinator failed for user {message.from_user.id}: {result.get('error')}")
                # Fall back to direct menu handling

        # Fallback to direct menu handling if coordinator is not available
        await self.handle_menu_command_impl(message)

    async def handle_menu_command(self, message: Message) -> None:
        """Handle /menu command."""
        logger.info(f"handle_menu_command called for user {message.from_user.id}")
        await self.handle_menu_command_impl(message)

    async def handle_help_command(self, message: Message) -> None:
        """Handle /help command."""
        logger.info(f"handle_help_command called for user {message.from_user.id}")
        # For now, treat help the same as menu
        await self.handle_menu_command_impl(message)

    async def handle_menu_command_impl(self, message: Message) -> None:
        """
        Handles menu-related commands, sends the menu, and tracks the message.
        This implementation provides direct menu handling when the coordinator is not available.
        """
        if not message.from_user:
            logger.warning("Received message without user information")
            return

        # Check if bot instance is available
        if not hasattr(self.message_manager, 'bot') or not self.message_manager.bot:
            logger.error("MessageManager bot instance is not available")
            return

        chat_id = message.chat.id
        user_id = str(message.from_user.id)
        command = message.text.split()[0] if message.text else ""

        logger.info(f"Handling command '{command}' for user {user_id} in chat {chat_id}")

        # Clean up previous messages for better UX
        await self.cleanup_previous_messages(chat_id)

        try:
            # Get enhanced user context with role validation and permissions
            user_context = await self.user_service.get_enhanced_user_menu_context(user_id)

            # Validate user has basic access permissions
            if not user_context:
                logger.error(f"No user context available for user {user_id}")
                sent_msg = await self.message_manager.bot.send_message(
                    chat_id,
                    "🔒 Unable to access your profile. Please try again or contact support."
                )
                await self.message_manager.track_message(sent_msg.chat.id, sent_msg.message_id, 'error_message')
                return

            # Log user context for debugging
            logger.debug(f"User context for {user_id}: role={user_context.get('role')}, vip={user_context.get('has_vip')}, level={user_context.get('narrative_level')}")

        except Exception as e:
            logger.error(f"Error getting user context for {user_id}: {e}", exc_info=True)
            sent_msg = await self.message_manager.bot.send_message(
                chat_id,
                "❌ Error retrieving your profile. Please try again."
            )
            await self.message_manager.track_message(sent_msg.chat.id, sent_msg.message_id, 'error_message')
            return

        # Track evaluation before generating menu for worthiness assessment
        await self._track_lucien_evaluation(user_id, command, {
            "message": message.model_dump_json(),
            "user_context": user_context,
            "command_type": "menu_access"
        })

        # Determine menu type based on command using centralized routing
        menu_id = "main_menu"  # Default to main menu for /start and /menu
        if command:
            # Remove the slash and get the menu ID from configuration
            clean_command = command.lstrip('/')
            from src.ui.menu_config import menu_system_config
            menu_id = menu_system_config.get_routing_rule(clean_command)
            logger.debug(f"Command '{clean_command}' routed to menu '{menu_id}'")

        # Generate menu using the factory with user context and role validation
        menu = await self.get_menu_for_context(user_context, menu_id)
        if not menu:
            logger.error(f"Failed to generate menu '{menu_id}' for user {user_id}")
            sent_msg = await self.message_manager.bot.send_message(
                chat_id,
                "⚠️ Could not generate the menu. Please try again."
            )
            await self.message_manager.track_message(sent_msg.chat.id, sent_msg.message_id, 'error_message')
            return

        # Render the menu with proper formatting and accessibility
        text, reply_markup = self._render_menu_parts(menu)

        try:
            # Send the main interface menu with enhanced formatting
            sent_menu_msg = await self.message_manager.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            logger.info(f"Successfully sent main interface menu to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to send menu message to user {user_id}: {e}")
            # Fallback: send simple message without markup
            try:
                sent_menu_msg = await self.message_manager.bot.send_message(
                    chat_id=chat_id,
                    text="🏠 Tu Mundo con Diana\n\nBienvenido a tu espacio personal. Si ves este mensaje, hay un problema temporal con la interfaz. Por favor, intenta nuevamente en unos momentos."
                )
            except Exception as fallback_error:
                logger.critical(f"Failed to send fallback message to user {user_id}: {fallback_error}")
                return

        # Track the new menu message with proper classification
        await self.message_manager.track_message(
            sent_menu_msg.chat.id,
            sent_menu_msg.message_id,
            'main_menu',
            is_main_menu=(menu_id == 'main_menu')
        )

        # Publish event for analytics and system monitoring
        await self.event_bus.publish("menu_command_handled", {
            "user_id": user_id,
            "command": command,
            "menu_id": menu_id,
            "user_role": user_context.get('role'),
            "has_vip": user_context.get('has_vip'),
            "timestamp": message.date.isoformat() if message.date else None
        })

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
            user_context = await self.user_service.get_enhanced_user_menu_context(user_id)
        except Exception as e:
            logger.error(f"Error getting user context for {user_id}: {e}", exc_info=True)
            await self.message_manager.bot.send_message(chat_id, "Error retrieving your profile.")
            return

        # Track evaluation before generating menu
        await self._track_lucien_evaluation(user_id, query.data, {"callback_query": query.model_dump_json(), "user_context": user_context})

        # Handle worthiness explanation requests
        if query.data.startswith("explain_divan_worthiness") or query.data.startswith("worthiness_explanation"):
            await self._handle_worthiness_explanation(query, user_context)
            return

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

    async def get_menu_for_context(self, user_context: Dict[str, Any], menu_identifier: Any = MenuType.MAIN) -> Optional[Menu]:
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
        # Handle both Menu objects and dictionaries
        if hasattr(menu, 'title'):
            menu_title = menu.title
            menu_description = getattr(menu, 'description', '')
            menu_header_text = getattr(menu, 'header_text', '')
            menu_footer_text = getattr(menu, 'footer_text', '')
            menu_max_columns = getattr(menu, 'max_columns', 2)
            menu_items = getattr(menu, 'items', [])
        else:
            # Assume it's a dictionary
            menu_title = menu.get('title', 'Menu')
            menu_description = menu.get('description', '')
            menu_header_text = menu.get('header_text', '')
            menu_footer_text = menu.get('footer_text', '')
            menu_max_columns = menu.get('max_columns', 2)
            menu_items = menu.get('items', [])
        
        text = f"<b>{menu_title}</b>\n\n{menu_description}"
        if menu_header_text:
            text = f"{menu_header_text}\n\n{text}"
        if menu_footer_text:
            text = f"{text}\n\n<i>{menu_footer_text}</i>"

        buttons = []
        row = []
        for item in menu_items:
            # Get item properties based on type (MenuItem object or dictionary)
            if isinstance(item, dict):
                item_text = item.get('text', 'Item')
                item_action_data = item.get('action_data', '')
            else:
                item_text = getattr(item, 'text', 'Item')
                item_action_data = getattr(item, 'action_data', '')
            
            row.append(InlineKeyboardButton(text=item_text, callback_data=item_action_data))
            if len(row) >= menu_max_columns:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        return text, reply_markup

    def set_coordinator_service(self, coordinator_service):
        """Set the coordinator service after initialization to avoid circular dependencies."""
        self.coordinator_service = coordinator_service
        logger.info("Coordinator service set for MenuHandlerSystem.")

    def register_handlers(self, dp):
        """Register handlers with the aiogram dispatcher."""
        from aiogram import types
        from aiogram.dispatcher.filters import Command
        
        # Register command handlers
        dp.register_message_handler(self.handle_start_command, Command("start"))
        dp.register_message_handler(self.handle_menu_command, Command("menu"))
        dp.register_message_handler(self.handle_help_command, Command("help"))
        
        # Register callback query handler
        dp.register_callback_query_handler(self.handle_callback)
        
        # Register a fallback message handler
        dp.register_message_handler(self.handle_fallback_message)
        
        logger.info("MenuHandlerSystem handlers registered with dispatcher")
        # Log all registered handlers for debugging
        for handler in dp.message_handlers.handlers:
            logger.debug(f"Registered message handler: {handler}")
        for handler in dp.callback_query_handlers.handlers:
            logger.debug(f"Registered callback handler: {handler}")

    async def handle_fallback_message(self, message: Message) -> None:
        """Handle any message that doesn't match other handlers."""
        if message.text and message.text.startswith('/'):
            # If it's an unknown command, treat it like a menu command
            await self.handle_menu_command_impl(message)
        else:
            # For non-command messages, you could implement other logic
            pass

    async def _handle_worthiness_explanation(self, query: CallbackQuery, user_context: Dict[str, Any]) -> None:
        """Handle worthiness explanation requests."""
        try:
            # Generate detailed worthiness explanation
            worthiness_explanation = await self.user_service.generate_worthiness_explanation(
                user_context.get("user_id"), 
                query.data
            )
            
            # Format the explanation as a message
            explanation_text = (
                f"<b>✨ Evaluación de Worthiness ✨</b>\n\n"
                f"<b>Puntaje Actual:</b> {worthiness_explanation['current_score']:.2f}\n"
                f"<b>Evaluación:</b> {worthiness_explanation['description_text']}\n\n"
                f"<b>Áreas de Mejora:</b>\n"
            )
            
            for area in worthiness_explanation['improvement_areas']:
                explanation_text += f"• {area.replace('_', ' ').title()}\n"
            
            explanation_text += "\n<b>Próximos Hitos:</b>\n"
            for milestone in worthiness_explanation['next_milestones']:
                explanation_text += f"• {milestone.replace('_', ' ').title()}\n"
            
            explanation_text += "\n<b>Orientación Personalizada:</b>\n"
            for guidance in worthiness_explanation['personalized_guidance']:
                explanation_text += f"• {guidance}\n"
            
            # Send the explanation as a new message
            await self.message_manager.bot.send_message(
                query.message.chat.id,
                explanation_text,
                parse_mode="HTML"
            )
            
            # Answer the callback query
            await query.answer("Evaluación de worthiness generada")

        except Exception as e:
            logger.error(f"Error handling worthiness explanation: {e}")
            await query.answer("Error generando la explicación", show_alert=True)

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

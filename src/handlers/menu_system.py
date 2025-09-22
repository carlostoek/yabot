import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from aiogram import Bot
from aiogram.types import Message, CallbackQuery

from src.handlers.base import BaseHandler
from src.handlers.menu_handler import MenuHandlerSystem
from src.handlers.callback_processor import CallbackProcessor
from src.ui.menu_factory import MenuFactory
from src.ui.message_manager import MessageManager
from src.ui.telegram_menu_renderer import TelegramMenuRenderer
from src.services.user import UserService
from src.events.bus import EventBus
from src.shared.monitoring.menu_performance import MenuPerformanceMonitor, MenuOperationType
from src.shared.resilience.circuit_breaker import CircuitBreaker
from src.utils.logger import get_logger

# Import centralized menu configuration
from src.ui.menu_config import menu_system_config

logger = get_logger(__name__)


class MenuSystemCoordinator:
    """
    Central coordinator for the complete menu system.

    Integrates all menu-related components to provide unified menu handling
    with performance monitoring, error handling, and event publishing.
    """

    def __init__(self, bot: Bot, event_bus: EventBus, user_service: UserService):
        """Initialize the Menu System Coordinator.

        Args:
            bot: Telegram Bot instance.
            event_bus: Event bus for publishing menu events.
            user_service: User service for context management.
        """
        self.bot = bot
        self.event_bus = event_bus
        self.user_service = user_service

        # Initialize core components
        self.menu_factory = MenuFactory()

        # Initialize message manager with error handling
        if hasattr(user_service, 'cache_manager') and user_service.cache_manager:
            self.message_manager = MessageManager(bot, user_service.cache_manager)
        else:
            logger.warning("UserService does not have cache_manager, using fallback CacheManager")
            from src.utils.cache_manager import CacheManager
            fallback_cache = CacheManager()
            self.message_manager = MessageManager(bot, fallback_cache)

        self.menu_renderer = TelegramMenuRenderer(bot)
        self.performance_monitor = MenuPerformanceMonitor(event_bus)

        # Initialize circuit breakers for resilience
        # Note: CircuitBreaker requires redis_client and service_name
        # For now, skip circuit breaker initialization to allow bot startup
        self.menu_generation_breaker = None
        self.callback_processing_breaker = None

        # Initialize handlers
        self.menu_handler = MenuHandlerSystem(
            user_service, event_bus, self.menu_factory, self.message_manager
        )
        self.callback_processor = CallbackProcessor(
            self.menu_factory, self.message_manager, self.performance_monitor
        )
        self.action_dispatcher = ActionDispatcher(event_bus)

        logger.info("MenuSystemCoordinator initialized successfully")

    async def initialize(self) -> bool:
        """Initialize all components of the menu system.

        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # Initialize message manager
            init_result = await self.message_manager.initialize()
            if not init_result:
                logger.error("Failed to initialize message manager")
                return False

            # Initialize performance monitoring
            await self.performance_monitor.reset_metrics()

            # Start background services
            self.message_manager.start_periodic_cleanup()

            logger.info("Menu system coordinator initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize menu system coordinator: {e}")
            return False

    @MenuPerformanceMonitor().monitor_operation(MenuOperationType.USER_INTERACTION)
    async def handle_menu_command(self, message: Message) -> Dict[str, Any]:
        """Handle menu command requests.

        Args:
            message: Telegram message requesting menu.

        Returns:
            Response data including menu and tracking info.
        """
        try:
            user_context = await self.user_service.get_enhanced_user_menu_context(str(message.from_user.id))

            # Determine menu type based on command or default to main
            command = message.text.strip() if message.text else "/menu"
            menu_id = menu_system_config.get_routing_rule(command.lstrip('/'))
            
            # Generate menu using centralized configuration
            menu = await self.menu_factory.create_menu(menu_id, user_context)
            if not menu:
                return {"success": False, "error": "Failed to generate menu"}

            # Render and send menu
            response = await self.menu_renderer.render_menu_response(menu)

            # Track message for cleanup
            sent_message = await self.bot.send_message(
                message.chat.id,
                response["text"],
                reply_markup=response.get("reply_markup")
            )

            await self.message_manager.track_message(
                message.chat.id,
                sent_message.message_id,
                "main_menu",
                is_main_menu=True
            )

            # Publish menu interaction event
            await self._publish_menu_interaction_event(
                user_context, menu.menu_id, "menu_command"
            )

            return {
                "success": True,
                "menu_id": menu.menu_id,
                "message_id": sent_message.message_id,
                "user_id": str(message.from_user.id)
            }

        except Exception as e:
            logger.error(f"Error handling menu command: {e}")
            return {"success": False, "error": str(e)}

    @MenuPerformanceMonitor().monitor_operation(MenuOperationType.CALLBACK_PROCESSING)
    async def handle_callback_query(self, callback_query: CallbackQuery) -> Dict[str, Any]:
        """Handle callback query processing.

        Args:
            callback_query: Telegram callback query.

        Returns:
            Response data including action result and tracking info.
        """
        try:
            user_context = await self.user_service.get_enhanced_user_menu_context(str(callback_query.from_user.id))

            # Process callback
            action_result = await self.callback_processor.process_callback(
                callback_query.data, user_context, callback_query.message.chat.id
            )

            if not action_result.success:
                await callback_query.answer("Error processing request", show_alert=True)
                return {"success": False, "error": action_result.response_message}

            # Handle worthiness explanations specially
            if callback_query.data.startswith("explain_divan_worthiness") or callback_query.data.startswith("worthiness_explanation"):
                await self._handle_worthiness_explanation(callback_query, user_context)
            elif action_result.new_menu:
                await self._handle_menu_update(callback_query, action_result, user_context)
            else:
                await self._handle_action_dispatch(callback_query, action_result, user_context)

            # Answer callback query
            await callback_query.answer(action_result.response_message)

            # Publish callback event
            await self._publish_callback_event(
                user_context, callback_query.data, action_result
            )

            return {
                "success": True,
                "action_type": action_result.response_message,
                "user_id": str(callback_query.from_user.id)
            }

        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await callback_query.answer("System error occurred", show_alert=True)
            return {"success": False, "error": str(e)}

    async def _handle_menu_update(self, callback_query: CallbackQuery,
                                action_result: Any, user_context: Dict[str, Any]) -> None:
        """Handle menu update after callback processing."""
        try:
            # Clean up old messages if enabled
            if action_result.cleanup_messages:
                await self.message_manager.delete_old_messages(callback_query.message.chat.id)

            # Render new menu
            response = await self.menu_renderer.render_menu_response(
                action_result.new_menu, edit_message=action_result.should_edit_menu
            )

            if action_result.should_edit_menu and callback_query.message:
                # Edit existing message
                await self.bot.edit_message_text(
                    response["text"],
                    callback_query.message.chat.id,
                    callback_query.message.message_id,
                    reply_markup=response.get("reply_markup")
                )
            else:
                # Send new message
                sent_message = await self.bot.send_message(
                    callback_query.message.chat.id,
                    response["text"],
                    reply_markup=response.get("reply_markup")
                )

                await self.message_manager.track_message(
                    callback_query.message.chat.id,
                    sent_message.message_id,
                    "main_menu",
                    is_main_menu=True
                )

        except Exception as e:
            logger.error(f"Error handling menu update: {e}")

    async def _handle_action_dispatch(self, callback_query: CallbackQuery,
                                    action_result: Any, user_context: Dict[str, Any]) -> None:
        """Handle action dispatch for non-menu callbacks."""
        try:
            await self.action_dispatcher.dispatch_action(
                action_result.response_message,
                callback_query.data,
                user_context
            )

        except Exception as e:
            logger.error(f"Error dispatching action: {e}")

    async def _handle_worthiness_explanation(self, callback_query: CallbackQuery, 
                                           user_context: Dict[str, Any]) -> None:
        """Handle worthiness explanation requests."""
        try:
            # Generate detailed worthiness explanation
            worthiness_explanation = await self.user_service.generate_worthiness_explanation(
                user_context.get("user_id"), 
                callback_query.data
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
            await self.bot.send_message(
                callback_query.message.chat.id,
                explanation_text,
                parse_mode="HTML"
            )
            
            # Answer the callback query
            await callback_query.answer("Evaluación de worthiness generada")

        except Exception as e:
            logger.error(f"Error handling worthiness explanation: {e}")
            await callback_query.answer("Error generando la explicación", show_alert=True)

    async def _publish_menu_interaction_event(self, user_context: Dict[str, Any],
                                            menu_id: str, interaction_type: str) -> None:
        """Publish menu interaction event."""
        try:
            event_data = {
                "user_id": user_context.get("user_id"),
                "menu_id": menu_id,
                "interaction_type": interaction_type,
                "timestamp": datetime.utcnow().isoformat(),
                "user_context": {
                    "role": user_context.get("role"),
                    "narrative_level": user_context.get("narrative_level"),
                    "has_vip": user_context.get("has_vip")
                }
            }

            await self.event_bus.publish("menu_interaction", event_data)

        except Exception as e:
            logger.error(f"Error publishing menu interaction event: {e}")

    async def _publish_callback_event(self, user_context: Dict[str, Any],
                                     callback_data: str, action_result: Any) -> None:
        """Publish callback processing event."""
        try:
            event_data = {
                "user_id": user_context.get("user_id"),
                "callback_data": callback_data,
                "success": action_result.success,
                "response_message": action_result.response_message,
                "timestamp": datetime.utcnow().isoformat()
            }

            await self.event_bus.publish("callback_processed", event_data)

        except Exception as e:
            logger.error(f"Error publishing callback event: {e}")

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information.

        Returns:
            System health metrics and status.
        """
        try:
            # Get performance metrics
            performance_metrics = await self.performance_monitor.get_real_time_metrics()

            # Get message manager statistics
            message_stats = await self.message_manager.get_performance_statistics()

            # Combine health information
            health_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "performance": performance_metrics,
                "message_management": message_stats,
                "components": {
                    "menu_factory": {"status": "healthy"},
                    "message_manager": {"status": "healthy"},
                    "callback_processor": {"status": "healthy"},
                    "action_dispatcher": {"status": "healthy"}
                },
                "overall_health_score": performance_metrics.get("health_score", 100)
            }

            return health_data

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "overall_health_score": 0
            }

    async def shutdown(self) -> None:
        """Gracefully shutdown the menu system coordinator."""
        try:
            # Shutdown message manager
            await self.message_manager.shutdown()

            # Reset performance metrics
            await self.performance_monitor.reset_metrics()

            logger.info("Menu system coordinator shutdown completed")

        except Exception as e:
            logger.error(f"Error during menu system shutdown: {e}")
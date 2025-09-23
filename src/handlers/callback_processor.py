
"""
Processes and dispatches callback queries from inline keyboards.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable

from src.ui.message_manager import MessageManager
from src.ui.menu_factory import MenuFactory, Menu
from src.events.bus import EventBus
from src.events.models import create_event

logger = logging.getLogger(__name__)

# --- Data Models (as per design document) ---

@dataclass
class CallbackActionResult:
    """Represents the result of processing a callback action."""
    success: bool
    response_message: Optional[str] = None
    new_menu: Optional[Menu] = None
    user_context_updates: Dict[str, Any] = field(default_factory=dict)
    events_to_publish: List[Dict[str, Any]] = field(default_factory=list)
    should_edit_menu: bool = True
    cleanup_messages: bool = True

# --- Action Dispatcher Implementation ---

ActionHandler = Callable[[str, Dict[str, Any]], Awaitable[CallbackActionResult]]

class ActionDispatcher:
    """Routes menu actions to appropriate modules and services."""
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._action_handlers: Dict[str, ActionHandler] = {}
        self.event_bus = event_bus
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register the default, built-in action handlers."""
        self.register_action_handler("gamification", self._handle_gamification_action)
        self.register_action_handler("daily_gift", self._handle_daily_gift_action)
        self.register_action_handler("shop", self._handle_shop_action)
        self.register_action_handler("inventory", self._handle_inventory_action)
        self.register_action_handler("vip", self._handle_vip_action)

    def register_action_handler(self, action_type: str, handler: ActionHandler):
        """Registers a new handler for a given action type."""
        logger.info(f"Registering handler for action type '{action_type}'.")
        self._action_handlers[action_type] = handler

    async def dispatch_action(
        self, action_type: str, action_data: str, user_context: Dict[str, Any]
    ) -> CallbackActionResult:
        """Looks up and executes the handler for a given action type."""
        # Publish event for menu interaction
        if self.event_bus:
            try:
                event = create_event(
                    "menu_interaction",
                    action_type=action_type,
                    action_data=action_data,
                    user_id=user_context.get("user_id"),
                    user_context=user_context
                )
                await self.event_bus.publish("menu_interaction", event.dict())
            except Exception as e:
                logger.error(f"Failed to publish menu interaction event: {e}")

        handler = self._action_handlers.get(action_type)
        if handler:
            logger.info(f"Dispatching action '{action_data}' to handler for '{action_type}'.")
            result = await handler(action_data, user_context)
            
            # Publish event for action completion
            if self.event_bus:
                try:
                    event = create_event(
                        "action_completed",
                        action_type=action_type,
                        action_data=action_data,
                        user_id=user_context.get("user_id"),
                        user_context=user_context,
                        success=result.success,
                        response_message=result.response_message
                    )
                    await self.event_bus.publish("action_completed", event.dict())
                except Exception as e:
                    logger.error(f"Failed to publish action completed event: {e}")
            
            return result
        else:
            logger.warning(f"No handler found for action type '{action_type}'.")
            result = CallbackActionResult(
                success=False,
                response_message=f"Action type '{action_type}' is not supported."
            )
            
            # Publish event for unsupported action
            if self.event_bus:
                try:
                    event = create_event(
                        "unsupported_action",
                        action_type=action_type,
                        action_data=action_data,
                        user_id=user_context.get("user_id"),
                        user_context=user_context
                    )
                    await self.event_bus.publish("unsupported_action", event.dict())
                except Exception as e:
                    logger.error(f"Failed to publish unsupported action event: {e}")
            
            return result

    async def _handle_gamification_action(
        self, action_data: str, user_context: Dict[str, Any]
    ) -> CallbackActionResult:
        """Handles gamification-related actions."""
        if action_data == "show_wallet":
            besitos = user_context.get('besitos_balance', 0)
            return CallbackActionResult(
                success=True,
                response_message=f"You have {besitos} besitos in your wallet.",
                cleanup_messages=False # Keep the menu open
            )
        
        return CallbackActionResult(
            success=False, 
            response_message=f"Unknown gamification action: {action_data}"
        )

# --- Main Class ---

class CallbackProcessor:
    """
    Processes Telegram callback queries, handling validation, compression,
    and routing to the appropriate action dispatcher or menu navigation.
    """

    def __init__(
        self,
        menu_factory: MenuFactory,
        message_manager: MessageManager,
        performance_monitor = None,
        event_bus: Optional[EventBus] = None
    ):
        self.menu_factory = menu_factory
        self.message_manager = message_manager
        self.performance_monitor = performance_monitor
        self.event_bus = event_bus

        # Initialize action dispatcher
        self.action_dispatcher = ActionDispatcher(event_bus)

        logger.info("CallbackProcessor initialized.")

    async def process_callback(
        self, callback_data: str, user_context: Dict[str, Any], chat_id: int
    ) -> CallbackActionResult:
        """
        Process the incoming callback data and return an action result.
        """
        # Publish event for callback received
        if self.event_bus:
            try:
                event = create_event(
                    "callback_received",
                    callback_data=callback_data,
                    user_id=user_context.get("user_id"),
                    chat_id=chat_id,
                    user_context=user_context
                )
                await self.event_bus.publish("callback_received", event.dict())
            except Exception as e:
                logger.error(f"Failed to publish callback received event: {e}")

        if not self.validate_callback_data(callback_data):
            logger.warning(f"Invalid callback data received: {callback_data}")

            # Send auto-cleanup error notification
            if hasattr(self.message_manager, 'send_auto_cleanup_notification'):
                await self.message_manager.send_auto_cleanup_notification(
                    chat_id,
                    "❌ Acción inválida. Por favor, intenta de nuevo.",
                    'error_message'
                )

            result = CallbackActionResult(success=False, response_message="Invalid action.")

            # Publish event for invalid callback
            if self.event_bus:
                try:
                    event = create_event(
                        "invalid_callback",
                        callback_data=callback_data,
                        user_id=user_context.get("user_id"),
                        chat_id=chat_id,
                        user_context=user_context
                    )
                    await self.event_bus.publish("invalid_callback", event.dict())
                except Exception as e:
                    logger.error(f"Failed to publish invalid callback event: {e}")

            return result

        # Handle worthiness explanation requests
        if callback_data.startswith("explain_divan_worthiness") or callback_data.startswith("worthiness_explanation"):
            result = CallbackActionResult(
                success=True,
                response_message="Worthiness explanation generated",
                should_edit_menu=False,
                cleanup_messages=False
            )
            
            # Publish event for worthiness explanation
            if self.event_bus:
                try:
                    event = create_event(
                        "worthiness_explanation_requested",
                        callback_data=callback_data,
                        user_id=user_context.get("user_id"),
                        chat_id=chat_id,
                        user_context=user_context
                    )
                    await self.event_bus.publish("worthiness_explanation_requested", event.dict())
                except Exception as e:
                    logger.error(f"Failed to publish worthiness explanation event: {e}")
            
            return result

        # Handle menu navigation
        if callback_data.startswith("menu:"):
            # Handle navigation
            menu_id = callback_data.split(":", 1)[1]
            new_menu = await self.menu_factory.create_menu(menu_id, user_context)
            result = CallbackActionResult(success=True, new_menu=new_menu)

            # Publish event for menu navigation
            if self.event_bus:
                try:
                    event = create_event(
                        "menu_navigation",
                        menu_id=menu_id,
                        user_id=user_context.get("user_id"),
                        chat_id=chat_id,
                        user_context=user_context
                    )
                    await self.event_bus.publish("menu_navigation", event.dict())
                except Exception as e:
                    logger.error(f"Failed to publish menu navigation event: {e}")

            return result
        else:
            # Handle action dispatch
            try:
                action_type, action_data_str = callback_data.split(":", 1)
            except ValueError:
                action_type = "generic_action"
                action_data_str = callback_data

            result = await self.action_dispatcher.dispatch_action(
                action_type, action_data_str, user_context
            )
            
            # Publish event for action processed
            if self.event_bus:
                try:
                    event = create_event(
                        "callback_processed",
                        action_type=action_type,
                        action_data=action_data_str,
                        user_id=user_context.get("user_id"),
                        chat_id=chat_id,
                        user_context=user_context,
                        success=result.success
                    )
                    await self.event_bus.publish("callback_processed", event.dict())
                except Exception as e:
                    logger.error(f"Failed to publish callback processed event: {e}")
            
            # Perform cleanup after an action is dispatched
            await self.cleanup_after_callback(chat_id)
        
        return result

    def validate_callback_data(self, data: str) -> bool:
        """Validate the callback data (e.g., length)."""
        return len(data.encode('utf-8')) <= 64

    def compress_callback_data(self, data: str) -> str:
        """
        Compress callback data if it exceeds Telegram's limits.
        Delegates to MenuFactory to ensure a centralized mapping.
        """
        # In a real implementation, this would be more robust.
        if not self.validate_callback_data(data):
            return self.menu_factory.compress_callback_data(data)
        return data

    async def cleanup_after_callback(self, chat_id: int) -> None:
        """
        Perform message cleanup after a callback has been processed.
        This might involve deleting temporary notification messages.
        """
        # Publish event for cleanup started
        if self.event_bus:
            try:
                event = create_event(
                    "cleanup_started",
                    chat_id=chat_id
                )
                await self.event_bus.publish("cleanup_started", event.dict())
            except Exception as e:
                logger.error(f"Failed to publish cleanup started event: {e}")

        # This is a placeholder; the exact logic might differ.
        # For now, we can assume it cleans up messages of type 'notification'.
        logger.debug(f"Performing post-callback cleanup for chat {chat_id}")
        # The main cleanup is handled by MenuHandlerSystem before sending a new menu,
        # so this can be reserved for special cases.
        
        # Publish event for cleanup completed
        if self.event_bus:
            try:
                event = create_event(
                    "cleanup_completed",
                    chat_id=chat_id
                )
                await self.event_bus.publish("cleanup_completed", event.dict())
            except Exception as e:
                logger.error(f"Failed to publish cleanup completed event: {e}")

    async def _handle_daily_gift_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle daily gift related actions."""
        try:
            if action_data == "daily_gift_menu":
                # Show daily gift status
                return CallbackActionResult(
                    success=True,
                    response_message="Mostrando estado de regalo diario",
                    should_edit_menu=False
                )
            elif action_data == "claim_daily_gift":
                # Try to connect to daily gift system
                try:
                    from src.modules.gamification.daily_gift import DailyGiftSystem
                    # Note: Would need actual Redis client and event bus here
                    # For now, return success simulation
                    return CallbackActionResult(
                        success=True,
                        response_message="¡Regalo diario reclamado! +10 besitos",
                        should_edit_menu=False
                    )
                except ImportError:
                    return CallbackActionResult(
                        success=False,
                        response_message="Sistema de regalos no disponible",
                        should_edit_menu=False
                    )
            else:
                return CallbackActionResult(
                    success=False,
                    response_message="Acción de regalo no reconocida",
                    should_edit_menu=False
                )
        except Exception as e:
            logger.error(f"Error handling daily gift action: {e}")
            return CallbackActionResult(
                success=False,
                response_message="Error en el sistema de regalos",
                should_edit_menu=False
            )

    async def _handle_shop_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle shop related actions."""
        try:
            if action_data.startswith("buy_"):
                # Extract item info from action_data
                parts = action_data.split("_")
                if len(parts) >= 3:
                    item_id = "_".join(parts[1:-1])
                    price = int(parts[-1])

                    besitos = user_context.get('besitos', 0)
                    if besitos >= price:
                        return CallbackActionResult(
                            success=True,
                            response_message=f"¡Compra exitosa! -{price} besitos",
                            user_context_updates={"besitos": besitos - price}
                        )
                    else:
                        return CallbackActionResult(
                            success=False,
                            response_message=f"Besitos insuficientes. Necesitas {price}, tienes {besitos}",
                            should_edit_menu=False
                        )
                else:
                    return CallbackActionResult(
                        success=False,
                        response_message="Formato de compra inválido",
                        should_edit_menu=False
                    )
            else:
                return CallbackActionResult(
                    success=True,
                    response_message="Mostrando opciones de tienda",
                    should_edit_menu=False
                )
        except Exception as e:
            logger.error(f"Error handling shop action: {e}")
            return CallbackActionResult(
                success=False,
                response_message="Error en la tienda",
                should_edit_menu=False
            )

    async def _handle_inventory_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle inventory/mochila related actions."""
        try:
            if action_data == "show_inventory_items":
                return CallbackActionResult(
                    success=True,
                    response_message="Mostrando tus items",
                    should_edit_menu=False
                )
            elif action_data == "show_resources":
                besitos = user_context.get('besitos', 0)
                return CallbackActionResult(
                    success=True,
                    response_message=f"💋 Besitos: {besitos}",
                    should_edit_menu=False
                )
            elif action_data == "show_progress":
                level = user_context.get('narrative_level', 1)
                worthiness = user_context.get('worthiness', 0.0)
                return CallbackActionResult(
                    success=True,
                    response_message=f"⭐ Nivel: {level} | 💫 Worthiness: {worthiness:.2f}",
                    should_edit_menu=False
                )
            else:
                return CallbackActionResult(
                    success=True,
                    response_message="Mostrando inventario",
                    should_edit_menu=False
                )
        except Exception as e:
            logger.error(f"Error handling inventory action: {e}")
            return CallbackActionResult(
                success=False,
                response_message="Error en inventario",
                should_edit_menu=False
            )

    async def _handle_vip_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle VIP related actions."""
        try:
            has_vip = user_context.get('has_vip', False)

            if action_data == "show_vip_benefits":
                benefits_text = (
                    "🌟 Beneficios VIP:\n"
                    "• 👑 Acceso al Diván exclusivo\n"
                    "• 💎 Besitos diarios dobles\n"
                    "• 🏆 Rankings y competencias\n"
                    "• 💰 Subastas exclusivas\n"
                    "• 🎨 Personalización avanzada"
                )
                return CallbackActionResult(
                    success=True,
                    response_message=benefits_text,
                    should_edit_menu=False
                )
            elif not has_vip:
                return CallbackActionResult(
                    success=False,
                    response_message="Esta función requiere membresía VIP",
                    should_edit_menu=False
                )
            else:
                return CallbackActionResult(
                    success=True,
                    response_message="Función VIP disponible",
                    should_edit_menu=False
                )
        except Exception as e:
            logger.error(f"Error handling VIP action: {e}")
            return CallbackActionResult(
                success=False,
                response_message="Error en función VIP",
                should_edit_menu=False
            )

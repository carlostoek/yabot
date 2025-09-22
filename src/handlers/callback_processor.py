
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
        action_dispatcher: ActionDispatcher, 
        message_manager: MessageManager, 
        menu_factory: MenuFactory,
        event_bus: Optional[EventBus] = None
    ):
        self.action_dispatcher = action_dispatcher
        self.message_manager = message_manager
        self.menu_factory = menu_factory
        self.event_bus = event_bus
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

        # Decompress if necessary (a real implementation would use the mapping)
        # For now, we assume no compression is used.

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

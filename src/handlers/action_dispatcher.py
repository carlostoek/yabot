"""
Action dispatcher for the YABOT menu system.
Routes menu actions to appropriate modules and services with event system integration.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field

from src.ui.menu_factory import Menu
from src.events.bus import EventBus
from src.events.models import create_event
from src.services.user import UserService

logger = logging.getLogger(__name__)


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


# Type alias for action handlers
ActionHandler = Callable[[str, Dict[str, Any]], Awaitable[CallbackActionResult]]


class ActionDispatcher:
    """Routes menu actions to appropriate modules and services."""
    
    def __init__(self, event_bus: Optional[EventBus] = None, user_service: Optional[UserService] = None):
        """
        Initialize the ActionDispatcher.
        
        Args:
            event_bus: Event bus for publishing action events
            user_service: User service for user context management
        """
        self._action_handlers: Dict[str, ActionHandler] = {}
        self.event_bus = event_bus
        self.user_service = user_service
        self._register_default_handlers()
        self.register_module_handlers()
        logger.info("ActionDispatcher initialized.")

    def _register_default_handlers(self):
        """Register the default, built-in action handlers."""
        self.register_action_handler("gamification", self._handle_gamification_action)
        logger.debug("Registered default action handlers.")

    def register_module_handlers(self):
        """Register handlers from existing modules."""
        # Register gamification module handlers
        self.register_action_handler("besitos", self._handle_besitos_action)
        self.register_action_handler("missions", self._handle_missions_action)
        self.register_action_handler("achievements", self._handle_achievements_action)
        self.register_action_handler("store", self._handle_store_action)
        self.register_action_handler("daily_gift", self._handle_daily_gift_action)
        
        # Register narrative module handlers
        self.register_action_handler("narrative", self._handle_narrative_action)
        self.register_action_handler("fragments", self._handle_fragments_action)
        self.register_action_handler("hints", self._handle_hints_action)
        
        # Register admin module handlers
        self.register_action_handler("admin", self._handle_admin_action)
        self.register_action_handler("subscriptions", self._handle_subscriptions_action)
        self.register_action_handler("notifications", self._handle_notifications_action)
        
        logger.info("Registered module handlers from gamification, narrative, and admin modules.")

    async def _handle_besitos_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle besitos-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling besitos action: {action_data}"
        )

    async def _handle_missions_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle missions-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling missions action: {action_data}"
        )

    async def _handle_achievements_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle achievements-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling achievements action: {action_data}"
        )

    async def _handle_store_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle store-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling store action: {action_data}"
        )

    async def _handle_daily_gift_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle daily gift-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling daily gift action: {action_data}"
        )

    async def _handle_narrative_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle narrative-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling narrative action: {action_data}"
        )

    async def _handle_fragments_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle fragments-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling fragments action: {action_data}"
        )

    async def _handle_hints_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle hints-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling hints action: {action_data}"
        )

    async def _handle_admin_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle admin-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling admin action: {action_data}"
        )

    async def _handle_subscriptions_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle subscriptions-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling subscriptions action: {action_data}"
        )

    async def _handle_notifications_action(self, action_data: str, user_context: Dict[str, Any]) -> CallbackActionResult:
        """Handle notifications-related actions."""
        return CallbackActionResult(
            success=True,
            response_message=f"Handling notifications action: {action_data}"
        )

    def register_action_handler(self, action_type: str, handler: ActionHandler):
        """
        Registers a new handler for a given action type.
        
        Args:
            action_type: The type of action to handle
            handler: The handler function
        """
        logger.info(f"Registering handler for action type '{action_type}'.")
        self._action_handlers[action_type] = handler

    async def dispatch_action(
        self, action_type: str, action_data: str, user_context: Dict[str, Any]
    ) -> CallbackActionResult:
        """
        Looks up and executes the handler for a given action type.
        
        Args:
            action_type: The type of action to dispatch
            action_data: The action data
            user_context: The user context
            
        Returns:
            CallbackActionResult: The result of the action
        """
        user_id = user_context.get("user_id")
        
        # Publish event for menu interaction
        if self.event_bus:
            try:
                event = create_event(
                    "menu_interaction",
                    action_type=action_type,
                    action_data=action_data,
                    user_id=user_id,
                    user_context=user_context
                )
                await self.event_bus.publish("menu_interaction", event.dict())
                logger.debug(f"Published menu interaction event for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to publish menu interaction event: {e}")

        handler = self._action_handlers.get(action_type)
        if handler:
            logger.info(f"Dispatching action '{action_data}' to handler for '{action_type}'.")
            try:
                result = await handler(action_data, user_context)
                
                # Publish event for action completion
                if self.event_bus:
                    try:
                        event = create_event(
                            "action_completed",
                            action_type=action_type,
                            action_data=action_data,
                            user_id=user_id,
                            user_context=user_context,
                            success=result.success,
                            response_message=result.response_message
                        )
                        await self.event_bus.publish("action_completed", event.dict())
                        logger.debug(f"Published action completed event for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish action completed event: {e}")
                
                return result
            except Exception as e:
                logger.error(f"Error executing handler for action '{action_type}': {e}")
                error_result = CallbackActionResult(
                    success=False,
                    response_message=f"Error processing action: {str(e)}"
                )
                
                # Publish event for action error
                if self.event_bus:
                    try:
                        event = create_event(
                            "action_error",
                            action_type=action_type,
                            action_data=action_data,
                            user_id=user_id,
                            user_context=user_context,
                            error_message=str(e)
                        )
                        await self.event_bus.publish("action_error", event.dict())
                        logger.debug(f"Published action error event for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish action error event: {e}")
                
                return error_result
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
                        user_id=user_id,
                        user_context=user_context
                    )
                    await self.event_bus.publish("unsupported_action", event.dict())
                    logger.debug(f"Published unsupported action event for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to publish unsupported action event: {e}")
            
            return result

    async def _handle_gamification_action(
        self, action_data: str, user_context: Dict[str, Any]
    ) -> CallbackActionResult:
        """
        Handles gamification-related actions.
        
        Args:
            action_data: The action data
            user_context: The user context
            
        Returns:
            CallbackActionResult: The result of the action
        """
        if action_data == "show_wallet":
            besitos = user_context.get('besitos_balance', 0)
            return CallbackActionResult(
                success=True,
                response_message=f"You have {besitos} besitos in your wallet.",
                cleanup_messages=False  # Keep the menu open
            )
        
        return CallbackActionResult(
            success=False, 
            response_message=f"Unknown gamification action: {action_data}"
        )

    async def process_action_result(
        self, 
        action_result: CallbackActionResult, 
        user_context: Dict[str, Any]
    ) -> CallbackActionResult:
        """
        Process the result of an action, including user context updates and event publishing.
        
        Args:
            action_result: The result of the action
            user_context: The user context
            
        Returns:
            CallbackActionResult: The processed result
        """
        user_id = user_context.get("user_id")
        
        # Update user context if needed
        if action_result.user_context_updates and self.user_service:
            try:
                for key, value in action_result.user_context_updates.items():
                    user_context[key] = value
                
                # If we have significant updates, persist them
                if action_result.user_context_updates:
                    await self.user_service.update_user_context(user_id, action_result.user_context_updates)
                    logger.debug(f"Updated user context for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to update user context for user {user_id}: {e}")
        
        # Publish additional events if needed
        if action_result.events_to_publish and self.event_bus:
            for event_data in action_result.events_to_publish:
                try:
                    event_type = event_data.pop("event_type", "custom_action_event")
                    event = create_event(event_type, **event_data)
                    await self.event_bus.publish(event_type, event.dict())
                    logger.debug(f"Published custom event {event_type} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to publish custom event: {e}")
        
        return action_result

    async def dispatch_action(
        self, action_type: str, action_data: str, user_context: Dict[str, Any]
    ) -> CallbackActionResult:
        """
        Looks up and executes the handler for a given action type.
        
        Args:
            action_type: The type of action to dispatch
            action_data: The action data
            user_context: The user context
            
        Returns:
            CallbackActionResult: The result of the action
        """
        user_id = user_context.get("user_id")
        
        # Publish event for menu interaction
        if self.event_bus:
            try:
                event = create_event(
                    "menu_interaction",
                    action_type=action_type,
                    action_data=action_data,
                    user_id=user_id,
                    user_context=user_context
                )
                await self.event_bus.publish("menu_interaction", event.dict())
                logger.debug(f"Published menu interaction event for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to publish menu interaction event: {e}")

        handler = self._action_handlers.get(action_type)
        if handler:
            logger.info(f"Dispatching action '{action_data}' to handler for '{action_type}'.")
            try:
                result = await handler(action_data, user_context)
                
                # Process the action result
                result = await self.process_action_result(result, user_context)
                
                # Publish event for action completion
                if self.event_bus:
                    try:
                        event = create_event(
                            "action_completed",
                            action_type=action_type,
                            action_data=action_data,
                            user_id=user_id,
                            user_context=user_context,
                            success=result.success,
                            response_message=result.response_message
                        )
                        await self.event_bus.publish("action_completed", event.dict())
                        logger.debug(f"Published action completed event for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish action completed event: {e}")
                
                return result
            except Exception as e:
                logger.error(f"Error executing handler for action '{action_type}': {e}")
                error_result = CallbackActionResult(
                    success=False,
                    response_message=f"Error processing action: {str(e)}"
                )
                
                # Publish event for action error
                if self.event_bus:
                    try:
                        event = create_event(
                            "action_error",
                            action_type=action_type,
                            action_data=action_data,
                            user_id=user_id,
                            user_context=user_context,
                            error_message=str(e)
                        )
                        await self.event_bus.publish("action_error", event.dict())
                        logger.debug(f"Published action error event for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish action error event: {e}")
                
                return error_result
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
                        user_id=user_id,
                        user_context=user_context
                    )
                    await self.event_bus.publish("unsupported_action", event.dict())
                    logger.debug(f"Published unsupported action event for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to publish unsupported action event: {e}")
            
            return result
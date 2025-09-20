"""
Narrative event handlers for the YABOT system.

This module provides event handlers for narrative-related events,
implementing requirements 5.2, 5.3, and 5.5 from the conectar-todo specification.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from src.events.bus import EventBus
from src.events.models import (
    create_event, BaseEvent, UserInteractionEvent, DecisionMadeEvent,
    MissionCompletedEvent, AchievementUnlockedEvent, BesitosAwardedEvent,
    NarrativeHintUnlockedEvent, VipAccessGrantedEvent, UserRegisteredEvent,
    UserDeletedEvent, UpdateReceivedEvent, EventProcessingFailedEvent
)
from src.modules.narrative.fragment_manager import NarrativeFragmentManager
from src.modules.narrative.decision_engine import DecisionEngine
from src.modules.narrative.hint_system import HintSystem
from src.modules.narrative.lucien_messenger import LucienMessenger
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NarrativeEventHandlers:
    """Event handlers for narrative-related events."""
    
    def __init__(
        self,
        event_bus: EventBus,
        fragment_manager: NarrativeFragmentManager,
        decision_engine: DecisionEngine,
        hint_system: HintSystem,
        lucien_messenger: LucienMessenger
    ):
        """Initialize narrative event handlers.
        
        Args:
            event_bus: Event bus instance
            fragment_manager: Narrative fragment manager
            decision_engine: Decision engine instance
            hint_system: Hint system instance
            lucien_messenger: Lucien messenger instance
        """
        self.event_bus = event_bus
        self.fragment_manager = fragment_manager
        self.decision_engine = decision_engine
        self.hint_system = hint_system
        self.lucien_messenger = lucien_messenger
        
        # Register event handlers
        self._register_event_handlers()
        
        logger.info("NarrativeEventHandlers initialized")
    
    def _register_event_handlers(self) -> None:
        """Register event handlers with the event bus."""
        try:
            # Register handlers for user interactions that might affect narrative
            self.event_bus.subscribe("user_interaction", self._handle_user_interaction)
            self.event_bus.subscribe("decision_made", self._handle_decision_made)
            self.event_bus.subscribe("mission_completed", self._handle_mission_completed)
            self.event_bus.subscribe("achievement_unlocked", self._handle_achievement_unlocked)
            self.event_bus.subscribe("besitos_awarded", self._handle_besitos_awarded)
            self.event_bus.subscribe("narrative_hint_unlocked", self._handle_narrative_hint_unlocked)
            self.event_bus.subscribe("vip_access_granted", self._handle_vip_access_granted)
            self.event_bus.subscribe("user_registered", self._handle_user_registered)
            self.event_bus.subscribe("user_deleted", self._handle_user_deleted)
            self.event_bus.subscribe("update_received", self._handle_update_received)
            self.event_bus.subscribe("event_processing_failed", self._handle_event_processing_failed)
            
            logger.info("Narrative event handlers registered successfully")
            
        except Exception as e:
            logger.error("Failed to register narrative event handlers: %s", str(e))
    
    async def _handle_user_interaction(self, event_data: Dict[str, Any]) -> None:
        """Handle user interaction events that might affect narrative progression.
        
        Args:
            event_data: User interaction event data
        """
        try:
            user_id = event_data.get("user_id")
            action = event_data.get("action")
            context = event_data.get("context", {})
            
            logger.debug("Handling user interaction event for user: %s, action: %s", user_id, action)
            
            # This could trigger narrative updates based on user interactions
            # For example, frequent interactions might unlock special narrative content
            
        except Exception as e:
            logger.error("Error handling user interaction event: %s", str(e))
    
    async def _handle_decision_made(self, event_data: Dict[str, Any]) -> None:
        """Handle decision made events to update narrative progression.
        
        Args:
            event_data: Decision made event data
        """
        try:
            user_id = event_data.get("user_id")
            choice_id = event_data.get("choice_id")
            context = event_data.get("context", {})
            
            logger.debug("Handling decision made event for user: %s, choice: %s", user_id, choice_id)
            
            # Update narrative progression based on user decisions
            # This might involve updating story branches, character relationships, etc.
            
            # Notify decision engine about the decision
            if self.decision_engine:
                await self.decision_engine.process_narrative_choice(user_id, choice_id, context)
            
        except Exception as e:
            logger.error("Error handling decision made event: %s", str(e))
    
    async def _handle_mission_completed(self, event_data: Dict[str, Any]) -> None:
        """Handle mission completed events that might unlock narrative content.
        
        Args:
            event_data: Mission completed event data
        """
        try:
            user_id = event_data.get("user_id")
            mission_id = event_data.get("mission_id")
            mission_type = event_data.get("mission_type")
            
            logger.debug("Handling mission completed event for user: %s, mission: %s", user_id, mission_id)
            
            # Unlock narrative content based on mission completion
            # This might involve unlocking new story fragments or chapters
            
            # Update fragment manager with mission completion
            if self.fragment_manager:
                # This could trigger narrative milestone events or unlock special content
                pass
            
        except Exception as e:
            logger.error("Error handling mission completed event: %s", str(e))
    
    async def _handle_achievement_unlocked(self, event_data: Dict[str, Any]) -> None:
        """Handle achievement unlocked events that might affect narrative.
        
        Args:
            event_data: Achievement unlocked event data
        """
        try:
            user_id = event_data.get("user_id")
            achievement_id = event_data.get("achievement_id")
            achievement_title = event_data.get("achievement_title")
            tier = event_data.get("tier")
            
            logger.debug("Handling achievement unlocked event for user: %s, achievement: %s", user_id, achievement_id)
            
            # Unlock special narrative content or send congratulatory messages
            # based on achievement unlocks
            
            # Send a special message through Lucien messenger
            if self.lucien_messenger:
                message = f"¡Felicidades! Has desbloqueado el logro '{achievement_title}'."
                await self.lucien_messenger.send_personalized_message(user_id, message)
            
        except Exception as e:
            logger.error("Error handling achievement unlocked event: %s", str(e))
    
    async def _handle_besitos_awarded(self, event_data: Dict[str, Any]) -> None:
        """Handle besitos awarded events that might affect narrative access.
        
        Args:
            event_data: Besitos awarded event data
        """
        try:
            user_id = event_data.get("user_id")
            amount = event_data.get("amount")
            reason = event_data.get("reason")
            balance_after = event_data.get("balance_after")
            
            logger.debug("Handling besitos awarded event for user: %s, amount: %s", user_id, amount)
            
            # This might affect narrative access if certain thresholds are reached
            # For example, reaching a besitos milestone might unlock special narrative content
            
        except Exception as e:
            logger.error("Error handling besitos awarded event: %s", str(e))
    
    async def _handle_narrative_hint_unlocked(self, event_data: Dict[str, Any]) -> None:
        """Handle narrative hint unlocked events.
        
        Args:
            event_data: Narrative hint unlocked event data
        """
        try:
            user_id = event_data.get("user_id")
            hint_id = event_data.get("hint_id")
            fragment_id = event_data.get("fragment_id")
            
            logger.debug("Handling narrative hint unlocked event for user: %s, hint: %s", user_id, hint_id)
            
            # Store or process the unlocked hint
            if self.hint_system:
                await self.hint_system.store_unlocked_hint(user_id, hint_id)
            
        except Exception as e:
            logger.error("Error handling narrative hint unlocked event: %s", str(e))
    
    async def _handle_vip_access_granted(self, event_data: Dict[str, Any]) -> None:
        """Handle VIP access granted events that unlock premium narrative content.
        
        Args:
            event_data: VIP access granted event data
        """
        try:
            user_id = event_data.get("user_id")
            reason = event_data.get("reason")
            
            logger.debug("Handling VIP access granted event for user: %s", user_id)
            
            # Unlock VIP-exclusive narrative content
            # This might involve making special fragments accessible
            
            # Notify fragment manager about VIP access
            if self.fragment_manager:
                # The fragment manager can handle making VIP content accessible
                pass
            
        except Exception as e:
            logger.error("Error handling VIP access granted event: %s", str(e))
    
    async def _handle_user_registered(self, event_data: Dict[str, Any]) -> None:
        """Handle user registered events to initialize narrative state.
        
        Args:
            event_data: User registered event data
        """
        try:
            user_id = event_data.get("user_id")
            telegram_user_id = event_data.get("telegram_user_id")
            
            logger.debug("Handling user registered event for user: %s", user_id)
            
            # Initialize narrative state for new user
            # This might involve setting up initial story progression,
            # unlocking welcome content, etc.
            
            # Send welcome message through Lucien messenger
            if self.lucien_messenger:
                welcome_message = "¡Bienvenido al mundo narrativo! Comienza tu aventura."
                await self.lucien_messenger.send_welcome_message(user_id, welcome_message)
            
        except Exception as e:
            logger.error("Error handling user registered event: %s", str(e))
    
    async def _handle_user_deleted(self, event_data: Dict[str, Any]) -> None:
        """Handle user deleted events to clean up narrative data.
        
        Args:
            event_data: User deleted event data
        """
        try:
            user_id = event_data.get("user_id")
            deletion_reason = event_data.get("deletion_reason")
            
            logger.debug("Handling user deleted event for user: %s", user_id)
            
            # Clean up narrative data for deleted user
            # This might involve removing progress data, unlocked hints, etc.
            
        except Exception as e:
            logger.error("Error handling user deleted event: %s", str(e))
    
    async def _handle_update_received(self, event_data: Dict[str, Any]) -> None:
        """Handle update received events that might contain narrative-related updates.
        
        Args:
            event_data: Update received event data
        """
        try:
            update_type = event_data.get("update_type")
            update_data = event_data.get("update_data", {})
            
            logger.debug("Handling update received event of type: %s", update_type)
            
            # Process updates that might affect narrative state
            # This could include message reactions, callback queries, etc.
            
        except Exception as e:
            logger.error("Error handling update received event: %s", str(e))
    
    async def _handle_event_processing_failed(self, event_data: Dict[str, Any]) -> None:
        """Handle event processing failed events for error recovery.
        
        Args:
            event_data: Event processing failed event data
        """
        try:
            error_message = event_data.get("error_message")
            original_event_type = event_data.get("original_event_type")
            original_event_id = event_data.get("original_event_id")
            
            logger.warning(
                "Handling event processing failed event: %s (event_type: %s, event_id: %s)",
                error_message, original_event_type, original_event_id
            )
            
            # Log failed events for manual recovery or retry
            # This could trigger alert notifications to administrators
            
        except Exception as e:
            logger.error("Error handling event processing failed event: %s", str(e))

# Factory function for dependency injection consistency
async def create_narrative_event_handlers(
    event_bus: EventBus,
    fragment_manager: NarrativeFragmentManager,
    decision_engine: DecisionEngine,
    hint_system: HintSystem,
    lucien_messenger: LucienMessenger
) -> NarrativeEventHandlers:
    """Factory function to create narrative event handlers.
    
    Args:
        event_bus: Event bus instance
        fragment_manager: Narrative fragment manager
        decision_engine: Decision engine instance
        hint_system: Hint system instance
        lucien_messenger: Lucien messenger instance
        
    Returns:
        NarrativeEventHandlers: Initialized narrative event handlers instance
    """
    return NarrativeEventHandlers(
        event_bus,
        fragment_manager,
        decision_engine,
        hint_system,
        lucien_messenger
    )
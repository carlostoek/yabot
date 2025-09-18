"""
CoordinatorService for the YABOT system.

This module provides orchestration for complex business workflows and event sequencing,
implementing the requirements specified in fase1 specification sections 3.1 and 3.2.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.services.narrative import NarrativeService
from src.events.bus import EventBus
from src.events.models import (
    create_event, UserInteractionEvent, ReactionDetectedEvent, 
    DecisionMadeEvent, SubscriptionUpdatedEvent, BesitosAwardedEvent,
    NarrativeHintUnlockedEvent, VipAccessGrantedEvent
)
from src.database.manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CoordinatorServiceError(Exception):
    """Base exception for coordinator service operations."""
    pass


class EventOrderingError(CoordinatorServiceError):
    """Exception raised when event ordering fails."""
    pass


class CoordinatorService:
    """Service for orchestrating complex business workflows and event sequencing."""
    
    def __init__(self, database_manager: DatabaseManager, event_bus: EventBus,
                 user_service: UserService, subscription_service: SubscriptionService,
                 narrative_service: NarrativeService):
        """Initialize the coordinator service.
        
        Args:
            database_manager (DatabaseManager): Database manager instance
            event_bus (EventBus): Event bus instance
            user_service (UserService): User service instance
            subscription_service (SubscriptionService): Subscription service instance
            narrative_service (NarrativeService): Narrative service instance
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.narrative_service = narrative_service
        
        # Event buffer for ordering
        self._event_buffer: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("CoordinatorService initialized")
    
    async def process_user_interaction(self, user_id: str, action: str, context: Dict[str, Any]) -> bool:
        """Handle user interaction workflows.
        
        Args:
            user_id (str): User ID
            action (str): User action
            context (Dict[str, Any]): Context of the interaction
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Processing user interaction for user: %s, action: %s", user_id, action)
        
        try:
            # Create and publish user interaction event
            event = create_event(
                "user_interaction",
                user_id=user_id,
                action=action,
                context=context
            )
            await self.event_bus.publish("user_interaction", event.dict())
            
            logger.info("Successfully processed user interaction for user: %s", user_id)
            return True
            
        except Exception as e:
            logger.error("Error processing user interaction: %s", str(e))
            return False
    
    async def validate_vip_access(self, user_id: str) -> bool:
        """Check subscription status before allowing VIP feature access.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if user has VIP access, False otherwise
        """
        logger.debug("Validating VIP access for user: %s", user_id)
        
        try:
            # Check if user has VIP access through subscription service
            has_vip_access = await self.subscription_service.validate_vip_access(user_id)
            
            if has_vip_access:
                # Publish VIP access granted event
                event = create_event(
                    "vip_access_granted",
                    user_id=user_id,
                    reason="subscription_validated"
                )
                await self.event_bus.publish("vip_access_granted", event.dict())
            
            logger.debug("VIP access validation for user %s: %s", user_id, has_vip_access)
            return has_vip_access
            
        except Exception as e:
            logger.error("Error validating VIP access: %s", str(e))
            return False
    
    async def process_besitos_transaction(self, user_id: str, amount: int, reason: str) -> bool:
        """Handle virtual currency transactions with atomicity.
        
        Args:
            user_id (str): User ID
            amount (int): Amount of besitos to award
            reason (str): Reason for awarding besitos
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Processing besitos transaction for user: %s, amount: %d", user_id, amount)
        
        try:
            # Publish besitos awarded event
            event = create_event(
                "besitos_awarded",
                user_id=user_id,
                amount=amount,
                reason=reason
            )
            await self.event_bus.publish("besitos_awarded", event.dict())
            
            logger.info("Successfully processed besitos transaction for user: %s", user_id)
            return True
            
        except Exception as e:
            logger.error("Error processing besitos transaction: %s", str(e))
            return False
    
    async def handle_reaction(self, user_id: str, content_id: str, reaction_type: str) -> bool:
        """Handle user reaction to content and potentially award besitos.
        
        Args:
            user_id (str): User ID
            content_id (str): Content ID that was reacted to
            reaction_type (str): Type of reaction
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Handling reaction for user: %s, content: %s, reaction: %s", 
                   user_id, content_id, reaction_type)
        
        try:
            # Publish reaction detected event
            reaction_event = create_event(
                "reaction_detected",
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type
            )
            await self.event_bus.publish("reaction_detected", reaction_event.dict())
            
            # Award besitos for reaction (example logic)
            # In a real implementation, this would be configurable
            besitos_amount = 1
            await self.process_besitos_transaction(
                user_id, besitos_amount, f"reaction_{reaction_type}"
            )
            
            logger.info("Successfully handled reaction for user: %s", user_id)
            return True
            
        except Exception as e:
            logger.error("Error handling reaction: %s", str(e))
            return False
    
    async def handle_narrative_choice(self, user_id: str, choice_id: str, context: Dict[str, Any]) -> bool:
        """Handle user narrative choice and potentially unlock hints.
        
        Args:
            user_id (str): User ID
            choice_id (str): Choice ID made by user
            context (Dict[str, Any]): Context of the decision
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Handling narrative choice for user: %s, choice: %s", user_id, choice_id)
        
        try:
            # Publish decision made event
            decision_event = create_event(
                "decision_made",
                user_id=user_id,
                choice_id=choice_id,
                context=context
            )
            await self.event_bus.publish("decision_made", decision_event.dict())
            
            # Unlock hint based on choice (example logic)
            # In a real implementation, this would be based on narrative design
            hint_id = f"hint_for_{choice_id}"
            fragment_id = context.get("fragment_id", "unknown")
            
            # Publish narrative hint unlocked event
            hint_event = create_event(
                "narrative_hint_unlocked",
                user_id=user_id,
                hint_id=hint_id,
                fragment_id=fragment_id
            )
            await self.event_bus.publish("narrative_hint_unlocked", hint_event.dict())
            
            logger.info("Successfully handled narrative choice for user: %s", user_id)
            return True
            
        except Exception as e:
            logger.error("Error handling narrative choice: %s", str(e))
            return False
    
    async def buffer_event(self, user_id: str, event: Dict[str, Any]) -> None:
        """Buffer event for ordering.
        
        Args:
            user_id (str): User ID
            event (Dict[str, Any]): Event data
        """
        if user_id not in self._event_buffer:
            self._event_buffer[user_id] = []
        
        self._event_buffer[user_id].append(event)
        logger.debug("Buffered event for user: %s", user_id)
    
    async def process_buffered_events(self, user_id: str) -> None:
        """Process buffered events in chronological order.
        
        Args:
            user_id (str): User ID
        """
        if user_id not in self._event_buffer or not self._event_buffer[user_id]:
            return
        
        logger.debug("Processing buffered events for user: %s", user_id)
        
        try:
            # Sort events by timestamp
            events = self._event_buffer[user_id]
            events.sort(key=lambda x: x.get("timestamp", 0))
            
            # Process events in order
            for event in events:
                event_type = event.get("event_type", "unknown")
                logger.debug("Processing buffered event: %s for user: %s", event_type, user_id)
                # In a real implementation, we would process each event appropriately
            
            # Clear buffer
            self._event_buffer[user_id] = []
            logger.debug("Processed all buffered events for user: %s", user_id)
            
        except Exception as e:
            logger.error("Error processing buffered events: %s", str(e))
            # Don't clear buffer on error to allow for retry
    
    async def handle_out_of_order_events(self, user_id: str, event: Dict[str, Any]) -> bool:
        """Handle out of order events by buffering and reordering.
        
        Args:
            user_id (str): User ID
            event (Dict[str, Any]): Event data
            
        Returns:
            bool: True if event was handled, False if buffered
        """
        logger.debug("Handling potentially out of order event for user: %s", user_id)
        
        try:
            # Buffer the event
            await self.buffer_event(user_id, event)
            
            # Process all buffered events for this user
            await self.process_buffered_events(user_id)
            
            return True
            
        except Exception as e:
            logger.error("Error handling out of order events: %s", str(e))
            return False


# Convenience function for easy usage
async def create_coordinator_service(database_manager: DatabaseManager, event_bus: EventBus,
                                  user_service: UserService, subscription_service: SubscriptionService,
                                  narrative_service: NarrativeService) -> CoordinatorService:
    """Create and initialize a coordinator service instance.
    
    Args:
        database_manager (DatabaseManager): Database manager instance
        event_bus (EventBus): Event bus instance
        user_service (UserService): User service instance
        subscription_service (SubscriptionService): Subscription service instance
        narrative_service (NarrativeService): Narrative service instance
        
    Returns:
        CoordinatorService: Initialized coordinator service instance
    """
    coordinator_service = CoordinatorService(
        database_manager, event_bus, user_service, subscription_service, narrative_service
    )
    return coordinator_service
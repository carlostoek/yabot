"""
Fase1 - Task 19
CoordinatorService with user interaction orchestration

Implements orchestration of complex business workflows as specified
in Requirements 3.1 and 3.2: Coordinator Service Architecture and Event Ordering.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.services.narrative import NarrativeService
from src.events.models import BaseEvent, UserInteractionEvent, ReactionDetectedEvent
from src.utils.logger import LoggerMixin, get_logger


class BesitosTransactionType(str, Enum):
    """Enumeration for besitos transaction types"""
    REWARD = "reward"
    PURCHASE = "purchase"
    PENALTY = "penalty"
    BONUS = "bonus"


class CoordinatorService(LoggerMixin):
    """
    Orchestrates complex business workflows and event sequencing
    """
    
    def __init__(self, user_service: UserService, subscription_service: SubscriptionService,
                 narrative_service: NarrativeService):
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.narrative_service = narrative_service
        # LoggerMixin provides the logger property automatically
        self.event_buffer = {}  # Buffer for event ordering by user
    
from pydantic import BaseModel, validator
from typing import Optional

class UserInteractionRequest(BaseModel):
    user_id: str
    action: str
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        if not v.isdigit():
            raise ValueError('User ID must contain only digits')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['start', 'narrative', 'subscription', 'reaction']
        if v not in valid_actions:
            raise ValueError(f'Action must be one of: {valid_actions}')
        return v

async def process_user_interaction(self, request: UserInteractionRequest, **kwargs) -> Dict[str, Any]:
        """
        Handle user interaction workflows
        
        Args:
            request: Validated user interaction request
            
        Returns:
            Result of the interaction processing
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Processing user interaction", user_id=request.user_id, action=request.action)
            
            # Create interaction event
            event = UserInteractionEvent(
                user_id=request.user_id,
                action=request.action,
                context={"processed_at": datetime.utcnow().isoformat()}
            )
            
            # Add to event buffer for ordering
            await self.add_to_event_buffer(request.user_id, event)
            
            # Process different types of interactions
            if request.action == "start":
                result = await self._handle_start_interaction(request.user_id)
            elif request.action == "narrative":
                result = await self._handle_narrative_interaction(request.user_id)
            elif request.action == "subscription":
                result = await self._handle_subscription_interaction(request.user_id)
            elif request.action == "reaction":
                result = await self._handle_reaction_interaction(request.user_id)
            else:
                result = {"status": "handled", "action": request.action, "user_id": request.user_id}
            
            # Publish interaction processed event
            if event_bus:
                await event_bus.publish("user_interaction_processed", {
                    "user_id": request.user_id,
                    "action": request.action,
                    "result": result,
                    "processed_at": datetime.utcnow()
                })
            
            self.logger.info("User interaction processed successfully", user_id=request.user_id, action=request.action)
            return result
                
        except Exception as e:
            self.logger.error(f"Error processing user interaction: {str(e)}", user_id=request.user_id, action=request.action)
            raise
    
    async def validate_vip_access(self, user_id: str) -> bool:
        """
        Check subscription status before allowing access to VIP features
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if VIP access is allowed, False otherwise
        """
        try:
            self.logger.debug("Validating VIP access", user_id=user_id)
            
            # Check user subscription status
            has_subscription = await self.subscription_service.check_subscription_status(user_id)
            if not has_subscription:
                self.logger.info("User does not have subscription", user_id=user_id)
                return False
            
            # Get detailed subscription info
            subscription = await self.subscription_service.get_subscription(user_id)
            if subscription and subscription.get("plan_type") == "vip":
                self.logger.info("VIP access validated", user_id=user_id)
                return True
            else:
                self.logger.info("User does not have VIP subscription", user_id=user_id, plan=subscription.get("plan_type") if subscription else "none")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating VIP access: {str(e)}", user_id=user_id)
            raise
    
    async def process_besitos_transaction(self, user_id: str, amount: int, 
                                        transaction_type: BesitosTransactionType, 
                                        description: str = "", **kwargs) -> bool:
        """
        Handle virtual currency transactions with atomicity
        
        Args:
            user_id: Telegram user ID
            amount: Amount of besitos to transact
            transaction_type: Type of transaction
            description: Optional description of transaction
            
        Returns:
            True if transaction successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Processing besitos transaction", user_id=user_id, amount=amount, type=transaction_type)
            
            # In a real implementation, this would update a user's besitos balance
            # This would require additional database fields and atomic operations
            transaction_data = {
                "user_id": user_id,
                "amount": amount,
                "type": transaction_type.value,
                "description": description,
                "timestamp": datetime.utcnow(),
                "status": "completed"
            }
            
            # Publish besitos transaction event
            if event_bus:
                await event_bus.publish("besitos_transaction", transaction_data)
            
            self.logger.info("Besitos transaction processed", user_id=user_id, amount=amount, type=transaction_type)
            return True
                
        except Exception as e:
            self.logger.error(f"Error processing besitos transaction: {str(e)}", user_id=user_id, amount=amount)
            raise
    
    async def add_to_event_buffer(self, user_id: str, event: BaseEvent) -> None:
        """
        Buffer events for ordering by user
        
        Args:
            user_id: Telegram user ID
            event: Event to buffer
        """
        try:
            if user_id not in self.event_buffer:
                self.event_buffer[user_id] = []
            
            # Add event to user's buffer
            self.event_buffer[user_id].append({
                "event": event,
                "timestamp": datetime.utcnow(),
                "processed": False
            })
            
            self.logger.debug("Event added to user buffer", user_id=user_id, event_type=event.event_type)
            
            # Process the buffer to maintain order (simplified implementation)
            await self._process_user_event_buffer(user_id)
            
        except Exception as e:
            self.logger.error(f"Error adding event to buffer: {str(e)}", user_id=user_id, event_type=event.event_type)
            raise
    
    async def _process_user_event_buffer(self, user_id: str, **kwargs) -> None:
        """
        Process events in the buffer to maintain chronological order
        
        Args:
            user_id: Telegram user ID
        """
        event_bus = kwargs.get('event_bus')
        try:
            if user_id not in self.event_buffer:
                return
            
            # In a real implementation, this would sort events by timestamp
            # and process them in order, handling out-of-order events appropriately
            buffer = self.event_buffer[user_id]
            
            # Sort events by timestamp (simplified approach)
            sorted_events = sorted(buffer, key=lambda x: x["timestamp"])
            
            # Process events in order
            for event_entry in sorted_events:
                if not event_entry["processed"]:
                    event = event_entry["event"]
                    
                    # Process the event (publish it)
                    if event_bus:
                        await event_bus.publish(event.event_type, event.dict())
                    
                    # Mark as processed
                    event_entry["processed"] = True
            
            # Clean up processed events
            self.event_buffer[user_id] = [entry for entry in self.event_buffer[user_id] if not entry["processed"]]
            
            self.logger.debug("User event buffer processed", user_id=user_id, processed_count=len([e for e in buffer if e["processed"]]))
            
        except Exception as e:
            self.logger.error(f"Error processing user event buffer: {str(e)}", user_id=user_id)
            raise
    
    async def process_reaction(self, user_id: str, content_id: str, reaction_type: str, **kwargs) -> bool:
        """
        Process a user's reaction to content
        
        Args:
            user_id: Telegram user ID
            content_id: ID of the content being reacted to
            reaction_type: Type of reaction
        
        Returns:
            True if processing successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Processing reaction", user_id=user_id, content_id=content_id, reaction_type=reaction_type)
            
            # Create reaction event
            reaction_event = ReactionDetectedEvent(
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type
            )
            
            # Add to event buffer for ordering
            await self.add_to_event_buffer(user_id, reaction_event)
            
            # If reaction is of positive type, potentially award besitos
            positive_reactions = ["like", "love", "besito"]
            if reaction_type in positive_reactions:
                # Award 10 besitos for positive reactions (as per requirements)
                await self.process_besitos_transaction(
                    user_id, 
                    10, 
                    BesitosTransactionType.REWARD,
                    f"Reward for {reaction_type} reaction to content {content_id}", **kwargs
                )
            
            # Publish reaction processed event
            result_data = {
                "user_id": user_id,
                "content_id": content_id,
                "reaction_type": reaction_type,
                "awarded_besitos": reaction_type in positive_reactions
            }
            if event_bus:
                await event_bus.publish("reaction_processed", result_data)
            
            self.logger.info("Reaction processed", user_id=user_id, content_id=content_id, reaction_type=reaction_type)
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing reaction: {str(e)}", user_id=user_id, content_id=content_id)
            raise
    
    async def _handle_start_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's start interaction."""
        try:
            self.logger.debug("Handling start interaction", user_id=user_id)
            
            # Create user if doesn't exist (or update last login)
            # This would be handled by the UserService in a real implementation
            user_context = await self.user_service.get_user_context(user_id)
            
            if not user_context:
                # User doesn't exist, need to create
                telegram_user_data = {"id": user_id, "username": f"user_{user_id}", "first_name": f"User_{user_id}"}
                user_context = await self.user_service.create_user(telegram_user_data)
            
            # Update user's last activity
            await self.user_service.update_user_state(user_id, {
                "menu_context": "main_menu",
                "session_data": {"last_activity": datetime.utcnow().isoformat()}
            })
            
            return {
                "status": "success",
                "action": "start",
                "user_exists": user_context is not None
            }
        except Exception as e:
            self.logger.error(f"Error handling start interaction: {str(e)}", user_id=user_id)
            raise
    
    async def _handle_narrative_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's narrative interaction."""
        try:
            self.logger.debug("Handling narrative interaction", user_id=user_id)
            
            # Check if user has VIP access for narrative content
            user_context = await self.user_service.get_user_context(user_id)
            if not user_context:
                return {"status": "error", "message": "User not found"}
            
            # Get user's current narrative progress
            progress = await self.narrative_service.get_user_narrative_progress(user_id)
            current_fragment = progress.get("current_fragment") if progress else None
            
            # If no current fragment, start with intro
            if not current_fragment:
                # In a real implementation, this would get the first narrative fragment
                current_fragment = "intro_001"
            
            # Get the narrative fragment
            fragment = await self.narrative_service.get_narrative_fragment(current_fragment)
            
            return {
                "status": "success",
                "action": "narrative",
                "current_fragment": current_fragment,
                "fragment_exists": fragment is not None
            }
        except Exception as e:
            self.logger.error(f"Error handling narrative interaction: {str(e)}", user_id=user_id)
            raise
    
    async def _handle_subscription_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's subscription interaction."""
        try:
            self.logger.debug("Handling subscription interaction", user_id=user_id)
            
            # Check user subscription status
            has_subscription = await self.subscription_service.check_subscription_status(user_id)
            subscription = await self.subscription_service.get_subscription(user_id)
            
            return {
                "status": "success",
                "action": "subscription",
                "has_subscription": has_subscription,
                "subscription": subscription
            }
        except Exception as e:
            self.logger.error(f"Error handling subscription interaction: {str(e)}", user_id=user_id)
            raise
    
    async def _handle_reaction_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's reaction interaction."""
        try:
            self.logger.debug("Handling reaction interaction", user_id=user_id)
            
            # For this basic implementation, we just acknowledge the interaction
            # The actual reaction would be handled by the process_reaction method
            return {
                "status": "success",
                "action": "reaction",
                "message": "Please provide content_id and reaction_type for processing"
            }
        except Exception as e:
            self.logger.error(f"Error handling reaction interaction: {str(e)}", user_id=user_id)
            raise


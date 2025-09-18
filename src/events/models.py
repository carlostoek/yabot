"""
Event models for the YABOT system.

This module provides Pydantic models for event serialization and validation as required by the fase1 specification.
These models follow the same patterns as src/core/models.py.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.core.models import BaseModel as CoreBaseModel


class BaseEvent(CoreBaseModel):
    """Base event model with common fields for all events."""
    
    event_id: str = Field(..., description="Unique identifier for the event")
    event_type: str = Field(..., description="Type of the event")
    timestamp: datetime = Field(..., description="Timestamp when the event occurred")
    correlation_id: str = Field(..., description="Correlation ID for tracing related events")
    user_id: Optional[str] = Field(None, description="User ID associated with the event")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")


class UserInteractionEvent(BaseEvent):
    """Event published when a user interacts with the bot."""
    
    action: str = Field(..., description="User action (e.g., 'start', 'menu', 'choice')")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context of the interaction")


class ReactionDetectedEvent(BaseEvent):
    """Event published when a user reacts to content."""
    
    content_id: str = Field(..., description="ID of the content that was reacted to")
    reaction_type: str = Field(..., description="Type of reaction (e.g., 'like', 'love', 'laugh')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional reaction metadata")


class DecisionMadeEvent(BaseEvent):
    """Event published when a user makes a narrative choice."""
    
    choice_id: str = Field(..., description="ID of the choice made")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context of the decision")


class SubscriptionUpdatedEvent(BaseEvent):
    """Event published when a user's subscription status changes."""
    
    plan_type: str = Field(..., description="Type of subscription plan")
    status: str = Field(..., description="New subscription status")
    start_date: datetime = Field(..., description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")


class BesitosAwardedEvent(BaseEvent):
    """Event published when besitos are awarded to a user."""
    
    amount: int = Field(..., description="Number of besitos awarded")
    reason: str = Field(..., description="Reason for awarding besitos")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional award metadata")


class NarrativeHintUnlockedEvent(BaseEvent):
    """Event published when a narrative hint is unlocked for a user."""
    
    hint_id: str = Field(..., description="ID of the unlocked hint")
    fragment_id: str = Field(..., description="ID of the narrative fragment")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional hint metadata")


class VipAccessGrantedEvent(BaseEvent):
    """Event published when VIP access is granted to a user."""
    
    reason: str = Field(..., description="Reason for granting VIP access")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional access metadata")


class UserRegisteredEvent(BaseEvent):
    """Event published when a user is registered."""
    
    telegram_user_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    language_code: Optional[str] = Field(None, description="Language code")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional registration metadata")


class UserDeletedEvent(BaseEvent):
    """Event published when a user is deleted."""
    
    deletion_reason: str = Field(..., description="Reason for user deletion")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional deletion metadata")


class UpdateReceivedEvent(BaseEvent):
    """Event published when an update is received from Telegram."""
    
    update_type: str = Field(..., description="Type of update received")
    update_data: Dict[str, Any] = Field(..., description="Raw update data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional update metadata")


class EventProcessingFailedEvent(BaseEvent):
    """Event published when event processing fails."""
    
    error_message: str = Field(..., description="Error message")
    original_event_type: str = Field(..., description="Original event type")
    original_event_id: str = Field(..., description="Original event ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional error metadata")


# Event type constants for easy reference
EVENT_MODELS = {
    "user_interaction": UserInteractionEvent,
    "reaction_detected": ReactionDetectedEvent,
    "decision_made": DecisionMadeEvent,
    "subscription_updated": SubscriptionUpdatedEvent,
    "besitos_awarded": BesitosAwardedEvent,
    "narrative_hint_unlocked": NarrativeHintUnlockedEvent,
    "vip_access_granted": VipAccessGrantedEvent,
    "user_registered": UserRegisteredEvent,
    "user_deleted": UserDeletedEvent,
    "update_received": UpdateReceivedEvent,
    "event_processing_failed": EventProcessingFailedEvent
}


def create_event(event_type: str, **kwargs) -> BaseEvent:
    """Factory function to create event instances.
    
    Args:
        event_type (str): Type of event to create
        **kwargs: Event-specific parameters
        
    Returns:
        BaseEvent: Created event instance
        
    Raises:
        ValueError: If event_type is not supported
    """
    if event_type not in EVENT_MODELS:
        raise ValueError(f"Unsupported event type: {event_type}")
    
    # Add common fields if not provided
    if "event_id" not in kwargs:
        import uuid
        kwargs["event_id"] = str(uuid.uuid4())
    
    if "timestamp" not in kwargs:
        from datetime import datetime
        kwargs["timestamp"] = datetime.utcnow()
    
    if "correlation_id" not in kwargs:
        import uuid
        kwargs["correlation_id"] = str(uuid.uuid4())
    
    # Ensure event_type is set
    kwargs["event_type"] = event_type
    
    # Create and return the event
    return EVENT_MODELS[event_type](**kwargs)
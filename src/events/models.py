"""
Event Models - Base Event Definitions

This module contains all event model definitions following Pydantic patterns
from existing models in src/core/models.py
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class EventStatus(str, Enum):
    """
    Status of an event during processing
    """
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRYING = "retrying"
    COMPLETED = "completed"


class BaseEvent(BaseModel):
    """
    Base event model that all specific events inherit from
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[str] = "system"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    retries: int = 0
    max_retries: int = 3
    
    @validator('timestamp', pre=True)
    def validate_timestamp(cls, value):
        """Validate that timestamp is a datetime object"""
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value

    def validate(self) -> bool:
        """
        Validate the event has required fields
        
        Returns:
            True if valid, False otherwise
        """
        return all([self.event_id, self.event_type, self.timestamp])

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary representation
        
        Returns:
            Dictionary representation of the event
        """
        return self.dict()

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class UserInteractionEvent(BaseModel):
    """
    Event for user interactions with the system
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "user_interaction"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: Optional[str] = None
    action: str  # "start", "menu", "choice", "reaction", etc.
    context: Dict[str, Any] = Field(default_factory=dict)
    source: str = "telegram"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('action')
    def validate_action(cls, value):
        """Validate action is one of the allowed values"""
        allowed_actions = ["start", "menu", "choice", "reaction", "help", "profile", "subscription", "narrative"]
        if value not in allowed_actions:
            raise ValueError(f"Action must be one of {allowed_actions}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class UserRegistrationEvent(BaseModel):
    """
    Event for user registration in the system
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "user_registration"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    telegram_data: Dict[str, Any]
    registration_method: str = "telegram"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class ReactionDetectedEvent(BaseModel):
    """
    Event for reactions to content
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "reaction_detected"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_id: str
    reaction_type: str  # "like", "love", "haha", "wow", "sad", "angry", "besito", etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = "telegram"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('reaction_type')
    def validate_reaction_type(cls, value):
        """Validate reaction type is one of the allowed values"""
        allowed_reactions = ["like", "love", "haha", "wow", "sad", "angry", "besito", "emoji_reaction"]
        if value not in allowed_reactions:
            raise ValueError(f"Reaction type must be one of {allowed_reactions}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class DecisionMadeEvent(BaseModel):
    """
    Event for user decisions in narrative
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "decision_made"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    choice_id: str
    fragment_id: str
    next_fragment_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class SubscriptionUpdatedEvent(BaseModel):
    """
    Event for subscription status changes
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "subscription_updated"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    old_status: str
    new_status: str
    plan_type: str
    changed_by: str = "system"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('new_status')
    def validate_status(cls, value):
        """Validate subscription status is one of the allowed values"""
        allowed_statuses = ["active", "inactive", "cancelled", "expired", "pending"]
        if value not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return value

    @validator('plan_type')
    def validate_plan_type(cls, value):
        """Validate plan type is one of the allowed values"""
        allowed_plans = ["free", "premium", "vip"]
        if value not in allowed_plans:
            raise ValueError(f"Plan type must be one of {allowed_plans}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class ContentViewedEvent(BaseModel):
    """
    Event for content being viewed by a user
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "content_viewed"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_id: str
    content_type: str  # "narrative", "image", "video", "hint", etc.
    view_duration: Optional[int] = None  # in seconds
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = "telegram"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('content_type')
    def validate_content_type(cls, value):
        """Validate content type is one of the allowed values"""
        allowed_types = ["narrative", "image", "video", "hint", "menu", "notification"]
        if value not in allowed_types:
            raise ValueError(f"Content type must be one of {allowed_types}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class HintUnlockedEvent(BaseModel):
    """
    Event for when a user unlocks a hint
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "hint_unlocked"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    hint_id: str
    hint_type: str  # "narrative", "puzzle", "location", etc.
    unlock_method: str  # "besitos", "time", "achievement", "vip", etc.
    cost: Optional[int] = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('hint_type')
    def validate_hint_type(cls, value):
        """Validate hint type is one of the allowed values"""
        allowed_types = ["narrative", "puzzle", "location", "character", "item", "general"]
        if value not in allowed_types:
            raise ValueError(f"Hint type must be one of {allowed_types}")
        return value

    @validator('unlock_method')
    def validate_unlock_method(cls, value):
        """Validate unlock method is one of the allowed values"""
        allowed_methods = ["besitos", "time", "achievement", "vip", "free", "subscription"]
        if value not in allowed_methods:
            raise ValueError(f"Unlock method must be one of {allowed_methods}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class SystemHealthEvent(BaseModel):
    """
    Event for system health status
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "system_health"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    component: str  # "database", "redis", "api", "bot", etc.
    status: str  # "healthy", "degraded", "unhealthy", "down"
    details: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    status_field: EventStatus = EventStatus.PENDING  # Using status_field to avoid conflict with status

    @validator('component')
    def validate_component(cls, value):
        """Validate component is one of the allowed values"""
        allowed_components = ["database", "redis", "api", "bot", "event_bus", "processor", "storage", "cache"]
        if value not in allowed_components:
            raise ValueError(f"Component must be one of {allowed_components}")
        return value

    @validator('status')
    def validate_health_status(cls, value):
        """Validate health status is one of the allowed values"""
        allowed_statuses = ["healthy", "degraded", "unhealthy", "down", "warning"]
        if value not in allowed_statuses:
            raise ValueError(f"Health status must be one of {allowed_statuses}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class SystemNotificationEvent(BaseModel):
    """
    Event for system notifications
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "system_notification"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    notification_type: str  # "info", "warning", "error", "maintenance", "update"
    message: str
    recipients: List[str] = Field(default_factory=list)  # List of user_ids or "all" for broadcast
    priority: str = "normal"  # "low", "normal", "high", "critical"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('notification_type')
    def validate_notification_type(cls, value):
        """Validate notification type is one of the allowed values"""
        allowed_types = ["info", "warning", "error", "maintenance", "update", "broadcast"]
        if value not in allowed_types:
            raise ValueError(f"Notification type must be one of {allowed_types}")
        return value

    @validator('priority')
    def validate_priority(cls, value):
        """Validate priority is one of the allowed values"""
        allowed_priorities = ["low", "normal", "high", "critical"]
        if value not in allowed_priorities:
            raise ValueError(f"Priority must be one of {allowed_priorities}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


# Type aliases for cleaner code
EventModel = BaseEvent
UserEvent = UserInteractionEvent
RegistrationEvent = UserRegistrationEvent
ReactionEvent = ReactionDetectedEvent
DecisionEvent = DecisionMadeEvent
SubscriptionEvent = SubscriptionUpdatedEvent
ContentEvent = ContentViewedEvent
HintEvent = HintUnlockedEvent
HealthEvent = SystemHealthEvent
NotificationEvent = SystemNotificationEvent
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


# System Resilience Event Models (Requirements 4.7, 5.5, 5.6)
class ModuleFailureEvent(BaseModel):
    """
    Event for when a module fails (Requirement 5.1, 5.2)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "module_failure"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    failed_module: str  # "narrative", "gamification", "admin", etc.
    error_type: str  # "connection_error", "timeout", "internal_error", "resource_unavailable"
    error_message: str
    stack_trace: Optional[str] = None
    affected_users_count: int = 0
    severity: str = "high"  # "low", "medium", "high", "critical"
    recovery_status: str = "none"  # "none", "attempting", "successful", "failed"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('failed_module')
    def validate_failed_module(cls, value):
        """Validate module name is one of the allowed values"""
        allowed_modules = ["narrative", "gamification", "admin", "event_bus", "api", "database", "redis"]
        if value not in allowed_modules:
            raise ValueError(f"Failed module must be one of {allowed_modules}")
        return value

    @validator('error_type')
    def validate_error_type(cls, value):
        """Validate error type is one of the allowed values"""
        allowed_error_types = ["connection_error", "timeout", "internal_error", "resource_unavailable", 
                              "authentication_failed", "authorization_failed", "validation_error"]
        if value not in allowed_error_types:
            raise ValueError(f"Error type must be one of {allowed_error_types}")
        return value

    @validator('severity')
    def validate_severity(cls, value):
        """Validate severity level is one of the allowed values"""
        allowed_severities = ["low", "medium", "high", "critical"]
        if value not in allowed_severities:
            raise ValueError(f"Severity must be one of {allowed_severities}")
        return value

    @validator('recovery_status')
    def validate_recovery_status(cls, value):
        """Validate recovery status is one of the allowed values"""
        allowed_statuses = ["none", "attempting", "successful", "failed"]
        if value not in allowed_statuses:
            raise ValueError(f"Recovery status must be one of {allowed_statuses}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class ModuleRecoveryEvent(BaseModel):
    """
    Event for when a module recovers (Requirement 5.2)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "module_recovery"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recovered_module: str  # "narrative", "gamification", "admin", etc.
    downtime_duration: float  # in seconds
    events_processed_count: int = 0
    events_lost_count: int = 0
    recovery_method: str = "automatic"  # "automatic", "manual", "restart", "reconfiguration"
    status_before_recovery: str  # status of the module before recovery
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('recovered_module')
    def validate_recovered_module(cls, value):
        """Validate module name is one of the allowed values"""
        allowed_modules = ["narrative", "gamification", "admin", "event_bus", "api", "database", "redis"]
        if value not in allowed_modules:
            raise ValueError(f"Recovered module must be one of {allowed_modules}")
        return value

    @validator('recovery_method')
    def validate_recovery_method(cls, value):
        """Validate recovery method is one of the allowed values"""
        allowed_methods = ["automatic", "manual", "restart", "reconfiguration"]
        if value not in allowed_methods:
            raise ValueError(f"Recovery method must be one of {allowed_methods}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class EventProcessingErrorEvent(BaseModel):
    """
    Event for when an event fails to process (Requirement 4.7)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "event_processing_error"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_event_id: str
    original_event_type: str
    error_message: str
    stack_trace: Optional[str] = None
    processing_attempts: int = 1
    max_processing_attempts: int = 3
    retry_delay: Optional[int] = None  # in seconds
    error_code: Optional[str] = None
    error_category: str = "system"  # "system", "validation", "timeout", "resource"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('error_category')
    def validate_error_category(cls, value):
        """Validate error category is one of the allowed values"""
        allowed_categories = ["system", "validation", "timeout", "resource", "external"]
        if value not in allowed_categories:
            raise ValueError(f"Error category must be one of {allowed_categories}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class CircuitBreakerEvent(BaseModel):
    """
    Event for circuit breaker state changes (Requirement 5.3)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "circuit_breaker_change"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    module_name: str
    operation: str  # specific operation that triggered the circuit breaker
    previous_state: str  # "CLOSED", "OPEN", "HALF_OPEN"
    new_state: str  # "CLOSED", "OPEN", "HALF_OPEN"
    failure_count: int = 0
    failure_threshold: int = 5  # default threshold
    timeout: float = 30.0  # in seconds
    reason: str  # reason for the state change
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('previous_state', 'new_state')
    def validate_circuit_state(cls, value):
        """Validate circuit breaker state is one of the allowed values"""
        allowed_states = ["CLOSED", "OPEN", "HALF_OPEN"]
        if value not in allowed_states:
            raise ValueError(f"Circuit state must be one of {allowed_states}")
        return value

    @validator('module_name')
    def validate_module_name(cls, value):
        """Validate module name is one of the allowed values"""
        allowed_modules = ["narrative", "gamification", "admin", "event_bus", "api", "database", "redis"]
        if value not in allowed_modules:
            raise ValueError(f"Module name must be one of {allowed_modules}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class ModuleIsolationEvent(BaseModel):
    """
    Event for module isolation due to failures (Requirement 5.1)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "module_isolation"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    isolated_module: str
    reason: str  # "failure", "high_error_rate", "timeout", "resource_exhaustion"
    duration: Optional[float] = None  # in seconds, None if permanent until manual intervention
    affected_modules: List[str] = Field(default_factory=list)  # modules that depend on this module
    fallback_activated: bool = False
    user_impact: str = "low"  # "none", "low", "medium", "high"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('isolated_module')
    def validate_isolated_module(cls, value):
        """Validate module name is one of the allowed values"""
        allowed_modules = ["narrative", "gamification", "admin", "event_bus", "api", "database", "redis"]
        if value not in allowed_modules:
            raise ValueError(f"Isolated module must be one of {allowed_modules}")
        return value

    @validator('reason')
    def validate_reason(cls, value):
        """Validate reason is one of the allowed values"""
        allowed_reasons = ["failure", "high_error_rate", "timeout", "resource_exhaustion", "unresponsive"]
        if value not in allowed_reasons:
            raise ValueError(f"Reason must be one of {allowed_reasons}")
        return value

    @validator('user_impact')
    def validate_user_impact(cls, value):
        """Validate user impact level is one of the allowed values"""
        allowed_impacts = ["none", "low", "medium", "high"]
        if value not in allowed_impacts:
            raise ValueError(f"User impact must be one of {allowed_impacts}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class DataInconsistencyEvent(BaseModel):
    """
    Event for detecting data inconsistency (Requirement 5.5)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "data_inconsistency_detected"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detection_method: str  # "comparison", "validation", "checksum", "business_rule_violation"
    inconsistent_module: str
    affected_collection: str
    inconsistency_type: str  # "mismatch", "missing_record", "validation_error", "constraint_violation"
    severity: str = "medium"  # "low", "medium", "high", "critical"
    records_affected: int = 0
    auto_repair_attempted: bool = False
    repair_status: str = "pending"  # "pending", "successful", "failed", "not_applicable"
    details: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('detection_method')
    def validate_detection_method(cls, value):
        """Validate detection method is one of the allowed values"""
        allowed_methods = ["comparison", "validation", "checksum", "business_rule_violation", "cross_module_sync"]
        if value not in allowed_methods:
            raise ValueError(f"Detection method must be one of {allowed_methods}")
        return value

    @validator('inconsistent_module')
    def validate_inconsistent_module(cls, value):
        """Validate module name is one of the allowed values"""
        allowed_modules = ["narrative", "gamification", "admin", "event_bus", "api", "database", "redis"]
        if value not in allowed_modules:
            raise ValueError(f"Inconsistent module must be one of {allowed_modules}")
        return value

    @validator('inconsistency_type')
    def validate_inconsistency_type(cls, value):
        """Validate inconsistency type is one of the allowed values"""
        allowed_types = ["mismatch", "missing_record", "validation_error", "constraint_violation", "duplicate_key"]
        if value not in allowed_types:
            raise ValueError(f"Inconsistency type must be one of {allowed_types}")
        return value

    @validator('severity')
    def validate_severity(cls, value):
        """Validate severity level is one of the allowed values"""
        allowed_severities = ["low", "medium", "high", "critical"]
        if value not in allowed_severities:
            raise ValueError(f"Severity must be one of {allowed_severities}")
        return value

    @validator('repair_status')
    def validate_repair_status(cls, value):
        """Validate repair status is one of the allowed values"""
        allowed_statuses = ["pending", "successful", "failed", "not_applicable"]
        if value not in allowed_statuses:
            raise ValueError(f"Repair status must be one of {allowed_statuses}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class ModuleHealthCheckEvent(BaseModel):
    """
    Event for module health check results (Requirement 5.6)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "module_health_check"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    module_name: str
    health_status: str  # "healthy", "degraded", "unhealthy", "critical"
    response_time: float  # in milliseconds
    error_rate: float = 0.0  # percentage of errors
    available_capacity: float = 100.0  # percentage of available capacity
    checks_performed: List[str] = Field(default_factory=list)  # list of health checks performed
    details: Dict[str, Any] = Field(default_factory=dict)
    alert_required: bool = False
    next_check_scheduled: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('module_name')
    def validate_module_name(cls, value):
        """Validate module name is one of the allowed values"""
        allowed_modules = ["narrative", "gamification", "admin", "event_bus", "api", "database", "redis"]
        if value not in allowed_modules:
            raise ValueError(f"Module name must be one of {allowed_modules}")
        return value

    @validator('health_status')
    def validate_health_status(cls, value):
        """Validate health status is one of the allowed values"""
        allowed_statuses = ["healthy", "degraded", "unhealthy", "critical"]
        if value not in allowed_statuses:
            raise ValueError(f"Health status must be one of {allowed_statuses}")
        return value

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class SystemResilienceEvent(BaseModel):
    """
    Event for system resilience and error recovery tracking
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "system_resilience"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    component: str  # "event_bus", "database", "api", "correlation_service"
    error_type: Optional[str] = None  # "timeout", "connection_error", "retry_exhausted"
    recovery_action: Optional[str] = None  # "retry", "failover", "circuit_breaker"
    retry_attempt: int = 0
    max_retries: int = 3
    recovery_success: Optional[bool] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING

    @validator('component')
    def validate_component(cls, value):
        """Validate component is one of the allowed values"""
        allowed_components = ["event_bus", "database", "api", "correlation_service", "redis", "telegram"]
        if value not in allowed_components:
            raise ValueError(f"Component must be one of {allowed_components}")
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
ResilienceEvent = SystemResilienceEvent
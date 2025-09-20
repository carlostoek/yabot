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
    source: str = Field(..., description="Source of the award (e.g., 'mission', 'daily_gift')")
    balance_after: int = Field(..., description="User balance after the award")
    transaction_id: str = Field(..., description="Transaction ID for tracking")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional award metadata")


class BesitosSpentEvent(BaseEvent):
    """Event published when besitos are spent by a user."""

    amount: int = Field(..., description="Number of besitos spent")
    reason: str = Field(..., description="Reason for spending besitos")
    item_id: Optional[str] = Field(None, description="Item ID if spent on an item")
    balance_after: int = Field(..., description="User balance after spending")
    transaction_id: str = Field(..., description="Transaction ID for tracking")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional spending metadata")


class MissionCompletedEvent(BaseEvent):
    """Event published when a user completes a mission."""

    mission_id: str = Field(..., description="ID of the completed mission")
    mission_type: str = Field(..., description="Type of mission completed")
    reward_besitos: int = Field(default=0, description="Besitos reward")
    reward_items: List[str] = Field(default_factory=list, description="Item rewards")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional mission metadata")


class AchievementUnlockedEvent(BaseEvent):
    """Event published when a user unlocks an achievement."""

    achievement_id: str = Field(..., description="ID of the unlocked achievement")
    achievement_title: str = Field(..., description="Title of the achievement")
    tier: str = Field(..., description="Achievement tier")
    reward_besitos: int = Field(default=0, description="Besitos reward")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional achievement metadata")


class TriviaAnsweredEvent(BaseEvent):
    """Event published when a user answers a trivia question."""

    trivia_id: str = Field(..., description="ID of the trivia session")
    question_id: str = Field(..., description="ID of the answered question")
    answer: int = Field(..., description="Index of selected answer")
    is_correct: bool = Field(..., description="Whether the answer was correct")
    points_earned: int = Field(..., description="Points earned for the answer")
    telegram_poll_id: Optional[str] = Field(None, description="Telegram poll ID if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional trivia metadata")


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


class UserUpdatedEvent(BaseEvent):
    """Event published when a user is updated."""
    
    update_type: str = Field(..., description="Type of update (profile, state, etc.)")
    updated_fields: Dict[str, Any] = Field(default_factory=dict, description="Fields that were updated")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional update metadata")


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


# System resilience event models (Requirements 4.7, 5.5, 5.6)

class ModuleFailureEvent(BaseEvent):
    """Event published when a module fails."""

    module_name: str = Field(..., description="Name of the failed module")
    failure_reason: str = Field(..., description="Reason for module failure")
    failure_type: str = Field(..., description="Type of failure (connection, timeout, error)")
    recovery_action: Optional[str] = Field(None, description="Recovery action taken")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional failure metadata")


class ModuleRecoveryEvent(BaseEvent):
    """Event published when a module recovers from failure."""

    module_name: str = Field(..., description="Name of the recovered module")
    downtime_seconds: float = Field(..., description="Duration of downtime in seconds")
    recovery_method: str = Field(..., description="Method used for recovery")
    queued_events_count: int = Field(0, description="Number of queued events processed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional recovery metadata")


class CircuitBreakerOpenedEvent(BaseEvent):
    """Event published when a circuit breaker opens."""

    service_name: str = Field(..., description="Name of the service with opened circuit")
    failure_count: int = Field(..., description="Number of failures that triggered the circuit")
    failure_threshold: int = Field(..., description="Threshold for opening the circuit")
    timeout_seconds: int = Field(..., description="Timeout duration in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional circuit breaker metadata")


class CircuitBreakerClosedEvent(BaseEvent):
    """Event published when a circuit breaker closes."""

    service_name: str = Field(..., description="Name of the service with closed circuit")
    open_duration_seconds: float = Field(..., description="Duration the circuit was open")
    test_request_success: bool = Field(..., description="Whether the test request succeeded")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional circuit breaker metadata")


class DatabaseConnectionLostEvent(BaseEvent):
    """Event published when database connection is lost."""

    database_type: str = Field(..., description="Type of database (mongodb, redis)")
    connection_pool_size: int = Field(..., description="Current connection pool size")
    error_details: str = Field(..., description="Detailed error information")
    retry_attempt: int = Field(0, description="Current retry attempt number")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional connection metadata")


class DatabaseConnectionRestoredEvent(BaseEvent):
    """Event published when database connection is restored."""

    database_type: str = Field(..., description="Type of database (mongodb, redis)")
    downtime_seconds: float = Field(..., description="Duration of connection loss")
    recovery_method: str = Field(..., description="Method used to restore connection")
    health_check_passed: bool = Field(..., description="Whether health check passed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional connection metadata")


class EventBusOverloadEvent(BaseEvent):
    """Event published when event bus is overloaded."""

    queue_size: int = Field(..., description="Current queue size")
    queue_limit: int = Field(..., description="Queue size limit")
    dropped_events_count: int = Field(0, description="Number of events dropped")
    processing_delay_ms: float = Field(..., description="Current processing delay in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional overload metadata")


class DataInconsistencyDetectedEvent(BaseEvent):
    """Event published when data inconsistency is detected."""

    module_source: str = Field(..., description="Module that detected the inconsistency")
    module_target: str = Field(..., description="Module with inconsistent data")
    inconsistency_type: str = Field(..., description="Type of inconsistency")
    affected_records: int = Field(..., description="Number of affected records")
    auto_repair_attempted: bool = Field(False, description="Whether auto-repair was attempted")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional inconsistency metadata")


class HealthCheckFailedEvent(BaseEvent):
    """Event published when module health check fails."""

    module_name: str = Field(..., description="Name of the module with failed health check")
    check_type: str = Field(..., description="Type of health check (database, api, memory)")
    failure_details: str = Field(..., description="Details of the health check failure")
    consecutive_failures: int = Field(..., description="Number of consecutive failures")
    alert_sent: bool = Field(False, description="Whether alert was sent to administrators")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional health check metadata")


class ModuleRestartEvent(BaseEvent):
    """Event published when a module restarts."""

    module_name: str = Field(..., description="Name of the restarted module")
    restart_reason: str = Field(..., description="Reason for module restart")
    last_known_state: Dict[str, Any] = Field(default_factory=dict, description="Last known state before restart")
    state_recovery_success: bool = Field(..., description="Whether state was successfully recovered")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional restart metadata")


class DailyGiftClaimedEvent(BaseEvent):
    """Event published when a user claims a daily gift."""

    gift_type: str = Field(..., description="Type of gift claimed")
    gift_amount: int = Field(..., description="Amount of gift claimed (e.g., besitos)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional gift metadata")


class PostScheduledEvent(BaseEvent):
    """Event published when a post is scheduled."""

    channel_id: str = Field(..., description="ID of the channel")
    status: str = Field(..., description="Status of the scheduled post (e.g., 'scheduled', 'published', 'failed')")
    error: Optional[str] = Field(None, description="Error message if the post failed to publish")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional post metadata")


class NotificationSentEvent(BaseEvent):
    """Event published when a notification is sent."""

    channel_id: str = Field(..., description="ID of the channel or user")
    status: str = Field(..., description="Status of the notification (e.g., 'sent', 'failed')")
    content: str = Field(..., description="Content of the notification")
    error: Optional[str] = Field(None, description="Error message if the notification failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional notification metadata")


class WorkflowStep(BaseModel):
    """Definition of a single step in a workflow."""
    
    step_id: str = Field(..., description="Unique identifier for the workflow step")
    name: str = Field(..., description="Name of the workflow step")
    description: Optional[str] = Field(None, description="Description of the workflow step")
    service: str = Field(..., description="Service responsible for executing this step")
    action: str = Field(..., description="Action to be performed by the service")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")
    timeout_seconds: int = Field(default=30, description="Timeout for step execution in seconds")
    retry_count: int = Field(default=0, description="Number of retries allowed for this step")
    dependencies: List[str] = Field(default_factory=list, description="List of step IDs that must complete before this step")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions that must be met for step execution")
    expected_outcome: Optional[str] = Field(None, description="Expected outcome of the step")


class WorkflowDefinition(BaseEvent):
    """Definition of a complete workflow."""
    
    workflow_id: str = Field(..., description="Unique identifier for the workflow")
    name: str = Field(..., description="Name of the workflow")
    description: Optional[str] = Field(None, description="Description of the workflow")
    version: str = Field(default="1.0.0", description="Version of the workflow definition")
    steps: List[WorkflowStep] = Field(default_factory=list, description="Ordered list of workflow steps")
    trigger_event: Optional[str] = Field(None, description="Event that triggers this workflow")
    timeout_seconds: int = Field(default=300, description="Overall timeout for workflow execution in seconds")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="Retry policy for the entire workflow")
    error_handling: Dict[str, Any] = Field(default_factory=dict, description="Error handling strategy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional workflow metadata")


class WorkflowExecutionStartedEvent(BaseEvent):
    """Event published when a workflow execution starts."""
    
    workflow_id: str = Field(..., description="ID of the workflow being executed")
    workflow_name: str = Field(..., description="Name of the workflow being executed")
    trigger_event_id: Optional[str] = Field(None, description="ID of the event that triggered the workflow")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")


class WorkflowStepCompletedEvent(BaseEvent):
    """Event published when a workflow step completes."""
    
    workflow_id: str = Field(..., description="ID of the workflow")
    step_id: str = Field(..., description="ID of the completed step")
    step_name: str = Field(..., description="Name of the completed step")
    outcome: str = Field(..., description="Outcome of the step execution")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="Result data from the step")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


class WorkflowCompletedEvent(BaseEvent):
    """Event published when a workflow completes."""
    
    workflow_id: str = Field(..., description="ID of the completed workflow")
    workflow_name: str = Field(..., description="Name of the completed workflow")
    status: str = Field(..., description="Final status of the workflow (success, failed, timeout)")
    total_execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    steps_executed: int = Field(..., description="Number of steps executed")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="Final result data from the workflow")


class WorkflowFailedEvent(BaseEvent):
    """Event published when a workflow fails."""
    
    workflow_id: str = Field(..., description="ID of the failed workflow")
    workflow_name: str = Field(..., description="Name of the failed workflow")
    failure_step_id: Optional[str] = Field(None, description="ID of the step where failure occurred")
    failure_reason: str = Field(..., description="Reason for workflow failure")
    error_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed error information")
    recovery_actions: List[str] = Field(default_factory=list, description="Suggested recovery actions")


class EmotionalSignatureUpdatedEvent(BaseEvent):
    """Event published when user's emotional signature is updated."""

    archetype: str = Field(..., description="User's emotional archetype")
    authenticity_score: float = Field(..., description="Authenticity score (0.0-1.0)")
    signature_strength: float = Field(..., description="Classification confidence")
    previous_archetype: Optional[str] = Field(None, description="Previous archetype if changed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional signature metadata")


class DianaLevelProgressionEvent(BaseEvent):
    """Event published when user advances to new Diana level."""

    previous_level: int = Field(..., description="Previous Diana level")
    new_level: int = Field(..., description="New Diana level")
    progression_reason: str = Field(..., description="Reason for level advancement")
    emotional_metrics: Dict[str, Any] = Field(..., description="Emotional metrics that triggered progression")
    vip_access_required: bool = Field(..., description="Whether VIP access is required for this level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional progression metadata")


class EmotionalMilestoneReachedEvent(BaseEvent):
    """Event published when user reaches emotional milestone."""

    milestone_type: str = Field(..., description="Type of emotional milestone")
    milestone_data: Dict[str, Any] = Field(..., description="Milestone-specific data")
    reward_besitos: int = Field(default=0, description="Besitos reward for milestone")
    unlock_content: Optional[str] = Field(None, description="Content unlocked by milestone")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional milestone metadata")


# Event type constants for easy reference
EVENT_MODELS = {
    "user_interaction": UserInteractionEvent,
    "reaction_detected": ReactionDetectedEvent,
    "decision_made": DecisionMadeEvent,
    "subscription_updated": SubscriptionUpdatedEvent,
    "besitos_awarded": BesitosAwardedEvent,
    "besitos_spent": BesitosSpentEvent,
    "mission_completed": MissionCompletedEvent,
    "achievement_unlocked": AchievementUnlockedEvent,
    "trivia_answered": TriviaAnsweredEvent,
    "narrative_hint_unlocked": NarrativeHintUnlockedEvent,
    "vip_access_granted": VipAccessGrantedEvent,
    "user_registered": UserRegisteredEvent,
    "user_deleted": UserDeletedEvent,
    "user_updated": UserUpdatedEvent,
    "update_received": UpdateReceivedEvent,
    "event_processing_failed": EventProcessingFailedEvent,
    # System resilience events
    "module_failure": ModuleFailureEvent,
    "module_recovery": ModuleRecoveryEvent,
    "circuit_breaker_opened": CircuitBreakerOpenedEvent,
    "circuit_breaker_closed": CircuitBreakerClosedEvent,
    "database_connection_lost": DatabaseConnectionLostEvent,
    "database_connection_restored": DatabaseConnectionRestoredEvent,
    "event_bus_overload": EventBusOverloadEvent,
    "data_inconsistency_detected": DataInconsistencyDetectedEvent,
    "health_check_failed": HealthCheckFailedEvent,
    "module_restart": ModuleRestartEvent,
    "daily_gift_claimed": DailyGiftClaimedEvent,
    "post_scheduled": PostScheduledEvent,
    "notification_sent": NotificationSentEvent,
    # Workflow events
    "workflow_definition": WorkflowDefinition,
    "workflow_execution_started": WorkflowExecutionStartedEvent,
    "workflow_step_completed": WorkflowStepCompletedEvent,
    "workflow_completed": WorkflowCompletedEvent,
    "workflow_failed": WorkflowFailedEvent,
    # Emotional events
    "emotional_signature_updated": EmotionalSignatureUpdatedEvent,
    "diana_level_progression": DianaLevelProgressionEvent,
    "emotional_milestone_reached": EmotionalMilestoneReachedEvent,
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
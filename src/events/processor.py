"""
Event Processor - Subscription Event Handling

This module provides an event processor that handles subscription events
and other business logic with reliability and monitoring features.
"""
import asyncio
import json
from typing import Dict, Any, Callable, Optional, List, Awaitable
from datetime import datetime
import time
import traceback
from enum import Enum

# Import event models and logger
from .models import (
    BaseEvent, UserInteractionEvent, ReactionDetectedEvent, 
    SubscriptionUpdatedEvent, DecisionMadeEvent, EventStatus
)
from .bus import EventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessingResult(Enum):
    """
    Result of event processing
    """
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    SKIPPED = "skipped"


class EventProcessingError(Exception):
    """
    Exception for event processing errors
    """
    def __init__(self, message: str, event: BaseEvent = None, original_error: Exception = None):
        super().__init__(message)
        self.event = event
        self.original_error = original_error


class EventProcessor:
    """
    Event processor that handles subscription and other business logic events
    """
    def __init__(self, subscriptions: Dict[str, Callable] = None, event_bus: EventBus = None):
        # Initialize event handlers
        self.event_handlers: Dict[str, Callable] = {}
        
        # Add default handlers for standard event types
        self._setup_default_handlers()
        
        # Add any user-provided handlers
        if subscriptions:
            self.event_handlers.update(subscriptions)
        
        # Reference to event bus if provided
        self.event_bus = event_bus
        
        # Processing metrics
        self.metrics = {
            'processed_events': 0,
            'failed_events': 0,
            'retried_events': 0,
            'processing_time_total': 0.0,
            'processing_time_avg': 0.0,
            'events_by_type': {}
        }
        
        # Track active processing tasks
        self._active_tasks = set()
        self._shutdown_event = asyncio.Event()
        
        logger.info("Event processor initialized")
    
    def _setup_default_handlers(self):
        """
        Set up default handlers for standard event types
        """
        self.event_handlers.update({
            'user_interaction': self._handle_user_interaction,
            'reaction_detected': self._handle_reaction_detected,
            'subscription_updated': self._handle_subscription_updated,
            'decision_made': self._handle_decision_made,
            'user_registration': self._handle_user_registration,
            'content_viewed': self._handle_content_viewed,
            'hint_unlocked': self._handle_hint_unlocked,
            'system_health': self._handle_system_health,
            'system_notification': self._handle_system_notification
        })
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type
        
        Args:
            event_type: Type of event to handle
            handler: Function to handle the event
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    def unregister_handler(self, event_type: str):
        """
        Unregister a handler for a specific event type
        
        Args:
            event_type: Type of event to remove handler for
        """
        if event_type in self.event_handlers:
            del self.event_handlers[event_type]
            logger.info(f"Unregistered handler for event type: {event_type}")
    
    async def process_event(self, event: BaseEvent) -> ProcessingResult:
        """
        Process a single event with reliability and error handling
        
        Args:
            event: The event to process
            
        Returns:
            ProcessingResult indicating the outcome
        """
        start_time = time.time()
        
        # Update metrics
        event_type = event.event_type
        if event_type not in self.metrics['events_by_type']:
            self.metrics['events_by_type'][event_type] = {
                'processed': 0,
                'failed': 0,
                'avg_processing_time': 0.0
            }
        
        try:
            # Log the event being processed
            logger.info(f"Processing event", event_id=event.event_id, event_type=event_type)
            
            # Find appropriate handler
            handler = self.event_handlers.get(event_type)
            
            if not handler:
                logger.warning(f"No handler found for event type: {event_type}")
                return ProcessingResult.SKIPPED
            
            # Update event status to processing
            event.status = EventStatus.PROCESSING
            
            # Process the event with the handler
            result = await handler(event)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics['processed_events'] += 1
            self.metrics['processing_time_total'] += processing_time
            
            # Update event type specific metrics
            type_metrics = self.metrics['events_by_type'][event_type]
            type_metrics['processed'] += 1
            # Calculate moving average
            total_processed = type_metrics['processed'] + type_metrics['failed']
            type_metrics['avg_processing_time'] = (
                (type_metrics['avg_processing_time'] * (total_processed - 1) + processing_time) / total_processed
            )
            
            # Calculate average processing time
            self.metrics['processing_time_avg'] = (
                self.metrics['processing_time_total'] / self.metrics['processed_events']
            )
            
            logger.info(f"Event processed successfully", 
                       event_id=event.event_id, 
                       event_type=event_type,
                       processing_time=processing_time)
            
            # Update event status to completed
            event.status = EventStatus.COMPLETED
            
            return ProcessingResult.SUCCESS
            
        except asyncio.CancelledError:
            logger.info(f"Event processing cancelled", event_id=event.event_id)
            return ProcessingResult.SKIPPED
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics['failed_events'] += 1
            
            # Update event type specific metrics
            type_metrics = self.metrics['events_by_type'][event_type]
            type_metrics['failed'] += 1
            
            logger.error(f"Error processing event", 
                        event_id=event.event_id, 
                        event_type=event_type,
                        error=str(e),
                        traceback=traceback.format_exc())
            
            # Update event status to failed
            event.status = EventStatus.FAILED
            
            # Check if we should retry based on retry count
            if event.retries < event.max_retries:
                event.retries += 1
                event.status = EventStatus.RETRYING
                logger.info(f"Scheduling retry for event", 
                           event_id=event.event_id, 
                           retry_count=event.retries)
                return ProcessingResult.RETRY
            else:
                logger.error(f"Max retries exceeded for event", 
                            event_id=event.event_id, 
                            retry_count=event.retries)
                return ProcessingResult.FAILED
    
    async def _handle_user_interaction(self, event: UserInteractionEvent) -> None:
        """
        Handle user interaction events
        
        Args:
            event: User interaction event to process
        """
        logger.info(f"Handling user interaction event", 
                   user_id=event.user_id, 
                   action=event.action)
        
        # Implement business logic for user interactions
        # This would typically update user state, log activity, etc.
        if event.action == "start":
            # Handle start command
            logger.info(f"User started interaction", user_id=event.user_id)
        elif event.action == "menu":
            # Handle menu selection
            logger.info(f"User accessed menu", 
                       user_id=event.user_id, 
                       menu_context=event.context.get('menu'))
        elif event.action == "choice":
            # Handle narrative choice
            logger.info(f"User made choice", 
                       user_id=event.user_id, 
                       choice_id=event.context.get('choice_id'))
    
    async def _handle_reaction_detected(self, event: ReactionDetectedEvent) -> None:
        """
        Handle reaction detected events
        
        Args:
            event: Reaction detected event to process
        """
        logger.info(f"Handling reaction event", 
                   user_id=event.user_id, 
                   content_id=event.content_id, 
                   reaction_type=event.reaction_type)
        
        # Implement business logic for reactions
        # This might trigger rewards, update statistics, etc.
        if event.reaction_type == "besito":
            # Handle besito reactions
            logger.info(f"Besito reaction detected", 
                       user_id=event.user_id, 
                       content_id=event.content_id)
    
    async def _handle_subscription_updated(self, event: SubscriptionUpdatedEvent) -> None:
        """
        Handle subscription updated events
        
        Args:
            event: Subscription updated event to process
        """
        logger.info(f"Handling subscription update", 
                   user_id=event.user_id, 
                   old_status=event.old_status, 
                   new_status=event.new_status)
        
        # Implement business logic for subscription updates
        # This might update user permissions, notify services, etc.
        if event.new_status == "active" and event.old_status != "active":
            # New subscription activated
            logger.info(f"New subscription activated for user", user_id=event.user_id)
        elif event.new_status == "expired" or event.new_status == "cancelled":
            # Subscription ended
            logger.info(f"Subscription ended for user", 
                       user_id=event.user_id, 
                       reason=event.new_status)
    
    async def _handle_decision_made(self, event: DecisionMadeEvent) -> None:
        """
        Handle decision made events
        
        Args:
            event: Decision made event to process
        """
        logger.info(f"Handling decision event", 
                   user_id=event.user_id, 
                   choice_id=event.choice_id)
        
        # Implement business logic for narrative decisions
        # This might update user progress, trigger new events, etc.
        logger.info(f"User decision recorded", 
                   user_id=event.user_id, 
                   fragment_id=event.fragment_id)
    
    async def _handle_user_registration(self, event: BaseEvent) -> None:
        """
        Handle user registration events
        
        Args:
            event: User registration event to process
        """
        logger.info(f"Handling user registration", user_id=event.user_id)
        
        # Implement business logic for user registration
        # This might initialize user data, send welcome messages, etc.
        logger.info(f"New user registered", user_id=event.user_id)
    
    async def _handle_content_viewed(self, event: BaseEvent) -> None:
        """
        Handle content viewed events
        
        Args:
            event: Content viewed event to process
        """
        logger.info(f"Handling content view", 
                   user_id=event.user_id, 
                   content_id=event.payload.get('content_id'))
        
        # Implement business logic for content viewing
        # This might track engagement, update statistics, etc.
        logger.info(f"Content viewed by user", 
                   user_id=event.user_id, 
                   content_id=event.payload.get('content_id'))
    
    async def _handle_hint_unlocked(self, event: BaseEvent) -> None:
        """
        Handle hint unlocked events
        
        Args:
            event: Hint unlocked event to process
        """
        logger.info(f"Handling hint unlock", 
                   user_id=event.user_id, 
                   hint_id=event.payload.get('hint_id'))
        
        # Implement business logic for hint unlock
        # This might update user's unlocked hints, charge besitos, etc.
        logger.info(f"Hint unlocked by user", 
                   user_id=event.user_id, 
                   hint_id=event.payload.get('hint_id'))
    
    async def _handle_system_health(self, event: BaseEvent) -> None:
        """
        Handle system health events
        
        Args:
            event: System health event to process
        """
        logger.info(f"Handling system health event", 
                   component=event.payload.get('component'),
                   status=event.payload.get('status'))
        
        # Implement business logic for system health
        # This might trigger alerts, initiate recovery, etc.
        if event.payload.get('status') == 'unhealthy':
            logger.warning(f"System component unhealthy", 
                          component=event.payload.get('component'))
    
    async def _handle_system_notification(self, event: BaseEvent) -> None:
        """
        Handle system notification events
        
        Args:
            event: System notification event to process
        """
        logger.info(f"Handling system notification", 
                   notification_type=event.payload.get('notification_type'),
                   message=event.payload.get('message'))
        
        # Implement business logic for system notifications
        # This might broadcast messages, trigger admin alerts, etc.
        logger.info(f"System notification processed", 
                   notification_type=event.payload.get('notification_type'))
    
    async def process_event_with_reliability(self, event: BaseEvent) -> ProcessingResult:
        """
        Process an event with reliability features like idempotency and retries
        
        Args:
            event: The event to process reliably
            
        Returns:
            ProcessingResult indicating the outcome
        """
        # Check if event has been processed before (idempotency check)
        # In a real implementation, this might check a database or cache
        # For now, we'll trust the event processing logic
        result = await self.process_event(event)
        
        # If result is retry, handle retry logic
        if result == ProcessingResult.RETRY and self.event_bus:
            # Add a delay before retrying
            await asyncio.sleep(2 ** event.retries)  # Exponential backoff
            
            # Add event back to bus for retry
            try:
                await self.event_bus.publish(event)
                self.metrics['retried_events'] += 1
                logger.info(f"Event rescheduled for retry", event_id=event.event_id)
            except Exception as e:
                logger.error(f"Failed to reschedule event for retry", 
                            event_id=event.event_id, error=str(e))
        
        return result
    
    async def shutdown(self):
        """
        Shutdown the event processor and clean up resources
        """
        logger.info("Shutting down event processor")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Wait for active tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
        logger.info("Event processor shutdown completed")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current processing metrics
        
        Returns:
            Dictionary with current metrics
        """
        return self.metrics.copy()
    
    def add_event_bus(self, event_bus: EventBus):
        """
        Add a reference to the event bus for retries and publishing
        
        Args:
            event_bus: EventBus instance
        """
        self.event_bus = event_bus
        logger.info("Event bus added to processor")


# Convenience function for creating a processor with common subscriptions
def create_subscription_processor(subscription_handler: Callable = None) -> EventProcessor:
    """
    Create an event processor configured for subscription handling
    
    Args:
        subscription_handler: Optional custom subscription handler
        
    Returns:
        Configured EventProcessor instance
    """
    processor = EventProcessor()
    
    # Register subscription-specific handler if provided
    if subscription_handler:
        processor.register_handler('subscription_updated', subscription_handler)
    
    return processor
"""
Event processor for handling subscriptions in the YABOT system.

This module provides an event processor that handles subscription-related events
as required by the fase1 specification.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from src.events.bus import EventBus
from src.events.models import BaseEvent, EVENT_MODELS, create_event
from src.utils.logger import get_logger
from src.config.manager import ConfigManager

logger = get_logger(__name__)


class EventProcessorError(Exception):
    """Base exception for event processor operations."""
    pass


class EventProcessingError(EventProcessorError):
    """Exception raised when event processing fails."""
    pass


class EventProcessor:
    """Event processor for handling subscription-related events."""
    
    def __init__(self, event_bus: EventBus, config_manager: Optional[ConfigManager] = None):
        """Initialize the event processor.
        
        Args:
            event_bus (EventBus): Event bus instance for publishing/subscribing to events
            config_manager (ConfigManager, optional): Configuration manager instance
        """
        self.event_bus = event_bus
        self.config_manager = config_manager or ConfigManager()
        self._handlers: Dict[str, List[Callable[[BaseEvent], Awaitable[None]]]] = {}
        self._is_processing = False
        self._processing_task: Optional[asyncio.Task] = None
        self._dead_letter_queue: List[Dict[str, Any]] = []
        self._max_dead_letter_queue_size: int = 1000
        
        # For idempotent processing - track processed events
        self._processed_events: Dict[str, float] = {}  # event_id -> timestamp
        self._processed_events_max_size: int = 10000  # Max size of processed events cache
        self._processed_events_ttl: int = 3600  # 1 hour TTL for processed events
        
        # For graceful shutdown - track currently processing events
        self._currently_processing_events: set = set()
        
        # Processing metrics
        self._metrics = {
            "events_processed": 0,
            "events_failed": 0,
            "events_retried": 0,
            "dlq_size": 0,
            "processing_times": []
        }
        self._max_processing_times = 1000  # Keep last 1000 processing times for metrics
        
        logger.info("EventProcessor initialized")
    
    async def start_processing(self) -> bool:
        """Start processing events.
        
        Returns:
            bool: True if processing was started successfully, False otherwise
        """
        logger.info("Starting event processing")
        
        try:
            if self._is_processing:
                logger.warning("Event processing is already running")
                return True
            
            # Register default handlers for subscription-related events
            await self._register_default_handlers()
            
            self._is_processing = True
            logger.info("Event processing started successfully")
            return True
            
        except Exception as e:
            logger.error("Error starting event processing: %s", str(e))
            return False
    
    async def stop_processing(self) -> bool:
        """Stop processing events with graceful shutdown.
        
        Returns:
            bool: True if processing was stopped successfully, False otherwise
        """
        logger.info("Stopping event processing")
        
        try:
            self._is_processing = False
            
            # Cancel processing task if running
            if self._processing_task and not self._processing_task.done():
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
            
            # Wait for any currently processing events to complete (up to 10 seconds)
            if self._currently_processing_events:
                logger.info("Waiting for %d events to complete processing", len(self._currently_processing_events))
                start_time = time.time()
                while self._currently_processing_events and (time.time() - start_time) < 10:
                    await asyncio.sleep(0.1)
                
                if self._currently_processing_events:
                    logger.warning(
                        "Timed out waiting for events to complete, %d events still processing",
                        len(self._currently_processing_events)
                    )
            
            logger.info("Event processing stopped successfully")
            return True
            
        except Exception as e:
            logger.error("Error stopping event processing: %s", str(e))
            return False
    
    async def _register_default_handlers(self) -> None:
        """Register default handlers for subscription-related events."""
        logger.debug("Registering default event handlers")
        
        # Register handlers for subscription-related events
        await self.register_handler("subscription_updated", self._handle_subscription_updated)
        await self.register_handler("user_registered", self._handle_user_registered)
        await self.register_handler("user_deleted", self._handle_user_deleted)
        await self.register_handler("besitos_awarded", self._handle_besitos_awarded)
        await self.register_handler("vip_access_granted", self._handle_vip_access_granted)
        
        logger.debug("Default event handlers registered")
    
    async def register_handler(self, event_type: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> bool:
        """Register a handler for a specific event type.
        
        Args:
            event_type (str): Type of event to handle
            handler (Callable): Handler function to call when event is received
            
        Returns:
            bool: True if handler was registered successfully, False otherwise
        """
        logger.debug("Registering handler for event type: %s", event_type)
        
        try:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            
            logger.debug("Handler registered for event type: %s", event_type)
            return True
            
        except Exception as e:
            logger.error("Error registering handler for event type %s: %s", event_type, str(e))
            return False
    
    async def _handle_subscription_updated(self, event: BaseEvent) -> None:
        """Handle subscription updated events.
        
        Args:
            event (BaseEvent): Subscription updated event
        """
        logger.debug("Handling subscription updated event: %s", event.event_id)
        
        # Track currently processing events for graceful shutdown
        self._currently_processing_events.add(event.event_id)
        
        try:
            # Check if event has already been processed (idempotent processing)
            if self._is_event_processed(event):
                logger.debug("Event already processed, skipping: %s", event.event_id)
                self._currently_processing_events.discard(event.event_id)
                return
        
            start_time = time.time()
            try:
                # Process subscription update
                await self._process_subscription_update(event)
                
                # Mark event as processed
                self._mark_event_processed(event)
                
                # Update metrics
                processing_time = time.time() - start_time
                self._metrics["events_processed"] += 1
                self._add_processing_time(processing_time)
                
                # Log successful processing
                logger.debug("Subscription updated event processed successfully: %s (took %.2fms)", 
                            event.event_id, processing_time * 1000)
                
            except Exception as e:
                processing_time = time.time() - start_time
                self._metrics["events_failed"] += 1
                self._add_processing_time(processing_time)
                logger.error("Error handling subscription updated event: %s", str(e))
                await self._handle_processing_failure(event, e)
        finally:
            # Remove from currently processing events
            self._currently_processing_events.discard(event.event_id)
    
    async def _handle_user_registered(self, event: BaseEvent) -> None:
        """Handle user registered events.
        
        Args:
            event (BaseEvent): User registered event
        """
        logger.debug("Handling user registered event: %s", event.event_id)
        
        # Track currently processing events for graceful shutdown
        self._currently_processing_events.add(event.event_id)
        
        try:
            # Check if event has already been processed (idempotent processing)
            if self._is_event_processed(event):
                logger.debug("Event already processed, skipping: %s", event.event_id)
                self._currently_processing_events.discard(event.event_id)
                return
        
            start_time = time.time()
            try:
                # Process user registration
                await self._process_user_registration(event)
                
                # Mark event as processed
                self._mark_event_processed(event)
                
                # Update metrics
                processing_time = time.time() - start_time
                self._metrics["events_processed"] += 1
                self._add_processing_time(processing_time)
                
                # Log successful processing
                logger.debug("User registered event processed successfully: %s (took %.2fms)", 
                            event.event_id, processing_time * 1000)
                
            except Exception as e:
                processing_time = time.time() - start_time
                self._metrics["events_failed"] += 1
                self._add_processing_time(processing_time)
                logger.error("Error handling user registered event: %s", str(e))
                await self._handle_processing_failure(event, e)
        finally:
            # Remove from currently processing events
            self._currently_processing_events.discard(event.event_id)
    
    async def _handle_user_deleted(self, event: BaseEvent) -> None:
        """Handle user deleted events.
        
        Args:
            event (BaseEvent): User deleted event
        """
        logger.debug("Handling user deleted event: %s", event.event_id)
        
        # Track currently processing events for graceful shutdown
        self._currently_processing_events.add(event.event_id)
        
        try:
            # Check if event has already been processed (idempotent processing)
            if self._is_event_processed(event):
                logger.debug("Event already processed, skipping: %s", event.event_id)
                self._currently_processing_events.discard(event.event_id)
                return
        
            start_time = time.time()
            try:
                # Process user deletion
                await self._process_user_deletion(event)
                
                # Mark event as processed
                self._mark_event_processed(event)
                
                # Update metrics
                processing_time = time.time() - start_time
                self._metrics["events_processed"] += 1
                self._add_processing_time(processing_time)
                
                # Log successful processing
                logger.debug("User deleted event processed successfully: %s (took %.2fms)", 
                            event.event_id, processing_time * 1000)
                
            except Exception as e:
                processing_time = time.time() - start_time
                self._metrics["events_failed"] += 1
                self._add_processing_time(processing_time)
                logger.error("Error handling user deleted event: %s", str(e))
                await self._handle_processing_failure(event, e)
        finally:
            # Remove from currently processing events
            self._currently_processing_events.discard(event.event_id)
    
    async def _handle_besitos_awarded(self, event: BaseEvent) -> None:
        """Handle besitos awarded events.
        
        Args:
            event (BaseEvent): Besitos awarded event
        """
        logger.debug("Handling besitos awarded event: %s", event.event_id)
        
        # Track currently processing events for graceful shutdown
        self._currently_processing_events.add(event.event_id)
        
        try:
            # Check if event has already been processed (idempotent processing)
            if self._is_event_processed(event):
                logger.debug("Event already processed, skipping: %s", event.event_id)
                self._currently_processing_events.discard(event.event_id)
                return
        
            start_time = time.time()
            try:
                # Process besitos award
                await self._process_besitos_award(event)
                
                # Mark event as processed
                self._mark_event_processed(event)
                
                # Update metrics
                processing_time = time.time() - start_time
                self._metrics["events_processed"] += 1
                self._add_processing_time(processing_time)
                
                # Log successful processing
                logger.debug("Besitos awarded event processed successfully: %s (took %.2fms)", 
                            event.event_id, processing_time * 1000)
                
            except Exception as e:
                processing_time = time.time() - start_time
                self._metrics["events_failed"] += 1
                self._add_processing_time(processing_time)
                logger.error("Error handling besitos awarded event: %s", str(e))
                await self._handle_processing_failure(event, e)
        finally:
            # Remove from currently processing events
            self._currently_processing_events.discard(event.event_id)
    
    async def _handle_vip_access_granted(self, event: BaseEvent) -> None:
        """Handle VIP access granted events.
        
        Args:
            event (BaseEvent): VIP access granted event
        """
        logger.debug("Handling VIP access granted event: %s", event.event_id)
        
        # Track currently processing events for graceful shutdown
        self._currently_processing_events.add(event.event_id)
        
        try:
            # Check if event has already been processed (idempotent processing)
            if self._is_event_processed(event):
                logger.debug("Event already processed, skipping: %s", event.event_id)
                self._currently_processing_events.discard(event.event_id)
                return
        
            start_time = time.time()
            try:
                # Process VIP access grant
                await self._process_vip_access_grant(event)
                
                # Mark event as processed
                self._mark_event_processed(event)
                
                # Update metrics
                processing_time = time.time() - start_time
                self._metrics["events_processed"] += 1
                self._add_processing_time(processing_time)
                
                # Log successful processing
                logger.debug("VIP access granted event processed successfully: %s (took %.2fms)", 
                            event.event_id, processing_time * 1000)
                
            except Exception as e:
                processing_time = time.time() - start_time
                self._metrics["events_failed"] += 1
                self._add_processing_time(processing_time)
                logger.error("Error handling VIP access granted event: %s", str(e))
                await self._handle_processing_failure(event, e)
        finally:
            # Remove from currently processing events
            self._currently_processing_events.discard(event.event_id)
    
    async def _process_subscription_update(self, event: BaseEvent) -> None:
        """Process subscription update.
        
        Args:
            event (BaseEvent): Subscription updated event
        """
        logger.debug("Processing subscription update for user: %s", event.user_id)
        
        # In a real implementation, this would:
        # 1. Update the user's subscription status in the database
        # 2. Send notifications to relevant services
        # 3. Update any cached user data
        # 4. Trigger any subscription-related workflows
        
        # For now, we'll just log the event
        logger.info(
            "Subscription updated for user %s: plan=%s, status=%s",
            event.user_id,
            event.payload.get("plan_type"),
            event.payload.get("status")
        )
    
    async def _process_user_registration(self, event: BaseEvent) -> None:
        """Process user registration.
        
        Args:
            event (BaseEvent): User registered event
        """
        logger.debug("Processing user registration for user: %s", event.user_id)
        
        # In a real implementation, this would:
        # 1. Create initial subscription records for the user
        # 2. Set up default subscription plan (free tier)
        # 3. Initialize user profile data
        # 4. Send welcome notifications
        
        # For now, we'll just log the event
        logger.info("User registered: %s", event.user_id)
    
    async def _process_user_deletion(self, event: BaseEvent) -> None:
        """Process user deletion.
        
        Args:
            event (BaseEvent): User deleted event
        """
        logger.debug("Processing user deletion for user: %s", event.user_id)
        
        # In a real implementation, this would:
        # 1. Cancel any active subscriptions
        # 2. Archive user data as required by privacy regulations
        # 3. Clean up any related resources
        # 4. Send notifications to relevant services
        
        # For now, we'll just log the event
        logger.info("User deleted: %s", event.user_id)
    
    async def _process_besitos_award(self, event: BaseEvent) -> None:
        """Process besitos award.
        
        Args:
            event (BaseEvent): Besitos awarded event
        """
        logger.debug("Processing besitos award for user: %s", event.user_id)
        
        # In a real implementation, this would:
        # 1. Update the user's besitos balance
        # 2. Record the transaction in the database
        # 3. Check if any thresholds have been met for unlocks
        # 4. Trigger any relevant workflows (e.g., achievement unlocks)
        
        # For now, we'll just log the event
        logger.info(
            "Besitos awarded to user %s: amount=%s, reason=%s",
            event.user_id,
            event.payload.get("amount"),
            event.payload.get("reason")
        )
    
    async def _process_vip_access_grant(self, event: BaseEvent) -> None:
        """Process VIP access grant.
        
        Args:
            event (BaseEvent): VIP access granted event
        """
        logger.debug("Processing VIP access grant for user: %s", event.user_id)
        
        # In a real implementation, this would:
        # 1. Update the user's VIP status in the database
        # 2. Grant any VIP-specific privileges or content access
        # 3. Send VIP welcome notifications
        # 4. Update any cached user data
        
        # For now, we'll just log the event
        logger.info("VIP access granted to user: %s", event.user_id)
    
    async def _handle_processing_failure(self, event: BaseEvent, error: Exception) -> None:
        """Handle event processing failure.
        
        Args:
            event (BaseEvent): Event that failed to process
            error (Exception): Error that occurred during processing
        """
        logger.warning("Event processing failed: %s - %s", event.event_id, str(error))
        
        # Update metrics
        self._metrics["events_failed"] += 1
        
        # Add event to dead letter queue
        await self._add_to_dead_letter_queue(event, error)
        
        # Publish error event
        try:
            error_event = create_event(
                "event_processing_failed",
                user_id=event.user_id,
                error_message=str(error),
                original_event_type=event.event_type,
                original_event_id=event.event_id,
                metadata={
                    "event_payload": event.dict()
                }
            )
            await self.event_bus.publish("event_processing_failed", error_event.dict())
        except Exception as e:
            logger.error("Failed to publish error event: %s", str(e))
    
    async def _add_to_dead_letter_queue(self, event: BaseEvent, error: Exception) -> None:
        """Add failed event to dead letter queue.
        
        Args:
            event (BaseEvent): Event that failed to process
            error (Exception): Error that occurred during processing
        """
        logger.debug("Adding event to dead letter queue: %s", event.event_id)
        
        try:
            # Check queue size
            if len(self._dead_letter_queue) >= self._max_dead_letter_queue_size:
                logger.warning("Dead letter queue is full, dropping oldest event")
                self._dead_letter_queue.pop(0)  # Remove oldest event
            
            # Add event to queue
            dead_letter_entry = {
                "event": event.dict(),
                "error": str(error),
                "timestamp": time.time(),
                "retry_count": 0,
                "last_retry_timestamp": time.time()
            }
            self._dead_letter_queue.append(dead_letter_entry)
            
            # Update metrics
            self._metrics["dlq_size"] = len(self._dead_letter_queue)
            
            logger.debug("Event added to dead letter queue: %s", event.event_id)
            
        except Exception as e:
            logger.error("Error adding event to dead letter queue: %s", str(e))
    
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate retry delay with exponential backoff.
        
        Args:
            retry_count (int): Number of retry attempts
            
        Returns:
            float: Delay in seconds
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, max 60s
        delay = min(2 ** retry_count, 60)
        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * (2 * (hash(str(retry_count)) % 1000) / 1000 - 1)
        return max(1, delay + jitter)
    
    async def retry_dead_letter_queue(self) -> None:
        """Retry processing events in the dead letter queue with exponential backoff."""
        logger.info("Retrying dead letter queue processing")
        
        if not self._dead_letter_queue:
            logger.debug("Dead letter queue is empty")
            return
        
        logger.debug("Processing %d events from dead letter queue", len(self._dead_letter_queue))
        
        # Process events in the dead letter queue
        processed_count = 0
        failed_count = 0
        current_time = time.time()
        
        # Create a copy of the queue to iterate over, as we'll be modifying the original
        dlq_copy = self._dead_letter_queue.copy()
        events_to_remove = []
        
        for dead_letter_entry in dlq_copy:
            try:
                # Check if enough time has passed for retry
                retry_count = dead_letter_entry.get("retry_count", 0)
                last_retry = dead_letter_entry.get("last_retry_timestamp", 0)
                retry_delay = self._calculate_retry_delay(retry_count)
                
                if current_time - last_retry < retry_delay:
                    # Not time to retry yet, skip this event
                    continue
                
                # Get event data
                event_data = dead_letter_entry["event"]
                event_type = event_data.get("event_type", "unknown")
                
                # Recreate event object
                event_class = EVENT_MODELS.get(event_type, BaseEvent)
                event = event_class(**event_data)
                
                # Check if we should retry this event (max 5 attempts)
                if retry_count >= 5:
                    logger.warning(
                        "Event has exceeded maximum retry attempts, keeping in dead letter queue: %s",
                        event.event_id
                    )
                    # Update retry timestamp but keep in queue
                    dead_letter_entry["last_retry_timestamp"] = current_time
                    failed_count += 1
                    continue
                
                # Try to process the event again
                if event_type in self._handlers:
                    success = False
                    for handler in self._handlers[event_type]:
                        try:
                            start_time = time.time()
                            await handler(event)
                            processing_time = time.time() - start_time
                            self._metrics["events_processed"] += 1
                            self._metrics["events_retried"] += 1
                            self._add_processing_time(processing_time)
                            success = True
                            processed_count += 1
                            # Mark for removal from DLQ
                            events_to_remove.append(dead_letter_entry)
                            logger.info("Successfully retried event: %s", event.event_id)
                            break  # Success, move to next event
                        except Exception as e:
                            processing_time = time.time() - start_time
                            self._add_processing_time(processing_time)
                            logger.warning(
                                "Failed to retry event processing: %s - %s",
                                event.event_id,
                                str(e)
                            )
                            break
                    
                    if not success:
                        # Increment retry count and update timestamp
                        dead_letter_entry["retry_count"] = retry_count + 1
                        dead_letter_entry["last_retry_timestamp"] = current_time
                        failed_count += 1
                else:
                    logger.warning("No handler found for event type: %s", event_type)
                    # For unknown event types, we'll keep them in the queue
                    dead_letter_entry["retry_count"] = retry_count + 1
                    dead_letter_entry["last_retry_timestamp"] = current_time
                    failed_count += 1
                    
            except Exception as e:
                logger.error("Error processing dead letter queue: %s", str(e))
                failed_count += 1
        
        # Remove successfully processed events from the original queue
        for entry in events_to_remove:
            if entry in self._dead_letter_queue:
                self._dead_letter_queue.remove(entry)
        
        # Update metrics
        self._metrics["dlq_size"] = len(self._dead_letter_queue)
        
        if processed_count > 0 or failed_count > 0:
            logger.info(
                "Dead letter queue processing complete: %d processed, %d failed",
                processed_count,
                failed_count
            )
    
    def _cleanup_expired_processed_events(self) -> None:
        """Clean up expired entries from the processed events cache."""
        current_time = time.time()
        expired_keys = [
            event_id for event_id, timestamp in self._processed_events.items()
            if current_time - timestamp > self._processed_events_ttl
        ]
        
        for event_id in expired_keys:
            del self._processed_events[event_id]
        
        logger.debug("Cleaned up %d expired processed events", len(expired_keys))
    
    def _is_event_processed(self, event: BaseEvent) -> bool:
        """Check if an event has already been processed (for idempotent processing).
        
        Args:
            event (BaseEvent): Event to check
            
        Returns:
            bool: True if event has been processed, False otherwise
        """
        # Clean up expired entries first
        self._cleanup_expired_processed_events()
        
        # Check if event has been processed
        return event.event_id in self._processed_events
    
    def _mark_event_processed(self, event: BaseEvent) -> None:
        """Mark an event as processed (for idempotent processing).
        
        Args:
            event (BaseEvent): Event to mark as processed
        """
        # Clean up expired entries first to maintain cache size
        self._cleanup_expired_processed_events()
        
        # If cache is at max size, remove oldest entry
        if len(self._processed_events) >= self._processed_events_max_size:
            oldest_key = min(self._processed_events.keys(), key=lambda k: self._processed_events[k])
            del self._processed_events[oldest_key]
        
        # Mark event as processed
        self._processed_events[event.event_id] = time.time()
        
        logger.debug("Marked event as processed: %s", event.event_id)
    
    def _add_processing_time(self, processing_time: float) -> None:
        """Add processing time to metrics.
        
        Args:
            processing_time (float): Processing time in seconds
        """
        self._metrics["processing_times"].append(processing_time)
        # Keep only the last N processing times
        if len(self._metrics["processing_times"]) > self._max_processing_times:
            self._metrics["processing_times"] = self._metrics["processing_times"][-self._max_processing_times:]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the event processor.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        logger.debug("Performing event processor health check")
        
        # Calculate processing time statistics
        processing_times = self._metrics["processing_times"]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        p95_processing_time = sorted(processing_times)[int(len(processing_times) * 0.95)] if processing_times else 0
        p99_processing_time = sorted(processing_times)[int(len(processing_times) * 0.99)] if processing_times else 0
        
        health_status = {
            "is_processing": self._is_processing,
            "handler_count": len(self._handlers),
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "event_bus_connected": self.event_bus.is_connected if self.event_bus else False,
            "processed_events_cache_size": len(self._processed_events),
            "metrics": {
                "events_processed": self._metrics["events_processed"],
                "events_failed": self._metrics["events_failed"],
                "events_retried": self._metrics["events_retried"],
                "dlq_size": self._metrics["dlq_size"],
                "processing_time_avg_ms": round(avg_processing_time * 1000, 2),
                "processing_time_p95_ms": round(p95_processing_time * 1000, 2),
                "processing_time_p99_ms": round(p99_processing_time * 1000, 2),
                "error_rate": round(
                    self._metrics["events_failed"] / max(self._metrics["events_processed"] + self._metrics["events_failed"], 1) * 100, 
                    2
                )
            }
        }
        
        logger.debug("Event processor health check results: %s", health_status)
        return health_status
    
    @property
    def is_processing(self) -> bool:
        """Check if the event processor is currently processing events.
        
        Returns:
            bool: True if processing events, False otherwise
        """
        return self._is_processing


# Convenience function for easy usage
async def create_event_processor(event_bus: EventBus, config_manager: Optional[ConfigManager] = None) -> EventProcessor:
    """Create and start an event processor instance.
    
    Args:
        event_bus (EventBus): Event bus instance
        config_manager (ConfigManager, optional): Configuration manager instance
        
    Returns:
        EventProcessor: Started event processor instance
    """
    event_processor = EventProcessor(event_bus, config_manager)
    await event_processor.start_processing()
    return event_processor
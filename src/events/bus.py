"""
Event bus implementation for the YABOT system.

This module provides the event bus functionality with Redis Pub/Sub and local fallback queue
as required by the fase1 specification.
"""

import asyncio
import json
import logging
import pickle
import time
import uuid
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from redis import asyncio as aioredis
from src.events.models import BaseEvent
from src.utils.logger import get_logger
from src.config.manager import ConfigManager

logger = get_logger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry mechanism."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class EventRetryInfo:
    """Information about event retry attempts."""
    event_id: str
    event_name: str
    payload: Dict[str, Any]
    attempt_count: int = 0
    first_attempt_time: datetime = field(default_factory=datetime.utcnow)
    last_attempt_time: datetime = field(default_factory=datetime.utcnow)
    next_retry_time: Optional[datetime] = None
    error_messages: List[str] = field(default_factory=list)


class EventBusError(Exception):
    """Base exception for event bus operations."""
    pass


class EventPublishError(EventBusError):
    """Exception raised when event publishing fails."""
    pass


class EventSubscribeError(EventBusError):
    """Exception raised when event subscription fails."""
    pass


class EventBus:
    """Event bus implementation with Redis Pub/Sub, local fallback queue, and retry mechanism."""

    def __init__(self, config_manager: Optional[ConfigManager] = None, retry_policy: Optional[RetryPolicy] = None):
        """Initialize the event bus.

        Args:
            config_manager (ConfigManager, optional): Configuration manager instance
            retry_policy (RetryPolicy, optional): Retry policy configuration
        """
        self.config_manager = config_manager or ConfigManager()
        self.retry_policy = retry_policy or RetryPolicy()
        self._redis_client: Optional[aioredis.Redis] = None
        self._is_connected = False
        self._local_queue: List[Dict[str, Any]] = []
        self._retry_queue: Dict[str, EventRetryInfo] = {}
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self._max_queue_size: int = 1000
        self._persistence_file: str = "event_queue.pkl"
        self._retry_persistence_file: str = "event_retry_queue.pkl"
        self._flush_interval: float = 5.0
        self._retry_check_interval: float = 2.0
        self._flush_task: Optional[asyncio.Task] = None
        self._retry_task: Optional[asyncio.Task] = None

        logger.info("EventBus initialized with retry policy: max_retries=%d, initial_delay=%.1fs",
                   self.retry_policy.max_retries, self.retry_policy.initial_delay)
    
    async def connect(self) -> bool:
        """Establish connection to Redis with retry logic.
        
        Returns:
            bool: True if connection was established successfully, False otherwise
        """
        logger.info("Connecting to Redis")
        
        try:
            # Get Redis configuration
            redis_config = self.config_manager.get_redis_config()
            
            # Update local queue configuration
            self._update_queue_config()
            
            # Load persisted events from file
            self._load_persisted_events()
            self._load_persisted_retry_queue()

            # Connect to Redis with retry logic
            max_retries = 3
            retry_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    # Create Redis client with connection pooling
                    self._redis_client = aioredis.from_url(
                        redis_config.redis_url,
                        password=redis_config.redis_password,
                        retry_on_timeout=True,
                        socket_connect_timeout=5,
                        socket_timeout=10,
                        max_connections=50
                    )
                    
                    # Test connection
                    await self._redis_client.ping()
                    
                    self._is_connected = True
                    logger.info("Successfully connected to Redis")
                    
                    # Start flush task to process local queue
                    self._start_flush_task()

                    # Start retry task to process retry queue
                    self._start_retry_task()

                    # Process any queued events
                    await self._process_local_queue()
                    await self._process_retry_queue()
                    
                    return True
                    
                except Exception as e:
                    logger.warning(
                        "Redis connection attempt %d failed: %s", 
                        attempt + 1, 
                        str(e)
                    )
                    
                    if attempt < max_retries - 1:
                        logger.info("Retrying in %d seconds...", int(retry_delay))
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error("Max retries exceeded for Redis connection")
                        # We're still initialized but not connected
                        self._is_connected = False
                        # Start flush task even without Redis connection
                        self._start_flush_task()
                        # Start retry task even without Redis connection
                        self._start_retry_task()
                        return False
                        
        except Exception as e:
            logger.error("Error connecting to Redis: %s", str(e))
            return False
    
    def _update_queue_config(self) -> None:
        """Update local queue configuration from event bus config."""
        # In a real implementation, this would come from config
        # For now, we use the defaults defined in the events/__init__.py
        try:
            from src.events import EVENT_BUS_CONFIG
            self._max_queue_size = EVENT_BUS_CONFIG.get("queue_max_size", 1000)
            self._persistence_file = EVENT_BUS_CONFIG.get("persistence_file", "event_queue.pkl")
            self._flush_interval = EVENT_BUS_CONFIG.get("flush_interval", 5.0)
        except ImportError:
            # Use defaults if config is not available
            pass
    
    def _load_persisted_events(self) -> None:
        """Load persisted events from file."""
        try:
            with open(self._persistence_file, 'rb') as f:
                self._local_queue = pickle.load(f)
            logger.info("Loaded %d events from persistence file", len(self._local_queue))
        except FileNotFoundError:
            logger.debug("No persistence file found, starting with empty queue")
            self._local_queue = []
        except Exception as e:
            logger.warning("Error loading persisted events: %s", str(e))
            self._local_queue = []
    
    def _persist_events(self) -> None:
        """Persist events to file."""
        try:
            with open(self._persistence_file, 'wb') as f:
                pickle.dump(self._local_queue, f)
            logger.debug("Persisted %d events to file", len(self._local_queue))
        except Exception as e:
            logger.warning("Error persisting events: %s", str(e))

    def _load_persisted_retry_queue(self) -> None:
        """Load persisted retry queue from file."""
        try:
            with open(self._retry_persistence_file, 'rb') as f:
                self._retry_queue = pickle.load(f)
            logger.info("Loaded %d events from retry persistence file", len(self._retry_queue))
        except FileNotFoundError:
            logger.debug("No retry persistence file found, starting with empty retry queue")
            self._retry_queue = {}
        except Exception as e:
            logger.warning("Error loading persisted retry queue: %s", str(e))
            self._retry_queue = {}

    def _persist_retry_queue(self) -> None:
        """Persist retry queue to file."""
        try:
            with open(self._retry_persistence_file, 'wb') as f:
                pickle.dump(self._retry_queue, f)
            logger.debug("Persisted %d retry events to file", len(self._retry_queue))
        except Exception as e:
            logger.warning("Error persisting retry queue: %s", str(e))
    
    def _start_flush_task(self) -> None:
        """Start the periodic flush task."""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.debug("Started flush task")

    def _start_retry_task(self) -> None:
        """Start the periodic retry task."""
        if self._retry_task is None or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._retry_loop())
            logger.debug("Started retry task")
    
    async def _flush_loop(self) -> None:
        """Periodically flush the local queue."""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                if self._is_connected:
                    await self._process_local_queue()
            except asyncio.CancelledError:
                logger.info("Flush task cancelled")
                break
            except Exception as e:
                logger.error("Error in flush loop: %s", str(e))

    async def _retry_loop(self) -> None:
        """Periodically process the retry queue."""
        while True:
            try:
                await asyncio.sleep(self._retry_check_interval)
                if self._is_connected:
                    await self._process_retry_queue()
            except asyncio.CancelledError:
                logger.info("Retry task cancelled")
                break
            except Exception as e:
                logger.error("Error in retry loop: %s", str(e))
    
    async def publish(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Publish an event to Redis Pub/Sub with retry mechanism.

        Args:
            event_name (str): Name of the event to publish
            payload (Dict[str, Any]): Event payload

        Returns:
            bool: True if event was published successfully, False otherwise
        """
        logger.debug("Publishing event: %s", event_name)

        try:
            # Add timestamp and event ID if not present
            if "timestamp" not in payload:
                payload["timestamp"] = time.time()
            if "event_id" not in payload:
                payload["event_id"] = str(uuid.uuid4())

            event_id = payload["event_id"]

            # Try to publish to Redis if connected
            if self._is_connected and self._redis_client:
                try:
                    success = await self._publish_to_redis(event_name, payload)
                    if success:
                        # Remove from retry queue if it was there
                        self._retry_queue.pop(event_id, None)
                        return True
                    else:
                        # Add to retry queue
                        await self._add_to_retry_queue(event_id, event_name, payload, "Redis publish failed")
                        return False

                except Exception as e:
                    error_msg = f"Failed to publish to Redis: {str(e)}"
                    logger.warning(error_msg)
                    await self._add_to_retry_queue(event_id, event_name, payload, error_msg)
                    return False

            # If Redis is not available, queue locally and add to retry queue
            local_success = await self._queue_locally(event_name, payload)
            if local_success:
                await self._add_to_retry_queue(event_id, event_name, payload, "Redis not connected")
            return local_success

        except Exception as e:
            logger.error("Error publishing event: %s", str(e))
            return False

    async def _publish_to_redis(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Publish event directly to Redis.

        Args:
            event_name (str): Name of the event to publish
            payload (Dict[str, Any]): Event payload

        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_payload = self._make_json_serializable(payload)

            # Serialize payload
            serialized_payload = json.dumps(serializable_payload)

            # Publish to Redis
            await self._redis_client.publish(event_name, serialized_payload)
            logger.debug("Event published to Redis: %s", event_name)
            return True

        except Exception as e:
            logger.warning("Redis publish failed: %s", str(e))
            return False

    async def _add_to_retry_queue(self, event_id: str, event_name: str, payload: Dict[str, Any], error_msg: str) -> None:
        """Add event to retry queue with exponential backoff.

        Args:
            event_id (str): Unique event identifier
            event_name (str): Name of the event
            payload (Dict[str, Any]): Event payload
            error_msg (str): Error message from failed attempt
        """
        current_time = datetime.utcnow()

        if event_id in self._retry_queue:
            # Update existing retry info
            retry_info = self._retry_queue[event_id]
            retry_info.attempt_count += 1
            retry_info.last_attempt_time = current_time
            retry_info.error_messages.append(error_msg)
        else:
            # Create new retry info
            retry_info = EventRetryInfo(
                event_id=event_id,
                event_name=event_name,
                payload=payload,
                attempt_count=1,
                first_attempt_time=current_time,
                last_attempt_time=current_time,
                error_messages=[error_msg]
            )
            self._retry_queue[event_id] = retry_info

        # Calculate next retry time with exponential backoff
        if retry_info.attempt_count <= self.retry_policy.max_retries:
            delay = self._calculate_retry_delay(retry_info.attempt_count)
            retry_info.next_retry_time = current_time + timedelta(seconds=delay)
            logger.debug("Event %s scheduled for retry %d in %.1f seconds",
                        event_id, retry_info.attempt_count, delay)
        else:
            # Max retries exceeded, publish error event
            logger.error("Event %s exceeded max retries (%d), giving up",
                        event_id, self.retry_policy.max_retries)
            await self._publish_retry_failure_event(retry_info)
            # Remove from retry queue
            del self._retry_queue[event_id]

        # Persist retry queue
        self._persist_retry_queue()

    def _calculate_retry_delay(self, attempt_count: int) -> float:
        """Calculate retry delay with exponential backoff and jitter.

        Args:
            attempt_count (int): Current attempt count

        Returns:
            float: Delay in seconds
        """
        delay = self.retry_policy.initial_delay * (self.retry_policy.backoff_multiplier ** (attempt_count - 1))
        delay = min(delay, self.retry_policy.max_delay)

        if self.retry_policy.jitter:
            import random
            # Add up to 25% jitter
            jitter = delay * 0.25 * random.random()
            delay += jitter

        return delay

    async def _publish_retry_failure_event(self, retry_info: EventRetryInfo) -> None:
        """Publish an event indicating that retry failed.

        Args:
            retry_info (EventRetryInfo): Information about the failed retry
        """
        try:
            from src.events.models import create_event

            error_event = create_event(
                "event_processing_failed",
                user_id=retry_info.payload.get("user_id"),
                error_message=f"Event retry failed after {retry_info.attempt_count} attempts",
                original_event_type=retry_info.event_name,
                original_event_id=retry_info.event_id,
                metadata={
                    "retry_attempts": retry_info.attempt_count,
                    "first_attempt_time": retry_info.first_attempt_time.isoformat(),
                    "last_attempt_time": retry_info.last_attempt_time.isoformat(),
                    "error_messages": retry_info.error_messages
                }
            )

            # Try to publish error event (without retry to avoid infinite loop)
            if self._is_connected and self._redis_client:
                await self._publish_to_redis("event_processing_failed", error_event.dict())
            else:
                # Queue locally if Redis is not available
                await self._queue_locally("event_processing_failed", error_event.dict())

        except Exception as e:
            logger.error("Failed to publish retry failure event: %s", str(e))
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert non-JSON-serializable objects to serializable formats.
        
        Args:
            obj: Object to make JSON serializable
            
        Returns:
            JSON-serializable version of the object
        """
        import datetime
        
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_json_serializable(item) for item in obj)
        elif isinstance(obj, set):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj

    async def _queue_locally(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Queue event locally when Redis is unavailable.
        
        Args:
            event_name (str): Name of the event to queue
            payload (Dict[str, Any]): Event payload
            
        Returns:
            bool: True if event was queued successfully, False otherwise
        """
        logger.debug("Queueing event locally: %s", event_name)
        
        try:
            # Check queue size
            if len(self._local_queue) >= self._max_queue_size:
                logger.warning("Local queue is full, dropping oldest event")
                self._local_queue.pop(0)  # Remove oldest event
            
            # Add event to queue
            queued_event = {
                "event_name": event_name,
                "payload": payload,
                "timestamp": time.time()
            }
            self._local_queue.append(queued_event)
            
            # Persist queue to file
            self._persist_events()
            
            logger.debug("Event queued locally: %s", event_name)
            return True
            
        except Exception as e:
            logger.error("Error queueing event locally: %s", str(e))
            return False
    
    async def _process_local_queue(self) -> None:
        """Process events in the local queue."""
        if not self._local_queue or not self._is_connected or not self._redis_client:
            return
        
        logger.debug("Processing %d events from local queue", len(self._local_queue))
        
        # Process events in batch
        processed_count = 0
        failed_count = 0
        
        while self._local_queue and self._is_connected:
            try:
                # Get event from queue
                queued_event = self._local_queue.pop(0)
                event_name = queued_event["event_name"]
                payload = queued_event["payload"]
                
                # Make payload JSON serializable
                serializable_payload = self._make_json_serializable(payload)
                
                # Serialize payload
                serialized_payload = json.dumps(serializable_payload)
                
                # Publish to Redis
                await self._redis_client.publish(event_name, serialized_payload)
                processed_count += 1
                
            except Exception as e:
                logger.warning("Failed to process queued event: %s", str(e))
                failed_count += 1
                # Put the event back at the beginning of the queue
                self._local_queue.insert(0, queued_event)
                break  # Stop processing if we encounter an error
        
        if processed_count > 0:
            logger.info("Processed %d events from local queue", processed_count)
            # Persist the updated queue
            self._persist_events()
        
        if failed_count > 0:
            logger.warning("Failed to process %d events from local queue", failed_count)

    async def _process_retry_queue(self) -> None:
        """Process events in the retry queue that are ready for retry."""
        if not self._retry_queue or not self._is_connected or not self._redis_client:
            return

        current_time = datetime.utcnow()
        ready_events = []

        # Find events ready for retry
        for event_id, retry_info in self._retry_queue.items():
            if (retry_info.next_retry_time and
                retry_info.next_retry_time <= current_time and
                retry_info.attempt_count <= self.retry_policy.max_retries):
                ready_events.append(event_id)

        if not ready_events:
            return

        logger.debug("Processing %d events from retry queue", len(ready_events))

        processed_count = 0
        failed_count = 0

        for event_id in ready_events:
            try:
                retry_info = self._retry_queue[event_id]

                # Try to publish the event
                success = await self._publish_to_redis(retry_info.event_name, retry_info.payload)

                if success:
                    # Remove from retry queue on success
                    del self._retry_queue[event_id]
                    processed_count += 1
                    logger.debug("Retry successful for event %s after %d attempts",
                               event_id, retry_info.attempt_count)
                else:
                    # Add back to retry queue with updated attempt count
                    await self._add_to_retry_queue(
                        event_id,
                        retry_info.event_name,
                        retry_info.payload,
                        "Retry attempt failed"
                    )
                    failed_count += 1

            except Exception as e:
                logger.warning("Error processing retry for event %s: %s", event_id, str(e))
                failed_count += 1

        if processed_count > 0:
            logger.info("Successfully retried %d events", processed_count)
            # Persist the updated retry queue
            self._persist_retry_queue()

        if failed_count > 0:
            logger.warning("Failed to retry %d events", failed_count)
    
    async def subscribe(self, event_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> bool:
        """Subscribe to an event.
        
        Args:
            event_name (str): Name of the event to subscribe to
            handler (Callable): Handler function to call when event is received
            
        Returns:
            bool: True if subscription was successful, False otherwise
        """
        logger.debug("Subscribing to event: %s", event_name)
        
        try:
            # Add handler to subscribers
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(handler)
            
            # If we have a Redis connection, subscribe to the channel
            if self._is_connected and self._redis_client:
                # In a real implementation, we would set up a Redis subscription
                # For now, we'll just log that we're subscribed
                logger.debug("Subscribed to event: %s", event_name)
            
            return True
            
        except Exception as e:
            logger.error("Error subscribing to event: %s", str(e))
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the event bus.

        Returns:
            Dict[str, Any]: Health status information
        """
        logger.debug("Performing event bus health check")

        health_status = {
            "connected": self._is_connected,
            "local_queue_size": len(self._local_queue),
            "retry_queue_size": len(self._retry_queue),
            "subscribers_count": sum(len(handlers) for handlers in self._subscribers.values()),
            "retry_policy": {
                "max_retries": self.retry_policy.max_retries,
                "initial_delay": self.retry_policy.initial_delay,
                "max_delay": self.retry_policy.max_delay,
                "backoff_multiplier": self.retry_policy.backoff_multiplier
            }
        }
        
        # Check Redis connection if connected
        if self._is_connected and self._redis_client:
            try:
                await self._redis_client.ping()
                health_status["redis_healthy"] = True
            except Exception as e:
                logger.warning("Redis health check failed: %s", str(e))
                health_status["redis_healthy"] = False
        
        logger.debug("Event bus health check results: %s", health_status)
        return health_status
    
    async def close(self) -> None:
        """Close the event bus connections and clean up."""
        logger.info("Closing event bus connections")
        
        # Cancel flush task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Cancel retry task
        if self._retry_task and not self._retry_task.done():
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        # Close Redis connection
        if self._redis_client:
            try:
                await self._redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error("Error closing Redis connection: %s", str(e))
        
        # Persist any remaining events
        self._persist_events()
        self._persist_retry_queue()
        
        self._is_connected = False
        logger.info("Event bus connections closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if the event bus is connected to Redis.
        
        Returns:
            bool: True if connected to Redis, False otherwise
        """
        return self._is_connected


# Convenience function for easy usage
async def create_event_bus(
    config_manager: Optional[ConfigManager] = None,
    retry_policy: Optional[RetryPolicy] = None
) -> EventBus:
    """Create and connect an event bus instance.

    Args:
        config_manager (ConfigManager, optional): Configuration manager instance
        retry_policy (RetryPolicy, optional): Retry policy configuration

    Returns:
        EventBus: Connected event bus instance
    """
    event_bus = EventBus(config_manager, retry_policy)
    await event_bus.connect()
    return event_bus

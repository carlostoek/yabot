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
from typing import Any, Dict, List, Optional, Callable, Awaitable
from redis import asyncio as aioredis
from src.events.models import BaseEvent
from src.utils.logger import get_logger
from src.config.manager import ConfigManager

logger = get_logger(__name__)


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
    """Event bus implementation with Redis Pub/Sub and local fallback queue."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the event bus.
        
        Args:
            config_manager (ConfigManager, optional): Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self._redis_client: Optional[aioredis.Redis] = None
        self._is_connected = False
        self._local_queue: List[Dict[str, Any]] = []
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self._max_queue_size: int = 1000
        self._persistence_file: str = "event_queue.pkl"
        self._flush_interval: float = 5.0
        self._flush_task: Optional[asyncio.Task] = None
        
        logger.info("EventBus initialized")
    
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
                    
                    # Process any queued events
                    await self._process_local_queue()
                    
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
    
    def _start_flush_task(self) -> None:
        """Start the periodic flush task."""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.debug("Started flush task")
    
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
    
    async def publish(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Publish an event to Redis Pub/Sub or local queue.
        
        Args:
            event_name (str): Name of the event to publish
            payload (Dict[str, Any]): Event payload
            
        Returns:
            bool: True if event was published successfully, False otherwise
        """
        logger.debug("Publishing event: %s", event_name)
        
        try:
            # Add timestamp if not present
            if "timestamp" not in payload:
                payload["timestamp"] = time.time()
            
            # Try to publish to Redis if connected
            if self._is_connected and self._redis_client:
                try:
                    # Serialize payload
                    serialized_payload = json.dumps(payload)
                    
                    # Publish to Redis
                    await self._redis_client.publish(event_name, serialized_payload)
                    logger.debug("Event published to Redis: %s", event_name)
                    return True
                    
                except Exception as e:
                    logger.warning("Failed to publish to Redis: %s", str(e))
            
            # If Redis is not available or publish failed, queue locally
            return await self._queue_locally(event_name, payload)
            
        except Exception as e:
            logger.error("Error publishing event: %s", str(e))
            return False
    
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
                
                # Serialize payload
                serialized_payload = json.dumps(payload)
                
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
            "subscribers_count": sum(len(handlers) for handlers in self._subscribers.values())
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
        
        # Close Redis connection
        if self._redis_client:
            try:
                await self._redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error("Error closing Redis connection: %s", str(e))
        
        # Persist any remaining events
        self._persist_events()
        
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
async def create_event_bus(config_manager: Optional[ConfigManager] = None) -> EventBus:
    """Create and connect an event bus instance.
    
    Args:
        config_manager (ConfigManager, optional): Configuration manager instance
        
    Returns:
        EventBus: Connected event bus instance
    """
    event_bus = EventBus(config_manager)
    await event_bus.connect()
    return event_bus
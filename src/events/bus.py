"""
Event Bus - Redis-based Event Publishing and Subscription

This module provides a Redis-based event bus with reliability features
and local fallback queue for when Redis is unavailable.
"""
import asyncio
import json
import pickle
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
import time
import os
from pathlib import Path

# Import Redis
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

# Import models and logger
from src.core.models import RedisConfig
from .models import BaseEvent, EventStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


from .exceptions import EventBusException, EventProcessingError


class LocalEventQueue:
    """
    Local fallback queue for events when Redis is unavailable
    """
    def __init__(self, max_size: int = 1000, persistence_file: str = "event_queue.pkl"):
        self.max_size = max_size
        self.persistence_file = Path(persistence_file)
        self.queue = asyncio.Queue(maxsize=max_size)
        self._persistence_lock = asyncio.Lock()
        
    async def enqueue(self, event: BaseEvent) -> bool:
        """
        Add an event to the local queue
        
        Args:
            event: The event to add to the queue
            
        Returns:
            True if successfully added, False if queue is full
        """
        try:
            if self.queue.full():
                logger.warning("Local event queue is full, dropping oldest event")
                try:
                    # Remove oldest event to make space
                    await self.queue.get()
                except asyncio.QueueEmpty:
                    pass
            
            await self.queue.put(event)
            logger.debug("Event added to local queue", event_id=event.event_id)
            
            # Persist the queue to file
            await self._persist_queue()
            
            return True
        except Exception as e:
            logger.error("Error adding event to local queue", error=str(e), event_id=event.event_id)
            return False
    
    async def dequeue(self) -> Optional[BaseEvent]:
        """
        Remove and return an event from the local queue
        
        Returns:
            The oldest event in the queue or None if empty
        """
        try:
            if self.queue.empty():
                event = await self._load_from_persistence()
                if event:
                    return event
                return None
            
            event = await self.queue.get()
            logger.debug("Event removed from local queue", event_id=event.event_id)
            
            # Persist the queue to file
            await self._persist_queue()
            
            return event
        except asyncio.QueueEmpty:
            logger.debug("Local event queue is empty")
            return None
        except Exception as e:
            logger.error("Error removing event from local queue", error=str(e))
            return None
    
    async def size(self) -> int:
        """
        Get the current size of the queue
        
        Returns:
            Number of events in the queue
        """
        return self.queue.qsize()
    
    async def _persist_queue(self):
        """
        Persist the current queue state to a file
        """
        async with self._persistence_lock:
            try:
                # Convert queue to list
                temp_list = []
                while not self.queue.empty():
                    event = self.queue.get_nowait()
                    temp_list.append(event)
                
                # Write to file
                with open(self.persistence_file, 'wb') as f:
                    pickle.dump(temp_list, f)
                
                # Put items back in queue
                for event in temp_list:
                    try:
                        self.queue.put_nowait(event)
                    except asyncio.QueueFull:
                        logger.warning("Queue became full during persistence, dropping event")
                        break
                        
            except Exception as e:
                logger.error("Error persisting queue to file", error=str(e))
    
    async def _load_from_persistence(self) -> Optional[BaseEvent]:
        """
        Load events from persistence file if queue is empty
        
        Returns:
            An event from the persisted file or None if empty
        """
        async with self._persistence_lock:
            try:
                if not self.persistence_file.exists():
                    return None
                
                with open(self.persistence_file, 'rb') as f:
                    temp_list = pickle.load(f)
                
                # Add items back to queue (up to max_size)
                added_count = 0
                for event in temp_list:
                    if added_count < self.max_size:
                        try:
                            self.queue.put_nowait(event)
                            added_count += 1
                        except asyncio.QueueFull:
                            logger.warning("Queue became full while loading from persistence")
                            break
                
                # If we have items to return, get the first one
                if not self.queue.empty():
                    try:
                        return self.queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return None
                
                return None
            except Exception as e:
                logger.error("Error loading queue from persistence", error=str(e))
                return None
    
    async def clear(self):
        """
        Clear all events from the queue and persistence file
        """
        # Clear in-memory queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Remove persistence file
        if self.persistence_file.exists():
            self.persistence_file.unlink()
        
        logger.info("Local event queue cleared")
    
    # Alias for compatibility with tests
    async def add(self, event: BaseEvent) -> bool:
        """
        Add an event to the local queue (alias for enqueue)
        
        Args:
            event: The event to add to the queue
            
        Returns:
            True if successfully added, False if queue is full
        """
        return await self.enqueue(event)
    
    async def get(self) -> Optional[BaseEvent]:
        """
        Remove and return an event from the local queue (alias for dequeue)
        
        Returns:
            The oldest event in the queue or None if empty
        """
        return await self.dequeue()


class EventBus:
    """
    Main event bus implementation with Redis and local fallback
    """
    def __init__(self, redis_config: Optional[RedisConfig] = None):
        # Use default config if none provided
        if redis_config is None:
            self.redis_config = RedisConfig(
                url='redis://localhost:6379',
                password=None,
                max_connections=50,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=10,
                local_queue_max_size=1000,
                local_queue_persistence_file='event_queue.pkl'
            )
        else:
            # Use provided config
            self.redis_config = redis_config
        
        # Initialize Redis connection
        self.redis_url = self.redis_config.url
        self.redis_password = self.redis_config.password
        self.max_connections = self.redis_config.max_connections
        self.retry_on_timeout = self.redis_config.retry_on_timeout
        self.socket_connect_timeout = self.redis_config.socket_connect_timeout
        self.socket_timeout = self.redis_config.socket_timeout

        # Get local queue config
        self.local_queue_max_size = self.redis_config.local_queue_max_size
        self.local_queue_persistence_file = self.redis_config.local_queue_persistence_file
        
        # Initialize attributes
        self.redis_client = None
        self.local_queue = LocalEventQueue(
            max_size=self.local_queue_max_size,
            persistence_file=self.local_queue_persistence_file
        )
        self._connected = False
        self._reconnection_task = None
        self._publisher_task = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            'published_events': 0,
            'failed_events': 0,
            'retried_events': 0,
            'redis_unavailable_time': 0
        }

    async def connect(self):
        """
        Establish connection to Redis with fallback to local queue
        """
        try:
            # Create Redis connection pool
            connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                password=self.redis_password,
                max_connections=self.max_connections,
                retry_on_timeout=self.retry_on_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_timeout=self.socket_timeout
            )
            
            self.redis_client = redis.Redis(connection_pool=connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            
            logger.info("Successfully connected to Redis", redis_url=self.redis_url)
            
            # Start publisher task to process local queue when Redis is available
            self._publisher_task = asyncio.create_task(self._process_local_queue_periodically())
            
        except (ConnectionError, TimeoutError, redis.ConnectionError) as e:
            self._connected = False
            logger.warning("Could not connect to Redis, using local fallback", error=str(e))
            
            # Continue with local queue only
            return True
        except Exception as e:
            logger.error("Unexpected error connecting to Redis", error=str(e))
            raise EventBusException(f"Failed to connect to Redis: {str(e)}")
    
    async def close(self):
        """
        Close the event bus and clean up resources
        """
        logger.info("Shutting down event bus")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Cancel publisher task
        if self._publisher_task and not self._publisher_task.done():
            self._publisher_task.cancel()
            try:
                await self._publisher_task
            except asyncio.CancelledError:
                pass
        
        # Close Redis connection if it exists
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Event bus shutdown completed")
    
    async def publish(self, event: BaseEvent, channel: str = "events") -> bool:
        """
        Publish an event to Redis with fallback to local queue
        
        Args:
            event: The event to publish
            channel: The channel to publish to (default: "events")
            
        Returns:
            True if successfully published or queued for later, False otherwise
        """
        try:
            # Update event timestamp
            event.timestamp = datetime.utcnow()
            
            # If Redis is connected, try to publish directly
            if self._connected:
                try:
                    # Serialize event
                    event_data = event.json()
                    
                    # Publish to Redis
                    result = await self.redis_client.publish(channel, event_data)
                    
                    # Update stats
                    self.stats['published_events'] += 1
                    
                    logger.debug("Event published to Redis", 
                               event_id=event.event_id, 
                               channel=channel, 
                               result=result)
                    
                    return True
                except (ConnectionError, TimeoutError, redis.ConnectionError, redis.TimeoutError) as e:
                    # Redis connection failed, switch to disconnected mode
                    self._connected = False
                    logger.warning("Redis connection failed, switching to local queue", error=str(e))
                    
                    # Add to local queue
                    return await self._add_to_local_queue(event)
            else:
                # Redis is not connected, add to local queue
                return await self._add_to_local_queue(event)
                
        except Exception as e:
            self.stats['failed_events'] += 1
            logger.error("Error publishing event", error=str(e), event_id=event.event_id)
            return False
    
    async def _add_to_local_queue(self, event: BaseEvent) -> bool:
        """
        Add an event to the local fallback queue
        
        Args:
            event: The event to add to the local queue
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            success = await self.local_queue.enqueue(event)
            if success:
                logger.info("Event added to local fallback queue", event_id=event.event_id)
            else:
                logger.error("Failed to add event to local queue (queue full)", event_id=event.event_id)
            
            return success
        except Exception as e:
            logger.error("Error adding event to local queue", error=str(e), event_id=event.event_id)
            return False
    
    async def subscribe(self, channel: str, handler: Callable[[str], None]):
        """
        Subscribe to events on a channel
        
        Args:
            channel: The channel to subscribe to
            handler: The handler function to call when an event is received
        """
        if not self._connected:
            raise EventBusException("Cannot subscribe when Redis is disconnected")
        
        async def _subscribe_task():
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            
            logger.info("Subscribed to Redis channel", channel=channel)
            
            try:
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            event_data = message['data'].decode('utf-8')
                            handler(event_data)
                        except Exception as e:
                            logger.error("Error in event handler", error=str(e))
            except Exception as e:
                logger.error("Error in subscription", error=str(e))
            finally:
                await pubsub.close()
        
        # Start subscription in background
        asyncio.create_task(_subscribe_task())
    
    async def _process_local_queue_periodically(self):
        """
        Periodically process events in the local queue when Redis is available
        """
        while not self._shutdown_event.is_set():
            try:
                # Check if Redis is available
                if self._connected:
                    # Try to process one event from the local queue
                    event = await self.local_queue.dequeue()
                    if event:
                        # Try to publish the event to Redis
                        success = await self.publish(event)
                        if success:
                            logger.info("Successfully published event from local queue", event_id=event.event_id)
                        else:
                            # If still failing, put it back in the queue
                            await self.local_queue.enqueue(event)
                    else:
                        # No events in queue, wait before checking again
                        await asyncio.sleep(1)
                else:
                    # Redis is not connected, try to reconnect
                    await self._attempt_reconnection()
                    
                    if self._connected:
                        # Successful reconnection, continue processing queue
                        continue
                    else:
                        # Still disconnected, wait longer before retrying
                        await asyncio.sleep(5)
                        
            except asyncio.CancelledError:
                logger.info("Local queue processing task cancelled")
                break
            except Exception as e:
                logger.error("Error in local queue processing", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _attempt_reconnection(self):
        """
        Attempt to reconnect to Redis
        """
        try:
            if self.redis_client:
                await self.redis_client.ping()
                self._connected = True
                logger.info("Reconnected to Redis")
            else:
                await self.connect()
        except (ConnectionError, TimeoutError, redis.ConnectionError, redis.TimeoutError):
            self._connected = False
        except Exception as e:
            logger.error("Error during reconnection attempt", error=str(e))
            self._connected = False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the event bus
        
        Returns:
            Dictionary with health status information
        """
        try:
            redis_connected = False
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    redis_connected = True
                except:
                    redis_connected = False
            
            local_queue_size = await self.local_queue.size()
            
            health_status = {
                'redis_connected': redis_connected,
                'local_queue_size': local_queue_size,
                'connected': self._connected,
                **self.stats,
            }
            
            logger.debug("Event bus health check completed", health_status=health_status)
            return health_status
        except Exception as e:
            logger.error("Error during health check", error=str(e))
            return {
                'redis_connected': False,
                'local_queue_size': 0,
                'connected': False,
                'redis_healthy': False,
                'overall_healthy': False,
                'error': str(e)
            }
    
    async def get_stats(self) -> Dict[str, int]:
        """
        Get current statistics for the event bus
        
        Returns:
            Dictionary with current statistics
        """
        local_queue_size = await self.local_queue.size()
        return {
            **self.stats,
            'local_queue_size': local_queue_size
        }
    
    async def clear_local_queue(self):
        """
        Clear all events from the local fallback queue
        """
        await self.local_queue.clear()
        logger.info("Local event queue cleared")
    
    async def replay_queue(self) -> int:
        """
        Replay events from the local queue when Redis becomes available
        
        Returns:
            Number of events successfully replayed
        """
        replayed_count = 0
        
        # Get events from local queue and publish them to Redis if available
        while True:
            # Get an event from the local queue
            event = await self.local_queue.dequeue()
            if event is None:
                # No more events in queue
                break
            
            # Try to publish the event
            success = await self.publish(event)
            if success:
                replayed_count += 1
                logger.info("Successfully replayed event from local queue", 
                           event_id=event.event_id)
            else:
                # If publishing fails, put the event back in the queue
                await self.local_queue.enqueue(event)
                logger.warning("Failed to replay event, putting back in local queue", 
                              event_id=event.event_id)
                break  # Stop replaying if we can't publish
        
        logger.info("Queue replay completed", replayed_count=replayed_count)
        return replayed_count
    
    def _serialize_event(self, event: BaseEvent) -> str:
        """
        Serialize an event to string for publishing
        
        Args:
            event: The event to serialize
            
        Returns:
            Serialized event as string
        """
        try:
            return event.json()
        except Exception as e:
            logger.error("Error serializing event", error=str(e), event_id=event.event_id)
            raise
    
    def _deserialize_event(self, serialized_event: str) -> Dict[str, Any]:
        """
        Deserialize an event from string
        
        Args:
            serialized_event: The serialized event string
            
        Returns:
            Deserialized event data as dictionary
        """
        try:
            event_data = json.loads(serialized_event)
            return {
                "event": BaseEvent.parse_raw(event_data) if isinstance(event_data, str) else event_data,
                "status": EventStatus.COMPLETE
            }
        except Exception as e:
            logger.error("Error deserializing event", error=str(e))
            return {"event": None, "status": EventStatus.ERROR, "error": str(e)}

"""
Event Correlation Service - Manages correlation IDs and event ordering

This module provides event correlation capabilities for tracking related events
and maintaining sequence order per user as required by Requirements 4.6, 4.8, and 4.9.
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

from src.core.models import RedisConfig
from src.events.models import BaseEvent
from src.utils.logger import get_logger


logger = get_logger(__name__)


class CorrelationStatus(Enum):
    """
    Status of correlation tracking
    """
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class CorrelationRecord:
    """
    Data structure for tracking correlation state
    """
    correlation_id: str
    user_id: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: CorrelationStatus = CorrelationStatus.ACTIVE
    timeout: int = 300  # 5 minutes default timeout
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_event(self, event: BaseEvent) -> None:
        """Add an event to the correlation record."""
        self.events.append({
            'event_id': event.event_id,
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat() if event.timestamp else datetime.utcnow().isoformat(),
            'payload': event.payload
        })
        self.updated_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark the correlation as completed."""
        self.status = CorrelationStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if the correlation has expired."""
        if self.status == CorrelationStatus.COMPLETED:
            return False  # Completed correlations don't expire
        if self.status == CorrelationStatus.EXPIRED:
            return True
            
        # Check if it's past the timeout
        age = datetime.utcnow() - self.updated_at
        return age.total_seconds() > self.timeout


class EventCorrelationService:
    """
    Service for managing event correlation and ordering
    
    Implements Requirements:
    - 4.6: Events SHALL be processed in chronological order using correlation IDs
    - 4.8: When events fail to process, the system SHALL publish error events with original event ID and error details
    - 4.9: When event ordering is critical, the system SHALL use message queues to maintain sequence per user
    """
    
    def __init__(self, redis_config: Optional[RedisConfig] = None):
        # Use default config if none provided
        if redis_config is None:
            self.redis_config = RedisConfig(
                url='redis://localhost:6379',
                password=None,
                max_connections=20,  # Lower connection count for correlation service
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=10,
                local_queue_max_size=1000,
                local_queue_persistence_file='correlation_queue.pkl'
            )
        else:
            self.redis_config = redis_config

        # Redis connection parameters
        self.redis_url = self.redis_config.url
        self.redis_password = self.redis_config.password
        self.max_connections = self.redis_config.max_connections
        self.retry_on_timeout = self.redis_config.retry_on_timeout
        self.socket_connect_timeout = self.redis_config.socket_connect_timeout
        self.socket_timeout = self.redis_config.socket_timeout

        # Redis client and connection status
        self.redis_client = None
        self._connected = False
        
        # Key patterns for Redis storage
        self._correlation_pattern = "correlation:{correlation_id}"
        self._user_sequence_pattern = "sequence:{user_id}:{correlation_id}"
        self._user_queue_pattern = "user_queue:{user_id}"
        
        # Statistics
        self.stats = {
            'tracked_correlations': 0,
            'completed_correlations': 0,
            'failed_correlations': 0,
            'expired_correlations': 0,
            'events_processed': 0
        }

    async def connect(self) -> bool:
        """
        Establish connection to Redis for correlation tracking
        
        Returns:
            True if connection successful, False otherwise
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
            
            logger.info("Event correlation service connected to Redis", redis_url=self.redis_url)
            return True
            
        except (ConnectionError, TimeoutError, redis.ConnectionError) as e:
            self._connected = False
            logger.warning("Could not connect to Redis for correlation service", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error connecting to Redis for correlation service", error=str(e))
            return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
        self._connected = False
        logger.info("Event correlation service disconnected from Redis")

    async def track_correlation(self, event: BaseEvent) -> bool:
        """
        Track an event in correlation context
        
        Args:
            event: The event to track in correlation context
            
        Returns:
            True if successfully tracked, False otherwise
        """
        try:
            if not self._connected:
                logger.warning("Redis not connected, cannot track correlation", event_id=event.event_id)
                return False

            # Create or update correlation record
            correlation_record = await self._get_correlation_record(event.correlation_id)
            
            if correlation_record is None:
                # Create new correlation record
                correlation_record = CorrelationRecord(
                    correlation_id=event.correlation_id,
                    user_id=event.user_id or "system",
                    timeout=300  # 5 minutes default
                )
            
            # Add event to correlation
            correlation_record.add_event(event)
            
            # Save correlation record to Redis
            correlation_key = self._correlation_pattern.format(correlation_id=event.correlation_id)
            correlation_data = {
                'correlation_id': correlation_record.correlation_id,
                'user_id': correlation_record.user_id,
                'events': correlation_record.events,
                'created_at': correlation_record.created_at.isoformat(),
                'updated_at': correlation_record.updated_at.isoformat(),
                'status': correlation_record.status.value,
                'timeout': correlation_record.timeout,
                'metadata': correlation_record.metadata
            }
            
            if correlation_record.completed_at:
                correlation_data['completed_at'] = correlation_record.completed_at.isoformat()
            
            # Save with expiration (timeout + buffer)
            await self.redis_client.setex(
                correlation_key,
                correlation_record.timeout + 60,  # Expire after timeout + 1 minute
                json.dumps(correlation_data)
            )
            
            # Add to user sequence if user_id is available
            if event.user_id:
                user_sequence_key = self._user_sequence_pattern.format(
                    user_id=event.user_id,
                    correlation_id=event.correlation_id
                )
                
                # Add event to user's sequence list with timestamp as score
                timestamp = time.time()
                await self.redis_client.zadd(user_sequence_key, {event.event_id: timestamp})
                
                # Set expiration on user sequence
                await self.redis_client.expire(user_sequence_key, correlation_record.timeout + 60)
            
            self.stats['events_processed'] += 1
            logger.debug("Event tracked in correlation", 
                        event_id=event.event_id, 
                        correlation_id=event.correlation_id)
            
            return True
            
        except Exception as e:
            logger.error("Error tracking correlation", error=str(e), event_id=event.event_id)
            return False

    async def track_event(self, event: BaseEvent, sequence_number: Optional[int] = None) -> bool:
        """
        Track an individual event for correlation and ordering

        Args:
            event: The event to track
            sequence_number: Optional sequence number for ordering

        Returns:
            True if successfully tracked, False otherwise
        """
        try:
            if not self._connected:
                logger.warning("Redis not connected, cannot track event", event_id=event.event_id)
                return False

            # Use track_correlation for the main functionality
            correlation_success = await self.track_correlation(event)

            if sequence_number is not None:
                # Also track sequence for ordering
                sequence_key = f"event_sequence:{event.user_id or 'system'}:{event.correlation_id}"
                await self.redis_client.zadd(
                    sequence_key,
                    {event.event_id: sequence_number}
                )
                # Set expiration
                await self.redis_client.expire(sequence_key, 3600)  # 1 hour

            return correlation_success

        except Exception as e:
            logger.error(f"Failed to track event {event.event_id}: {str(e)}")
            return False

    async def _get_correlation_record(self, correlation_id: str) -> Optional[CorrelationRecord]:
        """
        Retrieve correlation record from Redis
        
        Args:
            correlation_id: The correlation ID to retrieve
            
        Returns:
            CorrelationRecord if found, None otherwise
        """
        try:
            if not self._connected:
                return None
            
            correlation_key = self._correlation_pattern.format(correlation_id=correlation_id)
            correlation_data = await self.redis_client.get(correlation_key)
            
            if correlation_data is None:
                return None
            
            correlation_dict = json.loads(correlation_data)
            
            # Convert timestamps back to datetime
            created_at = datetime.fromisoformat(correlation_dict['created_at'])
            updated_at = datetime.fromisoformat(correlation_dict['updated_at'])
            
            completed_at = None
            if correlation_dict.get('completed_at'):
                completed_at = datetime.fromisoformat(correlation_dict['completed_at'])
            
            # Create CorrelationRecord
            record = CorrelationRecord(
                correlation_id=correlation_dict['correlation_id'],
                user_id=correlation_dict['user_id'],
                events=correlation_dict['events'],
                created_at=created_at,
                updated_at=updated_at,
                status=CorrelationStatus(correlation_dict['status']),
                timeout=correlation_dict['timeout'],
                completed_at=completed_at,
                metadata=correlation_dict.get('metadata', {})
            )
            
            return record
            
        except Exception as e:
            logger.error("Error retrieving correlation record", error=str(e), correlation_id=correlation_id)
            return None

    async def get_user_correlations(self, user_id: str) -> List[CorrelationRecord]:
        """
        Get all correlations for a specific user
        
        Args:
            user_id: The user ID to get correlations for
            
        Returns:
            List of correlation records for the user
        """
        try:
            if not self._connected:
                return []
            
            # Find correlations by user_id (this would require a more complex Redis query in practice)
            # For now, we'll return an empty list since finding all user correlations requires scanning
            # In a real implementation, we'd maintain a user -> correlations mapping
            correlations = []
            
            # In a production system, we'd maintain a set of correlation IDs per user
            user_correlations_key = f"user_correlations:{user_id}"
            correlation_ids = await self.redis_client.smembers(user_correlations_key)
            
            for correlation_id_bytes in correlation_ids:
                correlation_id = correlation_id_bytes.decode('utf-8')
                record = await self._get_correlation_record(correlation_id)
                if record:
                    correlations.append(record)
            
            logger.debug("Retrieved user correlations", user_id=user_id, count=len(correlations))
            return correlations
            
        except Exception as e:
            logger.error("Error retrieving user correlations", error=str(e), user_id=user_id)
            return []

    async def complete_correlation(self, correlation_id: str) -> bool:
        """
        Mark a correlation as completed
        
        Args:
            correlation_id: The correlation ID to complete
            
        Returns:
            True if successfully completed, False otherwise
        """
        try:
            if not self._connected:
                return False
            
            correlation_record = await self._get_correlation_record(correlation_id)
            if correlation_record is None:
                logger.warning("Cannot complete non-existent correlation", correlation_id=correlation_id)
                return False
            
            correlation_record.mark_completed()
            
            # Update in Redis
            correlation_key = self._correlation_pattern.format(correlation_id=correlation_id)
            correlation_data = {
                'correlation_id': correlation_record.correlation_id,
                'user_id': correlation_record.user_id,
                'events': correlation_record.events,
                'created_at': correlation_record.created_at.isoformat(),
                'updated_at': correlation_record.updated_at.isoformat(),
                'status': correlation_record.status.value,
                'timeout': correlation_record.timeout,
                'completed_at': correlation_record.completed_at.isoformat(),
                'metadata': correlation_record.metadata
            }
            
            # Save with shorter expiration since it's completed
            await self.redis_client.setex(
                correlation_key,
                3600,  # Keep completed correlations for 1 hour
                json.dumps(correlation_data)
            )
            
            self.stats['completed_correlations'] += 1
            logger.info("Correlation marked as completed", correlation_id=correlation_id)
            
            return True
            
        except Exception as e:
            logger.error("Error completing correlation", error=str(e), correlation_id=correlation_id)
            return False

    async def validate_event_order(self, event: BaseEvent, expected_previous_event_type: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate that an event is in the correct order in the sequence
        
        Args:
            event: The event to validate
            expected_previous_event_type: Optional expected previous event type
            
        Returns:
            Tuple of (is_valid, reason_or_none)
        """
        try:
            if not self._connected:
                return True, "Redis not connected, skipping order validation"
            
            if expected_previous_event_type is None:
                # For many events, we don't require specific ordering
                return True, None
            
            # Get the user's sequence for this correlation
            user_sequence_key = self._user_sequence_pattern.format(
                user_id=event.user_id or "system",
                correlation_id=event.correlation_id
            )
            
            # Get all event IDs in this user's correlation sequence
            event_ids = await self.redis_client.zrange(user_sequence_key, 0, -1)
            
            if not event_ids:
                # First event in sequence is always valid
                return True, None
            
            # Check if the expected previous event exists in the sequence
            if expected_previous_event_type:
                # Get all events in the sequence and check their types
                all_events = []
                
                for event_id_bytes in event_ids:
                    event_id = event_id_bytes.decode('utf-8')
                    
                    # Try to find this event in the correlation record
                    correlation_record = await self._get_correlation_record(event.correlation_id)
                    if correlation_record:
                        for event_data in correlation_record.events:
                            if event_data['event_id'] == event_id:
                                all_events.append(event_data)
                                break
                
                # Check if the expected previous event type exists in the sequence
                previous_event_exists = any(
                    event_data['event_type'] == expected_previous_event_type
                    for event_data in all_events
                )
                
                if not previous_event_exists:
                    reason = f"Expected previous event type '{expected_previous_event_type}' not found in sequence"
                    logger.warning("Event order validation failed", 
                                 event_id=event.event_id,
                                 expected_previous=expected_previous_event_type,
                                 reason=reason)
                    return False, reason
            
            logger.debug("Event order validation passed", event_id=event.event_id)
            return True, None
            
        except Exception as e:
            logger.error("Error validating event order", error=str(e), event_id=event.event_id)
            return True, f"Order validation error: {str(e)}"  # Fail open to avoid blocking events

    async def cleanup_expired_correlations(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired correlation records
        
        Args:
            max_age_seconds: Maximum age of correlations to keep (default: 1 hour)
            
        Returns:
            Number of expired correlations removed
        """
        # Note: In this Redis implementation, expiration is handled automatically by setting TTL
        # This method could be used for more complex cleanup, but for now it's mainly for stats
        logger.info("Expired correlation cleanup completed", processed_count=0)
        return 0

    async def get_correlation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about correlation tracking
        
        Returns:
            Dictionary with correlation statistics
        """
        return {
            **self.stats,
            'redis_connected': self._connected
        }
        
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the correlation service
        
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
            
            health_status = {
                'redis_connected': redis_connected,
                'connected': self._connected,
                'stats': await self.get_correlation_stats()
            }
            
            logger.debug("Event correlation service health check completed", 
                        health_status=health_status)
            return health_status
        except Exception as e:
            logger.error("Error during correlation service health check", error=str(e))
            return {
                'redis_connected': False,
                'connected': False,
                'stats': self.stats,
                'error': str(e)
            }


# Global instance for convenience (can be used if needed)
# _correlation_service = None

# async def get_correlation_service(redis_config: Optional[RedisConfig] = None) -> EventCorrelationService:
#     """
#     Get or create a global correlation service instance
#     """
#     global _correlation_service
#     if _correlation_service is None:
#         _correlation_service = EventCorrelationService(redis_config)
#         await _correlation_service.connect()
#     return _correlation_service
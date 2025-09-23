"""
Event correlation service for the YABOT system.

This module provides correlation ID tracking and event ordering as required by requirements 4.6, 4.8, 4.9.
It leverages existing Redis patterns for efficient correlation tracking and event sequence management.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

import redis.asyncio as redis
from src.core.models import BaseModel
from src.events.models import BaseEvent


class EventStatus(str, Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CorrelationSequence:
    """Represents a sequence of correlated events."""
    correlation_id: str
    user_id: Optional[str]
    sequence_number: int
    events: List[str] = field(default_factory=list)
    status: EventStatus = EventStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    timeout_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventCorrelationService:
    """
    Service for managing event correlation and ordering.

    This service ensures that cross-module events are processed in chronological order
    using correlation IDs and maintains event sequences per user as specified in
    requirements 4.6, 4.8, and 4.9.
    """

    def __init__(self, redis_client: redis.Redis, correlation_ttl: int = 3600):
        """
        Initialize the correlation service.

        Args:
            redis_client: Redis client for correlation storage
            correlation_ttl: TTL for correlation data in seconds (default 1 hour)
        """
        self.redis_client = redis_client
        self.correlation_ttl = correlation_ttl

        # Redis key patterns following existing conventions
        self.correlation_key = "correlation:{correlation_id}"
        self.user_sequence_key = "user_sequence:{user_id}"
        self.event_order_key = "event_order:{correlation_id}"
        self.pending_events_key = "pending_events:{module}"

    async def generate_correlation_id(self, user_id: Optional[str] = None) -> str:
        """
        Generate a new correlation ID with optional user context.

        Args:
            user_id: Optional user ID for user-specific correlations

        Returns:
            Generated correlation ID
        """
        base_id = str(uuid.uuid4())
        if user_id:
            # Include user context for better tracing
            sequence_num = await self._get_next_sequence_number(user_id)
            return f"{user_id}_{sequence_num}_{base_id[:8]}"
        return base_id

    async def _get_next_sequence_number(self, user_id: str) -> int:
        """Get the next sequence number for a user."""
        key = self.user_sequence_key.format(user_id=user_id)
        return await self.redis_client.incr(key)

    async def create_correlation_sequence(
        self,
        correlation_id: str,
        user_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> CorrelationSequence:
        """
        Create a new correlation sequence.

        Args:
            correlation_id: Unique correlation identifier
            user_id: Optional user ID for user-specific sequences
            timeout_seconds: Optional timeout for the sequence

        Returns:
            Created correlation sequence
        """
        sequence = CorrelationSequence(
            correlation_id=correlation_id,
            user_id=user_id,
            sequence_number=0
        )

        if timeout_seconds:
            sequence.timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        await self._store_correlation_sequence(sequence)
        return sequence

    async def _store_correlation_sequence(self, sequence: CorrelationSequence) -> None:
        """Store correlation sequence in Redis."""
        key = self.correlation_key.format(correlation_id=sequence.correlation_id)
        data = {
            "correlation_id": sequence.correlation_id,
            "user_id": sequence.user_id,
            "sequence_number": sequence.sequence_number,
            "events": sequence.events,
            "status": sequence.status.value,
            "created_at": sequence.created_at.isoformat(),
            "updated_at": sequence.updated_at.isoformat(),
            "timeout_at": sequence.timeout_at.isoformat() if sequence.timeout_at else None,
            "metadata": sequence.metadata
        }

        await self.redis_client.setex(
            key,
            self.correlation_ttl,
            json.dumps(data, default=str)
        )

    async def get_correlation_sequence(self, correlation_id: str) -> Optional[CorrelationSequence]:
        """
        Retrieve a correlation sequence by ID.

        Args:
            correlation_id: Correlation identifier

        Returns:
            Correlation sequence if found, None otherwise
        """
        key = self.correlation_key.format(correlation_id=correlation_id)
        data = await self.redis_client.get(key)

        if not data:
            return None

        sequence_data = json.loads(data)
        return CorrelationSequence(
            correlation_id=sequence_data["correlation_id"],
            user_id=sequence_data["user_id"],
            sequence_number=sequence_data["sequence_number"],
            events=sequence_data["events"],
            status=EventStatus(sequence_data["status"]),
            created_at=datetime.fromisoformat(sequence_data["created_at"]),
            updated_at=datetime.fromisoformat(sequence_data["updated_at"]),
            timeout_at=datetime.fromisoformat(sequence_data["timeout_at"]) if sequence_data["timeout_at"] else None,
            metadata=sequence_data["metadata"]
        )

    async def add_event_to_sequence(
        self,
        correlation_id: str,
        event: BaseEvent,
        expected_sequence: Optional[int] = None
    ) -> bool:
        """
        Add an event to a correlation sequence with ordering validation.

        Args:
            correlation_id: Correlation identifier
            event: Event to add to the sequence
            expected_sequence: Expected sequence number for ordering validation

        Returns:
            True if event was added successfully, False otherwise
        """
        sequence = await self.get_correlation_sequence(correlation_id)
        if not sequence:
            # Create new sequence if it doesn't exist
            sequence = await self.create_correlation_sequence(correlation_id, event.user_id)

        # Check if sequence is expired or in failed state
        if sequence.timeout_at and datetime.utcnow() > sequence.timeout_at:
            sequence.status = EventStatus.TIMEOUT
            await self._store_correlation_sequence(sequence)
            return False

        if sequence.status in [EventStatus.FAILED, EventStatus.TIMEOUT]:
            return False

        # Validate sequence order if expected_sequence is provided
        if expected_sequence is not None and expected_sequence != sequence.sequence_number + 1:
            # Event out of order - queue for later processing
            await self._queue_out_of_order_event(correlation_id, event, expected_sequence)
            return False

        # Add event to sequence
        sequence.events.append(event.event_id)
        sequence.sequence_number += 1
        sequence.updated_at = datetime.utcnow()

        await self._store_correlation_sequence(sequence)

        # Process any queued events that are now in order
        await self._process_queued_events(correlation_id)

        return True

    async def _queue_out_of_order_event(
        self,
        correlation_id: str,
        event: BaseEvent,
        expected_sequence: int
    ) -> None:
        """Queue an out-of-order event for later processing."""
        queue_key = f"out_of_order:{correlation_id}"
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "expected_sequence": expected_sequence,
            "timestamp": event.timestamp.isoformat(),
            "data": event.dict()
        }

        await self.redis_client.zadd(
            queue_key,
            {json.dumps(event_data): expected_sequence}
        )

        # Set TTL for the queue
        await self.redis_client.expire(queue_key, self.correlation_ttl)

    async def _process_queued_events(self, correlation_id: str) -> None:
        """Process queued out-of-order events that are now in sequence."""
        sequence = await self.get_correlation_sequence(correlation_id)
        if not sequence:
            return

        queue_key = f"out_of_order:{correlation_id}"
        next_expected = sequence.sequence_number + 1

        # Get events with the next expected sequence number
        events = await self.redis_client.zrangebyscore(
            queue_key,
            next_expected,
            next_expected,
            start=0,
            num=1,
            withscores=True
        )

        for event_data, score in events:
            event_info = json.loads(event_data)

            # Add to sequence
            sequence.events.append(event_info["event_id"])
            sequence.sequence_number += 1
            sequence.updated_at = datetime.utcnow()

            await self._store_correlation_sequence(sequence)

            # Remove from queue
            await self.redis_client.zrem(queue_key, event_data)

            # Recursively process more events
            await self._process_queued_events(correlation_id)
            break

    async def complete_correlation_sequence(self, correlation_id: str) -> bool:
        """
        Mark a correlation sequence as completed.

        Args:
            correlation_id: Correlation identifier

        Returns:
            True if sequence was completed successfully, False otherwise
        """
        sequence = await self.get_correlation_sequence(correlation_id)
        if not sequence:
            return False

        sequence.status = EventStatus.COMPLETED
        sequence.updated_at = datetime.utcnow()

        await self._store_correlation_sequence(sequence)

        # Clean up out-of-order queue
        queue_key = f"out_of_order:{correlation_id}"
        await self.redis_client.delete(queue_key)

        return True

    async def fail_correlation_sequence(
        self,
        correlation_id: str,
        error_message: str
    ) -> bool:
        """
        Mark a correlation sequence as failed.

        Args:
            correlation_id: Correlation identifier
            error_message: Error message describing the failure

        Returns:
            True if sequence was marked as failed, False otherwise
        """
        sequence = await self.get_correlation_sequence(correlation_id)
        if not sequence:
            return False

        sequence.status = EventStatus.FAILED
        sequence.updated_at = datetime.utcnow()
        sequence.metadata["error_message"] = error_message

        await self._store_correlation_sequence(sequence)
        return True

    async def get_user_active_correlations(self, user_id: str) -> List[CorrelationSequence]:
        """
        Get all active correlation sequences for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active correlation sequences
        """
        # This would require a secondary index in a production system
        # For now, we'll use a simple pattern search
        pattern = self.correlation_key.format(correlation_id=f"{user_id}_*")
        keys = await self.redis_client.keys(pattern)

        sequences = []
        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                sequence_data = json.loads(data)
                if sequence_data["status"] in ["pending", "processing"]:
                    sequences.append(CorrelationSequence(
                        correlation_id=sequence_data["correlation_id"],
                        user_id=sequence_data["user_id"],
                        sequence_number=sequence_data["sequence_number"],
                        events=sequence_data["events"],
                        status=EventStatus(sequence_data["status"]),
                        created_at=datetime.fromisoformat(sequence_data["created_at"]),
                        updated_at=datetime.fromisoformat(sequence_data["updated_at"]),
                        timeout_at=datetime.fromisoformat(sequence_data["timeout_at"]) if sequence_data["timeout_at"] else None,
                        metadata=sequence_data["metadata"]
                    ))

        return sequences

    async def cleanup_expired_sequences(self) -> int:
        """
        Clean up expired correlation sequences.

        Returns:
            Number of sequences cleaned up
        """
        # In production, this would be handled by Redis TTL
        # This method provides additional cleanup for complex scenarios

        pattern = self.correlation_key.format(correlation_id="*")
        keys = await self.redis_client.keys(pattern)
        cleaned_count = 0

        current_time = datetime.utcnow()

        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                sequence_data = json.loads(data)
                timeout_at = sequence_data.get("timeout_at")

                if timeout_at and datetime.fromisoformat(timeout_at) < current_time:
                    await self.redis_client.delete(key)
                    # Also clean up related out-of-order queue
                    correlation_id = sequence_data["correlation_id"]
                    queue_key = f"out_of_order:{correlation_id}"
                    await self.redis_client.delete(queue_key)
                    cleaned_count += 1

        return cleaned_count

    async def get_correlation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about correlation sequences.

        Returns:
            Dictionary with correlation statistics
        """
        pattern = self.correlation_key.format(correlation_id="*")
        keys = await self.redis_client.keys(pattern)

        stats = {
            "total_sequences": len(keys),
            "status_counts": {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "timeout": 0
            },
            "average_events_per_sequence": 0,
            "oldest_sequence": None,
            "newest_sequence": None
        }

        if not keys:
            return stats

        total_events = 0
        oldest_time = None
        newest_time = None

        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                sequence_data = json.loads(data)
                status = sequence_data["status"]
                stats["status_counts"][status] += 1

                total_events += len(sequence_data["events"])

                created_at = datetime.fromisoformat(sequence_data["created_at"])
                if oldest_time is None or created_at < oldest_time:
                    oldest_time = created_at
                    stats["oldest_sequence"] = sequence_data["correlation_id"]

                if newest_time is None or created_at > newest_time:
                    newest_time = created_at
                    stats["newest_sequence"] = sequence_data["correlation_id"]

        if len(keys) > 0:
            stats["average_events_per_sequence"] = total_events / len(keys)

        return stats


# Factory function for easier initialization
async def create_correlation_service(
    redis_url: str = "redis://localhost:6379",
    correlation_ttl: int = 3600
) -> EventCorrelationService:
    """
    Create and initialize an EventCorrelationService.

    Args:
        redis_url: Redis connection URL
        correlation_ttl: TTL for correlation data in seconds

    Returns:
        Initialized EventCorrelationService instance
    """
    redis_client = redis.from_url(redis_url, decode_responses=True)
    return EventCorrelationService(redis_client, correlation_ttl)
"""
Event ordering buffer for the YABOT system.

This module provides an event ordering buffer that ensures events are processed
in the correct chronological order, especially for events affecting the same user.
It implements the requirements from requirement 3.2 of the fase1 specification.
"""

import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.events.models import BaseEvent
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EventOrderingError(Exception):
    """Base exception for event ordering operations."""
    pass


class EventOrderingBuffer:
    """Event ordering buffer that ensures events are processed in the correct order."""
    
    def __init__(self, max_buffer_size: int = 1000, max_buffer_time: float = 300.0):
        """Initialize the event ordering buffer.
        
        Args:
            max_buffer_size (int): Maximum number of events to buffer per user
            max_buffer_time (float): Maximum time in seconds to buffer events
        """
        self.max_buffer_size = max_buffer_size
        self.max_buffer_time = max_buffer_time
        self._buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._processing_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._metrics = {
            "events_buffered": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "buffer_flushes": 0
        }
        
        logger.info(
            "EventOrderingBuffer initialized with max_buffer_size=%d, max_buffer_time=%.2fs",
            max_buffer_size,
            max_buffer_time
        )
    
    async def add_event(self, event: BaseEvent, processor_func) -> bool:
        """Add an event to the ordering buffer.
        
        Args:
            event (BaseEvent): Event to add to the buffer
            processor_func (Callable): Function to process the event when ready
            
        Returns:
            bool: True if event was added successfully, False otherwise
        """
        try:
            user_id = event.user_id or "no_user"
            logger.debug("Adding event to buffer for user %s: %s", user_id, event.event_id)
            
            # Add event to buffer
            event_entry = {
                "event": event,
                "processor_func": processor_func,
                "timestamp": event.timestamp.timestamp(),
                "added_time": time.time()
            }
            
            # Check buffer size for this user
            if len(self._buffer[user_id]) >= self.max_buffer_size:
                logger.warning(
                    "Buffer for user %s is full, dropping oldest event", 
                    user_id
                )
                self._buffer[user_id].pop(0)
                self._metrics["events_dropped"] += 1
            
            self._buffer[user_id].append(event_entry)
            self._metrics["events_buffered"] += 1
            
            # Sort events by timestamp
            self._buffer[user_id].sort(key=lambda x: x["timestamp"])
            
            logger.debug(
                "Event added to buffer for user %s. Buffer size: %d", 
                user_id, 
                len(self._buffer[user_id])
            )
            
            # Process events for this user
            await self._process_user_events(user_id)
            
            return True
            
        except Exception as e:
            logger.error("Error adding event to buffer: %s", str(e))
            return False
    
    async def _process_user_events(self, user_id: str) -> None:
        """Process buffered events for a specific user in chronological order.
        
        Args:
            user_id (str): User ID to process events for
        """
        # Use a lock to prevent concurrent processing for the same user
        async with self._processing_locks[user_id]:
            try:
                if not self._buffer[user_id]:
                    return
                
                current_time = time.time()
                events_to_process = []
                remaining_events = []
                
                # Separate events that should be processed now from those that should remain buffered
                for event_entry in self._buffer[user_id]:
                    # Process events that are either:
                    # 1. Older than max_buffer_time
                    # 2. The oldest event and we need to make progress
                    if (current_time - event_entry["added_time"] > self.max_buffer_time or 
                        len(events_to_process) == 0):
                        events_to_process.append(event_entry)
                    else:
                        remaining_events.append(event_entry)
                
                if not events_to_process:
                    return
                
                logger.debug(
                    "Processing %d events for user %s", 
                    len(events_to_process), 
                    user_id
                )
                
                # Process events in chronological order
                for event_entry in events_to_process:
                    try:
                        event = event_entry["event"]
                        processor_func = event_entry["processor_func"]
                        
                        logger.debug(
                            "Processing event for user %s: %s (type: %s)", 
                            user_id, 
                            event.event_id, 
                            event.event_type
                        )
                        
                        # Process the event
                        await processor_func(event)
                        self._metrics["events_processed"] += 1
                        
                    except Exception as e:
                        logger.error(
                            "Error processing event %s for user %s: %s", 
                            event_entry["event"].event_id, 
                            user_id, 
                            str(e)
                        )
                        # Keep the event in the buffer for retry
                        remaining_events.append(event_entry)
                
                # Update buffer with remaining events
                self._buffer[user_id] = remaining_events
                self._metrics["buffer_flushes"] += 1
                
                logger.debug(
                    "Finished processing events for user %s. Remaining in buffer: %d", 
                    user_id, 
                    len(self._buffer[user_id])
                )
                
            except Exception as e:
                logger.error("Error processing user events for user %s: %s", user_id, str(e))
    
    def _should_process_before(self, event_type_a: str, event_type_b: str) -> bool:
        """Determine if event_type_a should be processed before event_type_b.
        
        Based on requirement 3.2:
        - reaction_detected before besitos_awarded
        - besitos_awarded before narrative_hint_unlocked
        
        Args:
            event_type_a (str): First event type
            event_type_b (str): Second event type
            
        Returns:
            bool: True if event_type_a should be processed before event_type_b
        """
        # Define processing order priorities
        processing_order = {
            "reaction_detected": 1,
            "besitos_awarded": 2,
            "narrative_hint_unlocked": 3
        }
        
        priority_a = processing_order.get(event_type_a, 100)  # Default high priority
        priority_b = processing_order.get(event_type_b, 100)  # Default high priority
        
        return priority_a < priority_b
    
    async def flush_user_buffer(self, user_id: str) -> None:
        """Force flush all buffered events for a specific user.
        
        Args:
            user_id (str): User ID to flush events for
        """
        logger.debug("Force flushing buffer for user %s", user_id)
        
        if user_id in self._buffer:
            # Process all remaining events without time constraints
            events_to_process = self._buffer[user_id]
            self._buffer[user_id] = []
            
            async with self._processing_locks[user_id]:
                for event_entry in events_to_process:
                    try:
                        event = event_entry["event"]
                        processor_func = event_entry["processor_func"]
                        
                        logger.debug(
                            "Force processing event for user %s: %s", 
                            user_id, 
                            event.event_id
                        )
                        
                        await processor_func(event)
                        self._metrics["events_processed"] += 1
                        
                    except Exception as e:
                        logger.error(
                            "Error force processing event %s for user %s: %s", 
                            event_entry["event"].event_id, 
                            user_id, 
                            str(e)
                        )
            
            self._metrics["buffer_flushes"] += 1
            logger.debug("Force flushed buffer for user %s", user_id)
    
    async def flush_all_buffers(self) -> None:
        """Force flush all buffered events for all users."""
        logger.info("Force flushing all buffers")
        
        user_ids = list(self._buffer.keys())
        for user_id in user_ids:
            await self.flush_user_buffer(user_id)
        
        logger.info("Force flushed all buffers")
    
    def get_buffer_size(self, user_id: str) -> int:
        """Get the current buffer size for a specific user.
        
        Args:
            user_id (str): User ID to get buffer size for
            
        Returns:
            int: Number of events in the buffer for this user
        """
        return len(self._buffer.get(user_id, []))
    
    def get_metrics(self) -> Dict[str, int]:
        """Get buffer metrics.
        
        Returns:
            Dict[str, int]: Buffer metrics
        """
        return self._metrics.copy()
    
    async def close(self) -> None:
        """Close the event ordering buffer and flush all events."""
        logger.info("Closing event ordering buffer")
        
        # Force flush all buffers
        await self.flush_all_buffers()
        
        # Clear buffers
        self._buffer.clear()
        self._processing_locks.clear()
        
        logger.info("Event ordering buffer closed")


# Convenience function for easy usage
async def create_event_ordering_buffer(
    max_buffer_size: int = 1000, 
    max_buffer_time: float = 300.0
) -> EventOrderingBuffer:
    """Create an event ordering buffer instance.
    
    Args:
        max_buffer_size (int): Maximum number of events to buffer per user
        max_buffer_time (float): Maximum time in seconds to buffer events
        
    Returns:
        EventOrderingBuffer: Event ordering buffer instance
    """
    return EventOrderingBuffer(max_buffer_size, max_buffer_time)
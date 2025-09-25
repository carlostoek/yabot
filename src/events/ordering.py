"""
Fase1 - Task 20
Event Ordering Buffer

Implements event ordering and sequencing as specified in Requirement 3.2:
Event Ordering and Sequencing, ensuring events are processed in the correct order.
"""
import asyncio
import heapq
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import threading

from src.events.models import BaseEvent
from src.utils.logger import LoggerMixin, get_logger


@dataclass
class OrderableEvent:
    """Wrapper for events that can be ordered by timestamp"""
    event: BaseEvent
    user_id: str
    timestamp: datetime
    inserted_at: datetime = field(default_factory=datetime.utcnow)
    
    def __lt__(self, other):
        """For heap ordering - earlier events come first"""
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        # If timestamps are the same, use insertion order as tiebreaker
        return self.inserted_at < other.inserted_at


class EventOrderingBuffer(LoggerMixin):
    """
    Buffers and orders events to ensure they are processed in chronological order
    """
    
    def __init__(self, max_buffer_size: int = 100, processing_delay: float = 0.1):
        self.max_buffer_size = max_buffer_size
        self.processing_delay = processing_delay  # seconds
        self.buffers: Dict[str, List[OrderableEvent]] = {}  # Buffer per user
        self._lock = threading.Lock()
        self.logger = get_logger(self.__class__.__name__)
        self._stop_processing = False
        self._processor_task = None
        
    def add_event(self, user_id: str, event: BaseEvent) -> bool:
        """
        Add an event to the ordering buffer for the specified user
        
        Args:
            user_id: ID of the user associated with the event
            event: Event to buffer
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            with self._lock:
                if user_id not in self.buffers:
                    self.buffers[user_id] = []
                
                # Create orderable event
                orderable_event = OrderableEvent(
                    event=event,
                    user_id=user_id,
                    timestamp=event.timestamp
                )
                
                # Add to user's buffer and maintain heap order
                heapq.heappush(self.buffers[user_id], orderable_event)
                
                # Limit buffer size to prevent excessive memory usage
                if len(self.buffers[user_id]) > self.max_buffer_size:
                    # Remove oldest events to maintain size limit
                    self.buffers[user_id] = heapq.nsmallest(
                        self.max_buffer_size,
                        self.buffers[user_id]
                    )
                
                self.logger.debug("Event added to ordering buffer", 
                                user_id=user_id, 
                                event_type=event.event_type,
                                buffer_size=len(self.buffers[user_id]))
                
                return True
        except Exception as e:
            self.logger.error(f"Error adding event to buffer: {str(e)}", 
                            user_id=user_id, 
                            event_type=event.event_type)
            return False
    
    def get_ordered_events(self, user_id: str, max_events: int = 10) -> List[OrderableEvent]:
        """
        Get ordered events for a user and remove them from the buffer
        
        Args:
            user_id: ID of the user whose events to retrieve
            max_events: Maximum number of events to retrieve
            
        Returns:
            List of ordered events
        """
        try:
            with self._lock:
                if user_id not in self.buffers or not self.buffers[user_id]:
                    return []
                
                # Get up to max_events in chronological order
                ordered_events = []
                for _ in range(min(max_events, len(self.buffers[user_id]))):
                    if self.buffers[user_id]:
                        ordered_events.append(heapq.heappop(self.buffers[user_id]))
                
                # Clean up empty user buffer
                if not self.buffers[user_id]:
                    del self.buffers[user_id]
                
                self.logger.debug("Retrieved ordered events", 
                                user_id=user_id, 
                                count=len(ordered_events))
                
                return ordered_events
        except Exception as e:
            self.logger.error(f"Error getting ordered events: {str(e)}", user_id=user_id)
            return []
    
    def get_buffer_status(self) -> Dict[str, int]:
        """
        Get current buffer status showing number of events per user
        
        Returns:
            Dictionary mapping user IDs to number of events in buffer
        """
        with self._lock:
            return {user_id: len(buffer) for user_id, buffer in self.buffers.items()}
    
    def reorder_events_for_user(self, user_id: str) -> bool:
        """
        Reorder events for a specific user based on timestamps
        
        Args:
            user_id: ID of the user whose events to reorder
            
        Returns:
            True if reorder was successful, False otherwise
        """
        try:
            with self._lock:
                if user_id not in self.buffers:
                    self.logger.debug("No events to reorder for user", user_id=user_id)
                    return True
                
                # Rebuild heap to ensure correct ordering
                self.buffers[user_id] = heapq.nsmallest(
                    len(self.buffers[user_id]),
                    self.buffers[user_id]
                )
                
                self.logger.info("Events reordered for user", user_id=user_id, 
                               buffer_size=len(self.buffers[user_id]))
                return True
        except Exception as e:
            self.logger.error(f"Error reordering events: {str(e)}", user_id=user_id)
            return False
    
    async def process_buffer_with_handler(self, user_id: str, 
                                        event_handler: Callable[[BaseEvent], None],
                                        max_events: int = 10) -> int:
        """
        Process ordered events using a provided handler
        
        Args:
            user_id: ID of the user whose events to process
            event_handler: Function to handle the events
            max_events: Maximum number of events to process
            
        Returns:
            Number of events processed
        """
        try:
            ordered_events = self.get_ordered_events(user_id, max_events)
            processed_count = 0
            
            for orderable_event in ordered_events:
                try:
                    # Call the event handler
                    await event_handler(orderable_event.event)
                    processed_count += 1
                    self.logger.debug("Event processed", 
                                    user_id=orderable_event.user_id,
                                    event_type=orderable_event.event.event_type)
                except Exception as handler_error:
                    self.logger.error(f"Error in event handler: {str(handler_error)}",
                                    user_id=orderable_event.user_id,
                                    event_type=orderable_event.event.event_type)
                    # Put the event back in the buffer for later processing?
                    # This is a simplified implementation
                    continue
            
            self.logger.info("Events processed for user", user_id=user_id, 
                           processed_count=processed_count)
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing buffer: {str(e)}", user_id=user_id)
            return 0
    
    def buffer_has_events(self, user_id: str) -> bool:
        """
        Check if a user has events in the buffer
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            True if user has events in buffer, False otherwise
        """
        with self._lock:
            return user_id in self.buffers and len(self.buffers[user_id]) > 0
    
    def get_next_event_timestamp(self, user_id: str) -> Optional[datetime]:
        """
        Get the timestamp of the next event for a user (earliest timestamp)
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            Timestamp of next event or None if no events
        """
        with self._lock:
            if user_id in self.buffers and self.buffers[user_id]:
                # The smallest item according to heap property (earliest timestamp)
                return self.buffers[user_id][0].timestamp
            return None


class EventSequencer(LoggerMixin):
    """
    Higher-level orchestrator that ensures events are processed in the correct sequence
    """
    
    def __init__(self, event_buffer: EventOrderingBuffer):
        self.event_buffer = event_buffer
        self.logger = get_logger(self.__class__.__name__)
        self._sequence_trackers: Dict[str, Dict[str, datetime]] = {}  # Track last processed event per user
    
    async def process_ordered_event_sequence(self, user_id: str, 
                                           event_handler: Callable[[BaseEvent], None],
                                           max_events: int = 10) -> Dict[str, Any]:
        """
        Process events in correct chronological order for a user
        
        Args:
            user_id: ID of the user whose events to process
            event_handler: Function to handle the events
            max_events: Maximum number of events to process
            
        Returns:
            Dictionary with processing results
        """
        try:
            self.logger.info("Processing ordered event sequence", user_id=user_id)
            
            processed_count = await self.event_buffer.process_buffer_with_handler(
                user_id, event_handler, max_events
            )
            
            result = {
                "user_id": user_id,
                "processed_count": processed_count,
                "buffer_empty": not self.event_buffer.buffer_has_events(user_id),
                "timestamp": datetime.utcnow()
            }
            
            self.logger.info("Ordered event sequence processed", 
                           user_id=user_id, 
                           processed_count=processed_count)
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing ordered event sequence: {str(e)}", user_id=user_id)
            return {
                "user_id": user_id,
                "processed_count": 0,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def add_and_process_event(self, user_id: str, event: BaseEvent,
                                  event_handler: Callable[[BaseEvent], None]) -> bool:
        """
        Add an event to the ordering buffer and attempt to process it immediately
        
        Args:
            user_id: ID of the user associated with the event
            event: Event to add and process
            event_handler: Function to handle the event
            
        Returns:
            True if successfully handled, False otherwise
        """
        try:
            # Add event to buffer
            added = self.event_buffer.add_event(user_id, event)
            if not added:
                return False
            
            # Process all available events for this user in order
            await self.process_ordered_event_sequence(user_id, event_handler)
            
            return True
        except Exception as e:
            self.logger.error(f"Error adding and processing event: {str(e)}", 
                            user_id=user_id, 
                            event_type=event.event_type)
            return False
    
    def get_sequencing_status(self) -> Dict[str, Any]:
        """
        Get status of the event sequencer
        
        Returns:
            Dictionary with sequencer status information
        """
        buffer_status = self.event_buffer.get_buffer_status()
        
        status = {
            "timestamp": datetime.utcnow(),
            "buffer_status": buffer_status,
            "total_users_with_events": len(buffer_status),
            "total_events_buffered": sum(buffer_status.values())
        }
        
        self.logger.debug("Sequencer status retrieved", status=status)
        return status


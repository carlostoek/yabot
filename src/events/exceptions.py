"""
Event Bus Exceptions

This module defines custom exceptions for the event bus system.
"""


class EventBusException(Exception):
    """
    Base exception for event bus related errors
    """
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error
        self.message = message

    def __str__(self):
        if self.original_error:
            return f"{self.message}: {str(self.original_error)}"
        return self.message


class EventProcessingError(EventBusException):
    """
    Exception for errors that occur during event processing
    """
    def __init__(self, message: str, event_data: dict = None, original_error: Exception = None):
        super().__init__(message, original_error)
        self.event_data = event_data

    def __str__(self):
        base_msg = super().__str__()
        if self.event_data:
            return f"{base_msg} (Event ID: {self.event_data.get('event_id', 'unknown')})"
        return base_msg


class RedisConnectionError(EventBusException):
    """
    Exception for Redis connection related errors
    """
    pass


class EventSerializationError(EventBusException):
    """
    Exception for event serialization/deserialization errors
    """
    pass


class InvalidEventError(EventBusException):
    """
    Exception for invalid event structure
    """
    pass


class EventHandlerError(EventBusException):
    """
    Exception for errors in event handlers
    """
    pass
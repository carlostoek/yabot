"""
Fase1 - Task 15
Services module structure

This module provides the base structure for services in the YABOT system.
Following the design document requirements for unified user operations.
"""
from .user import UserService
from .subscription import SubscriptionService
from .narrative import NarrativeService
from .coordinator import CoordinatorService

__all__ = [
    "UserService",
    "SubscriptionService", 
    "NarrativeService",
    "CoordinatorService"
]

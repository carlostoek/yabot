"""
Services Module for YABOT - Fase1

This module provides the business logic services for the YABOT system,
including user management, narrative handling, subscription services,
and coordination services as specified in the Fase1 requirements.

Services:
- UserService: Unified user data operations across MongoDB and SQLite
- NarrativeService: Handles narrative fragments and story content
- SubscriptionService: Manages user subscriptions and premium features
- CoordinatorService: Orchestrates complex business workflows
"""

# Import core service classes
# These will be implemented in their respective files
from .user import UserService
from .narrative import NarrativeService
from .subscription import SubscriptionService
from .coordinator import CoordinatorService

# Module initialization
__version__ = "1.0.0"
__author__ = "YABOT Development Team"

# Define what should be imported with "from services import *"
__all__ = [
    "UserService",
    "NarrativeService",
    "SubscriptionService",
    "CoordinatorService"
]
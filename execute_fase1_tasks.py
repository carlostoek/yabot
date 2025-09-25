#!/usr/bin/env python3
"""
Sequential Execution of Fase1 Tasks 15-20

This script executes tasks 15-20 of the Fase1 specification in sequential order,
validating their existence before execution and maintaining detailed logs of the process.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Callable, Any
from datetime import datetime
import json

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_basic_logging, get_logger

# Initialize logging
setup_basic_logging()
logger = get_logger(__name__)

class TaskExecutor:
    """Manages the execution of Fase1 tasks 15-20 in sequential order."""
    
    def __init__(self):
        self.task_directory = project_root / ".claude/commands/fase1"
        self.src_directory = project_root / "src"
        self.executed_tasks = []
        self.failed_tasks = []
        self.start_time = None
        
    def validate_task_files(self, task_range: range) -> List[int]:
        """Validate that all required task files exist."""
        missing_tasks = []
        for task_id in task_range:
            task_file = self.task_directory / f"task-{task_id}.md"
            if not task_file.exists():
                missing_tasks.append(task_id)
        
        if missing_tasks:
            logger.error(f"Missing task files: {missing_tasks}")
            return missing_tasks
        
        logger.info(f"All task files exist for range {task_range.start} to {task_range.stop-1}")
        return []
    
    def validate_source_structure(self) -> bool:
        """Validate that necessary source directories exist."""
        required_dirs = [
            self.src_directory / "services",
            self.src_directory / "events",
            self.src_directory / "database"
        ]
        
        for directory in required_dirs:
            if not directory.exists():
                logger.error(f"Required directory does not exist: {directory}")
                return False
        
        logger.info("All required source directories exist")
        return True
        
    def create_services_init_file(self):
        """Task 15: Create services module structure in src/services/__init__.py"""
        logger.info("Executing Task 15: Creating services module structure")
        
        services_dir = self.src_directory / "services"
        init_file = services_dir / "__init__.py"
        
        # Content based on the task requirements
        content = '''"""
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
'''
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Task 15 completed: Services module structure created")
    
    def create_user_service(self):
        """Task 16: Create UserService for unified user operations in src/services/user.py"""
        logger.info("Executing Task 16: Creating UserService")
        
        user_service_file = self.src_directory / "services" / "user.py"
        
        content = '''"""
Fase1 - Task 16
UserService for unified user operations

Implements unified user data operations across MongoDB and SQLite
as specified in Requirement 1.3: User CRUD Operations.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.events.models import UserRegistrationEvent, UserInteractionEvent
from src.utils.logger import LoggerMixin, get_logger


class UserStatus(str, Enum):
    """Enumeration for user status values"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class UserService(LoggerMixin):
    """
    Unified user data operations across MongoDB and SQLite
    """
    
    def __init__(self, db_manager: DatabaseManager, event_bus: EventBus):
        self.db_manager = db_manager
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)
        
    async def create_user(self, telegram_user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create user in both databases atomically
        
        Args:
            telegram_user: Telegram user data from update
            
        Returns:
            Created user data or None if creation failed
        """
        try:
            self.logger.info("Creating new user", user_id=telegram_user.get("id"))
            
            # Prepare user data for both databases
            user_id = str(telegram_user["id"])
            
            # MongoDB user document (dynamic state)
            mongo_user_doc = {
                "user_id": user_id,
                "current_state": {
                    "menu_context": "main_menu",
                    "narrative_progress": {
                        "current_fragment": None,
                        "completed_fragments": [],
                        "choices_made": []
                    },
                    "session_data": {"last_activity": datetime.utcnow().isoformat()}
                },
                "preferences": {
                    "language": telegram_user.get("language_code", "es"),
                    "notifications_enabled": True,
                    "theme": "default"
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # SQLite user profile (for ACID compliance)
            sqlite_user_profile = {
                "user_id": user_id,
                "telegram_user_id": telegram_user["id"],
                "username": telegram_user.get("username"),
                "first_name": telegram_user.get("first_name"),
                "last_name": telegram_user.get("last_name"),
                "language_code": telegram_user.get("language_code"),
                "registration_date": datetime.utcnow(),
                "last_login": datetime.utcnow(),
                "is_active": True
            }
            
            # Create user in both databases (atomic operation)
            result = await self.db_manager.create_user_atomic(
                user_id, 
                mongo_user_doc, 
                sqlite_user_profile
            )
            
            if result:
                # Publish user registration event
                event = UserRegistrationEvent(
                    user_id=user_id,
                    telegram_data=telegram_user
                )
                await self.event_bus.publish("user_registered", event.dict())
                
                self.logger.info("User created successfully", user_id=user_id)
                return {
                    "user_id": user_id,
                    "mongo_created": True,
                    "sqlite_created": True,
                    "profile": sqlite_user_profile
                }
            else:
                self.logger.error("Failed to create user atomically", user_id=user_id)
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}", user_id=telegram_user.get("id"))
            raise
    
    async def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete user context combining data from both databases
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Complete user context or None if user not found
        """
        try:
            self.logger.debug("Retrieving user context", user_id=user_id)
            
            # Get user data from MongoDB (dynamic state)
            mongo_user = await self.db_manager.get_user_from_mongo(user_id)
            if not mongo_user:
                self.logger.warning("User not found in MongoDB", user_id=user_id)
                return None
            
            # Get user profile from SQLite
            sqlite_profile = await self.db_manager.get_user_profile_from_sqlite(user_id)
            if not sqlite_profile:
                self.logger.warning("User profile not found in SQLite", user_id=user_id)
                return None
            
            # Combine user context
            user_context = {
                "user_id": user_id,
                "mongo_data": mongo_user,
                "profile_data": sqlite_profile,
                "combined_context": {
                    **mongo_user,
                    "profile": sqlite_profile
                }
            }
            
            self.logger.info("User context retrieved successfully", user_id=user_id)
            return user_context
            
        except Exception as e:
            self.logger.error(f"Error retrieving user context: {str(e)}", user_id=user_id)
            raise
    
    async def update_user_state(self, user_id: str, new_state: Dict[str, Any]) -> bool:
        """
        Update MongoDB dynamic state
        
        Args:
            user_id: Telegram user ID
            new_state: Updated user state
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            self.logger.info("Updating user state", user_id=user_id)
            
            update_data = {
                "$set": {
                    "current_state": new_state,
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await self.db_manager.update_user_in_mongo(user_id, update_data)
            
            if result:
                # Publish user state update event
                event = UserInteractionEvent(
                    user_id=user_id,
                    action="update_state",
                    context=new_state
                )
                await self.event_bus.publish("user_state_updated", event.dict())
                
                self.logger.info("User state updated successfully", user_id=user_id)
                return True
            else:
                self.logger.warning("Failed to update user state", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating user state: {str(e)}", user_id=user_id)
            raise
    
    async def update_user_profile(self, user_id: str, profile_updates: Dict[str, Any]) -> bool:
        """
        Update SQLite profile data
        
        Args:
            user_id: Telegram user ID
            profile_updates: Updated profile data
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            self.logger.info("Updating user profile", user_id=user_id)
            
            # Update profile in SQLite
            result = await self.db_manager.update_user_profile_in_sqlite(user_id, profile_updates)
            
            if result:
                self.logger.info("User profile updated successfully", user_id=user_id)
                return True
            else:
                self.logger.warning("Failed to update user profile", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating user profile: {str(e)}", user_id=user_id)
            raise
    
    async def get_user_subscription_status(self, user_id: str) -> Optional[str]:
        """
        Get user subscription status from SQLite
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Subscription status string or None
        """
        try:
            self.logger.debug("Retrieving user subscription status", user_id=user_id)
            
            subscription = await self.db_manager.get_subscription_from_sqlite(user_id)
            if subscription:
                status = subscription.get("status", "inactive")
                self.logger.info("Subscription status retrieved", user_id=user_id, status=status)
                return status
            else:
                self.logger.info("No subscription found", user_id=user_id)
                return "inactive"
                
        except Exception as e:
            self.logger.error(f"Error retrieving subscription status: {str(e)}", user_id=user_id)
            raise
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Remove user from both databases and publish user_deleted event
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            self.logger.info("Deleting user", user_id=user_id)
            
            # Delete from both databases
            mongo_deleted = await self.db_manager.delete_user_from_mongo(user_id)
            sqlite_deleted = await self.db_manager.delete_user_profile_from_sqlite(user_id)
            
            if mongo_deleted and sqlite_deleted:
                # Publish user deletion event
                event_data = {
                    "event_type": "user_deleted",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow(),
                }
                await self.event_bus.publish("user_deleted", event_data)
                
                self.logger.info("User deleted successfully", user_id=user_id)
                return True
            else:
                self.logger.warning(
                    "Partial user deletion", 
                    user_id=user_id, 
                    mongo_deleted=mongo_deleted, 
                    sqlite_deleted=sqlite_deleted
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting user: {str(e)}", user_id=user_id)
            raise

'''
        
        with open(user_service_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Task 16 completed: UserService created")
    
    def create_subscription_service(self):
        """Task 17: Create SubscriptionService in src/services/subscription.py"""
        logger.info("Executing Task 17: Creating SubscriptionService")
        
        subscription_service_file = self.src_directory / "services" / "subscription.py"
        
        content = '''"""
Fase1 - Task 17
SubscriptionService

Implements subscription management functionality as specified
in Requirement 3.1: Coordinator Service Architecture.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.events.models import SubscriptionUpdatedEvent
from src.utils.logger import LoggerMixin, get_logger


class SubscriptionPlan(str, Enum):
    """Enumeration for subscription plan types"""
    FREE = "free"
    PREMIUM = "premium"
    VIP = "vip"


class SubscriptionStatus(str, Enum):
    """Enumeration for subscription statuses"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SubscriptionService(LoggerMixin):
    """
    Manages user subscription operations
    """
    
    def __init__(self, db_manager: DatabaseManager, event_bus: EventBus):
        self.db_manager = db_manager
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)
    
    async def create_subscription(self, user_id: str, plan_type: SubscriptionPlan, 
                                duration_days: int = 30) -> Optional[Dict[str, Any]]:
        """
        Create a new subscription for a user
        
        Args:
            user_id: Telegram user ID
            plan_type: Type of subscription plan
            duration_days: Duration of subscription in days (default 30)
            
        Returns:
            Created subscription data or None if creation failed
        """
        try:
            self.logger.info("Creating subscription", user_id=user_id, plan=plan_type)
            
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=duration_days)
            
            subscription_data = {
                "user_id": user_id,
                "plan_type": plan_type.value,
                "status": SubscriptionStatus.ACTIVE.value,
                "start_date": start_date,
                "end_date": end_date,
                "created_at": start_date,
                "updated_at": start_date
            }
            
            result = await self.db_manager.create_subscription(subscription_data)
            
            if result:
                # Publish subscription created event
                event = SubscriptionUpdatedEvent(
                    user_id=user_id,
                    old_status="inactive",
                    new_status=SubscriptionStatus.ACTIVE.value,
                    plan_type=plan_type.value
                )
                await self.event_bus.publish("subscription_created", event.dict())
                
                self.logger.info("Subscription created successfully", user_id=user_id)
                return subscription_data
            else:
                self.logger.error("Failed to create subscription", user_id=user_id)
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating subscription: {str(e)}", user_id=user_id)
            raise
    
    async def get_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription details for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Subscription details or None if not found
        """
        try:
            self.logger.debug("Retrieving subscription", user_id=user_id)
            
            subscription = await self.db_manager.get_subscription_from_sqlite(user_id)
            if subscription:
                self.logger.info("Subscription retrieved", user_id=user_id, status=subscription.get("status"))
                return subscription
            else:
                self.logger.info("No subscription found", user_id=user_id)
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving subscription: {str(e)}", user_id=user_id)
            raise
    
    async def update_subscription_status(self, user_id: str, new_status: SubscriptionStatus) -> bool:
        """
        Update subscription status for a user
        
        Args:
            user_id: Telegram user ID
            new_status: New subscription status
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            self.logger.info("Updating subscription status", user_id=user_id, new_status=new_status)
            
            # Get current subscription to determine old status
            current_sub = await self.db_manager.get_subscription_from_sqlite(user_id)
            old_status = current_sub.get("status") if current_sub else "inactive"
            
            # Update subscription status
            update_data = {
                "status": new_status.value,
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db_manager.update_subscription(user_id, update_data)
            
            if result:
                # Publish subscription updated event
                event = SubscriptionUpdatedEvent(
                    user_id=user_id,
                    old_status=old_status,
                    new_status=new_status.value,
                    plan_type=current_sub.get("plan_type", "free") if current_sub else "free"
                )
                await self.event_bus.publish("subscription_updated", event.dict())
                
                self.logger.info("Subscription status updated", user_id=user_id, new_status=new_status)
                return True
            else:
                self.logger.warning("Failed to update subscription status", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating subscription status: {str(e)}", user_id=user_id)
            raise
    
    async def check_subscription_status(self, user_id: str) -> bool:
        """
        Check if user has an active subscription
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if subscription is active, False otherwise
        """
        try:
            self.logger.debug("Checking subscription status", user_id=user_id)
            
            subscription = await self.db_manager.get_subscription_from_sqlite(user_id)
            if not subscription:
                self.logger.info("No subscription found", user_id=user_id)
                return False
            
            status = subscription.get("status")
            plan_type = subscription.get("plan_type")
            
            # Check if status is active
            if status == SubscriptionStatus.ACTIVE.value:
                # Check if subscription hasn't expired
                end_date = subscription.get("end_date")
                if end_date and isinstance(end_date, datetime):
                    if datetime.utcnow() > end_date:
                        # Subscription expired, update status
                        await self.update_subscription_status(user_id, SubscriptionStatus.EXPIRED)
                        self.logger.info("Subscription expired", user_id=user_id)
                        return False
                    else:
                        self.logger.info("Active subscription found", user_id=user_id, plan=plan_type)
                        return True
                else:
                    self.logger.info("Active subscription found (no expiration date)", user_id=user_id, plan=plan_type)
                    return True
            else:
                self.logger.info("Inactive subscription found", user_id=user_id, status=status)
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking subscription status: {str(e)}", user_id=user_id)
            raise
    
    async def upgrade_subscription(self, user_id: str, new_plan: SubscriptionPlan) -> bool:
        """
        Upgrade user subscription to a new plan
        
        Args:
            user_id: Telegram user ID
            new_plan: New subscription plan
            
        Returns:
            True if upgrade successful, False otherwise
        """
        try:
            self.logger.info("Upgrading subscription", user_id=user_id, new_plan=new_plan)
            
            # Get current subscription
            current_sub = await self.db_manager.get_subscription_from_sqlite(user_id)
            old_status = current_sub.get("status") if current_sub else "inactive"
            old_plan = current_sub.get("plan_type", "free")
            
            if not current_sub:
                # Create new subscription if none exists
                return await self.create_subscription(user_id, new_plan)
            
            # Update subscription plan
            update_data = {
                "plan_type": new_plan.value,
                "status": SubscriptionStatus.ACTIVE.value,  # Activate if upgrading
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db_manager.update_subscription(user_id, update_data)
            
            if result:
                # Publish subscription updated event
                event = SubscriptionUpdatedEvent(
                    user_id=user_id,
                    old_status=old_status,
                    new_status=SubscriptionStatus.ACTIVE.value,
                    plan_type=new_plan.value
                )
                await self.event_bus.publish("subscription_upgraded", event.dict())
                
                self.logger.info("Subscription upgraded", user_id=user_id, old_plan=old_plan, new_plan=new_plan)
                return True
            else:
                self.logger.warning("Failed to upgrade subscription", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error upgrading subscription: {str(e)}", user_id=user_id)
            raise
    
    async def cancel_subscription(self, user_id: str) -> bool:
        """
        Cancel user subscription
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            self.logger.info("Cancelling subscription", user_id=user_id)
            
            result = await self.update_subscription_status(user_id, SubscriptionStatus.CANCELLED)
            
            if result:
                self.logger.info("Subscription cancelled", user_id=user_id)
                return True
            else:
                self.logger.warning("Failed to cancel subscription", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelling subscription: {str(e)}", user_id=user_id)
            raise

'''
        
        with open(subscription_service_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Task 17 completed: SubscriptionService created")
    
    def create_narrative_service(self):
        """Task 18: Create NarrativeService in src/services/narrative.py"""
        logger.info("Executing Task 18: Creating NarrativeService")
        
        narrative_service_file = self.src_directory / "services" / "narrative.py"
        
        content = '''"""
Fase1 - Task 18
NarrativeService

Implements narrative operations as specified in Requirement 4.2: Core API Endpoints
and the design for narrative fragment operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from src.database.manager import DatabaseManager
from src.services.subscription import SubscriptionService
from src.events.bus import EventBus
from src.events.models import ContentViewedEvent, DecisionMadeEvent
from src.utils.logger import LoggerMixin, get_logger


class NarrativeDifficulty(str, Enum):
    """Enumeration for narrative difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class NarrativeType(str, Enum):
    """Enumeration for narrative types"""
    INTRO = "intro"
    ADVENTURE = "adventure"
    PUZZLE = "puzzle"
    CHARACTER = "character"
    LOCATION = "location"


class NarrativeService(LoggerMixin):
    """
    Manages narrative content operations
    """
    
    def __init__(self, db_manager: DatabaseManager, subscription_service: SubscriptionService, event_bus: EventBus):
        self.db_manager = db_manager
        self.subscription_service = subscription_service
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)
    
    async def get_narrative_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get narrative content with metadata
        
        Args:
            fragment_id: ID of the narrative fragment
            
        Returns:
            Narrative fragment data or None if not found
        """
        try:
            self.logger.debug("Retrieving narrative fragment", fragment_id=fragment_id)
            
            fragment = await self.db_manager.get_narrative_from_mongo(fragment_id)
            if fragment:
                self.logger.info("Narrative fragment retrieved", fragment_id=fragment_id)
                return fragment
            else:
                self.logger.warning("Narrative fragment not found", fragment_id=fragment_id)
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving narrative fragment: {str(e)}", fragment_id=fragment_id)
            raise
    
    async def get_user_narrative_progress(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's current narrative progress
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User's narrative progress or None if user not found
        """
        try:
            self.logger.debug("Retrieving user narrative progress", user_id=user_id)
            
            user_context = await self.db_manager.get_user_from_mongo(user_id)
            if not user_context:
                self.logger.warning("User not found", user_id=user_id)
                return None
            
            narrative_progress = user_context.get("current_state", {}).get("narrative_progress", {})
            self.logger.info("User narrative progress retrieved", user_id=user_id)
            return narrative_progress
                
        except Exception as e:
            self.logger.error(f"Error retrieving user narrative progress: {str(e)}", user_id=user_id)
            raise
    
    async def update_user_narrative_progress(self, user_id: str, fragment_id: str, 
                                           choice_id: str = None) -> bool:
        """
        Update user's narrative progress
        
        Args:
            user_id: Telegram user ID
            fragment_id: Current narrative fragment ID
            choice_id: Choice made by the user (optional)
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            self.logger.info("Updating user narrative progress", user_id=user_id, fragment_id=fragment_id)
            
            # Get current user state
            user_data = await self.db_manager.get_user_from_mongo(user_id)
            if not user_data:
                self.logger.warning("User not found", user_id=user_id)
                return False
            
            current_progress = user_data.get("current_state", {}).get("narrative_progress", {})
            
            # Update progress
            completed_fragments = current_progress.get("completed_fragments", [])
            if fragment_id not in completed_fragments:
                completed_fragments.append(fragment_id)
            
            choices_made = current_progress.get("choices_made", [])
            if choice_id:
                choices_made.append({
                    "fragment": fragment_id,
                    "choice": choice_id,
                    "timestamp": datetime.utcnow()
                })
            
            # Update user state in MongoDB
            update_data = {
                "$set": {
                    "current_state.narrative_progress": {
                        "current_fragment": fragment_id,
                        "completed_fragments": completed_fragments,
                        "choices_made": choices_made
                    },
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await self.db_manager.update_user_in_mongo(user_id, update_data)
            
            if result:
                self.logger.info("User narrative progress updated", user_id=user_id)
                
                # Publish decision made event if choice was made
                if choice_id:
                    event = DecisionMadeEvent(
                        user_id=user_id,
                        choice_id=choice_id,
                        fragment_id=fragment_id,
                        next_fragment_id=fragment_id  # This would come from the choice mapping
                    )
                    await self.event_bus.publish("decision_made", event.dict())
                
                return True
            else:
                self.logger.warning("Failed to update user narrative progress", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating user narrative progress: {str(e)}", user_id=user_id)
            raise
    
    async def validate_vip_access(self, user_id: str, fragment_id: str) -> bool:
        """
        Check if user has VIP access before allowing access to VIP content
        
        Args:
            user_id: Telegram user ID
            fragment_id: ID of the narrative fragment to access
            
        Returns:
            True if VIP access is granted, False otherwise
        """
        try:
            self.logger.debug("Validating VIP access", user_id=user_id, fragment_id=fragment_id)
            
            # Get the narrative fragment to check if it requires VIP access
            fragment = await self.get_narrative_fragment(fragment_id)
            if not fragment:
                self.logger.warning("Fragment not found", fragment_id=fragment_id)
                return False
            
            # Check if fragment requires VIP access
            vip_required = fragment.get("metadata", {}).get("vip_required", False)
            if not vip_required:
                self.logger.info("Fragment does not require VIP access", fragment_id=fragment_id)
                return True
            
            # Check user subscription status
            has_active_subscription = await self.subscription_service.check_subscription_status(user_id)
            is_vip = False
            
            if has_active_subscription:
                subscription = await self.subscription_service.get_subscription(user_id)
                if subscription and subscription.get("plan_type") == "vip":
                    is_vip = True
            
            if is_vip:
                self.logger.info("VIP access granted", user_id=user_id, fragment_id=fragment_id)
                return True
            else:
                self.logger.info("VIP access denied", user_id=user_id, fragment_id=fragment_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating VIP access: {str(e)}", user_id=user_id, fragment_id=fragment_id)
            raise
    
    async def get_available_choices(self, fragment_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get available choices for a narrative fragment
        
        Args:
            fragment_id: ID of the narrative fragment
            
        Returns:
            List of available choices or None if fragment not found
        """
        try:
            self.logger.debug("Retrieving available choices", fragment_id=fragment_id)
            
            fragment = await self.get_narrative_fragment(fragment_id)
            if fragment:
                choices = fragment.get("choices", [])
                self.logger.info(f"Retrieved {len(choices)} choices", fragment_id=fragment_id)
                return choices
            else:
                self.logger.warning("Fragment not found", fragment_id=fragment_id)
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving choices: {str(e)}", fragment_id=fragment_id)
            raise
    
    async def get_related_fragments(self, fragment_id: str, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get related narrative fragments based on tags
        
        Args:
            fragment_id: ID of the current narrative fragment
            tags: Tags to search for related fragments
            
        Returns:
            List of related narrative fragments
        """
        try:
            self.logger.debug("Retrieving related fragments", fragment_id=fragment_id, tags=tags)
            
            related_fragments = await self.db_manager.get_related_narratives(fragment_id, tags)
            self.logger.info(f"Retrieved {len(related_fragments)} related fragments", fragment_id=fragment_id)
            return related_fragments
                
        except Exception as e:
            self.logger.error(f"Error retrieving related fragments: {str(e)}", fragment_id=fragment_id)
            raise
    
    async def track_content_view(self, user_id: str, content_id: str, content_type: str) -> bool:
        """
        Track when a user views content
        
        Args:
            user_id: Telegram user ID
            content_id: ID of the content viewed
            content_type: Type of content viewed
            
        Returns:
            True if tracking successful, False otherwise
        """
        try:
            self.logger.info("Tracking content view", user_id=user_id, content_id=content_id)
            
            # Publish content viewed event
            event = ContentViewedEvent(
                user_id=user_id,
                content_id=content_id,
                content_type=content_type
            )
            await self.event_bus.publish("content_viewed", event.dict())
            
            # Update user's content view history in MongoDB
            update_data = {
                "$push": {
                    "current_state.view_history": {
                        "content_id": content_id,
                        "content_type": content_type,
                        "viewed_at": datetime.utcnow()
                    }
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await self.db_manager.update_user_in_mongo(user_id, update_data)
            
            if result:
                self.logger.info("Content view tracked", user_id=user_id, content_id=content_id)
                return True
            else:
                self.logger.warning("Failed to track content view", user_id=user_id, content_id=content_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error tracking content view: {str(e)}", user_id=user_id, content_id=content_id)
            raise

'''
        
        with open(narrative_service_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Task 18 completed: NarrativeService created")
    
    def create_coordinator_service(self):
        """Task 19: Add user interaction orchestration to CoordinatorService in src/services/coordinator.py"""
        logger.info("Executing Task 19: Creating CoordinatorService")
        
        coordinator_service_file = self.src_directory / "services" / "coordinator.py"
        
        content = '''"""
Fase1 - Task 19
CoordinatorService with user interaction orchestration

Implements orchestration of complex business workflows as specified
in Requirements 3.1 and 3.2: Coordinator Service Architecture and Event Ordering.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.services.narrative import NarrativeService
from src.events.bus import EventBus
from src.events.models import BaseEvent, UserInteractionEvent, ReactionDetectedEvent
from src.utils.logger import LoggerMixin, get_logger


class BesitosTransactionType(str, Enum):
    """Enumeration for besitos transaction types"""
    REWARD = "reward"
    PURCHASE = "purchase"
    PENALTY = "penalty"
    BONUS = "bonus"


class CoordinatorService(LoggerMixin):
    """
    Orchestrates complex business workflows and event sequencing
    """
    
    def __init__(self, user_service: UserService, subscription_service: SubscriptionService,
                 narrative_service: NarrativeService, event_bus: EventBus):
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.narrative_service = narrative_service
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)
        self.event_buffer = {}  # Buffer for event ordering by user
    
    async def process_user_interaction(self, user_id: str, action: str) -> Dict[str, Any]:
        """
        Handle user interaction workflows
        
        Args:
            user_id: Telegram user ID
            action: Type of interaction action
            
        Returns:
            Result of the interaction processing
        """
        try:
            self.logger.info("Processing user interaction", user_id=user_id, action=action)
            
            # Create interaction event
            event = UserInteractionEvent(
                user_id=user_id,
                action=action,
                context={"processed_at": datetime.utcnow().isoformat()}
            )
            
            # Add to event buffer for ordering
            await self.add_to_event_buffer(user_id, event)
            
            # Process different types of interactions
            if action == "start":
                result = await self._handle_start_interaction(user_id)
            elif action == "narrative":
                result = await self._handle_narrative_interaction(user_id)
            elif action == "subscription":
                result = await self._handle_subscription_interaction(user_id)
            elif action == "reaction":
                result = await self._handle_reaction_interaction(user_id)
            else:
                result = {"status": "handled", "action": action, "user_id": user_id}
            
            # Publish interaction processed event
            await self.event_bus.publish("user_interaction_processed", {
                "user_id": user_id,
                "action": action,
                "result": result,
                "processed_at": datetime.utcnow()
            })
            
            self.logger.info("User interaction processed successfully", user_id=user_id, action=action)
            return result
                
        except Exception as e:
            self.logger.error(f"Error processing user interaction: {str(e)}", user_id=user_id, action=action)
            raise
    
    async def validate_vip_access(self, user_id: str) -> bool:
        """
        Check subscription status before allowing access to VIP features
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if VIP access is allowed, False otherwise
        """
        try:
            self.logger.debug("Validating VIP access", user_id=user_id)
            
            # Check user subscription status
            has_subscription = await self.subscription_service.check_subscription_status(user_id)
            if not has_subscription:
                self.logger.info("User does not have subscription", user_id=user_id)
                return False
            
            # Get detailed subscription info
            subscription = await self.subscription_service.get_subscription(user_id)
            if subscription and subscription.get("plan_type") == "vip":
                self.logger.info("VIP access validated", user_id=user_id)
                return True
            else:
                self.logger.info("User does not have VIP subscription", user_id=user_id, plan=subscription.get("plan_type") if subscription else "none")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating VIP access: {str(e)}", user_id=user_id)
            raise
    
    async def process_besitos_transaction(self, user_id: str, amount: int, 
                                        transaction_type: BesitosTransactionType, 
                                        description: str = "") -> bool:
        """
        Handle virtual currency transactions with atomicity
        
        Args:
            user_id: Telegram user ID
            amount: Amount of besitos to transact
            transaction_type: Type of transaction
            description: Optional description of transaction
            
        Returns:
            True if transaction successful, False otherwise
        """
        try:
            self.logger.info("Processing besitos transaction", user_id=user_id, amount=amount, type=transaction_type)
            
            # In a real implementation, this would update a user's besitos balance
            # This would require additional database fields and atomic operations
            transaction_data = {
                "user_id": user_id,
                "amount": amount,
                "type": transaction_type.value,
                "description": description,
                "timestamp": datetime.utcnow(),
                "status": "completed"
            }
            
            # Publish besitos transaction event
            await self.event_bus.publish("besitos_transaction", transaction_data)
            
            self.logger.info("Besitos transaction processed", user_id=user_id, amount=amount, type=transaction_type)
            return True
                
        except Exception as e:
            self.logger.error(f"Error processing besitos transaction: {str(e)}", user_id=user_id, amount=amount)
            raise
    
    async def add_to_event_buffer(self, user_id: str, event: BaseEvent) -> None:
        """
        Buffer events for ordering by user
        
        Args:
            user_id: Telegram user ID
            event: Event to buffer
        """
        try:
            if user_id not in self.event_buffer:
                self.event_buffer[user_id] = []
            
            # Add event to user's buffer
            self.event_buffer[user_id].append({
                "event": event,
                "timestamp": datetime.utcnow(),
                "processed": False
            })
            
            self.logger.debug("Event added to user buffer", user_id=user_id, event_type=event.event_type)
            
            # Process the buffer to maintain order (simplified implementation)
            await self._process_user_event_buffer(user_id)
            
        except Exception as e:
            self.logger.error(f"Error adding event to buffer: {str(e)}", user_id=user_id, event_type=event.event_type)
            raise
    
    async def _process_user_event_buffer(self, user_id: str) -> None:
        """
        Process events in the buffer to maintain chronological order
        
        Args:
            user_id: Telegram user ID
        """
        try:
            if user_id not in self.event_buffer:
                return
            
            # In a real implementation, this would sort events by timestamp
            # and process them in order, handling out-of-order events appropriately
            buffer = self.event_buffer[user_id]
            
            # Sort events by timestamp (simplified approach)
            sorted_events = sorted(buffer, key=lambda x: x["timestamp"])
            
            # Process events in order
            for event_entry in sorted_events:
                if not event_entry["processed"]:
                    event = event_entry["event"]
                    
                    # Process the event (publish it)
                    await self.event_bus.publish(event.event_type, event.dict())
                    
                    # Mark as processed
                    event_entry["processed"] = True
            
            # Clean up processed events
            self.event_buffer[user_id] = [entry for entry in self.event_buffer[user_id] if not entry["processed"]]
            
            self.logger.debug("User event buffer processed", user_id=user_id, processed_count=len([e for e in buffer if e["processed"]]))
            
        except Exception as e:
            self.logger.error(f"Error processing user event buffer: {str(e)}", user_id=user_id)
            raise
    
    async def process_reaction(self, user_id: str, content_id: str, reaction_type: str) -> bool:
        """
        Process a user's reaction to content
        
        Args:
            user_id: Telegram user ID
            content_id: ID of the content being reacted to
            reaction_type: Type of reaction
        
        Returns:
            True if processing successful, False otherwise
        """
        try:
            self.logger.info("Processing reaction", user_id=user_id, content_id=content_id, reaction_type=reaction_type)
            
            # Create reaction event
            reaction_event = ReactionDetectedEvent(
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type
            )
            
            # Add to event buffer for ordering
            await self.add_to_event_buffer(user_id, reaction_event)
            
            # If reaction is of positive type, potentially award besitos
            positive_reactions = ["like", "love", "besito"]
            if reaction_type in positive_reactions:
                # Award besitos for positive reactions
                await self.process_besitos_transaction(
                    user_id, 
                    1, 
                    BesitosTransactionType.REWARD,
                    f"Reward for {reaction_type} reaction to content {content_id}"
                )
            
            # Publish reaction processed event
            result_data = {
                "user_id": user_id,
                "content_id": content_id,
                "reaction_type": reaction_type,
                "awarded_besitos": reaction_type in positive_reactions
            }
            await self.event_bus.publish("reaction_processed", result_data)
            
            self.logger.info("Reaction processed", user_id=user_id, content_id=content_id, reaction_type=reaction_type)
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing reaction: {str(e)}", user_id=user_id, content_id=content_id)
            raise
    
    async def _handle_start_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's start interaction."""
        try:
            self.logger.debug("Handling start interaction", user_id=user_id)
            
            # Create user if doesn't exist (or update last login)
            # This would be handled by the UserService in a real implementation
            user_context = await self.user_service.get_user_context(user_id)
            
            if not user_context:
                # User doesn't exist, need to create
                telegram_user_data = {"id": user_id, "username": f"user_{user_id}", "first_name": f"User_{user_id}"}
                user_context = await self.user_service.create_user(telegram_user_data)
            
            # Update user's last activity
            await self.user_service.update_user_state(user_id, {
                "menu_context": "main_menu",
                "session_data": {"last_activity": datetime.utcnow().isoformat()}
            })
            
            return {
                "status": "success",
                "action": "start",
                "user_exists": user_context is not None
            }
        except Exception as e:
            self.logger.error(f"Error handling start interaction: {str(e)}", user_id=user_id)
            raise
    
    async def _handle_narrative_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's narrative interaction."""
        try:
            self.logger.debug("Handling narrative interaction", user_id=user_id)
            
            # Check if user has VIP access for narrative content
            user_context = await self.user_service.get_user_context(user_id)
            if not user_context:
                return {"status": "error", "message": "User not found"}
            
            # Get user's current narrative progress
            progress = await self.narrative_service.get_user_narrative_progress(user_id)
            current_fragment = progress.get("current_fragment") if progress else None
            
            # If no current fragment, start with intro
            if not current_fragment:
                # In a real implementation, this would get the first narrative fragment
                current_fragment = "intro_001"
            
            # Get the narrative fragment
            fragment = await self.narrative_service.get_narrative_fragment(current_fragment)
            
            return {
                "status": "success",
                "action": "narrative",
                "current_fragment": current_fragment,
                "fragment_exists": fragment is not None
            }
        except Exception as e:
            self.logger.error(f"Error handling narrative interaction: {str(e)}", user_id=user_id)
            raise
    
    async def _handle_subscription_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's subscription interaction."""
        try:
            self.logger.debug("Handling subscription interaction", user_id=user_id)
            
            # Check user subscription status
            has_subscription = await self.subscription_service.check_subscription_status(user_id)
            subscription = await self.subscription_service.get_subscription(user_id)
            
            return {
                "status": "success",
                "action": "subscription",
                "has_subscription": has_subscription,
                "subscription": subscription
            }
        except Exception as e:
            self.logger.error(f"Error handling subscription interaction: {str(e)}", user_id=user_id)
            raise
    
    async def _handle_reaction_interaction(self, user_id: str) -> Dict[str, Any]:
        """Handle a user's reaction interaction."""
        try:
            self.logger.debug("Handling reaction interaction", user_id=user_id)
            
            # For this basic implementation, we just acknowledge the interaction
            # The actual reaction would be handled by the process_reaction method
            return {
                "status": "success",
                "action": "reaction",
                "message": "Please provide content_id and reaction_type for processing"
            }
        except Exception as e:
            self.logger.error(f"Error handling reaction interaction: {str(e)}", user_id=user_id)
            raise

'''
        
        with open(coordinator_service_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Task 19 completed: CoordinatorService created")
    
    def create_event_ordering_buffer(self):
        """Task 20: Create event ordering buffer in src/events/ordering.py"""
        logger.info("Executing Task 20: Creating event ordering buffer")
        
        event_ordering_file = self.src_directory / "events" / "ordering.py"
        
        content = '''"""
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

'''
        
        with open(event_ordering_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Task 20 completed: Event ordering buffer created")
    
    async def execute_task(self, task_id: int):
        """Execute a single task by ID."""
        try:
            logger.info(f"Starting execution of Task {task_id}")
            
            # Map task IDs to their implementation functions
            task_functions = {
                15: self.create_services_init_file,
                16: self.create_user_service,
                17: self.create_subscription_service,
                18: self.create_narrative_service,
                19: self.create_coordinator_service,
                20: self.create_event_ordering_buffer
            }
            
            if task_id not in task_functions:
                raise ValueError(f"Unknown task ID: {task_id}")
            
            # Execute the specific task
            task_functions[task_id]()
            
            self.executed_tasks.append(task_id)
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to execute Task {task_id}: {str(e)}")
            self.failed_tasks.append(task_id)
            raise
    
    async def execute_task_sequence(self, task_range: range):
        """Execute tasks in the specified range sequentially."""
        self.start_time = datetime.utcnow()
        
        logger.info(f"Starting execution of tasks in range {task_range.start} to {task_range.stop-1}")
        
        # Validate task files exist
        missing_tasks = self.validate_task_files(task_range)
        if missing_tasks:
            raise FileNotFoundError(f"Missing task files: {missing_tasks}")
        
        # Validate source structure
        if not self.validate_source_structure():
            raise FileNotFoundError("Required source directories missing")
        
        # Execute tasks sequentially
        for task_id in task_range:
            try:
                await self.execute_task(task_id)
                
                # Small delay between tasks to ensure proper sequencing
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Stopping execution due to error in Task {task_id}: {str(e)}")
                raise
    
    def generate_execution_report(self):
        """Generate a detailed report of the execution."""
        execution_time = (datetime.utcnow() - self.start_time) if self.start_time else None
        
        report = {
            "execution_summary": {
                "total_tasks": len(list(range(15, 21))),
                "executed_tasks": len(self.executed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "execution_time": str(execution_time) if execution_time else "N/A",
                "timestamp": datetime.utcnow().isoformat()
            },
            "executed_tasks": sorted(self.executed_tasks),
            "failed_tasks": sorted(self.failed_tasks),
            "task_details": {}
        }
        
        # Add specific details for each task
        for task_id in range(15, 21):
            report["task_details"][task_id] = {
                "status": "executed" if task_id in self.executed_tasks else "failed",
                "file_created": self.verify_task_artifacts(task_id)
            }
        
        logger.info(f"Execution report: {json.dumps(report, indent=2)}")
        return report
    
    def verify_task_artifacts(self, task_id: int) -> bool:
        """Verify that the expected files were created for a task."""
        try:
            if task_id == 15:
                # Task 15: Create services module structure in src/services/__init__.py
                file_path = self.src_directory / "services" / "__init__.py"
                return file_path.exists()
            elif task_id == 16:
                # Task 16: Create UserService for unified user operations in src/services/user.py
                file_path = self.src_directory / "services" / "user.py"
                return file_path.exists()
            elif task_id == 17:
                # Task 17: Create SubscriptionService in src/services/subscription.py
                file_path = self.src_directory / "services" / "subscription.py"
                return file_path.exists()
            elif task_id == 18:
                # Task 18: Create NarrativeService in src/services/narrative.py
                file_path = self.src_directory / "services" / "narrative.py"
                return file_path.exists()
            elif task_id == 19:
                # Task 19: Add user interaction orchestration to CoordinatorService in src/services/coordinator.py
                file_path = self.src_directory / "services" / "coordinator.py"
                return file_path.exists()
            elif task_id == 20:
                # Task 20: Create event ordering buffer in src/events/ordering.py
                file_path = self.src_directory / "events" / "ordering.py"
                return file_path.exists()
        except Exception:
            return False
        
        return False


async def main():
    """Main execution function."""
    logger.info("Starting sequential execution of Fase1 tasks 15-20")
    
    executor = TaskExecutor()
    
    try:
        # Execute tasks 15-20 sequentially
        await executor.execute_task_sequence(range(15, 21))
        
        # Generate execution report
        report = executor.generate_execution_report()
        
        logger.info("All tasks completed successfully")
        logger.info(f"Execution summary: {report['execution_summary']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
        
        # Generate partial report if execution failed
        if hasattr(executor, 'generate_execution_report'):
            try:
                report = executor.generate_execution_report()
                logger.info(f"Partial execution report: {report['execution_summary']}")
            except:
                pass
        
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
"""
Fase1 - Task 17
SubscriptionService

Implements subscription management functionality as specified
in Requirement 3.1: Coordinator Service Architecture.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

from src.database.manager import DatabaseManager
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
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        # LoggerMixin provides the logger property automatically
    
    async def create_subscription(self, user_id: str, plan_type: SubscriptionPlan, 
                                duration_days: int = 30, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Create a new subscription for a user
        
        Args:
            user_id: Telegram user ID
            plan_type: Type of subscription plan
            duration_days: Duration of subscription in days (default 30)
            
        Returns:
            Created subscription data or None if creation failed
        """
        event_bus = kwargs.get('event_bus')
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
                if event_bus:
                    event = SubscriptionUpdatedEvent(
                        user_id=user_id,
                        old_status="inactive",
                        new_status=SubscriptionStatus.ACTIVE.value,
                        plan_type=plan_type.value
                    )
                    await event_bus.publish("subscription_created", event)
                
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
    
    async def update_subscription_status(self, user_id: str, new_status: SubscriptionStatus, **kwargs) -> bool:
        """
        Update subscription status for a user
        
        Args:
            user_id: Telegram user ID
            new_status: New subscription status
            
        Returns:
            True if update successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
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
                if event_bus:
                    event = SubscriptionUpdatedEvent(
                        user_id=user_id,
                        old_status=old_status,
                        new_status=new_status.value,
                        plan_type=current_sub.get("plan_type", "free") if current_sub else "free"
                    )
                    await event_bus.publish("subscription_updated", event)
                
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
                if end_date:
                    # Parse end_date if it's a string (from SQLite)
                    if isinstance(end_date, str):
                        try:
                            # Try to parse ISO format date strings
                            if '+' in end_date:
                                # Handle timezone-aware datetime strings
                                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                            else:
                                # Handle timezone-naive datetime strings
                                end_date = datetime.fromisoformat(end_date)
                        except Exception as e:
                            self.logger.warning("Failed to parse end_date", user_id=user_id, end_date=end_date, error=str(e))
                            # If we can't parse the date, treat as no expiration
                            self.logger.info("Active subscription found (unparseable expiration date)", user_id=user_id, plan=plan_type)
                            return True

                    # Convert to UTC if not timezone-aware
                    if end_date.tzinfo is None:
                        end_date = end_date.replace(tzinfo=timezone.utc)

                    # Compare with current UTC time
                    now = datetime.now(timezone.utc)
                    if now > end_date:
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
    
    async def upgrade_subscription(self, user_id: str, new_plan: SubscriptionPlan, **kwargs) -> bool:
        """
        Upgrade user subscription to a new plan
        
        Args:
            user_id: Telegram user ID
            new_plan: New subscription plan
            
        Returns:
            True if upgrade successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Upgrading subscription", user_id=user_id, new_plan=new_plan)
            
            # Get current subscription
            current_sub = await self.db_manager.get_subscription_from_sqlite(user_id)
            old_status = current_sub.get("status") if current_sub else "inactive"
            old_plan = current_sub.get("plan_type", "free")
            
            if not current_sub:
                # Create new subscription if none exists
                return await self.create_subscription(user_id, new_plan, **kwargs)
            
            # Update subscription plan
            update_data = {
                "plan_type": new_plan.value,
                "status": SubscriptionStatus.ACTIVE.value,  # Activate if upgrading
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db_manager.update_subscription(user_id, update_data)
            
            if result:
                # Publish subscription updated event
                if event_bus:
                    event = SubscriptionUpdatedEvent(
                        user_id=user_id,
                        old_status=old_status,
                        new_status=SubscriptionStatus.ACTIVE.value,
                        plan_type=new_plan.value
                    )
                    await event_bus.publish("subscription_upgraded", event)
                
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


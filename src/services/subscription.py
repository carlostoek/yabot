"""
SubscriptionService for the YABOT system.

This module provides subscription management operations for the YABOT system,
implementing the requirements specified in fase1 specification section 1.2 and 3.1.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionServiceError(Exception):
    """Base exception for subscription service operations."""
    pass


class SubscriptionNotFoundError(SubscriptionServiceError):
    """Exception raised when subscription is not found."""
    pass


class SubscriptionService:
    """Service for managing user subscriptions and premium features."""
    
    def __init__(self, database_manager: DatabaseManager, event_bus: EventBus):
        """Initialize the subscription service.
        
        Args:
            database_manager (DatabaseManager): Database manager instance
            event_bus (EventBus): Event bus instance
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        logger.info("SubscriptionService initialized")
    
    async def create_subscription(self, user_id: str, plan_type: str, 
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Create a new subscription for a user.
        
        Args:
            user_id (str): User ID
            plan_type (str): Type of subscription plan (free, premium, vip)
            start_date (datetime, optional): Subscription start date
            end_date (datetime, optional): Subscription end date
            
        Returns:
            Dict[str, Any]: Created subscription data
            
        Raises:
            SubscriptionServiceError: If subscription creation fails
        """
        logger.info("Creating new subscription for user: %s with plan: %s", user_id, plan_type)
        
        # Validate plan type
        valid_plans = ["free", "premium", "vip"]
        if plan_type not in valid_plans:
            raise SubscriptionServiceError(f"Invalid plan type: {plan_type}. Valid plans: {valid_plans}")
        
        # Set default dates if not provided
        if start_date is None:
            start_date = datetime.utcnow()
        
        # Default status based on plan type
        status = "active" if plan_type != "free" else "inactive"
        
        try:
            # Create subscription in SQLite
            subscription_data = self._create_subscription_in_db(
                user_id, plan_type, status, start_date, end_date
            )
            
            if not subscription_data:
                raise SubscriptionServiceError("Failed to create subscription in database")
            
            # Publish subscription_updated event
            try:
                event = create_event(
                    "subscription_updated",
                    user_id=user_id,
                    plan_type=plan_type,
                    status=status,
                    start_date=start_date,
                    end_date=end_date
                )
                await self.event_bus.publish("subscription_updated", event.dict())
            except Exception as e:
                logger.warning("Failed to publish subscription_updated event: %s", str(e))
            
            logger.info("Successfully created subscription for user: %s", user_id)
            return subscription_data
            
        except Exception as e:
            logger.error("Error creating subscription: %s", str(e))
            raise SubscriptionServiceError(f"Failed to create subscription: {str(e)}")
    
    def _create_subscription_in_db(self, user_id: str, plan_type: str, status: str,
                                 start_date: datetime, end_date: Optional[datetime]) -> Optional[Dict[str, Any]]:
        """Create subscription in SQLite database.
        
        Args:
            user_id (str): User ID
            plan_type (str): Type of subscription plan
            status (str): Subscription status
            start_date (datetime): Subscription start date
            end_date (datetime, optional): Subscription end date
            
        Returns:
            Optional[Dict[str, Any]]: Created subscription data or None if failed
        """
        try:
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            
            # Create subscriptions table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan_type TEXT NOT NULL CHECK (plan_type IN ('free', 'premium', 'vip')),
                    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled', 'expired')),
                    start_date DATETIME NOT NULL,
                    end_date DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
                )
            """)
            
            # Insert subscription
            cursor.execute("""
                INSERT INTO subscriptions (
                    user_id, plan_type, status, start_date, end_date
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                plan_type,
                status,
                start_date.isoformat(),
                end_date.isoformat() if end_date else None
            ))
            
            conn.commit()
            
            # Get the created subscription
            subscription_id = cursor.lastrowid
            cursor.execute("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                subscription = dict(zip(columns, row))
                logger.debug("Created subscription in SQLite for user: %s", user_id)
                return subscription
            
            return None
            
        except Exception as e:
            logger.error("Error creating subscription in SQLite: %s", str(e))
            return None
    
    async def get_subscription(self, user_id: str) -> Dict[str, Any]:
        """Get subscription data for a user.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict[str, Any]: Subscription data
            
        Raises:
            SubscriptionNotFoundError: If subscription is not found
            SubscriptionServiceError: If operation fails
        """
        logger.debug("Retrieving subscription for user: %s", user_id)
        
        try:
            subscription = self._get_subscription_from_db(user_id)
            
            if subscription is None:
                raise SubscriptionNotFoundError(f"Subscription not found for user: {user_id}")
            
            logger.debug("Successfully retrieved subscription for user: %s", user_id)
            return subscription
            
        except SubscriptionNotFoundError:
            raise
        except Exception as e:
            logger.error("Error retrieving subscription: %s", str(e))
            raise SubscriptionServiceError(f"Failed to retrieve subscription: {str(e)}")
    
    def _get_subscription_from_db(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription from SQLite database.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Optional[Dict[str, Any]]: Subscription data or None if not found
        """
        try:
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                subscription = dict(zip(columns, row))
                logger.debug("Retrieved subscription from SQLite for user: %s", user_id)
                return subscription
            
            return None
            
        except Exception as e:
            logger.error("Error retrieving subscription from SQLite: %s", str(e))
            return None
    
    async def update_subscription(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update subscription data for a user.
        
        Args:
            user_id (str): User ID
            updates (Dict[str, Any]): Subscription updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Updating subscription for user: %s", user_id)
        
        try:
            # Filter valid update fields
            valid_fields = {"plan_type", "status", "start_date", "end_date"}
            filtered_updates = {k: v for k, v in updates.items() if k in valid_fields}
            
            if not filtered_updates:
                logger.warning("No valid updates provided for user: %s", user_id)
                return True
            
            # Update subscription in database
            success = self._update_subscription_in_db(user_id, filtered_updates)
            
            if success:
                logger.info("Successfully updated subscription for user: %s", user_id)
                
                # Publish subscription_updated event
                try:
                    # Get current subscription data for the event
                    subscription = self._get_subscription_from_db(user_id)
                    if subscription:
                        event = create_event(
                            "subscription_updated",
                            user_id=user_id,
                            plan_type=subscription.get("plan_type"),
                            status=subscription.get("status"),
                            start_date=datetime.fromisoformat(subscription.get("start_date")),
                            end_date=datetime.fromisoformat(subscription.get("end_date")) if subscription.get("end_date") else None
                        )
                        await self.event_bus.publish("subscription_updated", event.dict())
                except Exception as e:
                    logger.warning("Failed to publish subscription_updated event: %s", str(e))
            
            else:
                logger.warning("No changes made to subscription for user: %s", user_id)
            
            return success
            
        except Exception as e:
            logger.error("Error updating subscription: %s", str(e))
            return False
    
    def _update_subscription_in_db(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update subscription in SQLite database.
        
        Args:
            user_id (str): User ID
            updates (Dict[str, Any]): Subscription updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            
            # Build SET clause dynamically
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                # Handle datetime objects
                if isinstance(value, datetime):
                    set_clauses.append(f"{key} = ?")
                    values.append(value.isoformat())
                else:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            # Add updated_at timestamp
            set_clauses.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            
            # Add user_id for WHERE clause
            values.append(user_id)
            
            set_clause = ", ".join(set_clauses)
            
            # Update subscription
            cursor.execute(
                f"UPDATE subscriptions SET {set_clause} WHERE user_id = ?",
                values
            )
            
            conn.commit()
            
            success = cursor.rowcount > 0
            logger.debug("Updated subscription in SQLite for user: %s", user_id)
            return success
            
        except Exception as e:
            logger.error("Error updating subscription in SQLite: %s", str(e))
            return False
    
    async def cancel_subscription(self, user_id: str) -> bool:
        """Cancel a user's subscription.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Cancelling subscription for user: %s", user_id)
        
        try:
            # Update subscription status to cancelled
            success = await self.update_subscription(user_id, {"status": "cancelled"})
            
            if success:
                logger.info("Successfully cancelled subscription for user: %s", user_id)
            else:
                logger.warning("Failed to cancel subscription for user: %s", user_id)
            
            return success
            
        except Exception as e:
            logger.error("Error cancelling subscription: %s", str(e))
            return False
    
    async def check_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """Check if a user has an active subscription.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict[str, Any]: Subscription status information
            
        Raises:
            SubscriptionServiceError: If operation fails
        """
        logger.debug("Checking subscription status for user: %s", user_id)
        
        try:
            subscription = await self.get_subscription(user_id)
            
            # Check if subscription is active
            is_active = subscription.get("status") == "active"
            
            # Check if subscription is expired (if end_date is set)
            is_expired = False
            end_date_str = subscription.get("end_date")
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str)
                is_expired = end_date < datetime.utcnow()
                if is_expired and subscription.get("status") == "active":
                    # Update status to expired
                    await self.update_subscription(user_id, {"status": "expired"})
                    is_active = False
            
            status_info = {
                "user_id": user_id,
                "is_active": is_active,
                "is_expired": is_expired,
                "plan_type": subscription.get("plan_type"),
                "status": subscription.get("status"),
                "start_date": subscription.get("start_date"),
                "end_date": subscription.get("end_date")
            }
            
            logger.debug("Subscription status for user %s: active=%s, expired=%s", 
                        user_id, is_active, is_expired)
            return status_info
            
        except SubscriptionNotFoundError:
            # If no subscription exists, return inactive status
            status_info = {
                "user_id": user_id,
                "is_active": False,
                "is_expired": False,
                "plan_type": "free",
                "status": "inactive",
                "start_date": None,
                "end_date": None
            }
            return status_info
        except Exception as e:
            logger.error("Error checking subscription status: %s", str(e))
            raise SubscriptionServiceError(f"Failed to check subscription status: {str(e)}")
    
    async def validate_vip_access(self, user_id: str) -> bool:
        """Validate if a user has VIP access based on their subscription.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if user has VIP access, False otherwise
        """
        logger.debug("Validating VIP access for user: %s", user_id)
        
        try:
            status_info = await self.check_subscription_status(user_id)
            has_vip_access = (
                status_info.get("is_active") and 
                status_info.get("plan_type") in ["vip"]
            )
            
            logger.debug("VIP access for user %s: %s", user_id, has_vip_access)
            return has_vip_access
            
        except Exception as e:
            logger.error("Error validating VIP access: %s", str(e))
            return False

    async def is_user_vip(self, user_id: str) -> bool:
        """Check if a user has VIP status"""
        try:
            # Use the existing validate_vip_access which checks for active VIP subscription
            return await self.validate_vip_access(user_id)
        except Exception as e:
            logger.error("Error checking VIP status: %s", str(e))
            return False


# Convenience function for easy usage
async def create_subscription_service(database_manager: DatabaseManager, 
                                   event_bus: EventBus) -> SubscriptionService:
    """Create and initialize a subscription service instance.
    
    Args:
        database_manager (DatabaseManager): Database manager instance
        event_bus (EventBus): Event bus instance
        
    Returns:
        SubscriptionService: Initialized subscription service instance
    """
    subscription_service = SubscriptionService(database_manager, event_bus)
    return subscription_service

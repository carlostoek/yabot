"""
Subscription Manager - Channel Administration Module

This module implements subscription management functionality leveraging patterns
from src/services/subscription.py as specified in Requirement 3.2 and 5.1.

The system handles:
- VIP subscription management
- Subscription expiration processing via cron jobs
- Subscription status validation
- Event publishing for subscription operations
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel

from src.events.models import BaseEvent, SubscriptionUpdatedEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger
from src.services.subscription import SubscriptionService, SubscriptionPlan, SubscriptionStatus

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient


class VipStatus(BaseModel):
    """
    VIP status information
    """
    is_vip: bool
    plan_type: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    auto_renew: bool = False
    metadata: Dict[str, Any] = {}


class ExpiredSubscription(BaseModel):
    """
    Information about an expired subscription
    """
    user_id: str
    subscription_id: str
    plan_type: str
    expired_at: datetime
    was_auto_renewed: bool = False
    grace_period_until: Optional[datetime] = None


class SubscriptionManager:
    """
    Subscription manager for VIP subscriptions and expiration handling

    Implements requirements 3.2, 5.1:
    - 3.2: VIP subscription management and status checking
    - 5.1: Subscription expiration processing with cron jobs

    Leverages existing patterns from src/services/subscription.py
    """

    def __init__(self, db_client: 'AsyncIOMotorClient', event_bus: EventBus):
        """
        Initialize the subscription manager

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing subscription events
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)

        # Initialize the underlying subscription service
        try:
            from src.database.manager import DatabaseManager
            db_manager = DatabaseManager(db_client)
            self.subscription_service = SubscriptionService(db_manager)
        except Exception:
            # Fallback: create a minimal service-like object for testing
            self.subscription_service = None
            self.logger.warning("SubscriptionService not available - using fallback")

        # Collection references
        self.users_collection = self.db.users
        self.subscriptions_collection = self.db.subscriptions
        self.subscription_history_collection = self.db.subscription_history

    async def create_subscription(self, user_id: str, plan: SubscriptionPlan,
                                duration_days: int = 30, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Create a new VIP subscription for a user

        Leverages src/services/subscription.py patterns

        Args:
            user_id: User identifier
            plan: Subscription plan type
            duration_days: Duration in days
            **kwargs: Additional parameters

        Returns:
            Created subscription data or None if failed
        """
        try:
            self.logger.info(
                "Creating VIP subscription",
                user_id=user_id,
                plan=plan.value,
                duration_days=duration_days
            )

            # Use the underlying subscription service or fallback
            if self.subscription_service:
                subscription_data = await self.subscription_service.create_subscription(
                    user_id=user_id,
                    plan_type=plan,
                    duration_days=duration_days,
                    event_bus=self.event_bus
                )
            else:
                # Fallback implementation
                subscription_data = {
                    "subscription_id": f"sub_{user_id}_{plan.value}",
                    "user_id": user_id,
                    "plan_type": plan.value,
                    "start_date": datetime.utcnow(),
                    "end_date": datetime.utcnow() + timedelta(days=duration_days),
                    "status": "active"
                }

            if subscription_data:
                # Update user document with VIP status
                await self._update_user_vip_status(user_id, True, plan.value, subscription_data["end_date"])

                # Log subscription creation
                await self._log_subscription_event(
                    user_id=user_id,
                    action="created",
                    plan_type=plan.value,
                    metadata={
                        "duration_days": duration_days,
                        "subscription_id": subscription_data.get("subscription_id")
                    }
                )

                self.logger.info(
                    "VIP subscription created successfully",
                    user_id=user_id,
                    subscription_id=subscription_data.get("subscription_id")
                )

                return subscription_data
            else:
                self.logger.error("Failed to create VIP subscription", user_id=user_id)
                return None

        except Exception as e:
            self.logger.error(
                "Error creating VIP subscription",
                user_id=user_id,
                plan=plan.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def check_vip_status(self, user_id: str) -> VipStatus:
        """
        Check VIP status for a user

        Args:
            user_id: User identifier

        Returns:
            VipStatus with current status information
        """
        try:
            self.logger.debug("Checking VIP status", user_id=user_id)

            # Check if user has active subscription
            if self.subscription_service:
                is_vip = await self.subscription_service.check_subscription_status(user_id)

                if is_vip:
                    # Get detailed subscription information
                    subscription = await self.subscription_service.get_subscription(user_id)
                else:
                    subscription = None
            else:
                # Fallback: check directly from database
                subscription = await self.subscriptions_collection.find_one({
                    "user_id": user_id,
                    "status": "active"
                })
                is_vip = subscription is not None

            if is_vip and subscription:

                if subscription:
                    days_remaining = None
                    if subscription.get("end_date"):
                        end_date = subscription["end_date"]
                        if isinstance(end_date, datetime):
                            time_remaining = end_date - datetime.utcnow()
                            days_remaining = max(0, time_remaining.days)

                    return VipStatus(
                        is_vip=True,
                        plan_type=subscription.get("plan_type", "premium"),
                        status=subscription.get("status", "active"),
                        start_date=subscription.get("start_date"),
                        end_date=subscription.get("end_date"),
                        days_remaining=days_remaining,
                        auto_renew=subscription.get("auto_renew", False),
                        metadata={
                            "subscription_id": subscription.get("subscription_id"),
                            "created_at": subscription.get("created_at"),
                            "last_renewed": subscription.get("last_renewed")
                        }
                    )

            # No active subscription found
            return VipStatus(
                is_vip=False,
                plan_type="free",
                status="inactive"
            )

        except Exception as e:
            self.logger.error(
                "Error checking VIP status",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )

            # Return safe default status
            return VipStatus(
                is_vip=False,
                plan_type="free",
                status="error",
                metadata={"error": str(e)}
            )

    async def upgrade_subscription(self, user_id: str, new_plan: SubscriptionPlan) -> bool:
        """
        Upgrade user subscription to a higher plan

        Args:
            user_id: User identifier
            new_plan: New subscription plan

        Returns:
            True if upgrade successful
        """
        try:
            self.logger.info(
                "Upgrading subscription",
                user_id=user_id,
                new_plan=new_plan.value
            )

            # Use the underlying subscription service
            success = await self.subscription_service.upgrade_subscription(
                user_id=user_id,
                new_plan=new_plan,
                event_bus=self.event_bus
            )

            if success:
                # Update user VIP status
                subscription = await self.subscription_service.get_subscription(user_id)
                if subscription:
                    await self._update_user_vip_status(
                        user_id=user_id,
                        is_vip=True,
                        plan_type=new_plan.value,
                        end_date=subscription.get("end_date")
                    )

                # Log the upgrade
                await self._log_subscription_event(
                    user_id=user_id,
                    action="upgraded",
                    plan_type=new_plan.value,
                    metadata={"upgraded_to": new_plan.value}
                )

                self.logger.info(
                    "Subscription upgraded successfully",
                    user_id=user_id,
                    new_plan=new_plan.value
                )

            return success

        except Exception as e:
            self.logger.error(
                "Error upgrading subscription",
                user_id=user_id,
                new_plan=new_plan.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def cancel_subscription(self, user_id: str, immediate: bool = False) -> bool:
        """
        Cancel user subscription

        Args:
            user_id: User identifier
            immediate: Whether to cancel immediately or at end of period

        Returns:
            True if cancellation successful
        """
        try:
            self.logger.info(
                "Cancelling subscription",
                user_id=user_id,
                immediate=immediate
            )

            # Use underlying subscription service
            success = await self.subscription_service.cancel_subscription(user_id)

            if success:
                if immediate:
                    # Immediately update user VIP status
                    await self._update_user_vip_status(user_id, False, "free", None)

                # Log the cancellation
                await self._log_subscription_event(
                    user_id=user_id,
                    action="cancelled",
                    plan_type="cancelled",
                    metadata={"immediate": immediate}
                )

                self.logger.info(
                    "Subscription cancelled successfully",
                    user_id=user_id,
                    immediate=immediate
                )

            return success

        except Exception as e:
            self.logger.error(
                "Error cancelling subscription",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def process_expiration(self) -> List[ExpiredSubscription]:
        """
        Process expired subscriptions (to be called by cron job)

        Implements requirement 3.2: Subscription expiration processing

        Returns:
            List of expired subscriptions that were processed
        """
        try:
            self.logger.info("Processing subscription expirations")

            current_time = datetime.utcnow()
            expired_subscriptions = []

            # Find subscriptions that have expired
            cursor = self.subscriptions_collection.find({
                "status": SubscriptionStatus.ACTIVE.value,
                "end_date": {"$lte": current_time}
            })

            processed_count = 0
            async for subscription_doc in cursor:
                user_id = subscription_doc["user_id"]
                subscription_id = subscription_doc.get("subscription_id", str(subscription_doc["_id"]))

                try:
                    # Update subscription status to expired
                    await self.subscription_service.update_subscription_status(
                        user_id=user_id,
                        new_status=SubscriptionStatus.EXPIRED,
                        event_bus=self.event_bus
                    )

                    # Update user VIP status
                    await self._update_user_vip_status(user_id, False, "free", None)

                    # Create expired subscription record
                    expired_sub = ExpiredSubscription(
                        user_id=user_id,
                        subscription_id=subscription_id,
                        plan_type=subscription_doc["plan_type"],
                        expired_at=subscription_doc["end_date"]
                    )
                    expired_subscriptions.append(expired_sub)

                    # Log the expiration
                    await self._log_subscription_event(
                        user_id=user_id,
                        action="expired",
                        plan_type=subscription_doc["plan_type"],
                        metadata={
                            "subscription_id": subscription_id,
                            "expired_at": subscription_doc["end_date"].isoformat()
                        }
                    )

                    # Publish subscription expired event
                    await self._publish_expiration_event(user_id, subscription_doc)

                    processed_count += 1

                    self.logger.info(
                        "Subscription expired and processed",
                        user_id=user_id,
                        subscription_id=subscription_id,
                        plan_type=subscription_doc["plan_type"]
                    )

                except Exception as e:
                    self.logger.error(
                        "Error processing individual expired subscription",
                        user_id=user_id,
                        subscription_id=subscription_id,
                        error=str(e)
                    )

            self.logger.info(
                "Subscription expiration processing completed",
                processed_count=processed_count,
                total_expired=len(expired_subscriptions)
            )

            return expired_subscriptions

        except Exception as e:
            self.logger.error(
                "Error processing subscription expirations",
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def renew_subscription(self, user_id: str, duration_days: int = 30) -> bool:
        """
        Renew an existing subscription

        Args:
            user_id: User identifier
            duration_days: Duration to add in days

        Returns:
            True if renewal successful
        """
        try:
            self.logger.info(
                "Renewing subscription",
                user_id=user_id,
                duration_days=duration_days
            )

            # Get current subscription
            current_sub = await self.subscription_service.get_subscription(user_id)
            if not current_sub:
                self.logger.error("No subscription found to renew", user_id=user_id)
                return False

            # Calculate new end date
            current_end = current_sub.get("end_date", datetime.utcnow())
            if isinstance(current_end, str):
                current_end = datetime.fromisoformat(current_end)

            # If subscription is already expired, start from now
            if current_end < datetime.utcnow():
                new_end_date = datetime.utcnow() + timedelta(days=duration_days)
            else:
                new_end_date = current_end + timedelta(days=duration_days)

            # Update subscription
            update_data = {
                "end_date": new_end_date,
                "status": SubscriptionStatus.ACTIVE.value,
                "last_renewed": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await self.subscriptions_collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                # Update user VIP status
                await self._update_user_vip_status(
                    user_id=user_id,
                    is_vip=True,
                    plan_type=current_sub["plan_type"],
                    end_date=new_end_date
                )

                # Log the renewal
                await self._log_subscription_event(
                    user_id=user_id,
                    action="renewed",
                    plan_type=current_sub["plan_type"],
                    metadata={
                        "duration_days": duration_days,
                        "new_end_date": new_end_date.isoformat()
                    }
                )

                # Publish renewal event
                event = SubscriptionUpdatedEvent(
                    user_id=user_id,
                    old_status=current_sub.get("status", "unknown"),
                    new_status=SubscriptionStatus.ACTIVE.value,
                    plan_type=current_sub["plan_type"]
                )
                await self.event_bus.publish("subscription_renewed", event)

                self.logger.info(
                    "Subscription renewed successfully",
                    user_id=user_id,
                    new_end_date=new_end_date
                )
                return True
            else:
                self.logger.error("Failed to update subscription for renewal", user_id=user_id)
                return False

        except Exception as e:
            self.logger.error(
                "Error renewing subscription",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def get_subscription_stats(self) -> Dict[str, int]:
        """
        Get subscription statistics

        Returns:
            Dictionary with subscription statistics
        """
        try:
            stats = {}

            # Count active subscriptions by plan
            for plan in SubscriptionPlan:
                count = await self.subscriptions_collection.count_documents({
                    "plan_type": plan.value,
                    "status": SubscriptionStatus.ACTIVE.value
                })
                stats[f"active_{plan.value}"] = count

            # Count expired subscriptions
            stats["expired"] = await self.subscriptions_collection.count_documents({
                "status": SubscriptionStatus.EXPIRED.value
            })

            # Count cancelled subscriptions
            stats["cancelled"] = await self.subscriptions_collection.count_documents({
                "status": SubscriptionStatus.CANCELLED.value
            })

            # Total active VIP users
            stats["total_vip"] = await self.subscriptions_collection.count_documents({
                "status": SubscriptionStatus.ACTIVE.value,
                "plan_type": {"$ne": SubscriptionPlan.FREE.value}
            })

            return stats

        except Exception as e:
            self.logger.error(
                "Error getting subscription stats",
                error=str(e),
                error_type=type(e).__name__
            )
            return {}

    async def _update_user_vip_status(self, user_id: str, is_vip: bool,
                                    plan_type: str, end_date: Optional[datetime]) -> None:
        """
        Update user document with VIP status

        Args:
            user_id: User identifier
            is_vip: Whether user has VIP status
            plan_type: Type of plan
            end_date: Subscription end date
        """
        try:
            update_data = {
                "vip_status": {
                    "is_vip": is_vip,
                    "plan_type": plan_type,
                    "end_date": end_date,
                    "last_updated": datetime.utcnow()
                },
                "updated_at": datetime.utcnow()
            }

            await self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": update_data},
                upsert=True
            )

        except Exception as e:
            self.logger.error(
                "Error updating user VIP status",
                user_id=user_id,
                is_vip=is_vip,
                error=str(e)
            )

    async def _log_subscription_event(self, user_id: str, action: str, plan_type: str,
                                    metadata: Dict[str, Any]) -> None:
        """
        Log subscription event to history

        Args:
            user_id: User identifier
            action: Action performed
            plan_type: Plan type
            metadata: Additional metadata
        """
        try:
            event_doc = {
                "user_id": user_id,
                "action": action,
                "plan_type": plan_type,
                "timestamp": datetime.utcnow(),
                "metadata": metadata
            }

            await self.subscription_history_collection.insert_one(event_doc)

        except Exception as e:
            self.logger.error(
                "Error logging subscription event",
                user_id=user_id,
                action=action,
                error=str(e)
            )

    async def _publish_expiration_event(self, user_id: str, subscription_doc: Dict[str, Any]) -> None:
        """
        Publish subscription expiration event

        Args:
            user_id: User identifier
            subscription_doc: Subscription document
        """
        try:
            event = SubscriptionUpdatedEvent(
                user_id=user_id,
                old_status=SubscriptionStatus.ACTIVE.value,
                new_status=SubscriptionStatus.EXPIRED.value,
                plan_type=subscription_doc["plan_type"]
            )

            await self.event_bus.publish("subscription_expired", event)

            self.logger.debug(
                "Subscription expiration event published",
                user_id=user_id,
                plan_type=subscription_doc["plan_type"]
            )

        except Exception as e:
            self.logger.error(
                "Error publishing subscription expiration event",
                user_id=user_id,
                error=str(e)
            )
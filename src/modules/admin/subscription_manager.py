# src/modules/admin/subscription_manager.py

from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from pymongo.database import Database

from src.events.bus import EventBus
from src.events.models import create_event

class Subscription(BaseModel):
    id: str
    user_id: str
    plan_type: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str

class VipStatus(BaseModel):
    is_vip: bool
    plan_type: Optional[str] = None
    end_date: Optional[datetime] = None

class ExpiredSubscription(BaseModel):
    user_id: str
    subscription_id: str

class SubscriptionManager:
    def __init__(self, db: Database, event_bus: EventBus):
        self.db = db
        self.subscriptions = self.db["subscriptions"]
        self.event_bus = event_bus

    async def create_subscription(self, user_id: str, plan_type: str, duration_days: Optional[int] = None) -> Subscription:
        """Creates a new subscription for a user."""
        start_date = datetime.utcnow()
        end_date = None
        if duration_days:
            end_date = start_date + timedelta(days=duration_days)

        subscription_data = {
            "user_id": user_id,
            "plan_type": plan_type,
            "start_date": start_date,
            "end_date": end_date,
            "status": "active"
        }
        result = await self.subscriptions.insert_one(subscription_data)
        
        event = create_event(
            "subscription_updated",
            user_id=user_id,
            plan_type=plan_type,
            status="active",
            start_date=start_date,
            end_date=end_date,
        )
        await self.event_bus.publish(event)
        
        return Subscription(id=str(result.inserted_id), **subscription_data)

    async def check_vip_status(self, user_id: str) -> VipStatus:
        """Checks if a user has an active VIP subscription."""
        now = datetime.utcnow()
        subscription = await self.subscriptions.find_one({
            "user_id": user_id,
            "status": "active",
        })

        if subscription:
            if subscription.get("end_date") and subscription["end_date"] < now:
                await self.subscriptions.update_one(
                    {"_id": subscription["_id"]},
                    {"$set": {"status": "expired"}}
                )
                return VipStatus(is_vip=False)

            if subscription["plan_type"] == "vip":
                return VipStatus(
                    is_vip=True,
                    plan_type=subscription["plan_type"],
                    end_date=subscription["end_date"]
                )

        return VipStatus(is_vip=False)

    async def process_expiration(self) -> List[ExpiredSubscription]:
        """Processes expired subscriptions and updates their status."""
        now = datetime.utcnow()
        expired_subs = []
        cursor = self.subscriptions.find({
            "status": "active",
            "end_date": {"$lt": now}
        })
        async for sub in cursor:
            await self.subscriptions.update_one(
                {"_id": sub["_id"]},
                {"$set": {"status": "expired"}}
            )
            expired_subs.append(ExpiredSubscription(user_id=sub["user_id"], subscription_id=str(sub["_id"])))
            
            event = create_event(
                "subscription_updated",
                user_id=sub["user_id"],
                plan_type=sub["plan_type"],
                status="expired",
                start_date=sub["start_date"],
                end_date=sub["end_date"],
            )
            await self.event_bus.publish(event)

        return expired_subs

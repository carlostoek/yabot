# src/modules/gamification/daily_gift.py

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel
import redis.asyncio as redis

from src.events.bus import EventBus
from src.events.models import DailyGiftClaimedEvent, create_event

class GiftStatus(BaseModel):
    can_claim: bool
    cooldown_remaining: Optional[int] = None

class GiftResult(BaseModel):
    success: bool
    message: str
    gift_claimed: Optional[dict] = None

class DailyGiftSystem:
    def __init__(self, redis_client: redis.Redis, event_bus: EventBus):
        self.redis = redis_client
        self.event_bus = event_bus
        self.cooldown_seconds = 86400  # 24 hours

    async def check_gift_availability(self, user_id: str) -> GiftStatus:
        """Checks if a user can claim their daily gift."""
        key = f"gift:{user_id}:cooldown"
        ttl = await self.redis.ttl(key)
        if ttl > 0:
            return GiftStatus(can_claim=False, cooldown_remaining=ttl)
        return GiftStatus(can_claim=True)

    async def claim_daily_gift(self, user_id: str) -> GiftResult:
        """Allows a user to claim their daily gift."""
        status = await self.check_gift_availability(user_id)
        if not status.can_claim:
            return GiftResult(success=False, message="Ya has reclamado tu regalo diario. Intenta de nuevo más tarde.")

        key = f"gift:{user_id}:cooldown"
        await self.redis.setex(key, self.cooldown_seconds, "claimed")

        # Define the gift (e.g., some besitos)
        gift_amount = 10
        gift_type = "besitos"

        event = create_event(
            "daily_gift_claimed",
            user_id=user_id,
            gift_type=gift_type,
            gift_amount=gift_amount,
        )
        await self.event_bus.publish("daily_gift_claimed", event.dict())

        return GiftResult(
            success=True,
            message="¡Has reclamado tu regalo diario!",
            gift_claimed={"type": gift_type, "amount": gift_amount},
        )

    async def reset_daily_cooldowns(self) -> List[str]:
        """Resets all daily gift cooldowns. Intended for admin use."""
        keys_to_delete = []
        async for key in self.redis.scan_iter("gift:*:cooldown"):
            keys_to_delete.append(key)
        
        if keys_to_delete:
            await self.redis.delete(*keys_to_delete)
            
        return [key.decode('utf-8') for key in keys_to_delete]

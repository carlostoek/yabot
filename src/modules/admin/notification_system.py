# src/modules/admin/notification_system.py

from datetime import datetime, timedelta
from typing import Dict, Any
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NotificationSystem:
    def __init__(self, bot: Bot, scheduler: AsyncIOScheduler, event_bus: EventBus):
        self.bot = bot
        self.scheduler = scheduler
        self.event_bus = event_bus

    async def initialize(self) -> bool:
        """Initialize the notification system and subscribe to events.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Subscribe to events that might trigger notifications
            # For example, system alerts, user milestones, etc.
            
            logger.info("NotificationSystem initialized and subscribed to events")
            return True
            
        except Exception as e:
            logger.error("Error initializing notification system: %s", str(e))
            return False

    async def send_message(self, user_id: str, template: str, context: Dict) -> bool:
        """Sends a message to a user using a template."""
        try:
            message_text = template.format(**context)
            await self.bot.send_message(chat_id=user_id, text=message_text)
            
            event = create_event(
                "notification_sent",
                user_id=user_id,
                channel_id=user_id, # For user messages, channel_id is user_id
                status="sent",
                content=message_text
            )
            await self.event_bus.publish("notification_sent", event.dict())
            return True
        except Exception as e:
            message_text = template.format(**context)
            event = create_event(
                "notification_sent",
                user_id=user_id,
                channel_id=user_id,
                status="failed",
                content=message_text,
                error=str(e)
            )
            await self.event_bus.publish("notification_sent", event.dict())
            return False

    async def schedule_message(self, user_id: str, template: str, context: Dict, delay_seconds: int) -> bool:
        """Schedules a message to be sent to a user after a delay."""
        
        async def job():
            await self.send_message(user_id, template, context)

        run_date = datetime.now() + timedelta(seconds=delay_seconds)
        self.scheduler.add_job(job, 'date', run_date=run_date)
        return True

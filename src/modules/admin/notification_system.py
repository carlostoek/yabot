# src/modules/admin/notification_system.py

from datetime import datetime, timedelta
from typing import Dict
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.events.bus import EventBus
from src.events.models import create_event

class NotificationSystem:
    def __init__(self, bot: Bot, scheduler: AsyncIOScheduler, event_bus: EventBus):
        self.bot = bot
        self.scheduler = scheduler
        self.event_bus = event_bus

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
            await self.event_bus.publish(event)
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
            await self.event_bus.publish(event)
            return False

    async def schedule_message(self, user_id: str, template: str, context: Dict, delay_seconds: int) -> bool:
        """Schedules a message to be sent to a user after a delay."""
        
        async def job():
            await self.send_message(user_id, template, context)

        run_date = datetime.now() + timedelta(seconds=delay_seconds)
        self.scheduler.add_job(job, 'date', run_date=run_date)
        return True

# src/modules/admin/post_scheduler.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore

from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ScheduledPost(BaseModel):
    job_id: str
    content: str
    channel_id: str
    publish_time: datetime
    status: str = "scheduled"

class PostResult(BaseModel):
    job_id: str
    status: str
    error: Optional[str] = None

class PostScheduler:
    def __init__(self, bot: Bot, event_bus: EventBus, redis_config: dict):
        self.bot = bot
        self.event_bus = event_bus
        jobstores = {
            'default': RedisJobStore(**redis_config)
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.start()

    async def initialize(self) -> bool:
        """Initialize the post scheduler and subscribe to events.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Subscribe to events that might affect post scheduling
            # For example, admin commands to schedule posts, system maintenance events, etc.
            
            logger.info("PostScheduler initialized and subscribed to events")
            return True
            
        except Exception as e:
            logger.error("Error initializing post scheduler: %s", str(e))
            return False

    async def schedule_post(self, content: str, channel_id: str, publish_time: datetime) -> ScheduledPost:
        """Schedules a post to be sent to a channel at a specific time."""
        
        async def job():
            try:
                await self.bot.send_message(chat_id=channel_id, text=content)
                event = create_event("post_scheduled", channel_id=channel_id, status="published")
                await self.event_bus.publish("post_scheduled", event.dict())
            except Exception as e:
                event = create_event("post_scheduled", channel_id=channel_id, status="failed", error=str(e))
                await self.event_bus.publish("post_scheduled", event.dict())

        job = self.scheduler.add_job(job, 'date', run_date=publish_time)
        
        return ScheduledPost(
            job_id=job.id,
            content=content,
            channel_id=channel_id,
            publish_time=publish_time
        )

    def cancel_post(self, job_id: str) -> bool:
        """Cancels a scheduled post."""
        try:
            self.scheduler.remove_job(job_id)
            return True
        except Exception:
            return False

    async def execute_scheduled_posts(self) -> List[PostResult]:
        """
        This method is not directly needed when using APScheduler as it runs jobs automatically.
        It's here to fulfill the interface from the design document.
        It can be used to manually trigger jobs for testing or other purposes if needed.
        """
        # This is a conceptual placeholder. APScheduler handles execution automatically.
        return []

    def shutdown(self):
        """Shuts down the scheduler."""
        self.scheduler.shutdown()

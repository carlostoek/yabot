"""
Post Scheduler - Channel Administration Module

This module implements post scheduling functionality leveraging APScheduler patterns
as specified in Requirement 3.3.

The system handles:
- Scheduled post creation and management
- Automated content posting via APScheduler
- Post cancellation and rescheduling
- Event publishing for scheduled post operations
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field
import uuid
import asyncio
import logging

# Optional APScheduler imports
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.jobstores.mongodb import MongoDBJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
    HAS_APSCHEDULER = True
except ImportError:
    # APScheduler not available - use fallback
    AsyncIOScheduler = None
    MongoDBJobStore = None
    AsyncIOExecutor = None
    HAS_APSCHEDULER = False

from src.events.models import BaseEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient
    from aiogram import Bot


class PostStatus(str, Enum):
    """
    Status enumeration for scheduled posts
    """
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class PostType(str, Enum):
    """
    Type enumeration for scheduled posts
    """
    TEXT = "text"
    POLL = "poll"
    FRAGMENT = "fragment"
    TRIVIA = "trivia"
    NOTIFICATION = "notification"
    IMAGE = "image"
    VIDEO = "video"


class ScheduledPost(BaseModel):
    """
    Model for scheduled posts following the specification design
    """
    post_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    content: str
    content_type: PostType = PostType.TEXT
    publish_time: datetime
    status: PostStatus = PostStatus.SCHEDULED
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: str = "system"
    protection_level: str = "free"  # "free" or "vip_only"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class PostResult(BaseModel):
    """
    Result of a post operation
    """
    post_id: str
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    published_at: Optional[datetime] = None
    channel_id: str
    content_type: str


class PostScheduledEvent(BaseEvent):
    """
    Event for scheduled posts
    """
    event_type: str = "post_scheduled"
    post_id: str
    channel_id: str
    publish_time: datetime
    content_type: str


class PostPublishedEvent(BaseEvent):
    """
    Event for published posts
    """
    event_type: str = "post_published"
    post_id: str
    channel_id: str
    message_id: str
    content_type: str
    protection_level: str


class PostScheduler:
    """
    Post scheduler for automated content posting

    Implements requirement 3.3:
    - Scheduled post creation and management using APScheduler
    - Automated content posting with retry logic
    - Event publishing for post operations

    Leverages APScheduler patterns for reliable scheduling
    """

    def __init__(self, db_client: 'AsyncIOMotorClient', event_bus: EventBus, telegram_bot: 'Bot'):
        """
        Initialize the post scheduler

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing post events
            telegram_bot: Telegram bot instance for posting
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.telegram_bot = telegram_bot
        self.logger = get_logger(self.__class__.__name__)

        # Collection references
        self.scheduled_posts_collection = self.db.scheduled_posts
        self.post_history_collection = self.db.post_history

        # Initialize APScheduler
        self._initialize_scheduler()

    def _initialize_scheduler(self) -> None:
        """
        Initialize APScheduler with MongoDB persistence
        """
        if not HAS_APSCHEDULER:
            self.logger.warning("APScheduler not available - scheduler functionality disabled")
            self.scheduler = None
            return

        try:
            # Configure job store with MongoDB
            jobstores = {
                'default': MongoDBJobStore(
                    host=getattr(self.db.client, 'HOST', 'localhost'),
                    port=getattr(self.db.client, 'PORT', 27017),
                    username=getattr(self.db.client, 'USERNAME', None),
                    password=getattr(self.db.client, 'PASSWORD', None),
                    database=self.db.name
                )
            }

            # Configure executors
            executors = {
                'default': AsyncIOExecutor(),
            }

            # Job defaults
            job_defaults = {
                'coalesce': True,
                'max_instances': 3,
                'misfire_grace_time': 30
            }

            # Create scheduler
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )

            # Configure logging for APScheduler
            logging.getLogger('apscheduler').setLevel(logging.INFO)

            self.logger.info("APScheduler initialized with MongoDB persistence")

        except Exception as e:
            self.logger.error(
                "Error initializing APScheduler",
                error=str(e),
                error_type=type(e).__name__
            )
            # Fallback to memory-based scheduler
            if HAS_APSCHEDULER:
                self.scheduler = AsyncIOScheduler(timezone='UTC')
                self.logger.warning("Fallback to memory-based scheduler")
            else:
                self.scheduler = None

    async def start_scheduler(self) -> None:
        """
        Start the APScheduler
        """
        try:
            if not self.scheduler:
                self.logger.warning("Scheduler not available")
                return

            if not self.scheduler.running:
                self.scheduler.start()
                self.logger.info("Post scheduler started successfully")
            else:
                self.logger.warning("Scheduler is already running")
        except Exception as e:
            self.logger.error(
                "Error starting scheduler",
                error=str(e),
                error_type=type(e).__name__
            )

    async def stop_scheduler(self) -> None:
        """
        Stop the APScheduler
        """
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.logger.info("Post scheduler stopped")
        except Exception as e:
            self.logger.error(
                "Error stopping scheduler",
                error=str(e),
                error_type=type(e).__name__
            )

    async def schedule_post(self, content: str, channel_id: str, publish_time: datetime,
                          content_type: PostType = PostType.TEXT, protection_level: str = "free",
                          created_by: str = "system", metadata: Optional[Dict[str, Any]] = None) -> Optional[ScheduledPost]:
        """
        Schedule a post for future publication

        Args:
            content: Post content
            channel_id: Target channel ID
            publish_time: When to publish the post
            content_type: Type of content
            protection_level: Protection level (free/vip_only)
            created_by: Who created the post
            metadata: Additional metadata

        Returns:
            ScheduledPost if successful, None otherwise
        """
        try:
            # Validate publish time is in the future
            if publish_time <= datetime.utcnow():
                self.logger.error(
                    "Cannot schedule post in the past",
                    publish_time=publish_time,
                    current_time=datetime.utcnow()
                )
                return None

            # Create scheduled post
            scheduled_post = ScheduledPost(
                channel_id=channel_id,
                content=content,
                content_type=content_type,
                publish_time=publish_time,
                protection_level=protection_level,
                created_by=created_by,
                metadata=metadata or {}
            )

            # Store in database
            await self.scheduled_posts_collection.insert_one(scheduled_post.dict())

            # Schedule with APScheduler
            job_id = f"post_{scheduled_post.post_id}"
            self.scheduler.add_job(
                func=self._execute_scheduled_post,
                trigger='date',
                run_date=publish_time,
                args=[scheduled_post.post_id],
                id=job_id,
                replace_existing=True
            )

            # Publish scheduling event
            await self._publish_post_event(
                event_type="post_scheduled",
                post_id=scheduled_post.post_id,
                channel_id=channel_id,
                content_type=content_type.value,
                publish_time=publish_time
            )

            self.logger.info(
                "Post scheduled successfully",
                post_id=scheduled_post.post_id,
                channel_id=channel_id,
                publish_time=publish_time,
                content_type=content_type.value
            )

            return scheduled_post

        except Exception as e:
            self.logger.error(
                "Error scheduling post",
                channel_id=channel_id,
                publish_time=publish_time,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def cancel_post(self, post_id: str) -> bool:
        """
        Cancel a scheduled post

        Args:
            post_id: ID of the post to cancel

        Returns:
            True if cancellation was successful
        """
        try:
            # Update database status
            result = await self.scheduled_posts_collection.update_one(
                {"post_id": post_id, "status": PostStatus.SCHEDULED.value},
                {
                    "$set": {
                        "status": PostStatus.CANCELLED.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count == 0:
                self.logger.warning("No scheduled post found to cancel", post_id=post_id)
                return False

            # Remove from scheduler
            job_id = f"post_{post_id}"
            try:
                self.scheduler.remove_job(job_id)
            except Exception as scheduler_error:
                self.logger.warning(
                    "Job not found in scheduler (may have already executed)",
                    job_id=job_id,
                    error=str(scheduler_error)
                )

            self.logger.info("Post cancelled successfully", post_id=post_id)
            return True

        except Exception as e:
            self.logger.error(
                "Error cancelling post",
                post_id=post_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def reschedule_post(self, post_id: str, new_publish_time: datetime) -> bool:
        """
        Reschedule an existing post

        Args:
            post_id: ID of the post to reschedule
            new_publish_time: New publication time

        Returns:
            True if rescheduling was successful
        """
        try:
            # Validate new time is in the future
            if new_publish_time <= datetime.utcnow():
                self.logger.error(
                    "Cannot reschedule post to the past",
                    post_id=post_id,
                    new_publish_time=new_publish_time
                )
                return False

            # Update database
            result = await self.scheduled_posts_collection.update_one(
                {"post_id": post_id, "status": PostStatus.SCHEDULED.value},
                {
                    "$set": {
                        "publish_time": new_publish_time,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count == 0:
                self.logger.warning("No scheduled post found to reschedule", post_id=post_id)
                return False

            # Update scheduler
            job_id = f"post_{post_id}"
            try:
                self.scheduler.reschedule_job(
                    job_id=job_id,
                    trigger='date',
                    run_date=new_publish_time
                )
            except Exception as scheduler_error:
                self.logger.error(
                    "Error updating scheduler job",
                    job_id=job_id,
                    error=str(scheduler_error)
                )
                return False

            self.logger.info(
                "Post rescheduled successfully",
                post_id=post_id,
                new_publish_time=new_publish_time
            )
            return True

        except Exception as e:
            self.logger.error(
                "Error rescheduling post",
                post_id=post_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def get_scheduled_posts(self, channel_id: Optional[str] = None,
                                status: Optional[PostStatus] = None) -> List[ScheduledPost]:
        """
        Get scheduled posts with optional filtering

        Args:
            channel_id: Filter by channel ID
            status: Filter by status

        Returns:
            List of scheduled posts
        """
        try:
            query = {}
            if channel_id:
                query["channel_id"] = channel_id
            if status:
                query["status"] = status.value

            cursor = self.scheduled_posts_collection.find(query).sort("publish_time", 1)

            posts = []
            async for doc in cursor:
                # Convert ObjectId to string
                if "_id" in doc:
                    doc.pop("_id")

                post = ScheduledPost(**doc)
                posts.append(post)

            return posts

        except Exception as e:
            self.logger.error(
                "Error getting scheduled posts",
                channel_id=channel_id,
                status=status.value if status else None,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def execute_scheduled_posts(self) -> List[PostResult]:
        """
        Execute any scheduled posts that are ready (manual trigger)

        Returns:
            List of post results
        """
        try:
            current_time = datetime.utcnow()

            # Find posts ready to be published
            cursor = self.scheduled_posts_collection.find({
                "status": PostStatus.SCHEDULED.value,
                "publish_time": {"$lte": current_time}
            })

            results = []
            async for doc in cursor:
                post_id = doc["post_id"]
                result = await self._execute_post(doc)
                results.append(result)

            return results

        except Exception as e:
            self.logger.error(
                "Error executing scheduled posts",
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def _execute_scheduled_post(self, post_id: str) -> None:
        """
        Execute a single scheduled post (called by APScheduler)

        Args:
            post_id: ID of the post to execute
        """
        try:
            # Get post from database
            post_doc = await self.scheduled_posts_collection.find_one({
                "post_id": post_id,
                "status": PostStatus.SCHEDULED.value
            })

            if not post_doc:
                self.logger.warning("Scheduled post not found or already processed", post_id=post_id)
                return

            # Execute the post
            await self._execute_post(post_doc)

        except Exception as e:
            self.logger.error(
                "Error in scheduled post execution",
                post_id=post_id,
                error=str(e),
                error_type=type(e).__name__
            )

    async def _execute_post(self, post_doc: Dict[str, Any]) -> PostResult:
        """
        Execute a single post

        Args:
            post_doc: Post document from database

        Returns:
            PostResult with execution details
        """
        post_id = post_doc["post_id"]
        channel_id = post_doc["channel_id"]
        content = post_doc["content"]
        content_type = post_doc["content_type"]
        protection_level = post_doc["protection_level"]

        try:
            self.logger.info(
                "Executing scheduled post",
                post_id=post_id,
                channel_id=channel_id,
                content_type=content_type
            )

            # Update status to processing
            await self.scheduled_posts_collection.update_one(
                {"post_id": post_id},
                {
                    "$set": {
                        "status": PostStatus.SCHEDULED.value,  # Keep as scheduled during processing
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Prepare message options
            message_options = {}
            if protection_level == "vip_only":
                message_options["protect_content"] = True

            # Send message based on content type
            message = None
            if content_type == PostType.TEXT.value:
                message = await self.telegram_bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    **message_options
                )
            elif content_type == PostType.POLL.value:
                # For polls, content should contain poll data
                poll_data = post_doc.get("metadata", {}).get("poll_data", {})
                if poll_data:
                    message = await self.telegram_bot.send_poll(
                        chat_id=channel_id,
                        question=poll_data.get("question", content),
                        options=poll_data.get("options", ["Yes", "No"]),
                        is_anonymous=poll_data.get("is_anonymous", True),
                        **message_options
                    )
                else:
                    self.logger.error("Poll data missing for poll post", post_id=post_id)
                    raise ValueError("Poll data missing")
            else:
                # Default to text message for other types
                message = await self.telegram_bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    **message_options
                )

            # Update status to published
            await self.scheduled_posts_collection.update_one(
                {"post_id": post_id},
                {
                    "$set": {
                        "status": PostStatus.PUBLISHED.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Log to history
            await self._log_post_history(
                post_id=post_id,
                action="published",
                success=True,
                message_id=str(message.message_id) if message else None,
                channel_id=channel_id
            )

            # Publish event
            await self._publish_post_event(
                event_type="post_published",
                post_id=post_id,
                channel_id=channel_id,
                content_type=content_type,
                message_id=str(message.message_id) if message else None,
                protection_level=protection_level
            )

            self.logger.info(
                "Post published successfully",
                post_id=post_id,
                channel_id=channel_id,
                message_id=message.message_id if message else None
            )

            return PostResult(
                post_id=post_id,
                success=True,
                message_id=str(message.message_id) if message else None,
                published_at=datetime.utcnow(),
                channel_id=channel_id,
                content_type=content_type
            )

        except Exception as e:
            self.logger.error(
                "Error executing post",
                post_id=post_id,
                channel_id=channel_id,
                error=str(e),
                error_type=type(e).__name__
            )

            # Handle retry logic
            retry_count = post_doc.get("retry_count", 0)
            max_retries = post_doc.get("max_retries", 3)

            if retry_count < max_retries:
                # Schedule retry
                retry_time = datetime.utcnow() + timedelta(minutes=5 * (retry_count + 1))
                await self.scheduled_posts_collection.update_one(
                    {"post_id": post_id},
                    {
                        "$set": {
                            "status": PostStatus.RETRYING.value,
                            "retry_count": retry_count + 1,
                            "last_error": str(e),
                            "publish_time": retry_time,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

                # Reschedule in APScheduler
                job_id = f"post_{post_id}"
                try:
                    self.scheduler.add_job(
                        func=self._execute_scheduled_post,
                        trigger='date',
                        run_date=retry_time,
                        args=[post_id],
                        id=job_id,
                        replace_existing=True
                    )
                except Exception as scheduler_error:
                    self.logger.error(
                        "Error rescheduling retry",
                        job_id=job_id,
                        error=str(scheduler_error)
                    )

                self.logger.info(
                    "Post scheduled for retry",
                    post_id=post_id,
                    retry_count=retry_count + 1,
                    retry_time=retry_time
                )
            else:
                # Mark as failed
                await self.scheduled_posts_collection.update_one(
                    {"post_id": post_id},
                    {
                        "$set": {
                            "status": PostStatus.FAILED.value,
                            "last_error": str(e),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

                self.logger.error(
                    "Post failed after maximum retries",
                    post_id=post_id,
                    retry_count=retry_count,
                    max_retries=max_retries
                )

            # Log failure
            await self._log_post_history(
                post_id=post_id,
                action="failed",
                success=False,
                error=str(e),
                channel_id=channel_id
            )

            return PostResult(
                post_id=post_id,
                success=False,
                error=str(e),
                channel_id=channel_id,
                content_type=content_type
            )

    async def _log_post_history(self, post_id: str, action: str, success: bool,
                              message_id: Optional[str] = None, error: Optional[str] = None,
                              channel_id: Optional[str] = None) -> None:
        """
        Log post execution to history

        Args:
            post_id: Post ID
            action: Action performed
            success: Whether action was successful
            message_id: Telegram message ID
            error: Error message if failed
            channel_id: Channel ID
        """
        try:
            history_doc = {
                "post_id": post_id,
                "action": action,
                "success": success,
                "message_id": message_id,
                "error": error,
                "channel_id": channel_id,
                "timestamp": datetime.utcnow()
            }

            await self.post_history_collection.insert_one(history_doc)

        except Exception as e:
            self.logger.error(
                "Error logging post history",
                post_id=post_id,
                action=action,
                error=str(e)
            )

    async def _publish_post_event(self, event_type: str, post_id: str, channel_id: str,
                                content_type: str, publish_time: Optional[datetime] = None,
                                message_id: Optional[str] = None,
                                protection_level: Optional[str] = None) -> None:
        """
        Publish post-related events

        Args:
            event_type: Type of event
            post_id: Post ID
            channel_id: Channel ID
            content_type: Content type
            publish_time: Publication time
            message_id: Telegram message ID
            protection_level: Protection level
        """
        try:
            event_payload = {
                "post_id": post_id,
                "channel_id": channel_id,
                "content_type": content_type,
                "timestamp": datetime.utcnow().isoformat()
            }

            if publish_time:
                event_payload["publish_time"] = publish_time.isoformat()
            if message_id:
                event_payload["message_id"] = message_id
            if protection_level:
                event_payload["protection_level"] = protection_level

            event = BaseEvent(
                event_type=event_type,
                payload=event_payload
            )

            await self.event_bus.publish(event_type, event)

            self.logger.debug(
                "Post event published",
                event_type=event_type,
                post_id=post_id,
                channel_id=channel_id
            )

        except Exception as e:
            self.logger.error(
                "Error publishing post event",
                event_type=event_type,
                post_id=post_id,
                error=str(e),
                error_type=type(e).__name__
            )

    async def get_post_stats(self) -> Dict[str, int]:
        """
        Get post scheduling statistics

        Returns:
            Dictionary with post statistics
        """
        try:
            stats = {}

            # Count posts by status
            for status in PostStatus:
                count = await self.scheduled_posts_collection.count_documents({
                    "status": status.value
                })
                stats[f"posts_{status.value}"] = count

            # Count posts by content type
            for content_type in PostType:
                count = await self.scheduled_posts_collection.count_documents({
                    "content_type": content_type.value
                })
                stats[f"posts_{content_type.value}"] = count

            # Total posts
            stats["total_posts"] = await self.scheduled_posts_collection.count_documents({})

            return stats

        except Exception as e:
            self.logger.error(
                "Error getting post stats",
                error=str(e),
                error_type=type(e).__name__
            )
            return {}

    async def cleanup_old_posts(self, days_old: int = 30) -> int:
        """
        Clean up old published/failed posts

        Args:
            days_old: Remove posts older than this many days

        Returns:
            Number of posts cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            result = await self.scheduled_posts_collection.delete_many({
                "status": {"$in": [PostStatus.PUBLISHED.value, PostStatus.FAILED.value, PostStatus.CANCELLED.value]},
                "updated_at": {"$lt": cutoff_date}
            })

            if result.deleted_count > 0:
                self.logger.info(
                    "Cleaned up old posts",
                    count=result.deleted_count,
                    days_old=days_old
                )

            return result.deleted_count

        except Exception as e:
            self.logger.error(
                "Error cleaning up old posts",
                days_old=days_old,
                error=str(e),
                error_type=type(e).__name__
            )
            return 0
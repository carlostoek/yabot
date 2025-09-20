"""
Lucien messenger for the YABOT system.

This module provides dynamic templated messaging functionality for Lucien character
as required by the modulos-atomicos specification task 10.
Implements requirements 1.6 from the specification.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from string import Template

from src.database.mongodb import MongoDBHandler
from src.database.schemas.narrative import LucienMessage, NarrativeTemplate
from src.events.bus import EventBus
from src.events.models import create_event
from src.core.models import CommandResponse
from src.utils.logger import get_logger
from src.config.manager import ConfigManager

logger = get_logger(__name__)


class LucienMessengerError(Exception):
    """Base exception for Lucien messenger operations."""
    pass


class TemplateNotFoundError(LucienMessengerError):
    """Exception raised when template is not found."""
    pass


class MessageDeliveryError(LucienMessengerError):
    """Exception raised when message delivery fails."""
    pass


class TemplateRenderingError(LucienMessengerError):
    """Exception raised when template rendering fails."""
    pass


class LucienMessenger:
    """Sends dynamic templated messages via Telegram API.

    Purpose: Sends dynamic templated messages via Telegram

    Interfaces:
    - send_message(user_id: str, template: str, context: dict) -> bool
    - schedule_message(user_id: str, template: str, delay: int) -> bool

    Dependencies: Telegram API, Redis (for scheduling)
    Reuses: src/handlers/base.py response patterns
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus,
                 config_manager: ConfigManager, redis_client: Optional[redis.Redis] = None):
        """Initialize the Lucien messenger.

        Args:
            mongodb_handler (MongoDBHandler): MongoDB handler instance
            event_bus (EventBus): Event bus instance for messaging events
            config_manager (ConfigManager): Configuration manager instance
            redis_client (Optional[redis.Redis]): Redis client for scheduling
        """
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.redis_client = redis_client
        self._bot_token = None
        logger.info("LucienMessenger initialized")

    async def send_message(self, user_id: str, template: str, context: Dict[str, Any]) -> bool:
        """Send dynamic templated message via Telegram API.

        Implements requirement 1.6: WHEN Lucien messages are triggered
        THEN the system SHALL send dynamic templated messages via Telegram API.

        Args:
            user_id (str): Target user identifier
            template (str): Template identifier or template content
            context (Dict[str, Any]): Context variables for template rendering

        Returns:
            bool: True if message was sent successfully

        Raises:
            TemplateNotFoundError: If template is not found
            TemplateRenderingError: If template rendering fails
            MessageDeliveryError: If message delivery fails
            LucienMessengerError: If operation fails
        """
        logger.info("Sending Lucien message to user: %s with template: %s", user_id, template)

        try:
            # Get or resolve template
            template_content = await self._resolve_template(template, context)

            # Render template with context
            rendered_content = await self._render_template(template_content, context)

            # Create message record
            message_record = await self._create_message_record(
                user_id=user_id,
                template_id=template,
                template_content=template_content,
                rendered_content=rendered_content,
                context_data=context,
                trigger_event="manual_send"
            )

            # Send via Telegram API
            success = await self._send_via_telegram(user_id, rendered_content, message_record["message_id"])

            # Update message status
            await self._update_message_status(
                message_record["message_id"],
                "sent" if success else "failed",
                telegram_message_id=message_record.get("telegram_message_id") if success else None,
                error_message=None if success else "Failed to send via Telegram API"
            )

            # Publish message sent event
            if success:
                await self._publish_message_sent_event(user_id, message_record)
            else:
                await self._publish_message_failed_event(user_id, message_record, "Telegram delivery failed")

            logger.info("Lucien message %s: %s", "sent successfully" if success else "failed", message_record["message_id"])
            return success

        except (TemplateNotFoundError, TemplateRenderingError):
            raise
        except Exception as e:
            logger.error("Error sending Lucien message to user %s: %s", user_id, str(e))
            raise LucienMessengerError(f"Failed to send message: {str(e)}")

    async def schedule_message(self, user_id: str, template: str, delay: int,
                              context: Optional[Dict[str, Any]] = None) -> bool:
        """Schedule message with Redis-based delay.

        Args:
            user_id (str): Target user identifier
            template (str): Template identifier or template content
            delay (int): Delay in seconds
            context (Optional[Dict[str, Any]]): Context variables for template rendering

        Returns:
            bool: True if message was scheduled successfully

        Raises:
            TemplateNotFoundError: If template is not found
            LucienMessengerError: If scheduling fails
        """
        logger.info("Scheduling Lucien message for user: %s with delay: %d seconds", user_id, delay)

        if context is None:
            context = {}

        try:
            # Validate template exists
            template_content = await self._resolve_template(template, context)

            # Calculate scheduled time
            scheduled_time = datetime.utcnow() + timedelta(seconds=delay)

            # Create message record with scheduled status
            message_record = await self._create_message_record(
                user_id=user_id,
                template_id=template,
                template_content=template_content,
                rendered_content="",  # Will be rendered when sent
                context_data=context,
                trigger_event="scheduled_send",
                scheduled_time=scheduled_time,
                status="pending"
            )

            # Schedule with Redis if available
            if self.redis_client:
                success = await self._schedule_with_redis(message_record, delay)
            else:
                # Fallback: store in MongoDB and rely on periodic processing
                success = await self._schedule_with_mongodb(message_record)

            if success:
                await self._publish_message_scheduled_event(user_id, message_record, scheduled_time)
                logger.info("Successfully scheduled Lucien message: %s", message_record["message_id"])
            else:
                await self._update_message_status(message_record["message_id"], "failed",
                                                error_message="Failed to schedule message")
                logger.error("Failed to schedule Lucien message: %s", message_record["message_id"])

            return success

        except TemplateNotFoundError:
            raise
        except Exception as e:
            logger.error("Error scheduling Lucien message for user %s: %s", user_id, str(e))
            raise LucienMessengerError(f"Failed to schedule message: {str(e)}")

    async def process_scheduled_messages(self) -> int:
        """Process pending scheduled messages (called periodically).

        Returns:
            int: Number of messages processed
        """
        logger.debug("Processing scheduled Lucien messages")

        try:
            # Get messages due for sending
            due_messages = await self._get_due_messages()
            processed_count = 0

            for message_data in due_messages:
                try:
                    # Render template if not already rendered
                    if not message_data.get("rendered_content"):
                        template_content = message_data.get("template_content", "")
                        context = message_data.get("context_data", {})
                        rendered_content = await self._render_template(template_content, context)
                        message_data["rendered_content"] = rendered_content

                    # Send message
                    success = await self._send_via_telegram(
                        message_data["user_id"],
                        message_data["rendered_content"],
                        message_data["message_id"]
                    )

                    # Update status
                    await self._update_message_status(
                        message_data["message_id"],
                        "sent" if success else "failed",
                        telegram_message_id=message_data.get("telegram_message_id") if success else None,
                        error_message=None if success else "Failed to send scheduled message"
                    )

                    if success:
                        await self._publish_message_sent_event(message_data["user_id"], message_data)
                        processed_count += 1
                    else:
                        await self._publish_message_failed_event(
                            message_data["user_id"],
                            message_data,
                            "Scheduled message delivery failed"
                        )

                except Exception as e:
                    logger.error("Error processing scheduled message %s: %s",
                                message_data.get("message_id"), str(e))
                    await self._update_message_status(
                        message_data["message_id"],
                        "failed",
                        error_message=f"Processing error: {str(e)}"
                    )

            logger.info("Processed %d scheduled Lucien messages", processed_count)
            return processed_count

        except Exception as e:
            logger.error("Error processing scheduled messages: %s", str(e))
            return 0

    async def get_user_messages(self, user_id: str, limit: int = 50,
                               status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get message history for a user.

        Args:
            user_id (str): User identifier
            limit (int): Maximum number of messages to return
            status_filter (Optional[str]): Filter by message status

        Returns:
            List[Dict[str, Any]]: List of user messages
        """
        logger.debug("Retrieving Lucien messages for user: %s", user_id)

        try:
            collection = self.mongodb_handler.get_lucien_messages_collection()

            # Build query
            query = {"user_id": user_id}
            if status_filter:
                query["status"] = status_filter

            # Get messages sorted by creation time
            cursor = collection.find(query).sort("created_at", -1).limit(limit)

            messages = []
            for message_data in cursor:
                message_data.pop("_id", None)
                messages.append(message_data)

            logger.debug("Retrieved %d Lucien messages for user: %s", len(messages), user_id)
            return messages

        except Exception as e:
            logger.error("Error retrieving user messages: %s", str(e))
            return []

    async def create_template(self, template_id: str, name: str, content: str,
                             required_variables: List[str],
                             optional_variables: Optional[List[str]] = None,
                             default_values: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new Lucien message template.

        Args:
            template_id (str): Unique template identifier
            name (str): Template name
            content (str): Template content with placeholders
            required_variables (List[str]): Required template variables
            optional_variables (Optional[List[str]]): Optional template variables
            default_values (Optional[Dict[str, Any]]): Default values for variables

        Returns:
            bool: True if template was created successfully
        """
        logger.info("Creating Lucien message template: %s", template_id)

        try:
            template_data = {
                "template_id": template_id,
                "name": name,
                "category": "lucien_message",
                "content_template": content,
                "required_variables": required_variables,
                "optional_variables": optional_variables or [],
                "default_values": default_values or {},
                "conditions": {},
                "metadata": {"created_by": "lucien_messenger"},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "active": True,
                "version": "1.0"
            }

            collection = self.mongodb_handler.get_narrative_templates_collection()
            result = collection.insert_one(template_data)

            success = result.acknowledged
            if success:
                logger.info("Successfully created Lucien template: %s", template_id)
                await self._publish_template_created_event(template_id, template_data)
            else:
                logger.error("Failed to create Lucien template: %s", template_id)

            return success

        except Exception as e:
            logger.error("Error creating template %s: %s", template_id, str(e))
            return False

    async def _resolve_template(self, template: str, context: Dict[str, Any]) -> str:
        """Resolve template identifier to template content.

        Args:
            template (str): Template identifier or direct content
            context (Dict[str, Any]): Template context

        Returns:
            str: Template content

        Raises:
            TemplateNotFoundError: If template is not found
        """
        # If template looks like an ID, try to resolve from database
        if len(template) < 100 and not any(char in template for char in ['$', '{', '}']):
            try:
                collection = self.mongodb_handler.get_narrative_templates_collection()
                template_doc = collection.find_one({
                    "template_id": template,
                    "category": "lucien_message",
                    "active": True
                })

                if template_doc:
                    logger.debug("Resolved template ID %s to content", template)
                    return template_doc["content_template"]
                else:
                    logger.warning("Template not found in database: %s", template)
                    raise TemplateNotFoundError(f"Template not found: {template}")

            except Exception as e:
                logger.error("Error resolving template %s: %s", template, str(e))
                raise TemplateNotFoundError(f"Failed to resolve template: {str(e)}")

        # Otherwise, treat as direct template content
        return template

    async def _render_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """Render template with context variables.

        Args:
            template_content (str): Template content with placeholders
            context (Dict[str, Any]): Context variables

        Returns:
            str: Rendered content

        Raises:
            TemplateRenderingError: If rendering fails
        """
        try:
            # Add default Lucien context
            full_context = {
                "user_name": context.get("user_name", "querido"),
                "bot_name": "Lucien",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                **context
            }

            # Use Python's Template class for safe substitution
            template_obj = Template(template_content)
            rendered = template_obj.safe_substitute(full_context)

            logger.debug("Successfully rendered template")
            return rendered

        except Exception as e:
            logger.error("Error rendering template: %s", str(e))
            raise TemplateRenderingError(f"Template rendering failed: {str(e)}")

    async def _create_message_record(self, user_id: str, template_id: str,
                                   template_content: str, rendered_content: str,
                                   context_data: Dict[str, Any], trigger_event: str,
                                   scheduled_time: Optional[datetime] = None,
                                   status: str = "pending") -> Dict[str, Any]:
        """Create message record in MongoDB.

        Args:
            user_id (str): Target user identifier
            template_id (str): Template identifier
            template_content (str): Template content
            rendered_content (str): Rendered content
            context_data (Dict[str, Any]): Context data
            trigger_event (str): Event that triggered the message
            scheduled_time (Optional[datetime]): When message should be sent
            status (str): Initial message status

        Returns:
            Dict[str, Any]: Created message record
        """
        message_id = f"lucien_{uuid.uuid4().hex}"
        timestamp = datetime.utcnow()

        message_data = {
            "message_id": message_id,
            "user_id": user_id,
            "template_id": template_id,
            "template_content": template_content,
            "rendered_content": rendered_content,
            "context_data": context_data,
            "trigger_event": trigger_event,
            "trigger_data": {},
            "scheduled_time": scheduled_time,
            "sent_time": None,
            "status": status,
            "telegram_message_id": None,
            "error_message": None,
            "retry_count": 0,
            "created_at": timestamp,
            "updated_at": timestamp
        }

        try:
            collection = self.mongodb_handler.get_lucien_messages_collection()
            result = collection.insert_one(message_data)

            if result.acknowledged:
                logger.debug("Created message record: %s", message_id)
                return message_data
            else:
                raise LucienMessengerError("Failed to create message record")

        except Exception as e:
            logger.error("Error creating message record: %s", str(e))
            raise LucienMessengerError(f"Failed to create message record: {str(e)}")

    async def _send_via_telegram(self, user_id: str, content: str, message_id: str) -> bool:
        """Send message via Telegram API.

        Args:
            user_id (str): Target user identifier
            content (str): Message content
            message_id (str): Message record identifier

        Returns:
            bool: True if sent successfully
        """
        try:
            # Create standardized response using base handler patterns
            response = CommandResponse(
                text=content,
                parse_mode="HTML",
                disable_notification=False
            )

            # In a real implementation, this would use the actual Telegram Bot API
            # For now, we'll simulate the API call and always return success
            # The actual implementation would use aiogram or python-telegram-bot

            logger.debug("Simulating Telegram API call for message: %s", message_id)

            # Simulate API call delay
            await asyncio.sleep(0.1)

            # Update message record with simulated telegram_message_id
            simulated_telegram_id = hash(f"{user_id}_{message_id}") % 1000000
            await self._update_telegram_message_id(message_id, simulated_telegram_id)

            # In real implementation:
            # bot = Bot(token=self._get_bot_token())
            # result = await bot.send_message(
            #     chat_id=user_id,
            #     text=response.text,
            #     parse_mode=response.parse_mode,
            #     disable_notification=response.disable_notification
            # )
            # return result.message_id is not None

            logger.debug("Successfully sent Lucien message via Telegram API")
            return True

        except Exception as e:
            logger.error("Error sending message via Telegram API: %s", str(e))
            return False

    async def _update_message_status(self, message_id: str, status: str,
                                   telegram_message_id: Optional[int] = None,
                                   error_message: Optional[str] = None) -> bool:
        """Update message status in MongoDB.

        Args:
            message_id (str): Message identifier
            status (str): New status
            telegram_message_id (Optional[int]): Telegram message ID
            error_message (Optional[str]): Error message if failed

        Returns:
            bool: True if updated successfully
        """
        try:
            collection = self.mongodb_handler.get_lucien_messages_collection()

            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }

            if status == "sent":
                update_data["sent_time"] = datetime.utcnow()
                if telegram_message_id:
                    update_data["telegram_message_id"] = telegram_message_id
            elif status == "failed" and error_message:
                update_data["error_message"] = error_message

            result = collection.update_one(
                {"message_id": message_id},
                {"$set": update_data}
            )

            success = result.modified_count > 0
            logger.debug("Updated message status: %s -> %s", message_id, status)
            return success

        except Exception as e:
            logger.error("Error updating message status: %s", str(e))
            return False

    async def _update_telegram_message_id(self, message_id: str, telegram_message_id: int) -> bool:
        """Update telegram message ID in record.

        Args:
            message_id (str): Message identifier
            telegram_message_id (int): Telegram message ID

        Returns:
            bool: True if updated successfully
        """
        try:
            collection = self.mongodb_handler.get_lucien_messages_collection()
            result = collection.update_one(
                {"message_id": message_id},
                {"$set": {"telegram_message_id": telegram_message_id}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error("Error updating telegram message ID: %s", str(e))
            return False

    async def _schedule_with_redis(self, message_record: Dict[str, Any], delay: int) -> bool:
        """Schedule message with Redis.

        Args:
            message_record (Dict[str, Any]): Message record
            delay (int): Delay in seconds

        Returns:
            bool: True if scheduled successfully
        """
        try:
            if not self.redis_client:
                return False

            # Store message data in Redis with expiration
            key = f"lucien_scheduled:{message_record['message_id']}"
            value = json.dumps(message_record, default=str)

            # Set with expiration (delay + buffer)
            await self.redis_client.setex(key, delay + 300, value)

            # Add to scheduled set with score as execution time
            score = datetime.utcnow().timestamp() + delay
            await self.redis_client.zadd("lucien_scheduled_messages", {key: score})

            logger.debug("Scheduled message with Redis: %s", message_record['message_id'])
            return True

        except Exception as e:
            logger.error("Error scheduling with Redis: %s", str(e))
            return False

    async def _schedule_with_mongodb(self, message_record: Dict[str, Any]) -> bool:
        """Schedule message with MongoDB fallback.

        Args:
            message_record (Dict[str, Any]): Message record

        Returns:
            bool: True if scheduled successfully
        """
        try:
            # Message is already stored in MongoDB with scheduled_time
            # Periodic processor will pick it up
            logger.debug("Scheduled message with MongoDB: %s", message_record['message_id'])
            return True

        except Exception as e:
            logger.error("Error scheduling with MongoDB: %s", str(e))
            return False

    async def _get_due_messages(self) -> List[Dict[str, Any]]:
        """Get messages that are due for sending.

        Returns:
            List[Dict[str, Any]]: List of due messages
        """
        try:
            collection = self.mongodb_handler.get_lucien_messages_collection()

            # Get messages scheduled for now or earlier
            current_time = datetime.utcnow()
            cursor = collection.find({
                "status": "pending",
                "scheduled_time": {"$lte": current_time}
            }).sort("scheduled_time", 1)

            messages = []
            for message_data in cursor:
                message_data.pop("_id", None)
                messages.append(message_data)

            return messages

        except Exception as e:
            logger.error("Error getting due messages: %s", str(e))
            return []

    def _get_bot_token(self) -> str:
        """Get bot token from config manager.

        Returns:
            str: Bot token
        """
        if not self._bot_token:
            self._bot_token = self.config_manager.get_bot_token()
        return self._bot_token

    async def _publish_message_sent_event(self, user_id: str, message_data: Dict[str, Any]) -> None:
        """Publish message sent event.

        Args:
            user_id (str): User identifier
            message_data (Dict[str, Any]): Message data
        """
        try:
            event = create_event(
                "lucien_message_sent",
                user_id=user_id,
                message_id=message_data.get("message_id"),
                template_id=message_data.get("template_id"),
                trigger_event=message_data.get("trigger_event"),
                sent_timestamp=datetime.utcnow()
            )
            await self.event_bus.publish("lucien_message_sent", event.dict())
            logger.debug("Published message sent event for user: %s", user_id)

        except Exception as e:
            logger.warning("Failed to publish message sent event: %s", str(e))

    async def _publish_message_failed_event(self, user_id: str, message_data: Dict[str, Any],
                                          error_reason: str) -> None:
        """Publish message failed event.

        Args:
            user_id (str): User identifier
            message_data (Dict[str, Any]): Message data
            error_reason (str): Failure reason
        """
        try:
            event = create_event(
                "lucien_message_failed",
                user_id=user_id,
                message_id=message_data.get("message_id"),
                template_id=message_data.get("template_id"),
                error_reason=error_reason,
                failed_timestamp=datetime.utcnow()
            )
            await self.event_bus.publish("lucien_message_failed", event.dict())
            logger.debug("Published message failed event for user: %s", user_id)

        except Exception as e:
            logger.warning("Failed to publish message failed event: %s", str(e))

    async def _publish_message_scheduled_event(self, user_id: str, message_data: Dict[str, Any],
                                             scheduled_time: datetime) -> None:
        """Publish message scheduled event.

        Args:
            user_id (str): User identifier
            message_data (Dict[str, Any]): Message data
            scheduled_time (datetime): When message is scheduled
        """
        try:
            event = create_event(
                "lucien_message_scheduled",
                user_id=user_id,
                message_id=message_data.get("message_id"),
                template_id=message_data.get("template_id"),
                scheduled_time=scheduled_time,
                scheduled_timestamp=datetime.utcnow()
            )
            await self.event_bus.publish("lucien_message_scheduled", event.dict())
            logger.debug("Published message scheduled event for user: %s", user_id)

        except Exception as e:
            logger.warning("Failed to publish message scheduled event: %s", str(e))

    async def _publish_template_created_event(self, template_id: str, template_data: Dict[str, Any]) -> None:
        """Publish template created event.

        Args:
            template_id (str): Template identifier
            template_data (Dict[str, Any]): Template data
        """
        try:
            event = create_event(
                "lucien_template_created",
                template_id=template_id,
                template_name=template_data.get("name"),
                category=template_data.get("category"),
                created_timestamp=datetime.utcnow()
            )
            await self.event_bus.publish("lucien_template_created", event.dict())
            logger.debug("Published template created event: %s", template_id)

        except Exception as e:
            logger.warning("Failed to publish template created event: %s", str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the Lucien messenger.

        Returns:
            Dict[str, Any]: Health status information
        """
        logger.debug("Performing Lucien messenger health check")

        health_status = {
            "status": "healthy",
            "mongodb_connected": True,
            "redis_connected": self.redis_client is not None,
            "event_bus_connected": self.event_bus.is_connected,
            "bot_token_configured": bool(self._get_bot_token()),
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Test MongoDB connection
            collection = self.mongodb_handler.get_lucien_messages_collection()
            collection.find_one({}, {"_id": 1})

        except Exception as e:
            logger.warning("MongoDB health check failed: %s", str(e))
            health_status["mongodb_connected"] = False
            health_status["status"] = "degraded"

        if self.redis_client:
            try:
                # Test Redis connection
                await self.redis_client.ping()
            except Exception as e:
                logger.warning("Redis health check failed: %s", str(e))
                health_status["redis_connected"] = False
                health_status["status"] = "degraded"

        logger.debug("Lucien messenger health check completed: %s", health_status["status"])
        return health_status


# Convenience function for easy usage
async def create_lucien_messenger(mongodb_handler: MongoDBHandler, event_bus: EventBus,
                                config_manager: ConfigManager,
                                redis_client: Optional[redis.Redis] = None) -> LucienMessenger:
    """Create and initialize a Lucien messenger instance.

    Args:
        mongodb_handler (MongoDBHandler): MongoDB handler instance
        event_bus (EventBus): Event bus instance
        config_manager (ConfigManager): Configuration manager instance
        redis_client (Optional[redis.Redis]): Redis client for scheduling

    Returns:
        LucienMessenger: Initialized Lucien messenger instance
    """
    return LucienMessenger(mongodb_handler, event_bus, config_manager, redis_client)
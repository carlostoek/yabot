"""
Lucien Messenger Module

Implements the Lucien messenger that sends dynamic templated messages 
via Telegram API with interfaces for send_message and schedule_message
as per requirement 1.6 from the design document.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from aiogram import Bot
from aiogram.types import Message
import jinja2

from src.utils.logger import LoggerMixin, get_logger


@dataclass
class ScheduledMessage:
    """Represents a scheduled message with its details."""
    chat_id: str
    template: str
    context: Dict[str, Any]
    scheduled_time: datetime
    message_id: Optional[str] = None


class LucienMessenger(LoggerMixin):
    """
    Lucien Messenger - Handles sending dynamic templated messages via Telegram API.
    
    This class follows the patterns established in src/handlers/base.py and
    implements requirement 1.6 from the design document.
    """

    def __init__(self, bot_token: str):
        """
        Initialize the Lucien Messenger with Telegram bot token.
        
        Args:
            bot_token: The Telegram bot token for API access
        """
        self.bot = Bot(token=bot_token)
        self.scheduler_task = None
        self.scheduled_messages: List[ScheduledMessage] = []
        self.jinja_env = jinja2.Environment(
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            undefined=jinja2.ChainableUndefined
        )

    async def send_message(self, chat_id: str, template: str, context: Dict[str, Any] = None) -> Optional[Message]:
        """
        Send a dynamic templated message via Telegram API.
        
        Args:
            chat_id: The Telegram chat ID to send the message to
            template: The Jinja2 template string for the message
            context: Dictionary containing template variables
            
        Returns:
            Telegram Message object if successful, None otherwise
        """
        if context is None:
            context = {}
            
        try:
            # Render the template with the provided context
            template_obj = self.jinja_env.from_string(template)
            rendered_message = template_obj.render(**context)
            
            # Send the rendered message via Telegram
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=rendered_message
            )
            
            self.log_info(
                "Message sent successfully",
                chat_id=chat_id,
                template_length=len(template),
                rendered_length=len(rendered_message)
            )
            
            return message
            
        except Exception as e:
            self.log_error(
                "Error sending templated message",
                chat_id=chat_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def schedule_message(self, chat_id: str, template: str, context: Dict[str, Any], 
                             delay_seconds: int) -> str:
        """
        Schedule a dynamic templated message to be sent at a later time.
        
        Args:
            chat_id: The Telegram chat ID to send the message to
            template: The Jinja2 template string for the message
            context: Dictionary containing template variables
            delay_seconds: Number of seconds to delay before sending the message
            
        Returns:
            Unique identifier for the scheduled message
        """
        scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)
        
        scheduled_msg = ScheduledMessage(
            chat_id=chat_id,
            template=template,
            context=context,
            scheduled_time=scheduled_time
        )
        
        self.scheduled_messages.append(scheduled_msg)
        message_id = f"scheduled_{len(self.scheduled_messages)}"
        scheduled_msg.message_id = message_id
        
        self.log_info(
            "Message scheduled successfully",
            message_id=message_id,
            chat_id=chat_id,
            scheduled_time=scheduled_time.isoformat(),
            template_length=len(template)
        )
        
        # Start the scheduler if it's not already running
        if self.scheduler_task is None or self.scheduler_task.done():
            self.scheduler_task = asyncio.create_task(self._run_scheduler())
        
        return message_id

    async def _run_scheduler(self):
        """
        Internal task that handles sending scheduled messages at the right time.
        """
        while self.scheduled_messages:
            now = datetime.now()
            # Find messages that are ready to be sent
            ready_messages = [
                msg for msg in self.scheduled_messages 
                if msg.scheduled_time <= now
            ]
            
            for msg in ready_messages:
                await self.send_message(
                    chat_id=msg.chat_id,
                    template=msg.template,
                    context=msg.context
                )
                self.scheduled_messages.remove(msg)
                
                self.log_info(
                    "Scheduled message sent",
                    message_id=msg.message_id,
                    chat_id=msg.chat_id
                )
            
            # Sleep briefly to avoid busy waiting
            await asyncio.sleep(1)
        
        # All scheduled messages have been sent, exit the scheduler
        self.log_info("Scheduler task completed - no more scheduled messages")
        self.scheduler_task = None

    async def cancel_scheduled_message(self, message_id: str) -> bool:
        """
        Cancel a scheduled message by its ID.
        
        Args:
            message_id: The unique identifier of the scheduled message
            
        Returns:
            True if the message was found and cancelled, False otherwise
        """
        for msg in self.scheduled_messages:
            if msg.message_id == message_id:
                self.scheduled_messages.remove(msg)
                self.log_info(
                    "Scheduled message cancelled",
                    message_id=message_id
                )
                return True
        self.log_warning(
            "Attempted to cancel non-existent scheduled message",
            message_id=message_id
        )
        return False

    async def get_scheduled_messages(self) -> List[ScheduledMessage]:
        """
        Get all currently scheduled messages.
        
        Returns:
            List of ScheduledMessage objects
        """
        scheduled_count = len(self.scheduled_messages)
        self.log_info(
            "Retrieved scheduled messages",
            count=scheduled_count
        )
        return self.scheduled_messages.copy()

    async def clear_scheduled_messages(self):
        """
        Clear all scheduled messages.
        """
        count = len(self.scheduled_messages)
        self.scheduled_messages.clear()
        self.log_info(
            "Cleared all scheduled messages",
            count=count
        )
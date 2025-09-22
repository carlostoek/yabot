"""
Async Message Cleanup Optimization Manager for YABOT.

Enhanced message tracking and management system with async optimization,
batch operations, and intelligent cleanup strategies to ensure optimal
chat experience while respecting Telegram API limits as per REQ-MENU-002.4.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramServerError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from src.utils.cache_manager import CacheManager, cache_manager as global_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Enhanced TTL configuration with optimization strategies
MESSAGE_TTL_CONFIG = {
    'main_menu': -1,  # Never delete (preserved)
    'system_notification': 5,  # 5 seconds
    'error_message': 10,  # 10 seconds
    'success_feedback': 3,  # 3 seconds
    'loading_message': 2,  # 2 seconds
    'temporary_info': 8,  # 8 seconds
    'lucien_response': 6,  # 6 seconds (for standalone responses)
    'callback_response': 4,  # 4 seconds (for callback acknowledgments)
    'admin_notification': 15,  # 15 seconds (admin messages)
    'debug_message': 30,  # 30 seconds (debug information)
    'default': 60,  # Default TTL for other message types
}

# Telegram API rate limiting configuration
TELEGRAM_RATE_LIMITS = {
    'messages_per_second': 30,  # Maximum messages per second
    'messages_per_minute': 20,  # Per chat per minute
    'burst_limit': 100,  # Maximum burst messages
    'retry_delay': 1.0,  # Base retry delay in seconds
    'max_retries': 3,  # Maximum retry attempts
}

# Batch operation configuration
BATCH_CONFIG = {
    'max_batch_size': 20,  # Maximum messages per batch
    'batch_timeout': 2.0,  # Maximum time to wait for batch completion
    'concurrent_batches': 5,  # Maximum concurrent batch operations
    'queue_size_limit': 1000,  # Maximum queue size per chat
}


class CleanupStrategy(str, Enum):
    """Message cleanup strategies for optimization."""
    IMMEDIATE = "immediate"      # Delete immediately
    BATCHED = "batched"         # Batch delete operations
    SCHEDULED = "scheduled"     # Schedule for later deletion
    ADAPTIVE = "adaptive"       # Adapt based on chat activity


class MessagePriority(str, Enum):
    """Message deletion priority levels."""
    CRITICAL = "critical"       # Must be deleted immediately
    HIGH = "high"              # Delete in next batch
    NORMAL = "normal"          # Standard deletion queue
    LOW = "low"               # Background cleanup

@dataclass
class MessageTrackingRecord:
    """Enhanced message tracking record with optimization metadata."""
    chat_id: int
    message_id: int
    message_type: str  # e.g., 'main_menu', 'notification', 'system_message', 'temporary'
    created_at: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = -1  # Time-to-live in seconds. -1 means infinite
    should_delete: bool = True
    is_main_menu: bool = False
    priority: MessagePriority = MessagePriority.NORMAL
    strategy: CleanupStrategy = CleanupStrategy.BATCHED
    retry_count: int = 0
    last_retry: Optional[datetime] = None
    deletion_scheduled: bool = False
    user_context: Optional[Dict[str, Any]] = None

    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        if self.ttl_seconds == -1:
            return False
        expiration_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiration_time

    def can_retry(self) -> bool:
        """Check if message deletion can be retried."""
        return self.retry_count < TELEGRAM_RATE_LIMITS['max_retries']


@dataclass
class BatchOperation:
    """Represents a batch of message deletion operations."""
    chat_id: int
    message_ids: List[int]
    priority: MessagePriority
    created_at: datetime = field(default_factory=datetime.utcnow)
    attempts: int = 0
    max_attempts: int = 3

    def is_ready(self) -> bool:
        """Check if batch is ready for processing."""
        return (
            len(self.message_ids) >= BATCH_CONFIG['max_batch_size'] or
            (datetime.utcnow() - self.created_at).total_seconds() >= BATCH_CONFIG['batch_timeout']
        )


@dataclass
class CleanupMetrics:
    """Performance metrics for message cleanup operations."""
    total_messages_processed: int = 0
    successful_deletions: int = 0
    failed_deletions: int = 0
    batch_operations: int = 0
    average_batch_size: float = 0.0
    rate_limit_hits: int = 0
    total_processing_time: float = 0.0
    last_cleanup: Optional[datetime] = None

    def update_batch_metrics(self, batch_size: int, processing_time: float) -> None:
        """Update batch operation metrics."""
        self.batch_operations += 1
        self.total_processing_time += processing_time

        # Calculate new average batch size
        total_messages = self.average_batch_size * (self.batch_operations - 1) + batch_size
        self.average_batch_size = total_messages / self.batch_operations

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.successful_deletions + self.failed_deletions
        return (self.successful_deletions / total * 100) if total > 0 else 0.0

@dataclass
class MenuNavigationContext:
    """
    Holds the context for a user's navigation session through the menus.
    """
    current_menu_id: str
    navigation_path: List[str]
    user_context: Dict[str, Any]
    session_data: Dict[str, Any]
    main_menu_message_id: Optional[int] = None
    chat_cleanup_enabled: bool = True


class MessageManager:
    """
    Manages chat cleanliness by tracking and automatically deleting system messages.
    This class is designed to be a singleton or managed by a dependency injection container.
    """

    def __init__(self, bot: Bot, cache: CacheManager):
        """
        Initialize the MessageManager.

        Args:
            bot: The aiogram Bot instance.
            cache: The CacheManager instance for Redis operations.
        """
        self.bot = bot
        self.cache = cache
        self.scheduler = AsyncIOScheduler()
        self._initialized = False
        self._metrics = {
            "total_messages_tracked": 0,
            "total_messages_deleted": 0,
            "successful_deletions": 0,
            "failed_deletions": 0,
            "cache_errors": 0,
            "api_errors": 0
        }
        logger.info("MessageManager initialized.")

    async def initialize(self) -> bool:
        """
        Initialize the message manager components.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Connect to cache
            cache_connected = await self.cache.connect()
            if not cache_connected:
                logger.warning("Failed to connect to cache during initialization")
                # Continue initialization but mark cache as disconnected
            
            # Start scheduler
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Scheduler started successfully")
            
            self._initialized = True
            logger.info("MessageManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during MessageManager initialization: {e}")
            self._initialized = False
            return False

    def is_initialized(self) -> bool:
        """Check if the message manager is initialized."""
        return self._initialized

    async def initialize(self) -> bool:
        """
        Initialize the message manager and return a boolean indicating success.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Connect to cache
            if not await self.cache.connect():
                logger.error("Failed to connect to cache during initialization")
                return False
            
            # Start the scheduler
            if not self.scheduler.running:
                self.scheduler.start()
            
            self._initialized = True
            logger.info("MessageManager successfully initialized")
            return True
        except Exception as e:
            logger.error(f"Error during MessageManager initialization: {e}", exc_info=True)
            self._initialized = False
            return False

    def is_initialized(self) -> bool:
        """
        Check if the message manager is initialized.
        
        Returns:
            bool: True if initialized, False otherwise.
        """
        return self._initialized

    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Return performance statistics for the message manager.
        
        Returns:
            Dict[str, Any]: Dictionary containing performance metrics.
        """
        return {
            "total_messages_processed": self.metrics.total_messages_processed,
            "successful_deletions": self.metrics.successful_deletions,
            "failed_deletions": self.metrics.failed_deletions,
            "batch_operations": self.metrics.batch_operations,
            "average_batch_size": round(self.metrics.average_batch_size, 2),
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "total_processing_time": round(self.metrics.total_processing_time, 2),
            "success_rate": round(self.metrics.get_success_rate(), 2),
            "last_cleanup": self.metrics.last_cleanup.isoformat() if self.metrics.last_cleanup else None,
            "is_initialized": self._initialized,
            "scheduler_running": self.scheduler.running
        }

    def start_periodic_cleanup(self, interval_seconds: int = 60):
        """Starts the periodic cleanup of expired messages."""
        if not self._initialized:
            logger.warning("MessageManager not initialized. Skipping periodic cleanup setup.")
            return
            
        if not self.scheduler.running:
            self.scheduler.add_job(
                self._cleanup_expired_messages, 
                'interval', 
                seconds=interval_seconds,
                id='message_cleanup_job',
                replace_existing=True
            )
            self.scheduler.start()
            logger.info(f"Started periodic message cleanup every {interval_seconds} seconds.")

    async def _cleanup_expired_messages(self):
        """Job to clean up all expired messages across all chats."""
        if not self._initialized:
            logger.warning("MessageManager not initialized. Skipping periodic cleanup.")
            return
            
        if not await self.cache.connect():
            logger.warning("Cache not connected. Skipping periodic cleanup.")
            self._metrics["cache_errors"] += 1
            return

        logger.debug("Running periodic message cleanup job.")
        pattern = "msg_track:*:*"
        keys = await self.cache.get_keys_by_pattern(pattern)
        if not keys:
            return

        now = datetime.utcnow()
        deletion_tasks = []
        for key in keys:
            try:
                record_data_str = await self.cache.get_value(key)
                if not record_data_str:
                    continue
                
                record_data = json.loads(record_data_str)
                
                # Convert created_at from string to datetime before creating the record
                record_data['created_at'] = datetime.fromisoformat(record_data['created_at'])
                record = MessageTrackingRecord(**record_data)

                if record.should_delete and record.ttl_seconds != -1:
                    expiration_time = record.created_at + timedelta(seconds=record.ttl_seconds)
                    if now > expiration_time:
                        deletion_tasks.append(self.delete_message(record.chat_id, record.message_id))

            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.error(f"Failed to decode or process message tracking record from key {key}: {e}")
                self._metrics["cache_errors"] += 1
                # Delete the malformed key to prevent future errors
                await self.cache.delete_key(key)
            except Exception as e:
                logger.error(f"Unexpected error processing key {key} for periodic cleanup: {e}", exc_info=True)
                self._metrics["cache_errors"] += 1

        if deletion_tasks:
            logger.info(f"Periodically cleaning up {len(deletion_tasks)} expired messages.")
            await asyncio.gather(*deletion_tasks)

    def shutdown(self):
        """Shuts down the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("MessageManager scheduler shut down.")
        self._initialized = False
        logger.info("MessageManager shut down.")

    async def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics for the message manager.
        
        Returns:
            Dict containing performance metrics.
        """
        if not self._initialized:
            return {
                "status": "not_initialized",
                "error": "MessageManager not initialized",
                "metrics": {}
            }
            
        # Calculate success rate
        total_deletions = self._metrics["successful_deletions"] + self._metrics["failed_deletions"]
        success_rate = (self._metrics["successful_deletions"] / total_deletions * 100) if total_deletions > 0 else 0
        
        return {
            "status": "operational",
            "metrics": {
                "total_messages_tracked": self._metrics["total_messages_tracked"],
                "total_messages_deleted": self._metrics["total_messages_deleted"],
                "successful_deletions": self._metrics["successful_deletions"],
                "failed_deletions": self._metrics["failed_deletions"],
                "cache_errors": self._metrics["cache_errors"],
                "api_errors": self._metrics["api_errors"],
                "deletion_success_rate": round(success_rate, 2),
                "scheduler_status": "running" if self.scheduler.running else "stopped"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        self._initialized = False

    def _get_tracking_key(self, chat_id: int, message_id: int) -> str:
        """Generate a unique Redis key for tracking a message."""
        return f"msg_track:{chat_id}:{message_id}"

    def _get_chat_key_pattern(self, chat_id: int) -> str:
        """Generate the key pattern to find all tracked messages in a chat."""
        return f"msg_track:{chat_id}:*"
    
    def _get_main_menu_key(self, chat_id: int) -> str:
        """Generate the Redis key for storing the main menu message ID of a chat."""
        return f"main_menu:{chat_id}"

    async def track_message(
        self,
        chat_id: int,
        message_id: int,
        message_type: str,
        is_main_menu: bool = False
    ) -> None:
        """
        Track a message for potential automatic cleanup.

        Args:
            chat_id: The chat ID.
            message_id: The message ID.
            message_type: The type of the message (e.g., 'notification', 'main_menu').
            is_main_menu: Flag indicating if this is the main menu message.
        """
        if not self._initialized:
            logger.warning("MessageManager not initialized. Skipping message tracking.")
            return
            
        if not await self.cache.connect():
            logger.warning("Cache not connected. Skipping message tracking.")
            self._metrics["cache_errors"] += 1
            return

        ttl = MESSAGE_TTL_CONFIG.get(message_type, MESSAGE_TTL_CONFIG['default'])
        
        record = MessageTrackingRecord(
            chat_id=chat_id,
            message_id=message_id,
            message_type=message_type,
            ttl_seconds=ttl,
            should_delete=(ttl != -1 and not is_main_menu),
            is_main_menu=is_main_menu,
        )

        key = self._get_tracking_key(chat_id, message_id)
        # Use a slightly longer Redis TTL to allow for processing time
        redis_ttl = None if ttl == -1 else ttl + 10 
        
        await self.cache.set_value(key, record.__dict__, ttl=redis_ttl)
        self._metrics["total_messages_tracked"] += 1
        logger.debug(f"Tracking message {message_id} in chat {chat_id} with TTL {ttl}s.")

        if is_main_menu:
            await self.preserve_main_menu(chat_id, message_id)

    async def preserve_main_menu(self, chat_id: int, message_id: int) -> None:
        """
        Mark a message as the main menu, ensuring it's not deleted and deleting the old one.
        
        Args:
            chat_id: The chat ID.
            message_id: The ID of the new main menu message.
        """
        main_menu_key = self._get_main_menu_key(chat_id)
        old_main_menu_id_str = await self.cache.get_value(main_menu_key)

        # Schedule deletion of the old main menu message if it exists
        if old_main_menu_id_str:
            try:
                # Clean string - remove quotes if present
                cleaned_id_str = old_main_menu_id_str.strip('"').strip()
                old_main_menu_id = int(cleaned_id_str)
                if old_main_menu_id != message_id:
                    logger.debug(f"Scheduling old main menu {old_main_menu_id} for deletion.")
                    await self.delete_message(chat_id, old_main_menu_id)
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid old main menu ID found in cache: {old_main_menu_id_str}. Error: {e}")

        # Store the new main menu message ID
        await self.cache.set_value(main_menu_key, str(message_id), ttl=None) # Persist indefinitely
        logger.info(f"Preserving new main menu message {message_id} for chat {chat_id}.")

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        """
        Safely delete a single message and its tracking record from the cache.

        Args:
            chat_id: The chat ID.
            message_id: The message ID to delete.
        """
        if not self._initialized:
            logger.warning("MessageManager not initialized. Skipping message deletion.")
            return
            
        try:
            await self.bot.delete_message(chat_id, message_id)
            self._metrics["total_messages_deleted"] += 1
            self._metrics["successful_deletions"] += 1
            logger.debug(f"Successfully deleted message {message_id} from chat {chat_id}.")
        except TelegramBadRequest as e:
            if "message to delete not found" in e.message or "message can't be deleted" in e.message:
                logger.warning(f"Could not delete message {message_id} in chat {chat_id}: {e.message}")
                self._metrics["api_errors"] += 1
            else:
                logger.error(f"Error deleting message {message_id} in chat {chat_id}: {e}", exc_info=True)
                self._metrics["api_errors"] += 1
                self._metrics["failed_deletions"] += 1
        except Exception as e:
            logger.error(f"Unexpected error deleting message {message_id} in chat {chat_id}: {e}", exc_info=True)
            self._metrics["api_errors"] += 1
            self._metrics["failed_deletions"] += 1
        finally:
            # Always try to remove the tracking key from cache
            key = self._get_tracking_key(chat_id, message_id)
            cache_result = await self.cache.delete_key(key)
            if not cache_result:
                self._metrics["cache_errors"] += 1

    async def delete_old_messages(self, chat_id: int, keep_main_menu: bool = True) -> None:
        """
        Delete all tracked messages in a chat that are marked for deletion.

        This is typically called before sending a new menu or response to clean up the chat.

        Args:
            chat_id: The chat ID to clean up.
            keep_main_menu: If True, the current main menu message will not be deleted.
        """
        if not self._initialized:
            logger.warning("MessageManager not initialized. Skipping old message deletion.")
            return
            
        if not await self.cache.connect():
            logger.warning("Cache not connected. Skipping message cleanup.")
            self._metrics["cache_errors"] += 1
            return

        pattern = self._get_chat_key_pattern(chat_id)
        keys = await self.cache.get_keys_by_pattern(pattern)
        
        if not keys:
            logger.debug(f"No tracked messages to clean up for chat {chat_id}.")
            return

        logger.info(f"Found {len(keys)} tracked messages to potentially clean for chat {chat_id}.")

        main_menu_id = -1
        if keep_main_menu:
            main_menu_id_str = await self.cache.get_value(self._get_main_menu_key(chat_id))
            if main_menu_id_str:
                try:
                    # Clean string - remove quotes if present
                    cleaned_id_str = main_menu_id_str.strip('"').strip()
                    main_menu_id = int(cleaned_id_str)
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid main menu ID found in cache: {main_menu_id_str}. Error: {e}")
                    main_menu_id = -1

        deletion_tasks = []
        for key in keys:
            try:
                record_data_str = await self.cache.get_value(key)
                if not record_data_str:
                    continue
                
                # Pydantic or a proper deserializer would be better here
                record_data = json.loads(record_data_str)
                record = MessageTrackingRecord(**record_data)

                if record.should_delete and record.message_id != main_menu_id:
                    deletion_tasks.append(self.delete_message(record.chat_id, record.message_id))

            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to decode message tracking record from key {key}: {e}")
                self._metrics["cache_errors"] += 1
                # Delete the malformed key to prevent future errors
                await self.cache.delete_key(key)
            except Exception as e:
                logger.error(f"Unexpected error processing key {key} for cleanup: {e}", exc_info=True)
                self._metrics["cache_errors"] += 1

        if deletion_tasks:
            logger.info(f"Attempting to delete {len(deletion_tasks)} messages in chat {chat_id}.")
            await asyncio.gather(*deletion_tasks)
        else:
            logger.info(f"No messages marked for deletion in chat {chat_id}.")
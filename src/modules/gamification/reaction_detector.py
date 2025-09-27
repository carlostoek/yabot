"""
Reaction Detector - Gamification Module

This module detects and processes user reactions to content, triggering
besitos rewards and other gamification events. It implements requirements 2.5 and 4.3
by processing Telegram reaction events and publishing to the event bus for cross-module
coordination with the besitos wallet and hint system.

Implements:
- Reaction detection from Telegram updates
- Event publishing for reaction processing
- Cross-module API calls to besitos wallet and hint system
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from aiogram import Bot
from aiogram.types import Update, MessageReactionUpdated
from pydantic import BaseModel
import logging
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

from src.events.bus import EventBus
from src.events.models import ReactionDetectedEvent
from src.utils.logger import get_logger
from src.core.error_handler import ErrorHandler
from src.core.models import RedisConfig
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.shared.api.auth import get_cross_module_auth_service


class ReactionDetectorConfig(BaseModel):
    """
    Configuration for the reaction detector
    """
    auto_reward_enabled: bool = True
    positive_reaction_types: list = ["like", "love", "besito", "emoji_reaction"]
    reward_amount: int = 5  # besitos awarded for positive reactions
    reward_cooldown_seconds: int = 60  # seconds between rewards for same user


class ReactionDetector:
    """
    Detects and processes user reactions to content with cross-module integration.
    
    Implements the ReactionDetector component from the design document with interfaces:
    - process_reaction(update: Update): Process Telegram reaction updates
    - detect_reactions(message: Message): Analyze message reactions
    - trigger_rewards(user_id: str, reaction_type: str): Award besitos for reactions
    """
    
    def __init__(self,
                 event_bus: EventBus,
                 bot: Bot,
                 mission_manager: Optional['MissionManager'] = None,  # Add mission manager for requirement 2.4
                 config: Optional[ReactionDetectorConfig] = None,
                 redis_config: Optional[RedisConfig] = None):
        self.event_bus = event_bus
        self.bot = bot
        self.mission_manager = mission_manager  # Add for mission completion processing
        self.config = config or ReactionDetectorConfig()
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler()
        # Import database client here to avoid circular imports
        from motor.motor_asyncio import AsyncIOMotorClient
        import os

        # Create database client for ReactionDetector
        db_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/yabot')
        self.db_client = AsyncIOMotorClient(db_uri)
        self.besitos_wallet = BesitosWallet(self.db_client, event_bus)
        self.api_client = get_cross_module_auth_service()

        # Initialize Redis for cooldowns
        self.redis_config = redis_config or RedisConfig()
        self.redis_client = None
        self._redis_connected = False
        
        # Initialize reaction type mappings
        self.reaction_mappings = {
            "👍": "like",
            "❤️": "love",
            "😍": "love",
            "😂": "haha",
            "😮": "wow",
            "😢": "sad",
            "😠": "angry",
            "🎁": "besito",  # Special besito reaction
        }

        # Initialize Redis connection for cooldowns
        asyncio.create_task(self._initialize_redis())

    async def _initialize_redis(self) -> bool:
        """
        Initialize Redis connection for cooldown management

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # Create Redis connection pool
            connection_pool = redis.ConnectionPool.from_url(
                self.redis_config.url,
                password=self.redis_config.password,
                max_connections=self.redis_config.max_connections,
                retry_on_timeout=self.redis_config.retry_on_timeout,
                socket_connect_timeout=self.redis_config.socket_connect_timeout,
                socket_timeout=self.redis_config.socket_timeout
            )

            self.redis_client = redis.Redis(connection_pool=connection_pool)

            # Test connection
            await self.redis_client.ping()
            self._redis_connected = True

            self.logger.info("Connected to Redis for reaction cooldowns")
            return True

        except (ConnectionError, TimeoutError, redis.ConnectionError) as e:
            self._redis_connected = False
            self.logger.warning("Could not connect to Redis for cooldowns, disabling cooldown feature", error=str(e))
            return False
        except Exception as e:
            self._redis_connected = False
            self.logger.error("Unexpected error connecting to Redis", error=str(e))
            return False

    async def _check_cooldown(self, user_id: str, content_id: str) -> bool:
        """
        Check if user is on cooldown for reacting to specific content

        Args:
            user_id: User identifier
            content_id: Content identifier

        Returns:
            True if user is on cooldown, False if they can receive rewards
        """
        if not self._redis_connected or not self.redis_client:
            # If Redis is not available, don't enforce cooldown
            return False

        try:
            cooldown_key = f"reaction_cooldown:{user_id}:{content_id}"
            result = await self.redis_client.exists(cooldown_key)
            return bool(result)

        except Exception as e:
            self.logger.warning("Error checking cooldown, allowing reward", error=str(e))
            return False

    async def _set_cooldown(self, user_id: str, content_id: str) -> bool:
        """
        Set cooldown for user reaction to specific content

        Args:
            user_id: User identifier
            content_id: Content identifier

        Returns:
            True if cooldown was set successfully
        """
        if not self._redis_connected or not self.redis_client:
            # If Redis is not available, cooldown is not enforced
            return True

        try:
            cooldown_key = f"reaction_cooldown:{user_id}:{content_id}"
            # Set with expiration based on config
            await self.redis_client.setex(
                cooldown_key,
                self.config.reward_cooldown_seconds,
                "1"
            )
            return True

        except Exception as e:
            self.logger.warning("Error setting cooldown", error=str(e))
            return False
        
    async def process_reaction(self, update: Update) -> bool:
        """
        Process a Telegram update containing a reaction.
        
        Implements requirement 2.5: WHEN users react to content 
        THEN the system SHALL detect reactions via Telegram hooks and publish reaction_detected events
        
        Implements requirement 4.3: WHEN reaction events occur 
        THEN cross-module API calls SHALL be made to besitos wallet and hint system
        
        Args:
            update: The Telegram Update object containing a reaction
            
        Returns:
            True if the reaction was processed successfully, False otherwise
        """
        try:
            # Check if this is a reaction update
            if not hasattr(update, 'message_reaction') or update.message_reaction is None:
                if hasattr(update, 'channel_post_reactions') and update.channel_post_reactions:
                    # Handle channel post reactions
                    await self._process_channel_reaction(update)
                    return True
                return False
            
            reaction_update = update.message_reaction
            user_id = str(reaction_update.user.id) if reaction_update.user else str(reaction_update.actor_chat.id)
            message_id = reaction_update.message_id
            chat_id = reaction_update.chat.id
            
            # Determine the reaction type
            reaction_type = self._determine_reaction_type(reaction_update.new_reaction)
            
            # Validate that this is a reaction we want to process
            if not reaction_type or (self.config.positive_reaction_types and 
                                   reaction_type not in self.config.positive_reaction_types):
                self.logger.debug(
                    "Skipping reaction processing",
                    user_id=user_id,
                    reaction_type=reaction_type,
                    message_id=message_id
                )
                return True  # Still return True as it was processed (just not acted upon)
            
            # Create content ID from chat and message
            content_id = f"{chat_id}:{message_id}"
            
            # Create and publish reaction detected event
            reaction_event = ReactionDetectedEvent(
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type,
                metadata={
                    'chat_id': chat_id,
                    'message_id': message_id,
                    'old_reaction': self._determine_reaction_type(reaction_update.old_reaction),
                    'new_reaction': reaction_type
                }
            )
            
            self.logger.info(
                "Reaction detected and event created",
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type
            )
            
            # Publish the reaction event to the event bus
            await self.event_bus.publish("reaction_detected", reaction_event)
            
            # Trigger rewards if auto reward is enabled
            if self.config.auto_reward_enabled:
                await self._trigger_auto_rewards(user_id, content_id, reaction_type)
            
            # Also publish a user interaction event for analytics
            from src.events.models import UserInteractionEvent
            interaction_event = UserInteractionEvent(
                user_id=user_id,
                action="reaction",
                context={
                    'content_id': content_id,
                    'reaction_type': reaction_type,
                    'source': 'reaction_detector'
                },
                payload={
                    'reaction_type': reaction_type,
                    'content_id': content_id
                }
            )
            await self.event_bus.publish("user_interaction", interaction_event)
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Error processing reaction",
                error=str(e),
                error_type=type(e).__name__,
                update=str(update)[:500]  # First 500 chars of update
            )
            self.error_handler.handle_error(e, {
                'update': str(update),
                'error': str(e),
                'error_type': type(e).__name__
            })
            return False
    
    async def detect_reactions(self, message_reaction: MessageReactionUpdated) -> Dict[str, Any]:
        """
        Analyze reactions on a specific message_reaction object.
        
        Args:
            message_reaction: The MessageReactionUpdated object to analyze
            
        Returns:
            Dictionary containing reaction analysis results
        """
        try:
            result = {
                'message_id': message_reaction.message_id,
                'chat_id': message_reaction.chat.id,
                'user_id': str(message_reaction.user.id) if message_reaction.user else str(message_reaction.actor_chat.id),
                'old_reaction': self._determine_reaction_type(message_reaction.old_reaction),
                'new_reaction': self._determine_reaction_type(message_reaction.new_reaction),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Error detecting reactions on message",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                'message_id': getattr(message_reaction, 'message_id', None),
                'chat_id': getattr(message_reaction, 'chat_id', None),
                'error': str(e),
                'success': False
            }
    
    async def _process_channel_reaction(self, update: Update) -> bool:
        """
        Process reactions to channel posts with channel validation.
        
        Implements requirement 2.2: WHEN reaction mission is assigned 
        THEN the system SHALL provide the exact channel name "@yabot_canal" and required emoji "❤️"
        Implements requirement 2.3: WHEN user reacts with ❤️ in @yabot_canal 
        THEN the reaction detector SHALL capture the event within 5 seconds
        
        Args:
            update: The Telegram Update object containing channel reaction
            
        Returns:
            True if processed successfully
        """
        try:
            channel_post_reaction = update.channel_post_reactions[0] if update.channel_post_reactions else None
            if not channel_post_reaction:
                return False
                
            user_id = str(channel_post_reaction.user.id) if channel_post_reaction.user else str(channel_post_reaction.actor_chat.id)
            message_id = channel_post_reaction.message_id
            chat_id = channel_post_reaction.chat.id
            chat_username = channel_post_reaction.chat.username  # Get the chat username for validation
            
            # Validate that the reaction is in the expected channel (@yabot_canal)
            # This implements requirement 2.2: Validate the exact channel name
            expected_channel = "@yabot_canal"
            channel_username = f"@{chat_username}" if chat_username else f"@{chat_id}"
            
            # Check if this is our expected channel
            if channel_username != expected_channel and f"@{chat_id}" != expected_channel:
                self.logger.debug(
                    "Reaction in different channel, skipping",
                    user_id=user_id,
                    channel_username=channel_username,
                    expected_channel=expected_channel
                )
                return True  # This is still valid processing, just not for our mission
            
            # Determine the reaction type
            reaction_type = self._determine_reaction_type(channel_post_reaction.new_reaction)
            
            # Validate that this is the required reaction type (❤️)
            # This implements requirement 2.2: Required emoji validation
            required_emoji = "❤️"
            if reaction_type != "love" or "❤️" not in str(channel_post_reaction.new_reaction):
                self.logger.debug(
                    "Reaction with non-required emoji, skipping",
                    user_id=user_id,
                    reaction_type=reaction_type,
                    required_emoji=required_emoji
                )
                return True  # This is still valid processing, just not for our mission
            
            # Validate that this is a reaction we want to process
            if not reaction_type or (self.config.positive_reaction_types and 
                                   reaction_type not in self.config.positive_reaction_types):
                return True
            
            # Create content ID from chat and message
            content_id = f"{chat_id}:{message_id}"
            
            # Create and publish reaction detected event
            reaction_event = ReactionDetectedEvent(
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type,
                metadata={
                    'chat_id': chat_id,
                    'chat_username': channel_username,
                    'message_id': message_id,
                    'reaction_source': 'channel_post',
                    'channel_validation': True
                }
            )
            
            # Publish the reaction event to the event bus
            await self.event_bus.publish("reaction_detected", reaction_event)
            
            # Check if this user has an active mission for this channel reaction
            # This implements requirement 2.4: WHEN valid reaction is detected 
            # THEN the mission progress SHALL update to "completed" status
            if hasattr(self, 'mission_manager') and self.mission_manager:
                await self._process_reaction_mission_completion(user_id, chat_username, required_emoji)
            
            # Trigger rewards if auto reward is enabled
            if self.config.auto_reward_enabled:
                await self._trigger_auto_rewards(user_id, content_id, reaction_type)
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Error processing channel reaction",
                error=str(e),
                error_type=type(e).__name__
            )
            self.error_handler.handle_error(e, {
                'update': str(update),
                'error': str(e),
                'error_type': type(e).__name__
            })
            return False
    
    def _determine_reaction_type(self, reaction_list) -> Optional[str]:
        """
        Determine the reaction type from Telegram's reaction format.
        
        Args:
            reaction_list: List of reactions from Telegram API
            
        Returns:
            The normalized reaction type string or None
        """
        if not reaction_list:
            return None
            
        for reaction in reaction_list:
            if hasattr(reaction, 'emoji'):
                emoji = reaction.emoji
                # Map emoji to reaction type
                return self.reaction_mappings.get(emoji, "emoji_reaction")
            elif hasattr(reaction, 'custom_emoji_id'):
                # Handle custom emoji reactions
                return "emoji_reaction"
        
        return "reaction"
    
    async def _process_reaction_mission_completion(self, user_id: str, channel_username: str, required_emoji: str) -> bool:
        """
        Process mission completion when a valid reaction is detected in the correct channel.
        
        Implements requirement 2.4: WHEN valid reaction is detected 
        THEN the mission progress SHALL update to "completed" status
        Implements requirement 2.5: WHEN reaction mission is completed 
        THEN the system SHALL award exactly 10 besitos automatically
        
        Args:
            user_id: The user who reacted
            channel_username: The channel where the reaction occurred
            required_emoji: The required emoji that was detected
            
        Returns:
            True if mission completion was processed successfully
        """
        try:
            if not self.mission_manager:
                self.logger.warning("Mission manager not available, skipping mission completion processing")
                return False
            
            # Get the user's active missions to find the "Reacciona en el Canal Principal" mission
            from src.modules.gamification.mission_manager import MissionStatus
            active_missions = await self.mission_manager.get_active_missions(user_id)
            
            # Find the specific mission for reacting in the main channel
            target_mission = None
            for mission in active_missions:
                if mission.title == "Reacciona en el Canal Principal":
                    target_mission = mission
                    break
            
            if not target_mission:
                self.logger.debug(
                    "User doesn't have the target reaction mission",
                    user_id=user_id
                )
                return False
            
            # Validate that the reaction matches mission requirements
            expected_channel = "@yabot_canal"
            if channel_username != expected_channel:
                self.logger.debug(
                    "Reaction not in required channel for mission",
                    user_id=user_id,
                    actual_channel=channel_username,
                    required_channel=expected_channel
                )
                return False
            
            # Update mission progress for the reaction objective
            objective_id = "react_to_channel"
            progress_update = {
                "completed": True,
                "reaction_emoji": required_emoji,
                "channel": channel_username,
                "completed_at": datetime.utcnow()
            }
            
            success = await self.mission_manager.update_progress(
                user_id=user_id,
                mission_id=target_mission.mission_id,
                objective_id=objective_id,
                progress_data=progress_update
            )
            
            if success:
                self.logger.info(
                    "Reaction mission progress updated",
                    user_id=user_id,
                    mission_id=target_mission.mission_id,
                    objective_id=objective_id
                )
                
                # Check if the mission is now completed
                await self.mission_manager._check_mission_completion(user_id, target_mission.mission_id)
                
                return True
            else:
                self.logger.warning(
                    "Failed to update mission progress",
                    user_id=user_id,
                    mission_id=target_mission.mission_id
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "Error processing reaction mission completion",
                user_id=user_id,
                channel_username=channel_username,
                error=str(e),
                error_type=type(e).__name__
            )
            self.error_handler.handle_error(e, {
                'user_id': user_id,
                'channel_username': channel_username,
                'error': str(e),
                'error_type': type(e).__name__
            })
            return False

    async def _trigger_auto_rewards(self, user_id: str, content_id: str, reaction_type: str) -> bool:
        """
        Trigger automatic rewards for positive reactions with cooldown enforcement.

        Args:
            user_id: The user who reacted
            content_id: The content that was reacted to
            reaction_type: The type of reaction

        Returns:
            True if rewards were successfully processed or cooldown prevented duplicate reward
        """
        try:
            # Check if the reaction type qualifies for a reward
            if reaction_type in self.config.positive_reaction_types:
                # Check cooldown to prevent spam rewards
                if await self._check_cooldown(user_id, content_id):
                    self.logger.debug(
                        "User on cooldown for reaction rewards",
                        user_id=user_id,
                        content_id=content_id,
                        reaction_type=reaction_type,
                        cooldown_seconds=self.config.reward_cooldown_seconds
                    )
                    return True  # Return True as this is expected behavior, not an error

                # Award besitos for positive reactions
                reward_amount = self.config.reward_amount

                # Add besitos to user's wallet
                from src.modules.gamification.besitos_wallet import BesitosTransactionType
                result = await self.besitos_wallet.add_besitos(
                    user_id=user_id,
                    amount=reward_amount,
                    transaction_type=BesitosTransactionType.REACTION,
                    description=f"Reaction to content {content_id} ({reaction_type})",
                    reference_data={
                        'content_id': content_id,
                        'reaction_type': reaction_type,
                        'reward_amount': reward_amount,
                        'source': 'reaction_detector'
                    }
                )
                success = result.success

                if success:
                    # Set cooldown after successful reward
                    await self._set_cooldown(user_id, content_id)

                    self.logger.info(
                        "Besitos awarded for reaction",
                        user_id=user_id,
                        content_id=content_id,
                        reaction_type=reaction_type,
                        reward_amount=reward_amount
                    )
                else:
                    self.logger.warning(
                        "Failed to award besitos for reaction",
                        user_id=user_id,
                        content_id=content_id,
                        reaction_type=reaction_type
                    )

                return success
            else:
                # Not a positive reaction, no reward
                return True

        except Exception as e:
            self.logger.error(
                "Error triggering auto rewards",
                error=str(e),
                error_type=type(e).__name__,
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type
            )
            self.error_handler.handle_error(e, {
                'user_id': user_id,
                'content_id': content_id,
                'reaction_type': reaction_type,
                'error': str(e),
                'error_type': type(e).__name__
            })
            return False
    
    
    
    async def handle_reaction_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle a reaction event from the event bus.
        
        Args:
            event_data: The reaction event data
            
        Returns:
            True if handled successfully
        """
        try:
            user_id = event_data.get('user_id')
            content_id = event_data.get('content_id')
            reaction_type = event_data.get('reaction_type')
            
            self.logger.debug(
                "Handling reaction event",
                user_id=user_id,
                content_id=content_id,
                reaction_type=reaction_type
            )
            
            # Process cross-module interactions
            # This could trigger hint unlocks or other gamification events
            # based on the reaction type and context
            
            # For now, just log the event - more complex processing would go here
            # such as:
            # - Checking if this reaction qualifies for special achievements
            # - Updating mission progress if the reaction is part of a mission
            # - Triggering hint unlocks based on reaction patterns
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Error handling reaction event",
                error=str(e),
                error_type=type(e).__name__,
                event_data=str(event_data)
            )
            self.error_handler.handle_error(e, {
                'event_data': event_data,
                'error': str(e),
                'error_type': type(e).__name__
            })
            return False

    async def close(self):
        """
        Close Redis connection and cleanup resources
        """
        if self.redis_client and self._redis_connected:
            try:
                await self.redis_client.close()
                self._redis_connected = False
                self.logger.info("Closed Redis connection for reaction detector")
            except Exception as e:
                self.logger.warning("Error closing Redis connection", error=str(e))


# Global reaction detector instance
_reaction_detector = None


def get_reaction_detector(event_bus: EventBus, bot: Bot, mission_manager: Optional['MissionManager'] = None, redis_config: Optional[RedisConfig] = None) -> ReactionDetector:
    """
    Get or create the global reaction detector instance.

    Args:
        event_bus: The event bus instance
        bot: The aiogram Bot instance
        mission_manager: Optional mission manager for mission completion processing
        redis_config: Optional Redis configuration for cooldowns

    Returns:
        ReactionDetector instance
    """
    global _reaction_detector
    if _reaction_detector is None:
        _reaction_detector = ReactionDetector(event_bus, bot, mission_manager=mission_manager, redis_config=redis_config)
    return _reaction_detector


def reset_reaction_detector():
    """
    Reset the global reaction detector instance (useful for testing).
    """
    global _reaction_detector
    _reaction_detector = None
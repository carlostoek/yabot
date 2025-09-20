"""
Reaction detector module for the YABOT system.

This module detects user reactions via Telegram hooks and publishes reaction_detected events
to the event bus, implementing requirements 2.5 and 4.3 from the modulos-atomicos specification.
"""

import time
from typing import Any, Optional, Dict, List
from datetime import datetime

from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger
from src.utils.validators import InputValidator

logger = get_logger(__name__)


class ReactionDetectorError(Exception):
    """Base exception for reaction detector operations."""
    pass


class InvalidReactionError(ReactionDetectorError):
    """Exception raised when reaction data is invalid."""
    pass


class ReactionDetector:
    """Detects user reactions via Telegram hooks and publishes events.

    This class follows the webhook patterns established in src/handlers/webhook.py
    and implements the reaction detection functionality required by the specification.

    Implements requirement 2.5: WHEN users react to content THEN the system SHALL
    detect reactions via Telegram hooks and publish reaction_detected events.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize the reaction detector.

        Args:
            event_bus (Optional[EventBus]): Event bus for publishing events
        """
        self.event_bus = event_bus
        self._rate_limit_cache: Dict[str, List[float]] = {}
        self._max_reactions_per_minute = 30

        # Supported reaction types mapping from Telegram reactions to internal types
        self._reaction_mapping = {
            "👍": "thumbs_up",
            "👎": "thumbs_down",
            "❤️": "heart",
            "🔥": "fire",
            "🥰": "love",
            "👏": "clap",
            "😁": "laugh",
            "😱": "shocked",
            "😭": "cry",
            "🤮": "vomit",
            "🎉": "party",
            "🤩": "star_struck",
            "🙏": "pray",
            "👌": "ok",
            "🕊": "dove",
            "🤡": "clown",
            "🥱": "yawn",
            "🥴": "woozy",
            "😍": "heart_eyes",
            "🐳": "whale",
            "❤️‍🔥": "heart_on_fire",
            "🌚": "moon_face",
            "🌭": "hot_dog",
            "💯": "hundred",
            "🤣": "rofl",
            "⚡️": "lightning",
            "🍌": "banana",
            "🏆": "trophy",
            "💔": "broken_heart",
            "🤨": "raised_eyebrow",
            "😐": "neutral",
            "🍓": "strawberry",
            "🍾": "champagne",
            "💋": "kiss",
            "🖕": "middle_finger",
            "😈": "smiling_imp",
            "😴": "sleeping",
            "😭": "loudly_crying",
            "🤓": "nerd",
            "👻": "ghost",
            "👨‍💻": "technologist",
            "👀": "eyes",
            "🎃": "jack_o_lantern",
            "🙈": "see_no_evil",
            "😇": "innocent",
            "😨": "fearful",
            "🤝": "handshake",
            "✍️": "writing_hand",
            "🤗": "hugging",
            "🫡": "saluting",
            "🎅": "santa",
            "🎄": "christmas_tree",
            "☃️": "snowman",
            "💅": "nail_polish",
            "🤪": "zany",
            "🗿": "moai",
            "🆒": "cool",
            "💘": "cupid",
            "🙉": "hear_no_evil",
            "🙊": "speak_no_evil",
            "😤": "huffing",
            "😎": "sunglasses",
            "😒": "unamused",
            "😭": "sobbing",
            "😊": "blush",
            "🤷": "shrug",
            "😘": "kiss_heart",
            "🤌": "pinched_fingers",
            "🤷‍♂️": "man_shrug",
            "🤷‍♀️": "woman_shrug",
            "🤦": "facepalm",
            "🤦‍♂️": "man_facepalm",
            "🤦‍♀️": "woman_facepalm",
            "🙄": "eye_roll",
            "😮": "open_mouth",
            "🤐": "zipper_mouth",
            "🤫": "shushing"
        }

        logger.info("ReactionDetector initialized with %d supported reaction types",
                   len(self._reaction_mapping))

    async def detect_reaction_update(self, update: Any) -> bool:
        """Detect and process reaction updates from Telegram.

        Args:
            update (Any): The Telegram update object

        Returns:
            bool: True if reaction was processed successfully, False otherwise
        """
        logger.debug("Processing potential reaction update")

        try:
            # Validate the update object
            if not self._is_reaction_update(update):
                logger.debug("Update is not a reaction update")
                return False

            # Extract reaction data
            reaction_data = self._extract_reaction_data(update)
            if not reaction_data:
                logger.warning("Failed to extract reaction data from update")
                return False

            # Validate rate limits
            user_id = reaction_data.get("user_id")
            if user_id and not await self._check_rate_limit(user_id):
                logger.warning("Rate limit exceeded for user %s", user_id)
                return False

            # Sanitize and validate reaction data
            sanitized_data = self._sanitize_reaction_data(reaction_data)
            if not self._validate_reaction_data(sanitized_data):
                logger.warning("Invalid reaction data: %s", sanitized_data)
                return False

            # Publish reaction detected event
            success = await self._publish_reaction_event(sanitized_data)
            if success:
                logger.info("Successfully processed reaction from user %s: %s",
                           user_id, sanitized_data.get("reaction_type"))
            else:
                logger.warning("Failed to publish reaction event")

            return success

        except Exception as e:
            logger.error("Error processing reaction update: %s", str(e))
            return False

    def _is_reaction_update(self, update: Any) -> bool:
        """Check if the update is a reaction update.

        Args:
            update (Any): The update object to check

        Returns:
            bool: True if this is a reaction update
        """
        # Check for message_reaction or message_reaction_count updates
        if hasattr(update, 'message_reaction'):
            return True
        if hasattr(update, 'message_reaction_count'):
            return True

        # Check for dict-style access
        if isinstance(update, dict):
            return 'message_reaction' in update or 'message_reaction_count' in update

        # Check for update_type attribute
        if hasattr(update, 'update_type'):
            return update.update_type in ['message_reaction', 'message_reaction_count']

        return False

    def _extract_reaction_data(self, update: Any) -> Optional[Dict[str, Any]]:
        """Extract reaction data from the Telegram update.

        Args:
            update (Any): The Telegram update object

        Returns:
            Optional[Dict[str, Any]]: Extracted reaction data or None if extraction fails
        """
        try:
            reaction_data = {}

            # Handle message_reaction updates (individual user reactions)
            if hasattr(update, 'message_reaction') or (isinstance(update, dict) and 'message_reaction' in update):
                message_reaction = getattr(update, 'message_reaction', None) or update.get('message_reaction')

                if message_reaction:
                    # Extract basic info
                    reaction_data['user_id'] = str(getattr(message_reaction, 'user', {}).get('id', 'unknown'))
                    reaction_data['chat_id'] = str(getattr(message_reaction, 'chat', {}).get('id', 'unknown'))
                    reaction_data['message_id'] = str(getattr(message_reaction, 'message_id', 'unknown'))
                    reaction_data['date'] = getattr(message_reaction, 'date', int(time.time()))

                    # Extract reactions
                    new_reaction = getattr(message_reaction, 'new_reaction', [])
                    old_reaction = getattr(message_reaction, 'old_reaction', [])

                    # Determine reaction type and action
                    if new_reaction and not old_reaction:
                        # New reaction added
                        reaction_data['action'] = 'added'
                        reaction_data['reactions'] = new_reaction
                    elif old_reaction and not new_reaction:
                        # Reaction removed
                        reaction_data['action'] = 'removed'
                        reaction_data['reactions'] = old_reaction
                    elif new_reaction and old_reaction:
                        # Reaction changed
                        reaction_data['action'] = 'changed'
                        reaction_data['reactions'] = new_reaction
                        reaction_data['old_reactions'] = old_reaction
                    else:
                        # No reaction change
                        return None

            # Handle message_reaction_count updates (aggregate reaction counts)
            elif hasattr(update, 'message_reaction_count') or (isinstance(update, dict) and 'message_reaction_count' in update):
                message_reaction_count = getattr(update, 'message_reaction_count', None) or update.get('message_reaction_count')

                if message_reaction_count:
                    reaction_data['chat_id'] = str(getattr(message_reaction_count, 'chat', {}).get('id', 'unknown'))
                    reaction_data['message_id'] = str(getattr(message_reaction_count, 'message_id', 'unknown'))
                    reaction_data['date'] = getattr(message_reaction_count, 'date', int(time.time()))
                    reaction_data['action'] = 'count_updated'
                    reaction_data['reactions'] = getattr(message_reaction_count, 'reactions', [])

            if not reaction_data:
                return None

            # Generate content_id from chat_id and message_id
            chat_id = reaction_data.get('chat_id', 'unknown')
            message_id = reaction_data.get('message_id', 'unknown')
            reaction_data['content_id'] = f"{chat_id}_{message_id}"

            return reaction_data

        except Exception as e:
            logger.error("Error extracting reaction data: %s", str(e))
            return None

    def _sanitize_reaction_data(self, reaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize reaction data for security.

        Args:
            reaction_data (Dict[str, Any]): Raw reaction data

        Returns:
            Dict[str, Any]: Sanitized reaction data
        """
        sanitized = {}

        # Sanitize string fields
        for field in ['user_id', 'chat_id', 'message_id', 'content_id', 'action']:
            if field in reaction_data:
                value = str(reaction_data[field])
                sanitized[field] = InputValidator.sanitize_html_input(value)[:255]  # Limit length

        # Handle numeric fields
        if 'date' in reaction_data:
            try:
                sanitized['date'] = int(reaction_data['date'])
            except (ValueError, TypeError):
                sanitized['date'] = int(time.time())

        # Process reactions list
        if 'reactions' in reaction_data:
            sanitized['reactions'] = self._sanitize_reactions_list(reaction_data['reactions'])

        if 'old_reactions' in reaction_data:
            sanitized['old_reactions'] = self._sanitize_reactions_list(reaction_data['old_reactions'])

        return sanitized

    def _sanitize_reactions_list(self, reactions: List[Any]) -> List[Dict[str, Any]]:
        """Sanitize a list of reaction objects.

        Args:
            reactions (List[Any]): List of reaction objects

        Returns:
            List[Dict[str, Any]]: Sanitized reactions list
        """
        sanitized_reactions = []

        for reaction in reactions[:50]:  # Limit to 50 reactions max
            try:
                sanitized_reaction = {}

                # Handle emoji reactions
                if hasattr(reaction, 'emoji'):
                    emoji = getattr(reaction, 'emoji', '')
                    sanitized_reaction['type'] = 'emoji'
                    sanitized_reaction['emoji'] = emoji
                    sanitized_reaction['reaction_type'] = self._reaction_mapping.get(emoji, 'unknown')

                # Handle custom emoji reactions
                elif hasattr(reaction, 'custom_emoji'):
                    custom_emoji = getattr(reaction, 'custom_emoji', {})
                    sanitized_reaction['type'] = 'custom_emoji'
                    sanitized_reaction['custom_emoji_id'] = str(getattr(custom_emoji, 'custom_emoji_id', ''))
                    sanitized_reaction['reaction_type'] = 'custom'

                # Handle dict-style reactions
                elif isinstance(reaction, dict):
                    if 'emoji' in reaction:
                        emoji = reaction['emoji']
                        sanitized_reaction['type'] = 'emoji'
                        sanitized_reaction['emoji'] = emoji
                        sanitized_reaction['reaction_type'] = self._reaction_mapping.get(emoji, 'unknown')
                    elif 'custom_emoji' in reaction:
                        sanitized_reaction['type'] = 'custom_emoji'
                        sanitized_reaction['custom_emoji_id'] = str(reaction.get('custom_emoji', {}).get('custom_emoji_id', ''))
                        sanitized_reaction['reaction_type'] = 'custom'

                if sanitized_reaction:
                    sanitized_reactions.append(sanitized_reaction)

            except Exception as e:
                logger.warning("Error sanitizing reaction: %s", str(e))
                continue

        return sanitized_reactions

    def _validate_reaction_data(self, reaction_data: Dict[str, Any]) -> bool:
        """Validate sanitized reaction data.

        Args:
            reaction_data (Dict[str, Any]): Sanitized reaction data

        Returns:
            bool: True if data is valid
        """
        # Required fields
        required_fields = ['content_id', 'action']
        for field in required_fields:
            if field not in reaction_data or not reaction_data[field]:
                logger.debug("Missing required field: %s", field)
                return False

        # Validate action
        valid_actions = ['added', 'removed', 'changed', 'count_updated']
        if reaction_data['action'] not in valid_actions:
            logger.debug("Invalid action: %s", reaction_data['action'])
            return False

        # Validate reactions list exists for relevant actions
        if reaction_data['action'] in ['added', 'removed', 'changed', 'count_updated']:
            if 'reactions' not in reaction_data or not reaction_data['reactions']:
                logger.debug("Missing reactions for action: %s", reaction_data['action'])
                return False

        # Validate content_id format
        content_id = reaction_data['content_id']
        if not content_id or len(content_id) > 100:
            logger.debug("Invalid content_id: %s", content_id)
            return False

        return True

    async def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within reaction rate limits.

        Args:
            user_id (str): User ID to check

        Returns:
            bool: True if user is within limits
        """
        current_time = time.time()

        # Clean old entries
        if user_id in self._rate_limit_cache:
            self._rate_limit_cache[user_id] = [
                reaction_time for reaction_time in self._rate_limit_cache[user_id]
                if current_time - reaction_time < 60  # Keep last minute
            ]
        else:
            self._rate_limit_cache[user_id] = []

        # Check if under limit
        if len(self._rate_limit_cache[user_id]) >= self._max_reactions_per_minute:
            return False

        # Add current reaction
        self._rate_limit_cache[user_id].append(current_time)
        return True

    async def _publish_reaction_event(self, reaction_data: Dict[str, Any]) -> bool:
        """Publish a reaction_detected event to the event bus.

        Args:
            reaction_data (Dict[str, Any]): Sanitized reaction data

        Returns:
            bool: True if event was published successfully
        """
        if not self.event_bus:
            logger.warning("No event bus configured, cannot publish reaction event")
            return False

        try:
            # Determine the primary reaction type
            primary_reaction_type = self._get_primary_reaction_type(reaction_data)

            # Create the reaction detected event
            event = create_event(
                "reaction_detected",
                user_id=reaction_data.get("user_id"),
                content_id=reaction_data["content_id"],
                reaction_type=primary_reaction_type,
                metadata={
                    "action": reaction_data["action"],
                    "reactions": reaction_data.get("reactions", []),
                    "old_reactions": reaction_data.get("old_reactions", []),
                    "chat_id": reaction_data.get("chat_id"),
                    "message_id": reaction_data.get("message_id"),
                    "date": reaction_data.get("date"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # Publish the event
            success = await self.event_bus.publish("reaction_detected", event.dict())

            if success:
                logger.debug("Published reaction_detected event for content %s",
                           reaction_data["content_id"])
            else:
                logger.warning("Failed to publish reaction_detected event")

            return success

        except Exception as e:
            logger.error("Error publishing reaction event: %s", str(e))
            return False

    def _get_primary_reaction_type(self, reaction_data: Dict[str, Any]) -> str:
        """Get the primary reaction type from reaction data.

        Args:
            reaction_data (Dict[str, Any]): Reaction data

        Returns:
            str: Primary reaction type
        """
        reactions = reaction_data.get("reactions", [])

        if not reactions:
            return "unknown"

        # Return the first reaction's type
        first_reaction = reactions[0]
        return first_reaction.get("reaction_type", "unknown")

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the reaction detector.

        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "event_bus_connected": self.event_bus is not None,
            "supported_reactions": len(self._reaction_mapping),
            "active_rate_limits": len(self._rate_limit_cache),
            "max_reactions_per_minute": self._max_reactions_per_minute
        }

    def get_supported_reactions(self) -> Dict[str, str]:
        """Get the mapping of supported reactions.

        Returns:
            Dict[str, str]: Mapping of emoji to reaction type
        """
        return self._reaction_mapping.copy()
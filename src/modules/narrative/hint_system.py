"""
Hint system for the YABOT system.

This module provides hint management and unlocking logic for narrative hints (pistas)
as required by the modulos-atomicos specification task 9.
Implements requirements 1.3 and 4.3 from the specification.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout

from src.database.mongodb import MongoDBHandler
from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HintSystemError(Exception):
    """Base exception for hint system operations."""
    pass


class HintNotFoundError(HintSystemError):
    """Exception raised when hint is not found."""
    pass


class HintUnlockError(HintSystemError):
    """Exception raised when hint unlock fails."""
    pass


class GamificationAPIError(HintSystemError):
    """Exception raised when gamification API call fails."""
    pass


class Hint:
    """Hint data model."""

    def __init__(self, hint_id: str, content: str, fragment_id: str,
                 unlock_conditions: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize hint.

        Args:
            hint_id (str): Unique identifier for the hint
            content (str): Hint content text
            fragment_id (str): Associated narrative fragment ID
            unlock_conditions (Dict[str, Any], optional): Conditions required to unlock hint
            metadata (Dict[str, Any], optional): Additional hint metadata
        """
        self.hint_id = hint_id
        self.content = content
        self.fragment_id = fragment_id
        self.unlock_conditions = unlock_conditions or {}
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class HintSystem:
    """Manages narrative hints and unlocking logic.

    Purpose: Manages narrative hints (pistas) with conditional unlocking logic.

    Interfaces:
    - unlock_hint(user_id: str, hint_id: str) -> bool
    - get_user_hints(user_id: str) -> List[Hint]

    Dependencies: Item Manager (Gamification), MongoDB
    Reuses: Cross-module API patterns from existing services
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus,
                 gamification_api_url: str = "http://localhost:8001/api/v1/gamification"):
        """Initialize the hint system.

        Args:
            mongodb_handler (MongoDBHandler): MongoDB handler instance
            event_bus (EventBus): Event bus instance
            gamification_api_url (str): Base URL for gamification API
        """
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.gamification_api_url = gamification_api_url

        # Register event handlers
        self._register_event_handlers()

        logger.info("HintSystem initialized")

    def _register_event_handlers(self) -> None:
        """Register event handlers for reaction_detected events."""
        try:
            # Register handler for reaction_detected events (requirement 4.3)
            self.event_bus.subscribe("reaction_detected", self._handle_reaction_detected)
            logger.debug("Registered event handlers")
        except Exception as e:
            logger.warning("Failed to register event handlers: %s", str(e))

    async def unlock_hint(self, user_id: str, hint_id: str) -> bool:
        """Unlock a narrative hint for a user.

        Implements requirement 1.3: WHEN narrative pistas (hints) are unlocked
        THEN the system SHALL store them in the user's mochila (backpack) collection via API

        Args:
            user_id (str): User identifier
            hint_id (str): Hint identifier to unlock

        Returns:
            bool: True if hint was successfully unlocked, False otherwise

        Raises:
            HintNotFoundError: If hint is not found
            HintUnlockError: If hint unlock fails
        """
        logger.info("Unlocking hint %s for user %s", hint_id, user_id)

        try:
            # Get hint from database
            hint = await self._get_hint_by_id(hint_id)
            if not hint:
                raise HintNotFoundError(f"Hint not found: {hint_id}")

            # Check if user already has this hint
            user_hints = await self.get_user_hints(user_id)
            if any(h.hint_id == hint_id for h in user_hints):
                logger.debug("User %s already has hint %s", user_id, hint_id)
                return True

            # Check unlock conditions
            if not await self._check_unlock_conditions(user_id, hint.unlock_conditions):
                logger.debug("Unlock conditions not met for hint %s", hint_id)
                return False

            # Store hint in user's mochila via gamification API
            success = await self._store_hint_in_mochila(user_id, hint)
            if not success:
                raise HintUnlockError(f"Failed to store hint in mochila: {hint_id}")

            # Publish hint unlocked event
            await self._publish_hint_unlocked_event(user_id, hint_id, hint.fragment_id)

            logger.info("Successfully unlocked hint %s for user %s", hint_id, user_id)
            return True

        except HintNotFoundError:
            raise
        except HintUnlockError:
            raise
        except Exception as e:
            logger.error("Error unlocking hint %s for user %s: %s", hint_id, user_id, str(e))
            raise HintUnlockError(f"Failed to unlock hint: {str(e)}")

    async def get_user_hints(self, user_id: str) -> List[Hint]:
        """Get all hints unlocked by a user.

        Args:
            user_id (str): User identifier

        Returns:
            List[Hint]: List of hints unlocked by the user
        """
        logger.debug("Getting hints for user %s", user_id)

        try:
            # Get user hints from gamification API (mochila items with category "hint")
            hints = await self._get_user_hints_from_mochila(user_id)

            logger.debug("Found %d hints for user %s", len(hints), user_id)
            return hints

        except Exception as e:
            logger.error("Error getting hints for user %s: %s", user_id, str(e))
            return []

    async def create_hint(self, hint_id: str, content: str, fragment_id: str,
                         unlock_conditions: Optional[Dict[str, Any]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new hint in the system.

        Args:
            hint_id (str): Unique identifier for the hint
            content (str): Hint content text
            fragment_id (str): Associated narrative fragment ID
            unlock_conditions (Dict[str, Any], optional): Conditions required to unlock hint
            metadata (Dict[str, Any], optional): Additional hint metadata

        Returns:
            bool: True if hint was created successfully, False otherwise
        """
        logger.info("Creating hint %s for fragment %s", hint_id, fragment_id)

        try:
            # Get hints collection
            hints_collection = self.mongodb_handler.get_narrative_fragments_collection()

            # Create hint document
            hint_doc = {
                "hint_id": hint_id,
                "type": "hint",
                "content": content,
                "fragment_id": fragment_id,
                "unlock_conditions": unlock_conditions or {},
                "metadata": metadata or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Insert hint
            result = hints_collection.insert_one(hint_doc)

            if result.inserted_id:
                logger.info("Successfully created hint %s", hint_id)
                return True
            else:
                logger.warning("Failed to create hint %s", hint_id)
                return False

        except Exception as e:
            logger.error("Error creating hint %s: %s", hint_id, str(e))
            return False

    async def _get_hint_by_id(self, hint_id: str) -> Optional[Hint]:
        """Get hint by ID from database.

        Args:
            hint_id (str): Hint identifier

        Returns:
            Optional[Hint]: Hint instance if found, None otherwise
        """
        try:
            hints_collection = self.mongodb_handler.get_narrative_fragments_collection()

            hint_doc = hints_collection.find_one({
                "hint_id": hint_id,
                "type": "hint"
            })

            if hint_doc:
                return Hint(
                    hint_id=hint_doc["hint_id"],
                    content=hint_doc["content"],
                    fragment_id=hint_doc["fragment_id"],
                    unlock_conditions=hint_doc.get("unlock_conditions", {}),
                    metadata=hint_doc.get("metadata", {})
                )

            return None

        except Exception as e:
            logger.error("Error getting hint %s: %s", hint_id, str(e))
            return None

    async def _check_unlock_conditions(self, user_id: str, conditions: Dict[str, Any]) -> bool:
        """Check if unlock conditions are met for a user.

        Args:
            user_id (str): User identifier
            conditions (Dict[str, Any]): Unlock conditions to check

        Returns:
            bool: True if conditions are met, False otherwise
        """
        if not conditions:
            return True  # No conditions means always unlockable

        try:
            # Example conditions that could be checked:
            # - reaction_count: minimum number of reactions
            # - fragment_completion: specific fragments completed
            # - besitos_balance: minimum besitos balance

            # For now, implement basic reaction count check
            if "min_reactions" in conditions:
                # This would require tracking user reactions
                # For now, assume condition is met
                return True

            return True

        except Exception as e:
            logger.error("Error checking unlock conditions for user %s: %s", user_id, str(e))
            return False

    async def _store_hint_in_mochila(self, user_id: str, hint: Hint) -> bool:
        """Store hint in user's mochila via gamification API.

        Implements requirement 1.3: store hints in user's mochila collection via API

        Args:
            user_id (str): User identifier
            hint (Hint): Hint to store

        Returns:
            bool: True if successfully stored, False otherwise
        """
        try:
            # Prepare item data for gamification API
            item_data = {
                "user_id": user_id,
                "item_id": f"hint_{hint.hint_id}",
                "name": f"Pista: {hint.hint_id}",
                "description": hint.content,
                "category": "collectible",
                "rarity": "common",
                "quantity": 1,
                "value": 0,
                "emoji": "💡",
                "effects": {
                    "type": "narrative_hint",
                    "hint_id": hint.hint_id,
                    "fragment_id": hint.fragment_id
                },
                "equipped": False,
                "tradeable": False,
                "metadata": {
                    **hint.metadata,
                    "hint_type": "narrative",
                    "unlock_source": "narrative_system"
                }
            }

            # Make API call to gamification service
            url = f"{self.gamification_api_url}/items"
            timeout = 10  # 10 second timeout

            # Use sync requests since we're in an async context but calling external API
            # In a production environment, use aiohttp for async HTTP calls
            response = requests.post(
                url,
                json=item_data,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )

            if response.status_code == 201:
                logger.debug("Successfully stored hint %s in mochila for user %s", hint.hint_id, user_id)
                return True
            else:
                logger.warning("Failed to store hint in mochila. Status: %d, Response: %s",
                             response.status_code, response.text)
                return False

        except (ConnectionError, Timeout) as e:
            logger.error("Connection error storing hint in mochila: %s", str(e))
            raise GamificationAPIError(f"Connection error: {str(e)}")
        except RequestException as e:
            logger.error("Request error storing hint in mochila: %s", str(e))
            raise GamificationAPIError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error("Error storing hint %s in mochila for user %s: %s", hint.hint_id, user_id, str(e))
            return False

    async def _get_user_hints_from_mochila(self, user_id: str) -> List[Hint]:
        """Get user hints from mochila via gamification API.

        Args:
            user_id (str): User identifier

        Returns:
            List[Hint]: List of hints from user's mochila
        """
        try:
            # Make API call to get user items filtered by hint category
            url = f"{self.gamification_api_url}/users/{user_id}/items"
            params = {"category": "collectible", "type": "narrative_hint"}
            timeout = 10

            response = requests.get(
                url,
                params=params,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )

            if response.status_code == 200:
                items = response.json().get("items", [])
                hints = []

                for item in items:
                    if (item.get("effects", {}).get("type") == "narrative_hint" and
                        "hint_id" in item.get("effects", {})):

                        hint = Hint(
                            hint_id=item["effects"]["hint_id"],
                            content=item["description"],
                            fragment_id=item["effects"].get("fragment_id", ""),
                            unlock_conditions={},
                            metadata=item.get("metadata", {})
                        )
                        hints.append(hint)

                return hints
            else:
                logger.warning("Failed to get user hints from mochila. Status: %d", response.status_code)
                return []

        except (ConnectionError, Timeout) as e:
            logger.error("Connection error getting user hints: %s", str(e))
            return []
        except RequestException as e:
            logger.error("Request error getting user hints: %s", str(e))
            return []
        except Exception as e:
            logger.error("Error getting hints for user %s: %s", user_id, str(e))
            return []

    async def _publish_hint_unlocked_event(self, user_id: str, hint_id: str, fragment_id: str) -> None:
        """Publish hint unlocked event to the event bus.

        Args:
            user_id (str): User identifier
            hint_id (str): Hint identifier
            fragment_id (str): Fragment identifier
        """
        try:
            # Create hint unlocked event
            event = create_event(
                "narrative_hint_unlocked",
                user_id=user_id,
                hint_id=hint_id,
                fragment_id=fragment_id,
                metadata={"source": "hint_system"}
            )

            # Publish to event bus
            await self.event_bus.publish("narrative_hint_unlocked", event.dict())

            logger.debug("Published hint unlocked event for user: %s, hint: %s", user_id, hint_id)

        except Exception as e:
            logger.warning("Failed to publish hint unlocked event: %s", str(e))

    async def _handle_reaction_detected(self, event_data: Dict[str, Any]) -> None:
        """Handle reaction_detected events to potentially unlock hints.

        Implements requirement 4.3: WHEN a reaction_detected event occurs
        THEN narrative SHALL potentially unlock pistas

        Args:
            event_data (Dict[str, Any]): Event data from reaction_detected event
        """
        try:
            user_id = event_data.get("user_id")
            content_id = event_data.get("content_id")
            reaction_type = event_data.get("reaction_type")

            if not user_id or not content_id:
                logger.warning("Invalid reaction_detected event data: missing user_id or content_id")
                return

            logger.debug("Processing reaction_detected event for user %s, content %s, reaction %s",
                        user_id, content_id, reaction_type)

            # Check if this reaction should unlock any hints
            await self._check_reaction_based_unlocks(user_id, content_id, reaction_type)

        except Exception as e:
            logger.error("Error handling reaction_detected event: %s", str(e))

    async def _check_reaction_based_unlocks(self, user_id: str, content_id: str, reaction_type: str) -> None:
        """Check if reaction should unlock any hints.

        Args:
            user_id (str): User identifier
            content_id (str): Content identifier that was reacted to
            reaction_type (str): Type of reaction
        """
        try:
            # Get hints that might be unlocked by this reaction
            hints_collection = self.mongodb_handler.get_narrative_fragments_collection()

            # Find hints with reaction-based unlock conditions
            potential_hints = hints_collection.find({
                "type": "hint",
                "unlock_conditions.trigger": "reaction",
                "unlock_conditions.content_id": content_id
            })

            for hint_doc in potential_hints:
                hint_id = hint_doc["hint_id"]
                conditions = hint_doc.get("unlock_conditions", {})

                # Check if reaction type matches (if specified)
                required_reaction = conditions.get("reaction_type")
                if required_reaction and required_reaction != reaction_type:
                    continue

                # Try to unlock the hint
                try:
                    success = await self.unlock_hint(user_id, hint_id)
                    if success:
                        logger.info("Unlocked hint %s for user %s via reaction", hint_id, user_id)
                except Exception as e:
                    logger.warning("Failed to unlock hint %s for user %s: %s", hint_id, user_id, str(e))

        except Exception as e:
            logger.error("Error checking reaction-based unlocks: %s", str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the hint system.

        Returns:
            Dict[str, Any]: Health status information
        """
        logger.debug("Performing hint system health check")

        health_status = {
            "status": "healthy",
            "mongodb_connected": True,
            "event_bus_connected": self.event_bus.is_connected,
            "gamification_api_available": True,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Test MongoDB connection
        try:
            self.mongodb_handler.get_narrative_fragments_collection().find_one({}, {"_id": 1})
        except Exception as e:
            health_status["mongodb_connected"] = False
            health_status["mongodb_error"] = str(e)
            health_status["status"] = "degraded"

        # Test gamification API connection
        try:
            response = requests.get(
                f"{self.gamification_api_url}/health",
                timeout=5
            )
            if response.status_code != 200:
                health_status["gamification_api_available"] = False
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["gamification_api_available"] = False
            health_status["gamification_api_error"] = str(e)
            health_status["status"] = "degraded"

        # Overall status
        if not health_status["mongodb_connected"] or not health_status["event_bus_connected"]:
            health_status["status"] = "unhealthy"

        return health_status
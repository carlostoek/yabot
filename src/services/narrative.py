"""
NarrativeService for the YABOT system.

This module provides narrative management operations for the YABOT system,
implementing the requirements specified in fase1 specification section 4.2.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.database.manager import DatabaseManager
from src.services.subscription import SubscriptionService
from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NarrativeServiceError(Exception):
    """Base exception for narrative service operations."""
    pass


class NarrativeFragmentNotFoundError(NarrativeServiceError):
    """Exception raised when narrative fragment is not found."""
    pass


class NarrativeService:
    """Service for managing narrative fragments and story content."""
    
    def __init__(self, database_manager: DatabaseManager, 
                 subscription_service: SubscriptionService, 
                 event_bus: EventBus):
        """Initialize the narrative service.
        
        Args:
            database_manager (DatabaseManager): Database manager instance
            subscription_service (SubscriptionService): Subscription service instance
            event_bus (EventBus): Event bus instance
        """
        self.database_manager = database_manager
        self.subscription_service = subscription_service
        self.event_bus = event_bus
        logger.info("NarrativeService initialized")
    
    async def create_narrative_fragment(self, fragment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new narrative fragment in MongoDB.
        
        Args:
            fragment_data (Dict[str, Any]): Narrative fragment data
            
        Returns:
            Dict[str, Any]: Created narrative fragment data
            
        Raises:
            NarrativeServiceError: If fragment creation fails
        """
        logger.info("Creating new narrative fragment: %s", fragment_data.get("title", "unknown"))
        
        try:
            # Generate fragment ID if not provided
            if "fragment_id" not in fragment_data:
                fragment_data["fragment_id"] = str(uuid.uuid4())
            
            # Set creation timestamp
            if "created_at" not in fragment_data:
                fragment_data["created_at"] = datetime.utcnow()
            
            # Create fragment in MongoDB
            fragment = self._create_fragment_in_db(fragment_data)
            
            if not fragment:
                raise NarrativeServiceError("Failed to create narrative fragment in database")
            
            logger.info("Successfully created narrative fragment: %s", fragment_data["fragment_id"])
            return fragment
            
        except Exception as e:
            logger.error("Error creating narrative fragment: %s", str(e))
            raise NarrativeServiceError(f"Failed to create narrative fragment: {str(e)}")
    
    def _create_fragment_in_db(self, fragment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create narrative fragment in MongoDB database.
        
        Args:
            fragment_data (Dict[str, Any]): Narrative fragment data
            
        Returns:
            Optional[Dict[str, Any]]: Created fragment data or None if failed
        """
        try:
            db = self.database_manager.get_mongo_db()
            fragments_collection = db["narrative_fragments"]
            
            # Insert fragment
            result = fragments_collection.insert_one(fragment_data)
            
            if result.acknowledged:
                # Retrieve the created fragment
                fragment = fragments_collection.find_one({"_id": result.inserted_id})
                if fragment:
                    # Remove MongoDB-specific fields
                    fragment.pop("_id", None)
                    logger.debug("Created narrative fragment in MongoDB: %s", fragment_data.get("fragment_id"))
                    return fragment
            
            return None
            
        except Exception as e:
            logger.error("Error creating narrative fragment in MongoDB: %s", str(e))
            return None
    
    async def get_narrative_fragment(self, fragment_id: str) -> Dict[str, Any]:
        """Get narrative fragment by ID.
        
        Args:
            fragment_id (str): Narrative fragment ID
            
        Returns:
            Dict[str, Any]: Narrative fragment data
            
        Raises:
            NarrativeFragmentNotFoundError: If fragment is not found
            NarrativeServiceError: If operation fails
        """
        logger.debug("Retrieving narrative fragment: %s", fragment_id)
        
        try:
            fragment = self._get_fragment_from_db(fragment_id)
            
            if fragment is None:
                raise NarrativeFragmentNotFoundError(f"Narrative fragment not found: {fragment_id}")
            
            logger.debug("Successfully retrieved narrative fragment: %s", fragment_id)
            return fragment
            
        except NarrativeFragmentNotFoundError:
            raise
        except Exception as e:
            logger.error("Error retrieving narrative fragment: %s", str(e))
            raise NarrativeServiceError(f"Failed to retrieve narrative fragment: {str(e)}")
    
    def _get_fragment_from_db(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """Get narrative fragment from MongoDB database.
        
        Args:
            fragment_id (str): Narrative fragment ID
            
        Returns:
            Optional[Dict[str, Any]]: Narrative fragment data or None if not found
        """
        try:
            db = self.database_manager.get_mongo_db()
            fragments_collection = db["narrative_fragments"]
            
            fragment = fragments_collection.find_one({"fragment_id": fragment_id})
            
            if fragment:
                # Remove MongoDB-specific fields
                fragment.pop("_id", None)
                logger.debug("Retrieved narrative fragment from MongoDB: %s", fragment_id)
                return fragment
            
            return None
            
        except Exception as e:
            logger.error("Error retrieving narrative fragment from MongoDB: %s", str(e))
            return None
    
    async def update_narrative_fragment(self, fragment_id: str, updates: Dict[str, Any]) -> bool:
        """Update narrative fragment data.
        
        Args:
            fragment_id (str): Narrative fragment ID
            updates (Dict[str, Any]): Fragment updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Updating narrative fragment: %s", fragment_id)
        
        try:
            # Remove protected fields from updates
            protected_fields = {"fragment_id", "created_at"}
            filtered_updates = {k: v for k, v in updates.items() if k not in protected_fields}
            
            if not filtered_updates:
                logger.warning("No valid updates provided for fragment: %s", fragment_id)
                return True
            
            # Update fragment in database
            success = self._update_fragment_in_db(fragment_id, filtered_updates)
            
            if success:
                logger.info("Successfully updated narrative fragment: %s", fragment_id)
            else:
                logger.warning("No changes made to narrative fragment: %s", fragment_id)
            
            return success
            
        except Exception as e:
            logger.error("Error updating narrative fragment: %s", str(e))
            return False
    
    def _update_fragment_in_db(self, fragment_id: str, updates: Dict[str, Any]) -> bool:
        """Update narrative fragment in MongoDB database.
        
        Args:
            fragment_id (str): Narrative fragment ID
            updates (Dict[str, Any]): Fragment updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = self.database_manager.get_mongo_db()
            fragments_collection = db["narrative_fragments"]
            
            # Add updated timestamp
            updates["updated_at"] = datetime.utcnow()
            
            # Update fragment
            result = fragments_collection.update_one(
                {"fragment_id": fragment_id},
                {"$set": updates}
            )
            
            success = result.modified_count > 0
            logger.debug("Updated narrative fragment in MongoDB: %s", fragment_id)
            return success
            
        except Exception as e:
            logger.error("Error updating narrative fragment in MongoDB: %s", str(e))
            return False
    
    async def delete_narrative_fragment(self, fragment_id: str) -> bool:
        """Delete a narrative fragment.
        
        Args:
            fragment_id (str): Narrative fragment ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Deleting narrative fragment: %s", fragment_id)
        
        try:
            # Delete fragment from database
            success = self._delete_fragment_from_db(fragment_id)
            
            if success:
                logger.info("Successfully deleted narrative fragment: %s", fragment_id)
            else:
                logger.warning("Failed to delete narrative fragment: %s", fragment_id)
            
            return success
            
        except Exception as e:
            logger.error("Error deleting narrative fragment: %s", str(e))
            return False
    
    def _delete_fragment_from_db(self, fragment_id: str) -> bool:
        """Delete narrative fragment from MongoDB database.
        
        Args:
            fragment_id (str): Narrative fragment ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = self.database_manager.get_mongo_db()
            fragments_collection = db["narrative_fragments"]
            
            result = fragments_collection.delete_one({"fragment_id": fragment_id})
            success = result.deleted_count > 0
            
            logger.debug("Deleted narrative fragment from MongoDB: %s", fragment_id)
            return success
            
        except Exception as e:
            logger.error("Error deleting narrative fragment from MongoDB: %s", str(e))
            return False
    
    async def get_narrative_fragments_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all narrative fragments with a specific tag.
        
        Args:
            tag (str): Tag to search for
            
        Returns:
            List[Dict[str, Any]]: List of narrative fragments with the tag
        """
        logger.debug("Retrieving narrative fragments by tag: %s", tag)
        
        try:
            fragments = self._get_fragments_by_tag_from_db(tag)
            logger.debug("Found %d narrative fragments with tag: %s", len(fragments), tag)
            return fragments
            
        except Exception as e:
            logger.error("Error retrieving narrative fragments by tag: %s", str(e))
            return []
    
    def _get_fragments_by_tag_from_db(self, tag: str) -> List[Dict[str, Any]]:
        """Get narrative fragments by tag from MongoDB database.
        
        Args:
            tag (str): Tag to search for
            
        Returns:
            List[Dict[str, Any]]: List of narrative fragments with the tag
        """
        try:
            db = self.database_manager.get_mongo_db()
            fragments_collection = db["narrative_fragments"]
            
            # Find fragments with the specified tag
            cursor = fragments_collection.find({"metadata.tags": tag})
            
            fragments = []
            for fragment in cursor:
                # Remove MongoDB-specific fields
                fragment.pop("_id", None)
                fragments.append(fragment)
            
            logger.debug("Retrieved %d narrative fragments with tag from MongoDB: %s", len(fragments), tag)
            return fragments
            
        except Exception as e:
            logger.error("Error retrieving narrative fragments by tag from MongoDB: %s", str(e))
            return []
    
    async def get_vip_narrative_fragment(self, fragment_id: str, user_id: str) -> Dict[str, Any]:
        """Get a VIP narrative fragment if user has VIP access.
        
        Args:
            fragment_id (str): Narrative fragment ID
            user_id (str): User ID requesting access
            
        Returns:
            Dict[str, Any]: Narrative fragment data
            
        Raises:
            NarrativeFragmentNotFoundError: If fragment is not found
            NarrativeServiceError: If user doesn't have VIP access or operation fails
        """
        logger.debug("Retrieving VIP narrative fragment: %s for user: %s", fragment_id, user_id)
        
        try:
            # Check if user has VIP access
            has_vip_access = await self.subscription_service.validate_vip_access(user_id)
            
            if not has_vip_access:
                raise NarrativeServiceError(f"User {user_id} does not have VIP access to fragment {fragment_id}")
            
            # Get the fragment
            fragment = await self.get_narrative_fragment(fragment_id)
            
            # Check if fragment requires VIP access
            requires_vip = fragment.get("metadata", {}).get("vip_required", False)
            
            if not requires_vip:
                logger.warning("Fragment %s does not require VIP access but VIP access was checked", fragment_id)
            
            logger.debug("Successfully retrieved VIP narrative fragment: %s for user: %s", fragment_id, user_id)
            return fragment
            
        except NarrativeFragmentNotFoundError:
            raise
        except NarrativeServiceError:
            raise
        except Exception as e:
            logger.error("Error retrieving VIP narrative fragment: %s", str(e))
            raise NarrativeServiceError(f"Failed to retrieve VIP narrative fragment: {str(e)}")

    async def get_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """Get a narrative fragment by its ID"""
        try:
            return await self.get_narrative_fragment(fragment_id)
        except NarrativeFragmentNotFoundError:
            return None
        except Exception as e:
            logger.error("Error getting fragment: %s", str(e))
            return None

    async def get_personalized_content(
        self,
        user_id: str,
        fragment_id: str,
        emotional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get personalized narrative content based on user's emotional signature.

        This method implements REQ-3 and REQ-4 requirements by integrating with the
        emotional intelligence system to provide dynamic content personalization
        and emotional memory continuity.

        Args:
            user_id (str): User ID requesting personalized content
            fragment_id (str): Narrative fragment ID to personalize
            emotional_context (Dict[str, Any]): Current emotional context including
                                               conversation state and emotional metrics

        Returns:
            Dict[str, Any]: Personalized content including:
                           - content: The personalized narrative text
                           - personalization_details: Details about applied personalizations
                           - memory_integration: Information about incorporated memories
                           - emotional_context: Applied emotional context
                           - fallback_applied: Whether graceful degradation was used

        Raises:
            NarrativeFragmentNotFoundError: If the base fragment is not found
            NarrativeServiceError: If personalization fails
        """
        logger.debug("Getting personalized content for user %s, fragment %s", user_id, fragment_id)

        try:
            # 1. Get base narrative fragment using existing pattern
            base_fragment = await self.get_narrative_fragment(fragment_id)

            # 2. Try to get emotional intelligence service for personalization
            personalized_content = None
            fallback_applied = False

            try:
                # Attempt to use emotional intelligence for personalization
                personalized_content = await self._get_emotional_personalization(
                    user_id, fragment_id, base_fragment, emotional_context
                )
            except Exception as e:
                logger.warning("Emotional personalization failed, using graceful degradation: %s", str(e))
                fallback_applied = True

            # 3. Apply graceful degradation if emotional analysis is unavailable
            if not personalized_content or fallback_applied:
                personalized_content = await self._apply_graceful_degradation(
                    user_id, base_fragment, emotional_context
                )
                fallback_applied = True

            # 4. Ensure content consistency and publish event
            final_content = self._ensure_narrative_consistency(
                personalized_content, base_fragment, fallback_applied
            )

            # 5. Publish content personalization event for cross-module coordination
            try:
                event = create_event(
                    "narrative_content_personalized",
                    user_id=user_id,
                    fragment_id=fragment_id,
                    fallback_applied=fallback_applied,
                    personalization_applied=not fallback_applied,
                    emotional_context_available=bool(emotional_context)
                )
                await self.event_bus.publish("narrative_content_personalized", event.dict())
            except Exception as e:
                logger.warning("Failed to publish narrative personalization event: %s", str(e))

            logger.info(
                "Personalized content for user %s, fragment %s (fallback: %s)",
                user_id, fragment_id, fallback_applied
            )

            return final_content

        except NarrativeFragmentNotFoundError:
            raise
        except Exception as e:
            logger.error("Error getting personalized content: %s", str(e))
            raise NarrativeServiceError(f"Failed to get personalized content: {str(e)}")

    async def _get_emotional_personalization(
        self,
        user_id: str,
        fragment_id: str,
        base_fragment: Dict[str, Any],
        emotional_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get emotional personalization through the emotional intelligence service.

        Args:
            user_id (str): User ID
            fragment_id (str): Fragment ID
            base_fragment (Dict[str, Any]): Base narrative fragment
            emotional_context (Dict[str, Any]): Emotional context

        Returns:
            Optional[Dict[str, Any]]: Personalized content or None if unavailable
        """
        try:
            # Attempt emotional intelligence integration with graceful fallback
            # This provides a hook for future emotional intelligence service integration
            logger.debug("Attempting emotional intelligence integration for content personalization")

            # Try to get user's emotional signature directly from database for basic personalization
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            user_doc = users_collection.find_one(
                {"user_id": user_id},
                {
                    "emotional_signature": 1,
                    "state.emotional_journey": 1,
                    "name": 1
                }
            )

            if not user_doc:
                logger.debug("User not found for emotional personalization")
                return None

            # Extract available emotional data
            emotional_signature = user_doc.get("emotional_signature", {})
            emotional_journey = user_doc.get("state", {}).get("emotional_journey", {})

            # Apply basic emotional personalization based on available data
            content = base_fragment.get("text", "")
            personalization_applied = []

            # Apply archetype-based tone if available
            archetype = emotional_signature.get("archetype")
            if archetype and "variants" in base_fragment and archetype in base_fragment["variants"]:
                content = base_fragment["variants"][archetype]
                personalization_applied.append(f"archetype_{archetype}_variant")

            # Apply level-based adaptation if available
            current_level = emotional_journey.get("current_level", 1)
            if current_level > 3:  # Diván levels
                content = self._adapt_for_advanced_level(content)
                personalization_applied.append("advanced_level_adaptation")

            # Apply basic memory callbacks simulation for demonstration
            memory_callbacks = await self._simulate_memory_callbacks(user_id, emotional_context)

            # Return structured emotional personalization
            return {
                "content": content,
                "personalization_details": {
                    "emotional_personalization_applied": True,
                    "archetype": archetype,
                    "current_level": current_level,
                    "personalizations_applied": personalization_applied,
                    "original_fragment": fragment_id
                },
                "memory_integration": {
                    "relevant_memories_found": len(memory_callbacks),
                    "callbacks_generated": len(memory_callbacks),
                    "memory_fragments": memory_callbacks
                },
                "emotional_context": {
                    "archetype": archetype,
                    "current_level": current_level,
                    "stage_context": "divan" if current_level > 3 else "los_kinkys"
                },
                "source": "basic_emotional_integration"
            }

        except ImportError:
            logger.debug("Emotional intelligence modules not available")
            return None
        except Exception as e:
            logger.warning("Error getting emotional personalization: %s", str(e))
            return None

    async def _apply_graceful_degradation(
        self,
        user_id: str,
        base_fragment: Dict[str, Any],
        emotional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply graceful degradation when emotional analysis is unavailable.

        Args:
            user_id (str): User ID
            base_fragment (Dict[str, Any]): Base narrative fragment
            emotional_context (Dict[str, Any]): Available emotional context

        Returns:
            Dict[str, Any]: Fallback personalized content
        """
        logger.debug("Applying graceful degradation for user %s", user_id)

        try:
            # 1. Get user's basic profile if available
            user_profile = await self._get_user_basic_profile(user_id)

            # 2. Apply basic personalization based on available data
            content = base_fragment.get("text", "")
            personalization_applied = []

            # 3. Apply user name personalization if available
            if user_profile and user_profile.get("name"):
                # Simple name substitution for basic personalization
                content = content.replace("[USER_NAME]", user_profile["name"])
                personalization_applied.append("name_substitution")

            # 4. Apply basic context awareness
            if emotional_context.get("conversation_context"):
                conversation_context = emotional_context["conversation_context"]

                # Basic mood adaptation based on simple keywords
                if any(word in str(conversation_context).lower() for word in ["happy", "excited", "good"]):
                    content = self._adjust_tone_positive(content)
                    personalization_applied.append("positive_tone_adjustment")
                elif any(word in str(conversation_context).lower() for word in ["sad", "down", "difficult"]):
                    content = self._adjust_tone_supportive(content)
                    personalization_applied.append("supportive_tone_adjustment")

            # 5. Return fallback personalized content
            return {
                "content": content,
                "personalization_details": {
                    "emotional_personalization_applied": False,
                    "fallback_personalizations": personalization_applied,
                    "user_profile_available": bool(user_profile),
                    "original_fragment": base_fragment.get("fragment_id")
                },
                "memory_integration": {
                    "relevant_memories_found": 0,
                    "callbacks_generated": 0,
                    "memory_fragments": []
                },
                "emotional_context": emotional_context,
                "source": "graceful_degradation"
            }

        except Exception as e:
            logger.warning("Error in graceful degradation: %s", str(e))
            # Ultimate fallback - return base content unchanged
            return {
                "content": base_fragment.get("text", ""),
                "personalization_details": {
                    "emotional_personalization_applied": False,
                    "fallback_personalizations": [],
                    "error": str(e)
                },
                "memory_integration": {"relevant_memories_found": 0, "callbacks_generated": 0},
                "emotional_context": emotional_context,
                "source": "minimal_fallback"
            }

    async def _get_user_basic_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get basic user profile for graceful degradation personalization.

        Args:
            user_id (str): User ID

        Returns:
            Optional[Dict[str, Any]]: Basic user profile or None
        """
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            user_doc = users_collection.find_one(
                {"user_id": user_id},
                {"name": 1, "preferences": 1, "created_at": 1}  # Only basic fields
            )

            if user_doc:
                user_doc.pop("_id", None)
                return user_doc

            return None

        except Exception as e:
            logger.warning("Error getting user basic profile: %s", str(e))
            return None

    def _adjust_tone_positive(self, content: str) -> str:
        """Apply positive tone adjustments to content."""
        # Simple positive tone adjustments for graceful degradation
        if "." in content:
            content = content.replace(".", "! ")
        return content

    def _adjust_tone_supportive(self, content: str) -> str:
        """Apply supportive tone adjustments to content."""
        # Simple supportive tone adjustments for graceful degradation
        if not content.startswith(("I understand", "I'm here")):
            content = "I understand. " + content
        return content

    def _adapt_for_advanced_level(self, content: str) -> str:
        """Adapt content for advanced Diana levels (Diván).

        Args:
            content (str): Original content

        Returns:
            str: Content adapted for advanced levels
        """
        # Apply advanced level adaptations for Diván levels
        # More sophisticated language and deeper emotional engagement
        if not any(word in content.lower() for word in ["deeper", "profound", "explore"]):
            # Add depth indicators for advanced levels
            content = content.replace("feel", "deeply feel")
            content = content.replace("understand", "profoundly understand")

        return content

    async def _simulate_memory_callbacks(
        self,
        user_id: str,
        emotional_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Simulate memory callbacks for demonstration of relationship continuity.

        Args:
            user_id (str): User ID
            emotional_context (Dict[str, Any]): Current emotional context

        Returns:
            List[Dict[str, Any]]: List of simulated memory callbacks
        """
        try:
            # Try to get user's interaction history for basic memory simulation
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            user_doc = users_collection.find_one(
                {"user_id": user_id},
                {"current_state.narrative_progress.choices_made": 1}
            )

            if not user_doc:
                return []

            choices_made = user_doc.get("current_state", {}).get("narrative_progress", {}).get("choices_made", [])

            # Generate simple memory callbacks based on recent interactions
            memory_callbacks = []
            if len(choices_made) > 0:
                recent_choice = choices_made[-1]
                memory_callbacks.append({
                    "memory_id": f"choice_{recent_choice.get('fragment_id', 'unknown')}",
                    "callback_text": f"I remember when you chose {recent_choice.get('choice_data', {}).get('choice', 'that path')}...",
                    "emotional_significance": 0.7,
                    "memory_type": "choice_memory"
                })

            # Add context-based memory if emotional context provides clues
            if emotional_context.get("conversation_context", {}).get("previous_topic"):
                memory_callbacks.append({
                    "memory_id": "context_memory",
                    "callback_text": "This reminds me of our earlier conversation about this topic.",
                    "emotional_significance": 0.5,
                    "memory_type": "contextual_memory"
                })

            return memory_callbacks[:2]  # Limit to 2 callbacks for demonstration

        except Exception as e:
            logger.warning("Error simulating memory callbacks: %s", str(e))
            return []

    def _ensure_narrative_consistency(
        self,
        personalized_content: Dict[str, Any],
        base_fragment: Dict[str, Any],
        fallback_applied: bool
    ) -> Dict[str, Any]:
        """Ensure narrative consistency while adapting tone and approach.

        Args:
            personalized_content (Dict[str, Any]): Personalized content
            base_fragment (Dict[str, Any]): Original base fragment
            fallback_applied (bool): Whether fallback was applied

        Returns:
            Dict[str, Any]: Content with consistency ensured
        """
        try:
            # 1. Ensure required narrative structure is maintained
            if not personalized_content.get("content"):
                personalized_content["content"] = base_fragment.get("text", "")

            # 2. Preserve critical narrative elements from base fragment
            base_metadata = base_fragment.get("metadata", {})
            if base_metadata.get("preserve_structure"):
                # Maintain structural elements like choices, transitions
                personalized_content["structural_elements"] = base_metadata.get("structural_elements", {})

            # 3. Add narrative consistency metadata
            personalized_content["narrative_consistency"] = {
                "base_fragment_id": base_fragment.get("fragment_id"),
                "tone_adapted": not fallback_applied,
                "structure_preserved": True,
                "content_length_ratio": len(personalized_content["content"]) / len(base_fragment.get("text", "default"))
            }

            # 4. Add final metadata
            personalized_content.update({
                "fallback_applied": fallback_applied,
                "generation_timestamp": datetime.utcnow().isoformat(),
                "service_version": "narrative_service_v1"
            })

            return personalized_content

        except Exception as e:
            logger.warning("Error ensuring narrative consistency: %s", str(e))
            # Return content as-is if consistency check fails
            personalized_content["consistency_error"] = str(e)
            return personalized_content

    async def record_user_choice(
        self,
        user_id: str,
        fragment_id: str,
        choice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record a user's choice in the narrative"""
        try:
            # Update user's progress in MongoDB
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            # Add the choice to the user's narrative progress
            result = users_collection.update_one(
                {"user_id": user_id},
                {
                    "$push": {
                        "current_state.narrative_progress.choices_made": {
                            "fragment_id": fragment_id,
                            "choice_data": choice_data,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    },
                    "$set": {"updated_at": datetime.utcnow().isoformat()}
                }
            )

            if result.modified_count > 0:
                logger.info("Recorded choice for user %s in fragment %s", user_id, fragment_id)
                # Publish decision_made event
                try:
                    event = create_event(
                        "decision_made",
                        user_id=user_id,
                        fragment_id=fragment_id,
                        choice_data=choice_data
                    )
                    await self.event_bus.publish("decision_made", event.dict())
                except Exception as e:
                    logger.warning("Failed to publish decision_made event: %s", str(e))

                return {"success": True, "user_id": user_id, "fragment_id": fragment_id}
            else:
                logger.warning("No user found to record choice: %s", user_id)
                return {"success": False, "error": "User not found"}

        except Exception as e:
            logger.error("Error recording user choice: %s", str(e))
            return {"success": False, "error": str(e)}

    async def record_emotional_interaction(
        self,
        user_id: str,
        fragment_id: str,
        interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record an emotional interaction for behavioral analysis and memory continuity.

        This method implements REQ-1 (real-time behavioral analysis engine) and REQ-4
        (emotional memory and continuity system) by recording detailed emotional interaction
        data that can be used for personalization and relationship building.

        Args:
            user_id (str): User ID for the interaction
            fragment_id (str): Narrative fragment ID where interaction occurred
            interaction_data (Dict[str, Any]): Detailed interaction data including:
                - response_text: User's response text
                - response_timing: Time taken to respond (seconds)
                - emotional_indicators: Detected emotional markers
                - conversation_context: Current conversation state
                - authenticity_markers: Indicators of response authenticity
                - archetype_indicators: Behavioral archetype indicators
                - significance_score: Emotional significance (0.0-1.0)
                - interaction_type: Type of interaction (choice, free_text, reaction)

        Returns:
            Dict[str, Any]: Result containing:
                - success: Whether recording was successful
                - interaction_id: Unique ID for the recorded interaction
                - memory_created: Whether a significant memory was created
                - events_published: List of events published for cross-module coordination

        Raises:
            NarrativeServiceError: If interaction recording fails
        """
        logger.info("Recording emotional interaction for user %s in fragment %s", user_id, fragment_id)

        try:
            # Generate unique interaction ID
            interaction_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            # Extract and validate interaction data
            response_text = interaction_data.get("response_text", "")
            response_timing = interaction_data.get("response_timing", 0.0)
            emotional_indicators = interaction_data.get("emotional_indicators", {})
            conversation_context = interaction_data.get("conversation_context", {})
            authenticity_markers = interaction_data.get("authenticity_markers", {})
            archetype_indicators = interaction_data.get("archetype_indicators", {})
            significance_score = interaction_data.get("significance_score", 0.0)
            interaction_type = interaction_data.get("interaction_type", "unknown")

            # 1. Store emotional interaction data in MongoDB
            emotional_interaction_doc = {
                "interaction_id": interaction_id,
                "user_id": user_id,
                "fragment_id": fragment_id,
                "timestamp": timestamp,
                "response_data": {
                    "text": response_text,
                    "timing_seconds": response_timing,
                    "length": len(response_text),
                    "type": interaction_type
                },
                "emotional_analysis": {
                    "emotional_indicators": emotional_indicators,
                    "authenticity_markers": authenticity_markers,
                    "archetype_indicators": archetype_indicators,
                    "significance_score": significance_score,
                    "analysis_timestamp": timestamp
                },
                "context": {
                    "conversation_context": conversation_context,
                    "fragment_context": await self._get_fragment_context(fragment_id),
                    "user_journey_stage": await self._get_user_journey_stage(user_id)
                },
                "metadata": {
                    "service_version": "narrative_service_v1",
                    "analysis_source": "emotional_intelligence_integration",
                    "created_at": timestamp
                }
            }

            # Store in emotional_interactions collection
            interaction_stored = await self._store_emotional_interaction(emotional_interaction_doc)

            if not interaction_stored:
                logger.error("Failed to store emotional interaction in database")
                return {"success": False, "error": "Database storage failed"}

            # 2. Update user's emotional interaction history
            user_update_success = await self._update_user_emotional_history(
                user_id, interaction_id, fragment_id, timestamp, significance_score
            )

            # 3. Determine if this is a significant emotional moment for memory creation
            memory_created = False
            memory_id = None

            if significance_score >= 0.7:  # Threshold for significant moments
                memory_id = await self._create_emotional_memory(
                    user_id, fragment_id, interaction_data, emotional_interaction_doc
                )
                memory_created = bool(memory_id)

                if memory_created:
                    logger.info("Created emotional memory %s for significant interaction", memory_id)

            # 4. Publish events for cross-module coordination
            events_published = []

            # Publish emotional interaction event
            try:
                interaction_event = create_event(
                    "user_interaction",
                    user_id=user_id,
                    action="emotional_interaction",
                    context={
                        "fragment_id": fragment_id,
                        "interaction_id": interaction_id,
                        "significance_score": significance_score,
                        "interaction_type": interaction_type,
                        "memory_created": memory_created,
                        "emotional_indicators": emotional_indicators,
                        "archetype_indicators": archetype_indicators
                    }
                )
                await self.event_bus.publish("emotional_interaction_recorded", interaction_event.dict())
                events_published.append("emotional_interaction_recorded")

            except Exception as e:
                logger.warning("Failed to publish emotional interaction event: %s", str(e))

            # Publish emotional milestone event if significant
            if memory_created and significance_score >= 0.8:
                try:
                    milestone_event = create_event(
                        "emotional_milestone_reached",
                        user_id=user_id,
                        milestone_type="significant_emotional_moment",
                        milestone_data={
                            "interaction_id": interaction_id,
                            "fragment_id": fragment_id,
                            "significance_score": significance_score,
                            "memory_id": memory_id
                        },
                        reward_besitos=0,  # No direct reward for emotional milestones
                        unlock_content=None
                    )
                    await self.event_bus.publish("emotional_milestone_reached", milestone_event.dict())
                    events_published.append("emotional_milestone_reached")

                except Exception as e:
                    logger.warning("Failed to publish emotional milestone event: %s", str(e))

            # 5. Trigger emotional signature update if archetype indicators present
            if archetype_indicators and any(v > 0.6 for v in archetype_indicators.values()):
                try:
                    signature_event = create_event(
                        "emotional_signature_updated",
                        user_id=user_id,
                        archetype=max(archetype_indicators, key=archetype_indicators.get),
                        authenticity_score=authenticity_markers.get("authenticity_score", 0.5),
                        signature_strength=max(archetype_indicators.values()),
                        metadata={
                            "interaction_id": interaction_id,
                            "fragment_id": fragment_id,
                            "update_trigger": "emotional_interaction"
                        }
                    )
                    await self.event_bus.publish("emotional_signature_updated", signature_event.dict())
                    events_published.append("emotional_signature_updated")

                except Exception as e:
                    logger.warning("Failed to publish emotional signature update event: %s", str(e))

            logger.info(
                "Successfully recorded emotional interaction %s for user %s (memory: %s, events: %d)",
                interaction_id, user_id, memory_created, len(events_published)
            )

            return {
                "success": True,
                "interaction_id": interaction_id,
                "memory_created": memory_created,
                "memory_id": memory_id,
                "events_published": events_published,
                "significance_score": significance_score,
                "user_update_success": user_update_success
            }

        except Exception as e:
            logger.error("Error recording emotional interaction: %s", str(e))
            raise NarrativeServiceError(f"Failed to record emotional interaction: {str(e)}")

    async def _store_emotional_interaction(self, interaction_doc: Dict[str, Any]) -> bool:
        """Store emotional interaction document in MongoDB.

        Args:
            interaction_doc (Dict[str, Any]): Complete interaction document

        Returns:
            bool: True if successfully stored, False otherwise
        """
        try:
            db = self.database_manager.get_mongo_db()
            emotional_interactions_collection = db["emotional_interactions"]

            result = emotional_interactions_collection.insert_one(interaction_doc)

            if result.acknowledged:
                logger.debug("Stored emotional interaction: %s", interaction_doc["interaction_id"])
                return True

            return False

        except Exception as e:
            logger.error("Error storing emotional interaction: %s", str(e))
            return False

    async def _update_user_emotional_history(
        self,
        user_id: str,
        interaction_id: str,
        fragment_id: str,
        timestamp: datetime,
        significance_score: float
    ) -> bool:
        """Update user's emotional interaction history.

        Args:
            user_id (str): User ID
            interaction_id (str): Interaction ID
            fragment_id (str): Fragment ID
            timestamp (datetime): Interaction timestamp
            significance_score (float): Emotional significance score

        Returns:
            bool: True if successfully updated, False otherwise
        """
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            # Add interaction to user's emotional history
            result = users_collection.update_one(
                {"user_id": user_id},
                {
                    "$push": {
                        "emotional_profile.interaction_history": {
                            "interaction_id": interaction_id,
                            "fragment_id": fragment_id,
                            "timestamp": timestamp.isoformat(),
                            "significance_score": significance_score
                        }
                    },
                    "$set": {
                        "emotional_profile.last_interaction": timestamp.isoformat(),
                        "emotional_profile.total_interactions": {"$add": ["$emotional_profile.total_interactions", 1]},
                        "updated_at": timestamp.isoformat()
                    }
                }
            )

            success = result.modified_count > 0
            if success:
                logger.debug("Updated emotional history for user: %s", user_id)
            else:
                logger.warning("No user found to update emotional history: %s", user_id)

            return success

        except Exception as e:
            logger.error("Error updating user emotional history: %s", str(e))
            return False

    async def _create_emotional_memory(
        self,
        user_id: str,
        fragment_id: str,
        interaction_data: Dict[str, Any],
        interaction_doc: Dict[str, Any]
    ) -> Optional[str]:
        """Create an emotional memory for significant interactions.

        Args:
            user_id (str): User ID
            fragment_id (str): Fragment ID
            interaction_data (Dict[str, Any]): Original interaction data
            interaction_doc (Dict[str, Any]): Stored interaction document

        Returns:
            Optional[str]: Memory ID if created, None otherwise
        """
        try:
            memory_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            # Get user's current Diana level for memory context
            user_journey_stage = await self._get_user_journey_stage(user_id)

            # Create memory document
            memory_doc = {
                "memory_id": memory_id,
                "user_id": user_id,
                "interaction_context": {
                    "fragment_id": fragment_id,
                    "interaction_id": interaction_doc["interaction_id"],
                    "response_text": interaction_data.get("response_text", ""),
                    "conversation_context": interaction_data.get("conversation_context", {})
                },
                "emotional_significance": interaction_data.get("significance_score", 0.0),
                "memory_type": self._determine_memory_type(interaction_data),
                "content_summary": self._generate_memory_summary(interaction_data),
                "diana_response_context": f"User showed significant emotional response in {fragment_id}",
                "recall_triggers": self._extract_recall_triggers(interaction_data),
                "relationship_stage": user_journey_stage.get("current_level", 1),
                "reference_count": 0,
                "last_referenced": None,
                "created_at": timestamp
            }

            # Store in emotional_memories collection
            db = self.database_manager.get_mongo_db()
            memories_collection = db["emotional_memories"]

            result = memories_collection.insert_one(memory_doc)

            if result.acknowledged:
                logger.debug("Created emotional memory: %s", memory_id)
                return memory_id

            return None

        except Exception as e:
            logger.error("Error creating emotional memory: %s", str(e))
            return None

    async def _get_fragment_context(self, fragment_id: str) -> Dict[str, Any]:
        """Get contextual information about a narrative fragment.

        Args:
            fragment_id (str): Fragment ID

        Returns:
            Dict[str, Any]: Fragment context information
        """
        try:
            fragment = await self.get_fragment(fragment_id)
            if fragment:
                return {
                    "title": fragment.get("title", ""),
                    "tags": fragment.get("metadata", {}).get("tags", []),
                    "emotional_theme": fragment.get("metadata", {}).get("emotional_theme", ""),
                    "narrative_stage": fragment.get("metadata", {}).get("narrative_stage", "")
                }

            return {"title": "", "tags": [], "emotional_theme": "", "narrative_stage": ""}

        except Exception as e:
            logger.warning("Error getting fragment context: %s", str(e))
            return {"title": "", "tags": [], "emotional_theme": "", "narrative_stage": ""}

    async def _get_user_journey_stage(self, user_id: str) -> Dict[str, Any]:
        """Get user's current journey stage and Diana level.

        Args:
            user_id (str): User ID

        Returns:
            Dict[str, Any]: Journey stage information
        """
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            user_doc = users_collection.find_one(
                {"user_id": user_id},
                {"state.emotional_journey": 1, "emotional_signature": 1}
            )

            if user_doc:
                emotional_journey = user_doc.get("state", {}).get("emotional_journey", {})
                emotional_signature = user_doc.get("emotional_signature", {})

                return {
                    "current_level": emotional_journey.get("current_level", 1),
                    "stage_name": emotional_journey.get("stage_name", "los_kinkys"),
                    "archetype": emotional_signature.get("archetype", "unknown"),
                    "progression_score": emotional_journey.get("progression_score", 0.0)
                }

            return {"current_level": 1, "stage_name": "los_kinkys", "archetype": "unknown", "progression_score": 0.0}

        except Exception as e:
            logger.warning("Error getting user journey stage: %s", str(e))
            return {"current_level": 1, "stage_name": "los_kinkys", "archetype": "unknown", "progression_score": 0.0}

    def _determine_memory_type(self, interaction_data: Dict[str, Any]) -> str:
        """Determine the type of emotional memory based on interaction data.

        Args:
            interaction_data (Dict[str, Any]): Interaction data

        Returns:
            str: Memory type classification
        """
        significance_score = interaction_data.get("significance_score", 0.0)
        emotional_indicators = interaction_data.get("emotional_indicators", {})

        # Classify based on emotional content and significance
        if significance_score >= 0.9:
            return "breakthrough"
        elif significance_score >= 0.8:
            return "vulnerability"
        elif emotional_indicators.get("trust_markers", 0) > 0.7:
            return "trust_building"
        elif emotional_indicators.get("resistance_markers", 0) > 0.6:
            return "resistance"
        elif emotional_indicators.get("curiosity_markers", 0) > 0.7:
            return "exploration"
        else:
            return "general_emotional"

    def _generate_memory_summary(self, interaction_data: Dict[str, Any]) -> str:
        """Generate a summary of the interaction for memory storage.

        Args:
            interaction_data (Dict[str, Any]): Interaction data

        Returns:
            str: Memory summary
        """
        response_text = interaction_data.get("response_text", "")
        interaction_type = interaction_data.get("interaction_type", "unknown")
        significance_score = interaction_data.get("significance_score", 0.0)

        # Create a concise summary
        if len(response_text) > 100:
            text_summary = response_text[:97] + "..."
        else:
            text_summary = response_text

        return f"{interaction_type.title()} interaction (sig: {significance_score:.2f}): {text_summary}"

    def _extract_recall_triggers(self, interaction_data: Dict[str, Any]) -> List[str]:
        """Extract keywords and triggers for memory recall.

        Args:
            interaction_data (Dict[str, Any]): Interaction data

        Returns:
            List[str]: List of recall trigger keywords
        """
        triggers = []

        # Extract from response text
        response_text = interaction_data.get("response_text", "").lower()
        if response_text:
            # Simple keyword extraction (could be enhanced with NLP)
            important_words = [word for word in response_text.split()
                             if len(word) > 4 and word.isalpha()]
            triggers.extend(important_words[:5])  # Limit to 5 most relevant

        # Add emotional indicators as triggers
        emotional_indicators = interaction_data.get("emotional_indicators", {})
        for emotion, score in emotional_indicators.items():
            if score > 0.6:
                triggers.append(emotion)

        # Add conversation context keywords
        conversation_context = interaction_data.get("conversation_context", {})
        if "topic" in conversation_context:
            triggers.append(conversation_context["topic"])

        return list(set(triggers))  # Remove duplicates


# Convenience function for easy usage
async def create_narrative_service(database_manager: DatabaseManager, 
                                subscription_service: SubscriptionService,
                                event_bus: EventBus) -> NarrativeService:
    """Create and initialize a narrative service instance.
    
    Args:
        database_manager (DatabaseManager): Database manager instance
        subscription_service (SubscriptionService): Subscription service instance
        event_bus (EventBus): Event bus instance
        
    Returns:
        NarrativeService: Initialized narrative service instance
    """
    narrative_service = NarrativeService(database_manager, subscription_service, event_bus)
    return narrative_service

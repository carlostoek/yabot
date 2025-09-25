"""
Fase1 - Task 18
NarrativeService

Implements narrative operations as specified in Requirement 4.2: Core API Endpoints
and the design for narrative fragment operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from src.database.manager import DatabaseManager
from src.services.subscription import SubscriptionService
from src.events.models import ContentViewedEvent, DecisionMadeEvent
from src.utils.logger import LoggerMixin, get_logger


class NarrativeDifficulty(str, Enum):
    """Enumeration for narrative difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class NarrativeType(str, Enum):
    """Enumeration for narrative types"""
    INTRO = "intro"
    ADVENTURE = "adventure"
    PUZZLE = "puzzle"
    CHARACTER = "character"
    LOCATION = "location"


class NarrativeService(LoggerMixin):
    """
    Manages narrative content operations
    """
    
    def __init__(self, db_manager: DatabaseManager, subscription_service: SubscriptionService):
        self.db_manager = db_manager
        self.subscription_service = subscription_service
        # LoggerMixin provides the logger property automatically
    
    async def get_narrative_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get narrative content with metadata
        
        Args:
            fragment_id: ID of the narrative fragment
            
        Returns:
            Narrative fragment data or None if not found
        """
        try:
            self.logger.debug("Retrieving narrative fragment", fragment_id=fragment_id)
            
            fragment = await self.db_manager.get_narrative_from_mongo(fragment_id)
            if fragment:
                self.logger.info("Narrative fragment retrieved", fragment_id=fragment_id)
                return fragment
            else:
                self.logger.warning("Narrative fragment not found", fragment_id=fragment_id)
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving narrative fragment: {str(e)}", fragment_id=fragment_id)
            raise
    
    async def get_user_narrative_progress(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's current narrative progress
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User's narrative progress or None if user not found
        """
        try:
            self.logger.debug("Retrieving user narrative progress", user_id=user_id)
            
            user_context = await self.db_manager.get_user_from_mongo(user_id)
            if not user_context:
                self.logger.warning("User not found", user_id=user_id)
                return None
            
            narrative_progress = user_context.get("current_state", {}).get("narrative_progress", {})
            self.logger.info("User narrative progress retrieved", user_id=user_id)
            return narrative_progress
                
        except Exception as e:
            self.logger.error(f"Error retrieving user narrative progress: {str(e)}", user_id=user_id)
            raise
    
    async def update_user_narrative_progress(self, user_id: str, fragment_id: str, 
                                           choice_id: str = None, **kwargs) -> bool:
        """
        Update user's narrative progress
        
        Args:
            user_id: Telegram user ID
            fragment_id: Current narrative fragment ID
            choice_id: Choice made by the user (optional)
            
        Returns:
            True if update successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Updating user narrative progress", user_id=user_id, fragment_id=fragment_id)
            
            # Get current user state
            user_data = await self.db_manager.get_user_from_mongo(user_id)
            if not user_data:
                self.logger.warning("User not found", user_id=user_id)
                return False
            
            current_progress = user_data.get("current_state", {}).get("narrative_progress", {})
            
            # Update progress
            completed_fragments = current_progress.get("completed_fragments", [])
            if fragment_id not in completed_fragments:
                completed_fragments.append(fragment_id)
            
            choices_made = current_progress.get("choices_made", [])
            if choice_id:
                choices_made.append({
                    "fragment": fragment_id,
                    "choice": choice_id,
                    "timestamp": datetime.utcnow()
                })
            
            # Update user state in MongoDB
            update_data = {
                "$set": {
                    "current_state.narrative_progress": {
                        "current_fragment": fragment_id,
                        "completed_fragments": completed_fragments,
                        "choices_made": choices_made
                    },
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await self.db_manager.update_user_in_mongo(user_id, update_data)
            
            if result:
                self.logger.info("User narrative progress updated", user_id=user_id)
                
                # Publish decision made event if choice was made
                if choice_id and event_bus:
                    event = DecisionMadeEvent(
                        user_id=user_id,
                        choice_id=choice_id,
                        fragment_id=fragment_id,
                        next_fragment_id=fragment_id  # This would come from the choice mapping
                    )
                    await event_bus.publish("decision_made", event.dict())
                
                return True
            else:
                self.logger.warning("Failed to update user narrative progress", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating user narrative progress: {str(e)}", user_id=user_id)
            raise
    
    async def validate_vip_access(self, user_id: str, fragment_id: str) -> bool:
        """
        Check if user has VIP access before allowing access to VIP content
        
        Args:
            user_id: Telegram user ID
            fragment_id: ID of the narrative fragment to access
            
        Returns:
            True if VIP access is granted, False otherwise
        """
        try:
            self.logger.debug("Validating VIP access", user_id=user_id, fragment_id=fragment_id)
            
            # Get the narrative fragment to check if it requires VIP access
            fragment = await self.get_narrative_fragment(fragment_id)
            if not fragment:
                self.logger.warning("Fragment not found", fragment_id=fragment_id)
                return False
            
            # Check if fragment requires VIP access
            vip_required = fragment.get("metadata", {}).get("vip_required", False)
            if not vip_required:
                self.logger.info("Fragment does not require VIP access", fragment_id=fragment_id)
                return True
            
            # Check user subscription status
            has_active_subscription = await self.subscription_service.check_subscription_status(user_id)
            is_vip = False
            
            if has_active_subscription:
                subscription = await self.subscription_service.get_subscription(user_id)
                if subscription and subscription.get("plan_type") == "vip":
                    is_vip = True
            
            if is_vip:
                self.logger.info("VIP access granted", user_id=user_id, fragment_id=fragment_id)
                return True
            else:
                self.logger.info("VIP access denied", user_id=user_id, fragment_id=fragment_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating VIP access: {str(e)}", user_id=user_id, fragment_id=fragment_id)
            raise
    
    async def get_available_choices(self, fragment_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get available choices for a narrative fragment
        
        Args:
            fragment_id: ID of the narrative fragment
            
        Returns:
            List of available choices or None if fragment not found
        """
        try:
            self.logger.debug("Retrieving available choices", fragment_id=fragment_id)
            
            fragment = await self.get_narrative_fragment(fragment_id)
            if fragment:
                choices = fragment.get("choices", [])
                self.logger.info(f"Retrieved {len(choices)} choices", fragment_id=fragment_id)
                return choices
            else:
                self.logger.warning("Fragment not found", fragment_id=fragment_id)
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving choices: {str(e)}", fragment_id=fragment_id)
            raise
    
    async def get_related_fragments(self, fragment_id: str, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get related narrative fragments based on tags
        
        Args:
            fragment_id: ID of the current narrative fragment
            tags: Tags to search for related fragments
            
        Returns:
            List of related narrative fragments
        """
        try:
            self.logger.debug("Retrieving related fragments", fragment_id=fragment_id, tags=tags)
            
            related_fragments = await self.db_manager.get_related_narratives(fragment_id, tags)
            self.logger.info(f"Retrieved {len(related_fragments)} related fragments", fragment_id=fragment_id)
            return related_fragments
                
        except Exception as e:
            self.logger.error(f"Error retrieving related fragments: {str(e)}", fragment_id=fragment_id)
            raise
    
    async def track_content_view(self, user_id: str, content_id: str, content_type: str, **kwargs) -> bool:
        """
        Track when a user views content
        
        Args:
            user_id: Telegram user ID
            content_id: ID of the content viewed
            content_type: Type of content viewed
            
        Returns:
            True if tracking successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Tracking content view", user_id=user_id, content_id=content_id)
            
            # Publish content viewed event
            if event_bus:
                event = ContentViewedEvent(
                    user_id=user_id,
                    content_id=content_id,
                    content_type=content_type
                )
                await event_bus.publish("content_viewed", event.dict())
            
            # Update user's content view history in MongoDB
            update_data = {
                "$push": {
                    "current_state.view_history": {
                        "content_id": content_id,
                        "content_type": content_type,
                        "viewed_at": datetime.utcnow()
                    }
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await self.db_manager.update_user_in_mongo(user_id, update_data)
            
            if result:
                self.logger.info("Content view tracked", user_id=user_id, content_id=content_id)
                return True
            else:
                self.logger.warning("Failed to track content view", user_id=user_id, content_id=content_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error tracking content view: {str(e)}", user_id=user_id, content_id=content_id)
            raise


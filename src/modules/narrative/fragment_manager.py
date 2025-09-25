"""
Narrative Fragment Manager for YABOT

This module provides narrative content storage and retrieval interfaces
with methods for getting fragments, user progress, and updating progress.
It follows the requirements from the modulos-atomicos specification.
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime
import asyncio

from src.database.mongodb import MongoDBHandler
from src.utils.logger import get_logger


class NarrativeFragmentManager:
    """
    Narrative fragment manager providing storage and retrieval of narrative content.
    
    Implements requirements 1.1, 1.4, 1.5 from the modulos-atomicos specification:
    1.1: Handle narrative content storage and retrieval
    1.4: Provide interface for getting user progress
    1.5: Provide interface for updating user progress
    """
    
    def __init__(self, db_handler: MongoDBHandler):
        self.logger = get_logger(self.__class__.__name__)
        self.db = db_handler
        
    async def get_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a narrative fragment by its ID.
        
        Args:
            fragment_id: The fragment ID to search for
            
        Returns:
            Fragment document if found, None otherwise
        """
        try:
            fragment_doc = await self.db.get_narrative_fragment(fragment_id)
            if fragment_doc:
                self.logger.debug("Narrative fragment found", fragment_id=fragment_id)
            else:
                self.logger.debug("Narrative fragment not found", fragment_id=fragment_id)
            return fragment_doc
        except Exception as e:
            self.logger.error(
                "Error retrieving narrative fragment",
                fragment_id=fragment_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def get_user_progress(self, user_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get the narrative progress for a user.
        
        Args:
            user_id: The user ID to retrieve progress for
            
        Returns:
            User document containing narrative progress if found, None otherwise
        """
        try:
            user_doc = await self.db.get_user(user_id)
            if user_doc:
                progress = user_doc.get("narrative_progress", {})
                self.logger.debug("User progress retrieved", user_id=user_id, progress=progress)
                return user_doc
            else:
                self.logger.debug("User not found for progress retrieval", user_id=user_id)
                # Create a default user document with empty narrative progress
                default_user_data = {
                    "user_id": str(user_id),
                    "narrative_progress": {
                        "current_fragment": None,
                        "completed_fragments": [],
                        "unlocked_hints": []
                    }
                }
                # Create the user document with default progress
                success = await self.db.create_user(default_user_data)
                if success:
                    self.logger.info("New user created with default narrative progress", user_id=user_id)
                    return default_user_data
                else:
                    self.logger.error("Failed to create new user with default progress", user_id=user_id)
                    return None
        except Exception as e:
            self.logger.error(
                "Error retrieving user progress",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def update_progress(self, user_id: Union[str, int], progress_update: Dict[str, Any]) -> bool:
        """
        Update the narrative progress for a user.
        
        Args:
            user_id: The user ID to update progress for
            progress_update: Dictionary containing the progress update fields
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Prepare update data with timestamp
            update_data = {
                "narrative_progress": progress_update,
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db.update_user(str(user_id), update_data)
            if result:
                self.logger.debug("User narrative progress updated", user_id=user_id)
                return True
            else:
                self.logger.warning("Failed to update user progress", user_id=user_id)
                return False
        except Exception as e:
            self.logger.error(
                "Error updating user progress",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def append_to_completed_fragments(self, user_id: Union[str, int], fragment_id: str) -> bool:
        """
        Append a fragment ID to the user's completed fragments list.
        
        Args:
            user_id: The user ID
            fragment_id: The fragment ID to add to completed fragments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the user document by adding the fragment_id to completed_fragments array
            result = await self.db.push_to_user_array(
                str(user_id), 
                "narrative_progress.completed_fragments", 
                fragment_id
            )
            
            if result:
                self.logger.debug(
                    "Fragment added to completed list", 
                    user_id=user_id, 
                    fragment_id=fragment_id
                )
                return True
            else:
                self.logger.warning(
                    "Failed to add fragment to completed list", 
                    user_id=user_id, 
                    fragment_id=fragment_id
                )
                return False
        except Exception as e:
            self.logger.error(
                "Error adding fragment to completed list",
                user_id=user_id,
                fragment_id=fragment_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def increment_user_stat(self, user_id: Union[str, int], stat_path: str, increment: int = 1) -> bool:
        """
        Increment a user statistic by a given amount.
        
        Args:
            user_id: The user ID
            stat_path: The path to the statistic in the user document
            increment: The amount to increment by (default 1)
            
        Returns:
            True if increment successful, False otherwise
        """
        try:
            result = await self.db.increment_user_stat(user_id, stat_path, increment)
            if result:
                self.logger.debug(
                    "User statistic incremented", 
                    user_id=user_id, 
                    stat_path=stat_path, 
                    increment=increment
                )
            return result
        except Exception as e:
            self.logger.error(
                "Error incrementing user statistic",
                user_id=user_id,
                stat_path=stat_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
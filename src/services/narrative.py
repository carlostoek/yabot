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
"""
MongoDB Handler for YABOT

This module provides MongoDB collection access methods with proper error handling,
logging, and follows the requirements for database operations.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from src.utils.logger import get_logger


class MongoDBHandler:
    """
    MongoDB handler providing access methods to collections with proper error handling.
    
    Implements requirement 1.2: Database Collections and Tables
    1. WHEN the system starts THEN it SHALL create/verify the following MongoDB collections:
       - Users (dynamic state, preferences, current context)
       - NarrativeFragments (story content, choices, metadata)
       - Items (virtual items, gifts, achievements)
    """
    
    def __init__(self, mongo_db: AsyncIOMotorDatabase):
        self.logger = get_logger(self.__class__.__name__)
        self.db = mongo_db
        
        # Define collections
        self.users_collection: AsyncIOMotorCollection = mongo_db.users
        self.narrative_fragments_collection: AsyncIOMotorCollection = mongo_db.narrative_fragments
        self.items_collection: AsyncIOMotorCollection = mongo_db.items
    
    async def get_user(self, user_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get user data by user ID.
        
        Args:
            user_id: The user ID to search for
            
        Returns:
            User document if found, None otherwise
        """
        try:
            user_doc = await self.users_collection.find_one({"user_id": str(user_id)})
            if user_doc:
                self.logger.debug("User found", user_id=user_id)
            else:
                self.logger.debug("User not found", user_id=user_id)
            return user_doc
        except Exception as e:
            self.logger.error(
                "Error retrieving user from MongoDB",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Create a new user document in MongoDB.
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            True if creation successful, False otherwise
        """
        try:
            # Add timestamp fields
            user_data["created_at"] = datetime.utcnow()
            user_data["updated_at"] = datetime.utcnow()
            
            result = await self.users_collection.insert_one(user_data)
            if result.inserted_id:
                self.logger.info("User created successfully", user_id=user_data.get("user_id"))
                return True
            else:
                self.logger.error("Failed to create user", user_id=user_data.get("user_id"))
                return False
        except Exception as e:
            self.logger.error(
                "Error creating user in MongoDB",
                user_id=user_data.get("user_id"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def update_user(self, user_id: Union[str, int], update_data: Dict[str, Any]) -> bool:
        """
        Update user data in MongoDB.
        
        Args:
            user_id: The user ID to update
            update_data: Dictionary containing updated fields
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Add timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.users_collection.update_one(
                {"user_id": str(user_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                self.logger.debug("User updated successfully", user_id=user_id)
                return True
            else:
                self.logger.warning("No user found to update", user_id=user_id)
                return False
        except Exception as e:
            self.logger.error(
                "Error updating user in MongoDB",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def delete_user(self, user_id: Union[str, int]) -> bool:
        """
        Delete a user from MongoDB.
        
        Args:
            user_id: The user ID to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            result = await self.users_collection.delete_one({"user_id": str(user_id)})
            if result.deleted_count > 0:
                self.logger.info("User deleted successfully", user_id=user_id)
                return True
            else:
                self.logger.warning("No user found to delete", user_id=user_id)
                return False
        except Exception as e:
            self.logger.error(
                "Error deleting user from MongoDB",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def get_narrative_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a narrative fragment by its ID.
        
        Args:
            fragment_id: The fragment ID to search for
            
        Returns:
            Fragment document if found, None otherwise
        """
        try:
            fragment_doc = await self.narrative_fragments_collection.find_one(
                {"fragment_id": fragment_id}
            )
            if fragment_doc:
                self.logger.debug("Narrative fragment found", fragment_id=fragment_id)
            else:
                self.logger.debug("Narrative fragment not found", fragment_id=fragment_id)
            return fragment_doc
        except Exception as e:
            self.logger.error(
                "Error retrieving narrative fragment from MongoDB",
                fragment_id=fragment_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def create_narrative_fragment(self, fragment_data: Dict[str, Any]) -> bool:
        """
        Create a new narrative fragment document in MongoDB.
        
        Args:
            fragment_data: Dictionary containing fragment information
            
        Returns:
            True if creation successful, False otherwise
        """
        try:
            # Add timestamp fields
            fragment_data["created_at"] = datetime.utcnow()
            fragment_data["updated_at"] = datetime.utcnow()
            
            result = await self.narrative_fragments_collection.insert_one(fragment_data)
            if result.inserted_id:
                self.logger.info(
                    "Narrative fragment created successfully", 
                    fragment_id=fragment_data.get("fragment_id")
                )
                return True
            else:
                self.logger.error(
                    "Failed to create narrative fragment", 
                    fragment_id=fragment_data.get("fragment_id")
                )
                return False
        except Exception as e:
            self.logger.error(
                "Error creating narrative fragment in MongoDB",
                fragment_id=fragment_data.get("fragment_id"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def update_narrative_fragment(self, fragment_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a narrative fragment in MongoDB.
        
        Args:
            fragment_id: The fragment ID to update
            update_data: Dictionary containing updated fields
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Add timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.narrative_fragments_collection.update_one(
                {"fragment_id": fragment_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                self.logger.debug("Narrative fragment updated successfully", fragment_id=fragment_id)
                return True
            else:
                self.logger.warning("No narrative fragment found to update", fragment_id=fragment_id)
                return False
        except Exception as e:
            self.logger.error(
                "Error updating narrative fragment in MongoDB",
                fragment_id=fragment_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an item by its ID.
        
        Args:
            item_id: The item ID to search for
            
        Returns:
            Item document if found, None otherwise
        """
        try:
            item_doc = await self.items_collection.find_one({"item_id": item_id})
            if item_doc:
                self.logger.debug("Item found", item_id=item_id)
            else:
                self.logger.debug("Item not found", item_id=item_id)
            return item_doc
        except Exception as e:
            self.logger.error(
                "Error retrieving item from MongoDB",
                item_id=item_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def create_item(self, item_data: Dict[str, Any]) -> bool:
        """
        Create a new item document in MongoDB.
        
        Args:
            item_data: Dictionary containing item information
            
        Returns:
            True if creation successful, False otherwise
        """
        try:
            # Add timestamp fields
            item_data["created_at"] = datetime.utcnow()
            item_data["updated_at"] = datetime.utcnow()
            
            result = await self.items_collection.insert_one(item_data)
            if result.inserted_id:
                self.logger.info("Item created successfully", item_id=item_data.get("item_id"))
                return True
            else:
                self.logger.error("Failed to create item", item_id=item_data.get("item_id"))
                return False
        except Exception as e:
            self.logger.error(
                "Error creating item in MongoDB",
                item_id=item_data.get("item_id"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def update_item(self, item_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update an item in MongoDB.
        
        Args:
            item_id: The item ID to update
            update_data: Dictionary containing updated fields
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Add timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.items_collection.update_one(
                {"item_id": item_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                self.logger.debug("Item updated successfully", item_id=item_id)
                return True
            else:
                self.logger.warning("No item found to update", item_id=item_id)
                return False
        except Exception as e:
            self.logger.error(
                "Error updating item in MongoDB",
                item_id=item_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def find_users_by_criteria(self, criteria: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find users based on criteria.
        
        Args:
            criteria: Dictionary of search criteria
            limit: Maximum number of results to return
            
        Returns:
            List of user documents matching criteria
        """
        try:
            cursor = self.users_collection.find(criteria).limit(limit)
            users = await cursor.to_list(length=limit)
            self.logger.debug("Users found by criteria", count=len(users), criteria=criteria)
            return users
        except Exception as e:
            self.logger.error(
                "Error finding users by criteria in MongoDB",
                criteria=criteria,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def find_narrative_fragments_by_criteria(self, criteria: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find narrative fragments based on criteria.
        
        Args:
            criteria: Dictionary of search criteria
            limit: Maximum number of results to return
            
        Returns:
            List of narrative fragment documents matching criteria
        """
        try:
            cursor = self.narrative_fragments_collection.find(criteria).limit(limit)
            fragments = await cursor.to_list(length=limit)
            self.logger.debug(
                "Narrative fragments found by criteria", 
                count=len(fragments), 
                criteria=criteria
            )
            return fragments
        except Exception as e:
            self.logger.error(
                "Error finding narrative fragments by criteria in MongoDB",
                criteria=criteria,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def find_items_by_criteria(self, criteria: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find items based on criteria.
        
        Args:
            criteria: Dictionary of search criteria
            limit: Maximum number of results to return
            
        Returns:
            List of item documents matching criteria
        """
        try:
            cursor = self.items_collection.find(criteria).limit(limit)
            items = await cursor.to_list(length=limit)
            self.logger.debug("Items found by criteria", count=len(items), criteria=criteria)
            return items
        except Exception as e:
            self.logger.error(
                "Error finding items by criteria in MongoDB",
                criteria=criteria,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def increment_user_stat(self, user_id: Union[str, int], stat_path: str, increment: int = 1) -> bool:
        """
        Increment a user statistic by a given amount.
        
        Args:
            user_id: The user ID
            stat_path: The path to the statistic in the user document (e.g., "stats.messages_sent")
            increment: The amount to increment by (default 1)
            
        Returns:
            True if increment successful, False otherwise
        """
        try:
            result = await self.users_collection.update_one(
                {"user_id": str(user_id)},
                {"$inc": {stat_path: increment}}
            )
            
            if result.modified_count > 0:
                self.logger.debug(
                    "User statistic incremented", 
                    user_id=user_id, 
                    stat_path=stat_path, 
                    increment=increment
                )
                return True
            else:
                self.logger.warning(
                    "No user found to increment statistic", 
                    user_id=user_id, 
                    stat_path=stat_path
                )
                return False
        except Exception as e:
            self.logger.error(
                "Error incrementing user statistic in MongoDB",
                user_id=user_id,
                stat_path=stat_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def push_to_user_array(self, user_id: Union[str, int], array_path: str, value: Any) -> bool:
        """
        Push a value to a user array field.
        
        Args:
            user_id: The user ID
            array_path: The path to the array in the user document (e.g., "items_owned")
            value: The value to push to the array
            
        Returns:
            True if push successful, False otherwise
        """
        try:
            result = await self.users_collection.update_one(
                {"user_id": str(user_id)},
                {"$push": {array_path: value}}
            )
            
            if result.modified_count > 0:
                self.logger.debug(
                    "Value pushed to user array", 
                    user_id=user_id, 
                    array_path=array_path, 
                    value=value
                )
                return True
            else:
                self.logger.warning(
                    "No user found to push to array", 
                    user_id=user_id, 
                    array_path=array_path
                )
                return False
        except Exception as e:
            self.logger.error(
                "Error pushing to user array in MongoDB",
                user_id=user_id,
                array_path=array_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def ensure_user_index(self, field_name: str, unique: bool = False) -> bool:
        """
        Ensure an index exists on a user collection field.
        
        Args:
            field_name: Name of the field to index
            unique: Whether the index should be unique
            
        Returns:
            True if index exists or was created, False otherwise
        """
        try:
            if unique:
                await self.users_collection.create_index(field_name, unique=True)
            else:
                await self.users_collection.create_index(field_name)
            
            self.logger.info(
                "User collection index ensured", 
                field_name=field_name, 
                unique=unique
            )
            return True
        except Exception as e:
            self.logger.error(
                "Error ensuring user index in MongoDB",
                field_name=field_name,
                unique=unique,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def batch_create_users(self, users_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple users in a batch operation.
        
        Args:
            users_data: List of user data dictionaries
            
        Returns:
            Dictionary with results of the batch operation
        """
        if not users_data:
            return {"inserted_count": 0, "errors": []}
        
        try:
            # Add timestamp fields to all users
            for user_data in users_data:
                user_data["created_at"] = datetime.utcnow()
                user_data["updated_at"] = datetime.utcnow()
            
            result = await self.users_collection.insert_many(users_data)
            inserted_count = len(result.inserted_ids)
            
            self.logger.info("Batch user creation completed", inserted_count=inserted_count)
            return {
                "inserted_count": inserted_count,
                "inserted_ids": result.inserted_ids,
                "errors": []
            }
        except Exception as e:
            self.logger.error(
                "Error in batch user creation in MongoDB",
                error=str(e),
                error_type=type(e).__name__
            )
            return {"inserted_count": 0, "errors": [str(e)]}
"""
MongoDB handler for the YABOT system.

This module provides access methods for MongoDB collections as required by the fase1 specification.
"""

from typing import Any, Dict, Optional
from pymongo.database import Database
from pymongo.collection import Collection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBHandler:
    """Handler for MongoDB collections and operations."""
    
    def __init__(self, database: Database):
        """Initialize the MongoDB handler.
        
        Args:
            database (Database): MongoDB database instance
        """
        self._db = database
        logger.info("MongoDBHandler initialized")
    
    def get_users_collection(self) -> Collection:
        """Get the Users collection for user dynamic state management.
        
        Returns:
            Collection: MongoDB collection for user data
        """
        logger.debug("Accessing Users collection")
        return self._db["users"]
    
    def get_narrative_fragments_collection(self) -> Collection:
        """Get the NarrativeFragments collection for story content.
        
        Returns:
            Collection: MongoDB collection for narrative fragments
        """
        logger.debug("Accessing NarrativeFragments collection")
        return self._db["narrative_fragments"]
    
    def get_items_collection(self) -> Collection:
        """Get the Items collection for virtual items.
        
        Returns:
            Collection: MongoDB collection for items
        """
        logger.debug("Accessing Items collection")
        return self._db["items"]
    
    async def initialize_collections(self) -> bool:
        """Initialize and verify MongoDB collections.
        
        Creates indexes and validates schema compatibility for all required collections.
        
        Returns:
            bool: True if all collections were initialized successfully, False otherwise
        """
        try:
            logger.info("Initializing MongoDB collections")
            
            # Initialize Users collection
            users_collection = self.get_users_collection()
            await self._initialize_users_collection(users_collection)
            
            # Initialize NarrativeFragments collection
            narrative_collection = self.get_narrative_fragments_collection()
            await self._initialize_narrative_fragments_collection(narrative_collection)
            
            # Initialize Items collection
            items_collection = self.get_items_collection()
            await self._initialize_items_collection(items_collection)
            
            logger.info("All MongoDB collections initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Error initializing MongoDB collections: %s", str(e))
            return False
    
    async def _initialize_users_collection(self, collection: Collection) -> None:
        """Initialize the Users collection with required indexes.
        
        Args:
            collection (Collection): Users collection
        """
        logger.debug("Initializing Users collection indexes")
        
        # Create indexes for common query patterns
        collection.create_index("user_id", unique=True)
        collection.create_index("current_state.narrative_progress.current_fragment")
        collection.create_index("preferences.language")
        collection.create_index("created_at")
        collection.create_index("updated_at")
        
        logger.debug("Users collection indexes created")
    
    async def _initialize_narrative_fragments_collection(self, collection: Collection) -> None:
        """Initialize the NarrativeFragments collection with required indexes.
        
        Args:
            collection (Collection): NarrativeFragments collection
        """
        logger.debug("Initializing NarrativeFragments collection indexes")
        
        # Create indexes for common query patterns
        collection.create_index("fragment_id", unique=True)
        collection.create_index("metadata.tags")
        collection.create_index("metadata.vip_required")
        collection.create_index("created_at")
        
        logger.debug("NarrativeFragments collection indexes created")
    
    async def _initialize_items_collection(self, collection: Collection) -> None:
        """Initialize the Items collection with required indexes.
        
        Args:
            collection (Collection): Items collection
        """
        logger.debug("Initializing Items collection indexes")
        
        # Create indexes for common query patterns
        collection.create_index("item_id", unique=True)
        collection.create_index("type")
        collection.create_index("metadata.value")
        collection.create_index("created_at")
        
        logger.debug("Items collection indexes created")
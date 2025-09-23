"""
MongoDB emotional collections setup for the Diana Emotional System.

This module provides migration functionality to set up the MongoDB collections
required for the emotional intelligence system, implementing Requirement 6
from the emocional specification.
"""

from typing import Dict, Any, Optional
import logging
from pymongo.database import Database
from pymongo.errors import PyMongoError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmotionalCollectionsMigration:
    """Handles MongoDB migration for emotional intelligence collections."""
    
    def __init__(self, db: Database):
        """Initialize the emotional collections migration handler.
        
        Args:
            db (Database): MongoDB database instance
        """
        self.db = db
        logger.info("EmotionalCollectionsMigration initialized")
    
    def setup_emotional_collections(self) -> bool:
        """Set up all required emotional intelligence collections in MongoDB.
        
        Creates collections for:
        - Emotional signatures and user archetypes
        - Emotional journey states and level progression
        - Memory fragments for relationship continuity
        - Emotional interactions for analysis
        - Emotional milestones and achievements
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        try:
            logger.info("Setting up emotional intelligence collections")
            
            # Setup emotional signatures collection
            if not self._setup_emotional_signatures_collection():
                logger.error("Failed to set up emotional signatures collection")
                return False
            
            # Setup emotional journey collection
            if not self._setup_emotional_journey_collection():
                logger.error("Failed to set up emotional journey collection")
                return False
            
            # Setup memory fragments collection
            if not self._setup_memory_fragments_collection():
                logger.error("Failed to set up memory fragments collection")
                return False
            
            # Setup emotional interactions collection
            if not self._setup_emotional_interactions_collection():
                logger.error("Failed to set up emotional interactions collection")
                return False
            
            # Setup indexes for optimal querying
            if not self._setup_emotional_indexes():
                logger.error("Failed to set up emotional indexes")
                return False
            
            logger.info("Emotional intelligence collections setup completed successfully")
            return True
            
        except Exception as e:
            logger.error("Error setting up emotional collections: %s", str(e))
            return False
    
    def _setup_emotional_signatures_collection(self) -> bool:
        """Set up the emotional signatures collection.
        
        This collection stores user emotional signatures including:
        - Archetype classifications
        - Authenticity scores
        - Vulnerability levels
        - Communication styles
        - Response patterns
        - Evolution history
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        try:
            collection_name = "emotional_signatures"
            
            # Create collection if it doesn't exist
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                logger.info("Created emotional_signatures collection")
            
            # Get collection reference
            collection = self.db[collection_name]
            
            # Ensure basic structure
            logger.debug("Emotional signatures collection ready")
            return True
            
        except Exception as e:
            logger.error("Error setting up emotional signatures collection: %s", str(e))
            return False
    
    def _setup_emotional_journey_collection(self) -> bool:
        """Set up the emotional journey collection.
        
        This collection tracks user emotional journey progression including:
        - Current Diana level
        - Level entry dates
        - Progression history
        - Milestone achievements
        - Relationship depth scores
        - VIP integration status
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        try:
            collection_name = "emotional_journeys"
            
            # Create collection if it doesn't exist
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                logger.info("Created emotional_journeys collection")
            
            # Get collection reference
            collection = self.db[collection_name]
            
            # Ensure basic structure
            logger.debug("Emotional journey collection ready")
            return True
            
        except Exception as e:
            logger.error("Error setting up emotional journey collection: %s", str(e))
            return False
    
    def _setup_memory_fragments_collection(self) -> bool:
        """Set up the memory fragments collection.
        
        This collection stores emotional memory fragments for:
        - Relationship continuity
        - Contextual personalization
        - Meaningful moment preservation
        - Recall triggers
        - Emotional significance scoring
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        try:
            collection_name = "memory_fragments"
            
            # Create collection if it doesn't exist
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                logger.info("Created memory_fragments collection")
            
            # Get collection reference
            collection = self.db[collection_name]
            
            # Ensure basic structure
            logger.debug("Memory fragments collection ready")
            return True
            
        except Exception as e:
            logger.error("Error setting up memory fragments collection: %s", str(e))
            return False
    
    def _setup_emotional_interactions_collection(self) -> bool:
        """Set up the emotional interactions collection.
        
        This collection records emotional interactions for:
        - Behavioral analysis
        - Authenticity detection
        - Vulnerability assessment
        - Archetype reinforcement
        - Progression triggering
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        try:
            collection_name = "emotional_interactions"
            
            # Create collection if it doesn't exist
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                logger.info("Created emotional_interactions collection")
            
            # Get collection reference
            collection = self.db[collection_name]
            
            # Ensure basic structure
            logger.debug("Emotional interactions collection ready")
            return True
            
        except Exception as e:
            logger.error("Error setting up emotional interactions collection: %s", str(e))
            return False
    
    def _setup_emotional_indexes(self) -> bool:
        """Set up recommended indexes for emotional collections.
        
        Creates indexes for optimal querying of:
        - User emotional signatures
        - Journey progression
        - Memory fragments
        - Interaction analysis
        
        Returns:
            bool: True if indexes were created successfully, False otherwise
        """
        try:
            # Index for emotional signatures
            self.db["emotional_signatures"].create_index("user_id", unique=True)
            self.db["emotional_signatures"].create_index("archetype")
            self.db["emotional_signatures"].create_index("authenticity_score")
            self.db["emotional_signatures"].create_index("last_analysis")
            logger.debug("Created indexes for emotional_signatures collection")
            
            # Index for emotional journeys
            self.db["emotional_journeys"].create_index("user_id", unique=True)
            self.db["emotional_journeys"].create_index("current_level")
            self.db["emotional_journeys"].create_index("level_entry_date")
            logger.debug("Created indexes for emotional_journeys collection")
            
            # Index for memory fragments
            self.db["memory_fragments"].create_index("user_id")
            self.db["memory_fragments"].create_index("memory_id", unique=True)
            self.db["memory_fragments"].create_index("recall_triggers")
            self.db["memory_fragments"].create_index("emotional_significance")
            self.db["memory_fragments"].create_index("relationship_stage")
            self.db["memory_fragments"].create_index("created_at")
            logger.debug("Created indexes for memory_fragments collection")
            
            # Index for emotional interactions
            self.db["emotional_interactions"].create_index("user_id")
            self.db["emotional_interactions"].create_index("interaction_id", unique=True)
            self.db["emotional_interactions"].create_index("interaction_type")
            self.db["emotional_interactions"].create_index("authenticity_detected")
            self.db["emotional_interactions"].create_index("created_at")
            logger.debug("Created indexes for emotional_interactions collection")
            
            logger.info("All emotional indexes created successfully")
            return True
            
        except Exception as e:
            logger.error("Error setting up emotional indexes: %s", str(e))
            return False
    
    def migrate_existing_users(self) -> bool:
        """Migrate existing users to include emotional intelligence fields.
        
        Adds emotional signature and journey fields to existing user documents.
        
        Returns:
            bool: True if migration was successful, False otherwise
        """
        try:
            logger.info("Migrating existing users to include emotional intelligence fields")
            
            # Get users collection
            users_collection = self.db["users"]
            
            # Add emotional fields to existing users
            result = users_collection.update_many(
                {
                    "$or": [
                        {"emotional_signature": {"$exists": False}},
                        {"emotional_journey": {"$exists": False}}
                    ]
                },
                {
                    "$set": {
                        "emotional_signature": {},
                        "emotional_journey": {}
                    }
                }
            )
            
            logger.info(
                "Migrated %d existing users to include emotional intelligence fields", 
                result.modified_count
            )
            return True
            
        except Exception as e:
            logger.error("Error migrating existing users: %s", str(e))
            return False


# Convenience function for easy migration
def setup_emotional_collections(db: Database) -> bool:
    """Convenience function to set up emotional collections.
    
    Args:
        db (Database): MongoDB database instance
        
    Returns:
        bool: True if setup was successful, False otherwise
    """
    migration_handler = EmotionalCollectionsMigration(db)
    return migration_handler.setup_emotional_collections()


def migrate_existing_users_for_emotions(db: Database) -> bool:
    """Convenience function to migrate existing users for emotional intelligence.
    
    Args:
        db (Database): MongoDB database instance
        
    Returns:
        bool: True if migration was successful, False otherwise
    """
    migration_handler = EmotionalCollectionsMigration(db)
    return migration_handler.migrate_existing_users()
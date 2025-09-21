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

    def get_besitos_transactions_collection(self) -> Collection:
        """Get the BesitosTransactions collection for besitos transactions.

        Returns:
            Collection: MongoDB collection for besitos transactions
        """
        logger.debug("Accessing BesitosTransactions collection")
        return self._db["besitos_transactions"]

    def get_missions_collection(self) -> Collection:
        """Get the Missions collection for user missions.

        Returns:
            Collection: MongoDB collection for missions
        """
        logger.debug("Accessing Missions collection")
        return self._db["missions"]

    def get_user_items_collection(self) -> Collection:
        """Get the UserItems collection for user inventory (mochila).

        Returns:
            Collection: MongoDB collection for user items
        """
        logger.debug("Accessing UserItems collection")
        return self._db["user_items"]

    def get_subscriptions_collection(self) -> Collection:
        """Get the Subscriptions collection for user subscriptions.

        Returns:
            Collection: MongoDB collection for subscriptions
        """
        logger.debug("Accessing Subscriptions collection")
        return self._db["subscriptions"]

    def get_auctions_collection(self) -> Collection:
        """Get the Auctions collection for item auctions.

        Returns:
            Collection: MongoDB collection for auctions
        """
        logger.debug("Accessing Auctions collection")
        return self._db["auctions"]

    def get_trivias_collection(self) -> Collection:
        """Get the Trivias collection for trivia games.

        Returns:
            Collection: MongoDB collection for trivias
        """
        logger.debug("Accessing Trivias collection")
        return self._db["trivias"]

    def get_user_achievements_collection(self) -> Collection:
        """Get the UserAchievements collection for user achievements (logros).

        Returns:
            Collection: MongoDB collection for user achievements
        """
        logger.debug("Accessing UserAchievements collection")
        return self._db["user_achievements"]

    def get_user_choice_logs_collection(self) -> Collection:
        """Get the UserChoiceLogs collection for narrative decision analytics.

        Returns:
            Collection: MongoDB collection for user choice logs
        """
        logger.debug("Accessing UserChoiceLogs collection")
        return self._db["user_choice_logs"]

    def get_lucien_messages_collection(self) -> Collection:
        """Get the LucienMessages collection for Lucien dynamic messages.

        Returns:
            Collection: MongoDB collection for Lucien messages
        """
        logger.debug("Accessing LucienMessages collection")
        return self._db["lucien_messages"]

    def get_narrative_templates_collection(self) -> Collection:
        """Get the NarrativeTemplates collection for dynamic content templates.

        Returns:
            Collection: MongoDB collection for narrative templates
        """
        logger.debug("Accessing NarrativeTemplates collection")
        return self._db["narrative_templates"]
    
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

            # Initialize gamification collections
            await self._initialize_gamification_collections()

            # Initialize narrative collections
            await self._initialize_narrative_collections()

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

    async def _initialize_gamification_collections(self) -> None:
        """Initialize all gamification collections with indexes and validation rules."""
        logger.info("Initializing gamification collections")

        # Import schema definitions
        from src.database.schemas.gamification import GamificationCollections

        # Get collection schemas
        schemas = GamificationCollections.get_collection_schemas()

        # Initialize each gamification collection
        for collection_name, schema_config in schemas.items():
            logger.debug("Initializing %s collection", collection_name)

            # Get collection reference
            collection = self._db[collection_name]

            # Create indexes
            for index_spec in schema_config["indexes"]:
                try:
                    collection.create_index(**index_spec)
                except Exception as e:
                    logger.warning("Failed to create index %s on %s: %s",
                                 index_spec, collection_name, str(e))

            # Apply validation rules (MongoDB 3.6+)
            try:
                self._db.command("collMod", collection_name, **schema_config["validator"])
            except Exception as e:
                logger.warning("Failed to apply validation to %s: %s", collection_name, str(e))

            logger.debug("%s collection initialized successfully", collection_name)

        logger.info("All gamification collections initialized successfully")

    async def _initialize_narrative_collections(self) -> None:
        """Initialize narrative collections with indexes and validation rules."""
        logger.info("Initializing narrative collections")

        # Import schema definitions
        from src.database.schemas.narrative import NARRATIVE_INDEXES, NARRATIVE_COLLECTION_SCHEMAS

        # Initialize Lucien messages collection
        lucien_collection = self.get_lucien_messages_collection()
        for index_spec in NARRATIVE_INDEXES.get("lucien_messages", []):
            try:
                lucien_collection.create_index([(key, value) for key, value in index_spec.items()])
            except Exception as e:
                logger.warning("Failed to create index %s on lucien_messages: %s", index_spec, str(e))

        # Initialize narrative templates collection
        templates_collection = self.get_narrative_templates_collection()
        for index_spec in NARRATIVE_INDEXES.get("narrative_templates", []):
            try:
                templates_collection.create_index([(key, value) for key, value in index_spec.items()])
            except Exception as e:
                logger.warning("Failed to create index %s on narrative_templates: %s", index_spec, str(e))

        # Apply validation schemas if available
        for collection_name, schema in NARRATIVE_COLLECTION_SCHEMAS.items():
            if collection_name in ["lucien_messages", "narrative_templates"]:
                try:
                    self._db.command("collMod", collection_name, validator=schema)
                except Exception as e:
                    logger.warning("Failed to apply validation to %s: %s", collection_name, str(e))

        logger.info("Narrative collections initialized successfully")
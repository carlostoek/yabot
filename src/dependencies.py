# src/dependencies.py

from functools import lru_cache
from aiogram import Bot
import redis.asyncio as redis
from pymongo import MongoClient

from src.config.manager import ConfigManager
from src.database.mongodb import MongoDBHandler
from src.events.bus import EventBus
from src.modules.narrative.fragment_manager import NarrativeFragmentManager
from src.modules.gamification.mission_manager import MissionManager
from src.modules.admin.access_control import AccessControl
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.modules.admin.subscription_manager import SubscriptionManager

# This is a simplified dependency setup. In a real application,
# you would have a more robust system for managing connections and sessions.

@lru_cache()
def get_config_manager() -> ConfigManager:
    return ConfigManager()

@lru_cache()
def get_mongodb_handler() -> MongoDBHandler:
    config = get_config_manager().get_database_config()
    client = MongoClient(config.mongodb_uri)
    db = client[config.mongodb_database]
    return MongoDBHandler(db)

@lru_cache()
def get_event_bus() -> EventBus:
    return EventBus()

@lru_cache()
def get_bot() -> Bot:
    return Bot(token=get_config_manager().get_bot_token())

def get_narrative_fragment_manager() -> NarrativeFragmentManager:
    mongodb_handler = get_mongodb_handler()
    event_bus = get_event_bus()
    return NarrativeFragmentManager(mongodb_handler, event_bus)

def get_mission_manager() -> MissionManager:
    mongodb_handler = get_mongodb_handler()
    event_bus = get_event_bus()
    return MissionManager(mongodb_handler, event_bus)

def get_access_control() -> AccessControl:
    bot = get_bot()
    subscription_manager = SubscriptionManager(get_mongodb_handler()._db, get_event_bus())
    return AccessControl(bot, subscription_manager)

def get_besitos_wallet() -> BesitosWallet:
    mongodb_handler = get_mongodb_handler()
    event_bus = get_event_bus()
    return BesitosWallet(mongodb_handler, event_bus)

async def get_emotional_intelligence_service():
    """Get emotional intelligence service instance."""
    # Note: In a full implementation, this would need to properly import and instantiate
    # the EmotionalIntelligenceService with its required dependencies
    # For now, we're providing a placeholder that follows the pattern
    from src.modules.emotional.intelligence_service import EmotionalIntelligenceService
    from src.database.manager import DatabaseManager
    
    database_manager = DatabaseManager(get_config_manager())
    event_bus = get_event_bus()
    
    # These would need to be properly implemented with actual dependency injection
    # For now, using placeholders as indicated in the original pattern
    user_service = None  # This would be properly injected
    narrative_service = None  # This would be properly injected
    
    return EmotionalIntelligenceService(
        database_manager=database_manager,
        event_bus=event_bus,
        user_service=user_service,
        narrative_service=narrative_service
    )

async def get_emotional_memory_service():
    """Get emotional memory service instance."""
    # Note: In a full implementation, this would need to properly import and instantiate
    # the EmotionalMemoryService with its required dependencies
    # For now, we're providing a placeholder that follows the pattern
    from src.modules.emotional.memory_service import EmotionalMemoryService
    from src.database.manager import DatabaseManager
    
    database_manager = DatabaseManager(get_config_manager())
    event_bus = get_event_bus()
    
    return EmotionalMemoryService(
        database_manager=database_manager,
        event_bus=event_bus
    )

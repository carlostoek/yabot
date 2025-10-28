"""
Gamification schema definitions for the YABOT system.

This module provides Pydantic models for gamification collections including
besitos transactions, missions, items, auctions, trivias, and achievements
as required by the modulos-atomicos specification.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class TransactionType(str, Enum):
    """Types of besitos transactions."""
    AWARDED = "awarded"
    SPENT = "spent"
    REFUND = "refund"
    BONUS = "bonus"


class TransactionStatus(str, Enum):
    """Status of besitos transactions."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BesitosTransaction(BaseModel):
    """Besitos transaction model for the BesitosTransactions collection.

    Supports atomic transaction requirements from 2.1, 2.2, and 6.5.
    """
    transaction_id: str = Field(..., description="Unique identifier for the transaction")
    user_id: str = Field(..., description="User ID associated with the transaction")
    type: TransactionType = Field(..., description="Type of transaction")
    amount: int = Field(..., description="Amount of besitos (positive for awards, negative for spending)")
    balance_before: int = Field(..., description="User balance before transaction")
    balance_after: int = Field(..., description="User balance after transaction")
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, description="Transaction status")
    reason: str = Field(..., description="Reason for the transaction")
    source: str = Field(..., description="Source of the transaction (e.g., 'mission', 'daily_gift', 'purchase')")
    reference_id: Optional[str] = Field(None, description="Reference to related entity (mission_id, item_id, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional transaction metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="When the transaction was completed")


class MissionType(str, Enum):
    """Types of missions."""
    DAILY = "daily"
    WEEKLY = "weekly"
    STORY = "story"
    SPECIAL = "special"
    ACHIEVEMENT = "achievement"


class MissionStatus(str, Enum):
    """Status of missions."""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    LOCKED = "locked"


class MissionObjective(BaseModel):
    """Mission objective sub-model."""
    objective_id: str = Field(..., description="Unique identifier for the objective")
    description: str = Field(..., description="Description of the objective")
    target_value: int = Field(..., description="Target value to reach")
    current_value: int = Field(default=0, description="Current progress value")
    completed: bool = Field(default=False, description="Whether objective is completed")


class Mission(BaseModel):
    """Mission model for the Missions collection."""
    mission_id: str = Field(..., description="Unique identifier for the mission")
    user_id: str = Field(..., description="User ID associated with the mission")
    title: str = Field(..., description="Mission title")
    description: str = Field(..., description="Mission description")
    type: MissionType = Field(..., description="Type of mission")
    status: MissionStatus = Field(default=MissionStatus.AVAILABLE, description="Mission status")
    objectives: List[MissionObjective] = Field(default_factory=list, description="List of mission objectives")
    reward_besitos: int = Field(default=0, description="Besitos reward for completion")
    reward_items: List[str] = Field(default_factory=list, description="Item IDs awarded on completion")
    requirements: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Requirements to unlock/complete")
    expires_at: Optional[datetime] = Field(None, description="Mission expiration time")
    started_at: Optional[datetime] = Field(None, description="When mission was started")
    completed_at: Optional[datetime] = Field(None, description="When mission was completed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional mission metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ItemRarity(str, Enum):
    """Item rarity levels."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class ItemCategory(str, Enum):
    """Item categories."""
    CONSUMABLE = "consumable"
    EQUIPMENT = "equipment"
    COSMETIC = "cosmetic"
    COLLECTIBLE = "collectible"
    SPECIAL = "special"


class UserItem(BaseModel):
    """User item model for the UserItems collection (mochila system).

    Supports CRUD operations requirement from 2.6.
    """
    user_item_id: str = Field(..., description="Unique identifier for user's item instance")
    user_id: str = Field(..., description="User ID who owns the item")
    item_id: str = Field(..., description="Reference to base item definition")
    name: str = Field(..., description="Item name")
    description: str = Field(..., description="Item description")
    category: ItemCategory = Field(..., description="Item category")
    rarity: ItemRarity = Field(default=ItemRarity.COMMON, description="Item rarity")
    quantity: int = Field(default=1, description="Quantity owned")
    max_stack: int = Field(default=1, description="Maximum stack size")
    value: int = Field(default=0, description="Besitos value of the item")
    emoji: Optional[str] = Field(None, description="Emoji representation")
    effects: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Item effects and bonuses")
    equipped: bool = Field(default=False, description="Whether item is equipped")
    tradeable: bool = Field(default=True, description="Whether item can be traded")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional item metadata")
    acquired_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuctionStatus(str, Enum):
    """Status of auctions."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Bid(BaseModel):
    """Bid sub-model for auctions."""
    bid_id: str = Field(..., description="Unique identifier for the bid")
    bidder_id: str = Field(..., description="User ID of the bidder")
    amount: int = Field(..., description="Bid amount in besitos")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional bid metadata")


class Auction(BaseModel):
    """Auction model for the Auctions collection."""
    auction_id: str = Field(..., description="Unique identifier for the auction")
    seller_id: str = Field(..., description="User ID of the seller")
    item_id: str = Field(..., description="Item being auctioned")
    item_name: str = Field(..., description="Name of the item")
    item_quantity: int = Field(default=1, description="Quantity of items being auctioned")
    starting_price: int = Field(..., description="Starting bid price in besitos")
    current_price: int = Field(..., description="Current highest bid")
    buyout_price: Optional[int] = Field(None, description="Immediate purchase price")
    status: AuctionStatus = Field(default=AuctionStatus.ACTIVE, description="Auction status")
    bids: List[Bid] = Field(default_factory=list, description="Bid history")
    current_winner_id: Optional[str] = Field(None, description="Current highest bidder")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime = Field(..., description="Auction end time")
    completed_at: Optional[datetime] = Field(None, description="When auction was completed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional auction metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TriviaStatus(str, Enum):
    """Status of trivia sessions."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TriviaParticipant(BaseModel):
    """Trivia participant sub-model."""
    user_id: str = Field(..., description="User ID of participant")
    score: int = Field(default=0, description="Current score")
    answers: List[Dict[str, Any]] = Field(default_factory=list, description="Answer history")
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    completed: bool = Field(default=False, description="Whether participant completed the trivia")


class TriviaQuestion(BaseModel):
    """Trivia question sub-model."""
    question_id: str = Field(..., description="Unique identifier for the question")
    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., description="Answer options")
    correct_answer: int = Field(..., description="Index of correct answer")
    points: int = Field(default=10, description="Points awarded for correct answer")
    time_limit: int = Field(default=30, description="Time limit in seconds")


class Trivia(BaseModel):
    """Trivia model for the Trivias collection."""
    trivia_id: str = Field(..., description="Unique identifier for the trivia")
    title: str = Field(..., description="Trivia title")
    description: str = Field(..., description="Trivia description")
    status: TriviaStatus = Field(default=TriviaStatus.ACTIVE, description="Trivia status")
    questions: List[TriviaQuestion] = Field(..., description="List of questions")
    participants: List[TriviaParticipant] = Field(default_factory=list, description="List of participants")
    max_participants: Optional[int] = Field(None, description="Maximum number of participants")
    reward_pool: int = Field(default=0, description="Total besitos reward pool")
    reward_distribution: Dict[str, int] = Field(default_factory=dict, description="How rewards are distributed")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(None, description="Trivia end time")
    completed_at: Optional[datetime] = Field(None, description="When trivia was completed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional trivia metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AchievementType(str, Enum):
    """Types of achievements."""
    PROGRESS = "progress"
    MILESTONE = "milestone"
    COLLECTION = "collection"
    SOCIAL = "social"
    SPECIAL = "special"


class AchievementTier(str, Enum):
    """Achievement tiers."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class AchievementProgress(BaseModel):
    """Achievement progress sub-model."""
    current_value: int = Field(default=0, description="Current progress value")
    target_value: int = Field(..., description="Target value to reach")
    percentage: float = Field(default=0.0, description="Progress percentage")


class UserAchievement(BaseModel):
    """User achievement model for the UserAchievements collection (logros system)."""
    user_achievement_id: str = Field(..., description="Unique identifier for user's achievement")
    user_id: str = Field(..., description="User ID who earned the achievement")
    achievement_id: str = Field(..., description="Reference to base achievement definition")
    title: str = Field(..., description="Achievement title")
    description: str = Field(..., description="Achievement description")
    type: AchievementType = Field(..., description="Achievement type")
    tier: AchievementTier = Field(default=AchievementTier.BRONZE, description="Achievement tier")
    progress: AchievementProgress = Field(..., description="Progress towards achievement")
    completed: bool = Field(default=False, description="Whether achievement is completed")
    reward_besitos: int = Field(default=0, description="Besitos reward")
    reward_items: List[str] = Field(default_factory=list, description="Item rewards")
    icon: Optional[str] = Field(None, description="Achievement icon")
    secret: bool = Field(default=False, description="Whether achievement is secret")
    completed_at: Optional[datetime] = Field(None, description="When achievement was completed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional achievement metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Collection schemas for MongoDB operations
class GamificationCollections:
    """MongoDB collection schemas for gamification system."""

    @staticmethod
    def get_collection_schemas() -> Dict[str, Dict[str, Any]]:
        """Get collection schemas with validation rules and indexes.

        Returns:
            Dict containing collection schemas with validation and indexing rules.
        """
        return {
            "besitos_transactions": {
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["transaction_id", "user_id", "type", "amount", "balance_before", "balance_after", "reason", "source"],
                        "properties": {
                            "transaction_id": {"bsonType": "string"},
                            "user_id": {"bsonType": "string"},
                            "type": {"enum": ["awarded", "spent", "refund", "bonus"]},
                            "amount": {"bsonType": "int"},
                            "balance_before": {"bsonType": "int", "minimum": 0},
                            "balance_after": {"bsonType": "int", "minimum": 0},
                            "status": {"enum": ["pending", "completed", "failed", "cancelled"]},
                            "reason": {"bsonType": "string"},
                            "source": {"bsonType": "string"}
                        }
                    }
                },
                "indexes": [
                    {"key": {"transaction_id": 1}, "unique": True},
                    {"key": {"user_id": 1, "created_at": -1}},  # Compound index for user queries
                    {"key": {"user_id": 1, "status": 1}},
                    {"key": {"user_id": 1, "type": 1, "created_at": -1}},
                    {"key": {"status": 1}},
                    {"key": {"created_at": -1}},
                    {"key": {"reference_id": 1}}
                ]
            },

            "missions": {
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["mission_id", "user_id", "title", "type", "status"],
                        "properties": {
                            "mission_id": {"bsonType": "string"},
                            "user_id": {"bsonType": "string"},
                            "title": {"bsonType": "string"},
                            "type": {"enum": ["daily", "weekly", "story", "special", "achievement"]},
                            "status": {"enum": ["available", "in_progress", "completed", "expired", "locked"]}
                        }
                    }
                },
                "indexes": [
                    {"key": {"mission_id": 1}, "unique": True},
                    {"key": {"user_id": 1, "status": 1}},
                    {"key": {"user_id": 1, "type": 1}},
                    {"key": {"user_id": 1, "created_at": -1}},
                    {"key": {"type": 1, "status": 1}},
                    {"key": {"expires_at": 1}},
                    {"key": {"status": 1, "created_at": -1}}
                ]
            },

            "user_items": {
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_item_id", "user_id", "item_id", "name", "category"],
                        "properties": {
                            "user_item_id": {"bsonType": "string"},
                            "user_id": {"bsonType": "string"},
                            "item_id": {"bsonType": "string"},
                            "name": {"bsonType": "string"},
                            "category": {"enum": ["consumable", "equipment", "cosmetic", "collectible", "special"]},
                            "rarity": {"enum": ["common", "uncommon", "rare", "epic", "legendary"]},
                            "quantity": {"bsonType": "int", "minimum": 0}
                        }
                    }
                },
                "indexes": [
                    {"key": {"user_item_id": 1}, "unique": True},
                    {"key": {"user_id": 1, "category": 1}},
                    {"key": {"user_id": 1, "item_id": 1}},
                    {"key": {"user_id": 1, "equipped": 1}},
                    {"key": {"user_id": 1, "acquired_at": -1}},
                    {"key": {"item_id": 1}},
                    {"key": {"rarity": 1, "category": 1}}
                ]
            },

            "auctions": {
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["auction_id", "seller_id", "item_id", "starting_price", "current_price", "end_time"],
                        "properties": {
                            "auction_id": {"bsonType": "string"},
                            "seller_id": {"bsonType": "string"},
                            "item_id": {"bsonType": "string"},
                            "starting_price": {"bsonType": "int", "minimum": 1},
                            "current_price": {"bsonType": "int", "minimum": 1},
                            "status": {"enum": ["active", "completed", "cancelled", "expired"]}
                        }
                    }
                },
                "indexes": [
                    {"key": {"auction_id": 1}, "unique": True},
                    {"key": {"status": 1, "end_time": 1}},
                    {"key": {"seller_id": 1, "status": 1}},
                    {"key": {"item_id": 1, "status": 1}},
                    {"key": {"status": 1, "current_price": 1}},
                    {"key": {"end_time": 1}},
                    {"key": {"created_at": -1}}
                ]
            },

            "trivias": {
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["trivia_id", "title", "status", "questions"],
                        "properties": {
                            "trivia_id": {"bsonType": "string"},
                            "title": {"bsonType": "string"},
                            "status": {"enum": ["active", "completed", "cancelled"]},
                            "questions": {"bsonType": "array", "minItems": 1}
                        }
                    }
                },
                "indexes": [
                    {"key": {"trivia_id": 1}, "unique": True},
                    {"key": {"status": 1, "start_time": -1}},
                    {"key": {"status": 1, "end_time": 1}},
                    {"key": {"participants.user_id": 1}},
                    {"key": {"created_at": -1}}
                ]
            },

            "user_achievements": {
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_achievement_id", "user_id", "achievement_id", "title", "type"],
                        "properties": {
                            "user_achievement_id": {"bsonType": "string"},
                            "user_id": {"bsonType": "string"},
                            "achievement_id": {"bsonType": "string"},
                            "title": {"bsonType": "string"},
                            "type": {"enum": ["progress", "milestone", "collection", "social", "special"]},
                            "tier": {"enum": ["bronze", "silver", "gold", "platinum", "diamond"]},
                            "completed": {"bsonType": "bool"}
                        }
                    }
                },
                "indexes": [
                    {"key": {"user_achievement_id": 1}, "unique": True},
                    {"key": {"user_id": 1, "completed": 1}},
                    {"key": {"user_id": 1, "type": 1}},
                    {"key": {"user_id": 1, "tier": 1}},
                    {"key": {"achievement_id": 1}},
                    {"key": {"completed": 1, "completed_at": -1}},
                    {"key": {"user_id": 1, "created_at": -1}}
                ]
            }
        }


# Event models for gamification system integration with event bus
class BesitosAddedEvent(BaseModel):
    """Event published when besitos are awarded (requirement 2.1)."""
    user_id: str
    transaction_id: str
    amount: int
    reason: str
    source: str
    balance_after: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BesitosSpentEvent(BaseModel):
    """Event published when besitos are spent (requirement 2.2)."""
    user_id: str
    transaction_id: str
    amount: int
    reason: str
    item_id: Optional[str] = None
    balance_after: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MissionCompletedEvent(BaseModel):
    """Event published when a mission is completed."""
    user_id: str
    mission_id: str
    mission_type: str
    reward_besitos: int
    reward_items: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AchievementUnlockedEvent(BaseModel):
    """Event published when an achievement is unlocked."""
    user_id: str
    achievement_id: str
    achievement_title: str
    tier: str
    reward_besitos: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BidPlacedEvent(BaseModel):
    """Event published when a bid is placed on an auction (requirement 2.8)."""
    auction_id: str
    bidder_id: str
    bid_id: str
    bid_amount: int
    previous_price: int
    new_current_price: int
    previous_winner_id: Optional[str] = None
    auction_end_time: datetime
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuctionClosedEvent(BaseModel):
    """Event published when an auction is closed (requirement 2.8)."""
    auction_id: str
    seller_id: str
    item_id: str
    item_name: str
    final_price: int
    winner_id: Optional[str] = None
    total_bids: int
    status: str  # "completed", "expired", "cancelled"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
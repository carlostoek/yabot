"""
Gamification Module Schemas - MongoDB

This module contains all MongoDB schema definitions for the gamification module
following Pydantic patterns from existing models and requirements 2.1, 2.2, 2.6, 6.5.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from pydantic_core import core_schema


# Custom ObjectId field compatible with Pydantic v2
class PyObjectId(str):
    """Custom ObjectId field for Pydantic models"""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Any,
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()

    @classmethod
    def validate(cls, v: Any) -> str:
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        elif isinstance(v, ObjectId):
            return str(v)
        else:
            raise ValueError("Invalid ObjectId")


class BesitosTransactionMongoSchema(BaseModel):
    """
    MongoDB schema for besitos transactions ensuring atomicity
    Implements requirements 2.1, 2.2: atomic transactions and besitos balance tracking
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    transaction_id: str  # Unique transaction identifier
    user_id: str  # User ID receiving/spending besitos
    amount: int  # Positive for credits, negative for debits
    transaction_type: str  # "credit", "debit", "transfer", "payout", "refund"
    reason: str  # Reason for the transaction
    balance_after: int  # Balance after the transaction
    reference_id: Optional[str] = None  # Reference to related object (mission, auction, etc.)
    reference_type: Optional[str] = None  # Type of reference object
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True


class UserGamificationData(BaseModel):
    """
    MongoDB schema for user gamification data stored in the users collection
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    besitos_balance: int = 0  # Current besitos balance
    total_earned_besitos: int = 0  # Total besitos earned
    total_spent_besitos: int = 0  # Total besitos spent
    last_besitos_earned: Optional[datetime] = None
    last_besitos_spent: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class MissionMongoSchema(BaseModel):
    """
    MongoDB schema for user missions
    Implements requirement 2.3: mission assignment and progress tracking
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    mission_id: str
    user_id: str
    mission_type: str  # "reaction", "decision", "hint", "achievement", "trivia", etc.
    title: str
    description: str
    progress: Dict[str, Any] = Field(default_factory=dict)  # Progress tracking data
    reward: Dict[str, Any] = Field(default_factory=dict)  # Rewards upon completion
    status: str = "active"  # "active", "completed", "failed", "cancelled"
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True


class ItemMongoSchema(BaseModel):
    """
    MongoDB schema for items (mochila/backpack) in the system
    Implements requirements 2.6, 6.3: item management and CRUD operations
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    item_id: str
    name: str
    description: str
    item_type: str  # "tool", "gift", "badge", "virtual_item", "consumable", etc.
    rarity: str = "common"  # "common", "rare", "epic", "legendary"
    value: int = 0  # Can be used for besitos value or other metrics
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class UserInventoryMongoSchema(BaseModel):
    """
    MongoDB schema for user inventory (mochila)
    Implements requirement 2.6: user item collection via MongoDB API
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    items: List[Dict[str, Any]] = Field(default_factory=list)  # List of {item_id, quantity, metadata}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class AuctionMongoSchema(BaseModel):
    """
    MongoDB schema for auctions (subastas)
    Implements requirement 2.8: auction management with timers and bid handling
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    auction_id: str
    item_id: str
    item_name: str
    item_description: str
    starting_bid: int
    current_bid: int
    current_bidder: Optional[str] = None  # User ID of current highest bidder
    bid_history: List[Dict[str, Any]] = Field(default_factory=list)  # [{user_id, amount, timestamp}]
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime
    status: str = "active"  # "active", "closed", "cancelled", "ended"
    min_increment: int = 1  # Minimum bid increment
    buy_now_price: Optional[int] = None  # Optional buy now price
    created_by: str  # User ID of auction creator
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True


class TriviaMongoSchema(BaseModel):
    """
    MongoDB schema for trivia questions and results
    Implements requirement 2.9: trivia question processing and results
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    trivia_id: str
    question: str
    options: List[str]
    correct_answer: int  # Index of correct answer in options
    reward_amount: int = 0  # Besitos reward for correct answer
    created_at: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None  # When trivia closes
    status: str = "active"  # "active", "closed", "graded"
    participants: List[Dict[str, Any]] = Field(default_factory=list)  # [{user_id, answer, timestamp, points}]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True


class AchievementMongoSchema(BaseModel):
    """
    MongoDB schema for achievements (logros)
    Implements requirement 2.10: achievement tracking and unlocking
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    achievement_id: str
    name: str
    description: str
    icon: Optional[str] = None  # Emoji or image reference
    criteria: Dict[str, Any]  # Criteria needed to unlock this achievement
    reward: Dict[str, Any] = Field(default_factory=dict)  # Rewards for unlocking
    rarity: str = "common"  # "common", "rare", "epic", "legendary"
    total_unlocked: int = 0  # Number of times this achievement has been unlocked globally
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class UserAchievementMongoSchema(BaseModel):
    """
    MongoDB schema for user achievement data
    Implements requirement 2.10: user achievement tracking
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    achievement_id: str
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)
    progress: Optional[Dict[str, Any]] = Field(default_factory=dict)  # For achievements that track progress
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True


class DailyGiftMongoSchema(BaseModel):
    """
    MongoDB schema for daily gift system
    Implements requirement 2.11: daily gift claims with cooldowns
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    gift_type: str = "daily"  # "daily", "weekly", "special", etc.
    reward: Dict[str, Any]  # What the user receives
    claimed_at: Optional[datetime] = None
    next_available_at: datetime
    consecutive_days: int = 0  # For streak tracking
    total_claims: int = 0
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True


class TransactionLogMongoSchema(BaseModel):
    """
    MongoDB schema for transaction logs to support atomicity and audit trail
    Implements requirement 6.5: atomicity for critical operations
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    operation_id: str  # Unique operation identifier for transaction grouping
    operation_type: str  # "balance_update", "item_transfer", "auction_bid", etc.
    user_id: str
    action: str  # "credit", "debit", "transfer", "adjustment", etc.
    amount: int
    balance_before: int
    balance_after: int
    status: str  # "pending", "completed", "failed", "rolled_back"
    reference: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Reference to related object
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True
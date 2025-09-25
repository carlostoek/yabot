"""
Narrative Module Schemas - MongoDB

This module contains all MongoDB schema definitions for the narrative module
following Pydantic patterns from existing models and requirements 1.1, 1.4, 6.1.
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


class Choice(BaseModel):
    """Choice within a narrative fragment"""
    choice_id: str
    text: str
    next_fragment_id: Optional[str] = None  # Can be None for ending fragments
    conditions: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Conditions to unlock this choice
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NarrativeFragmentMongoSchema(BaseModel):
    """
    MongoDB schema for narrative fragments containing story content and choices
    Implements requirements 1.1 and 6.1: storing narrative fragments with text and decisions
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    fragment_id: str
    title: str
    content: str
    choices: List[Choice] = Field(default_factory=list)
    vip_required: bool = False  # Requirement 1.4: VIP access to premium narrative levels
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class NarrativeProgress(BaseModel):
    """
    Schema for tracking user's narrative progress
    Implements requirement 6.2: maintaining narrative_progress in users collection
    """
    current_fragment: str
    completed_fragments: List[str] = Field(default_factory=list)
    unlocked_hints: List[str] = Field(default_factory=list)  # pistas
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    progression_path: List[str] = Field(default_factory=list)  # Track the path user took through the narrative


class NarrativeUserState(BaseModel):
    """
    Extended user state for narrative module
    """
    narrative_progress: Optional[NarrativeProgress] = Field(default_factory=NarrativeProgress)
    current_checkpoint: Optional[str] = None  # For requirement 1.5: narrative checkpoint validation
    last_interaction_time: datetime = Field(default_factory=datetime.utcnow)


class HintMongoSchema(BaseModel):
    """
    MongoDB schema for narrative hints (pistas)
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    hint_id: str
    title: str
    content: str
    hint_type: str = "narrative"  # "narrative", "puzzle", "location", etc.
    unlock_conditions: Dict[str, Any] = Field(default_factory=dict)  # Requirements to unlock this hint
    cost: Optional[int] = 0  # Cost in besitos to unlock
    creator_id: Optional[str] = None  # User ID of the creator if user-generated
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class UserNarrativeData(BaseModel):
    """
    Schema for narrative-specific user data stored in the users collection
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    narrative_progress: Optional[NarrativeProgress] = Field(default_factory=NarrativeProgress)
    unlocked_hints: List[str] = Field(default_factory=list)
    favorite_fragments: List[str] = Field(default_factory=list)
    reading_history: List[Dict[str, Any]] = Field(default_factory=list)  # Track user's reading history
    last_narrative_interaction: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class NarrativeInteractionMongoSchema(BaseModel):
    """
    Schema for tracking narrative interactions and decisions
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    fragment_id: str
    choice_made: Optional[str] = None
    interaction_type: str = "read"  # "read", "choice", "hint_used", "checkpoint_reached"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class NarrativeCheckpointMongoSchema(BaseModel):
    """
    Schema for narrative checkpoints that validate progression conditions
    Implements requirement 1.5: validating progression conditions via coordinator service
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    checkpoint_id: str
    name: str
    description: str
    required_fragments: List[str] = Field(default_factory=list)  # Fragments required to reach this checkpoint
    required_hints: List[str] = Field(default_factory=list)  # Hints required to reach this checkpoint
    requirements: Dict[str, Any] = Field(default_factory=dict)  # Additional requirements
    rewards: Dict[str, Any] = Field(default_factory=dict)  # Rewards for reaching this checkpoint
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class NarrativeTagMongoSchema(BaseModel):
    """
    Schema for narrative tags to organize and filter content
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    tag_id: str
    name: str
    description: str
    category: str = "general"  # "genre", "theme", "difficulty", etc.
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class LucienMessageMongoSchema(BaseModel):
    """
    Schema for Lucien messages that are sent via Telegram API
    Implements requirement 1.6: sending dynamic templated messages via Telegram API
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    message_id: str
    template_name: str
    title: Optional[str] = None
    content: str
    context_variables: Dict[str, Any] = Field(default_factory=dict)
    recipients: List[str] = Field(default_factory=list)  # List of user IDs to send to
    scheduled_time: Optional[datetime] = None
    sent_time: Optional[datetime] = None
    delivery_status: str = "pending"  # "pending", "sent", "failed", "delivered"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class NarrativeProgressMongoSchema(BaseModel):
    """
    MongoDB schema for narrative progress tracking as a standalone collection
    Implements requirement 6.2: maintaining narrative_progress in the database
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    current_fragment: str
    completed_fragments: List[str] = Field(default_factory=list)
    unlocked_hints: List[str] = Field(default_factory=list)  # pistas unlocked
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    progression_path: List[str] = Field(default_factory=list)  # Track path through narrative
    checkpoints_reached: List[str] = Field(default_factory=list)
    total_reading_time: int = 0  # Total time spent reading in seconds
    narrative_score: int = 0  # Score based on choices and progression
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

"""
Database Schemas - MongoDB

This module contains all MongoDB schema definitions used throughout the application
following Pydantic patterns from existing models.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId
from pydantic_core import core_schema


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


class NarrativeProgress(BaseModel):
    """Schema for tracking user's narrative progress according to requirements"""
    current_fragment: str = ""
    completed_fragments: List[str] = Field(default_factory=list)
    unlocked_hints: List[str] = Field(default_factory=list)  # pistas
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    progression_path: List[str] = Field(default_factory=list)  # Track the path user took through the narrative


class UserState(BaseModel):
    """Current state of user including menu context and narrative progress"""
    menu_context: str = "main_menu"
    narrative_progress: Optional[NarrativeProgress] = Field(default_factory=NarrativeProgress)
    session_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UserPreferences(BaseModel):
    """User preferences like language, notifications, theme"""
    language: str = "es"
    notifications_enabled: bool = True
    theme: str = "default"


class UserMongoSchema(BaseModel):
    """
    MongoDB schema for user data including dynamic state and preferences
    Extended to support requirements 1.2, 2.1, 3.1, 6.2:
    - 1.2: Narrative state updated in database (narrative_progress)
    - 2.1: Besitos atomic transactions (besitos_balance, transaction tracking)
    - 3.1: User access validation via Telegram API (access control fields)
    - 6.2: Maintain narrative_progress in users collection
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str  # Telegram user ID
    current_state: UserState = Field(default_factory=UserState)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Gamification fields (Requirement 2.1)
    besitos_balance: int = 0
    total_earned_besitos: int = 0
    total_spent_besitos: int = 0
    last_besitos_activity: Optional[datetime] = None
    
    # Narrative fields (Requirements 1.2, 6.2)
    narrative_progress: Optional[NarrativeProgress] = Field(default_factory=NarrativeProgress)
    
    # Narrative level field (Requirement 5.2)
    narrative_level: int = 1
    
    # Administration fields (Requirement 3.1)
    is_admin: bool = False
    access_level: str = "user"  # "user", "moderator", "admin", "super_admin"
    channels_access: List[str] = Field(default_factory=list)  # List of accessible channels
    subscription_status: str = "free"  # "free", "premium", "vip"
    subscription_expires_at: Optional[datetime] = None
    
    # Mission and achievement tracking
    active_missions: List[Dict[str, Any]] = Field(default_factory=list)
    unlocked_achievements: List[str] = Field(default_factory=list)
    
    # Inventory (mochila)
    inventory: List[Dict[str, Any]] = Field(default_factory=list)  # [{"item_id": "id", "quantity": 1}]
    
    # Activity tracking
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True  # Pydantic v2 compatibility


class Choice(BaseModel):
    """Choice within a narrative fragment"""
    id: str
    text: str
    next_fragment: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NarrativeMetadata(BaseModel):
    """Metadata for narrative fragments"""
    difficulty: str = "easy"
    tags: List[str] = Field(default_factory=list)
    vip_required: bool = False


class NarrativeFragmentMongoSchema(BaseModel):
    """
    MongoDB schema for narrative fragments containing story content and choices
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    fragment_id: str
    title: str
    content: str
    choices: List[Choice] = Field(default_factory=list)
    metadata: NarrativeMetadata = Field(default_factory=NarrativeMetadata)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ItemMetadata(BaseModel):
    """Metadata for items in the system"""
    value: int = 1
    emoji: str = ""
    description: str = ""


class ItemMongoSchema(BaseModel):
    """
    MongoDB schema for items (virtual items, gifts, achievements)
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    item_id: str
    name: str
    type: str  # currency, achievement, gift, etc.
    metadata: ItemMetadata = Field(default_factory=ItemMetadata)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class DatabaseMigration(BaseModel):
    """
    MongoDB schema for tracking database migrations
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    migration_id: str
    description: str
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    applied_by: str = "system"

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
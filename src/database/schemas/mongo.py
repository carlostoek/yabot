"""
Database Schemas - MongoDB

This module contains all MongoDB schema definitions used throughout the application
following Pydantic patterns from existing models.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId field for Pydantic models"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserState(BaseModel):
    """Current state of user including menu context and narrative progress"""
    menu_context: str = "main_menu"
    narrative_progress: Optional[Dict[str, Any]] = Field(default_factory=dict)
    session_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UserPreferences(BaseModel):
    """User preferences like language, notifications, theme"""
    language: str = "es"
    notifications_enabled: bool = True
    theme: str = "default"


class UserMongoSchema(BaseModel):
    """
    MongoDB schema for user data including dynamic state and preferences
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str  # Telegram user ID
    current_state: UserState = Field(default_factory=UserState)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


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
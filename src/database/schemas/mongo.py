"""
MongoDB schema definitions for the YABOT system.

This module provides Pydantic models for MongoDB collections as required by the fase1 specification.
These models are used for data validation and serialization when working with MongoDB collections.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class UserState(BaseModel):
    """User dynamic state model."""
    menu_context: Optional[str] = None
    narrative_progress: Optional[Dict[str, Any]] = None
    session_data: Optional[Dict[str, Any]] = None


class UserPreferences(BaseModel):
    """User preferences model."""
    language: Optional[str] = "en"
    notifications_enabled: Optional[bool] = True
    theme: Optional[str] = "default"


class User(BaseModel):
    """User document model for the Users collection."""
    user_id: str = Field(..., description="Telegram user ID (primary key)")
    current_state: Optional[UserState] = None
    preferences: Optional[UserPreferences] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Choice(BaseModel):
    """Choice model for narrative fragments."""
    id: str
    text: str
    next_fragment: Optional[str] = None


class NarrativeFragmentMetadata(BaseModel):
    """Metadata model for narrative fragments."""
    difficulty: Optional[str] = "medium"
    tags: Optional[List[str]] = Field(default_factory=list)
    vip_required: Optional[bool] = False


class NarrativeFragment(BaseModel):
    """Narrative fragment model for the NarrativeFragments collection."""
    fragment_id: str = Field(..., description="Unique identifier for the fragment")
    title: str
    content: str
    choices: Optional[List[Choice]] = Field(default_factory=list)
    metadata: Optional[NarrativeFragmentMetadata] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ItemMetadata(BaseModel):
    """Metadata model for items."""
    value: Optional[int] = 0
    emoji: Optional[str] = None
    description: Optional[str] = None


class Item(BaseModel):
    """Item model for the Items collection."""
    item_id: str = Field(..., description="Unique identifier for the item")
    name: str
    type: str
    metadata: Optional[ItemMetadata] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
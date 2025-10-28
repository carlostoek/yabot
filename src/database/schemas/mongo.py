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


class SubscriptionInfo(BaseModel):
    """User subscription information for VIP status management."""
    is_vip: Optional[bool] = False
    subscription_type: Optional[str] = None  # "monthly", "yearly", "lifetime"
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    auto_renewal: Optional[bool] = False


class GamificationStats(BaseModel):
    """User gamification statistics."""
    level: Optional[int] = 1
    experience_points: Optional[int] = 0
    achievements: Optional[List[str]] = Field(default_factory=list)
    badges: Optional[List[str]] = Field(default_factory=list)
    daily_streak: Optional[int] = 0
    last_activity: Optional[datetime] = None


class AdminInfo(BaseModel):
    """Administrative information for user management."""
    is_admin: Optional[bool] = False
    permissions: Optional[List[str]] = Field(default_factory=list)
    moderation_flags: Optional[Dict[str, Any]] = Field(default_factory=dict)
    last_login: Optional[datetime] = None


class EmotionalSignature(BaseModel):
    """User emotional signature and archetype data."""
    archetype: Optional[str] = None  # EXPLORADOR_PROFUNDO, DIRECTO_AUTENTICO, etc.
    authenticity_score: Optional[float] = 0.0
    vulnerability_level: Optional[float] = 0.0
    response_patterns: Optional[Dict[str, Any]] = Field(default_factory=dict)
    signature_strength: Optional[float] = 0.0
    last_analysis: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class EmotionalJourney(BaseModel):
    """User emotional journey and Diana level progression."""
    current_level: Optional[int] = 1
    level_entry_date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    progression_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    emotional_milestones: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    vip_integration_status: Optional[Dict[str, Any]] = Field(default_factory=dict)
    circle_intimo_access: Optional[bool] = False
    relationship_depth_score: Optional[float] = 0.0
    last_progression_check: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    """User document model for the Users collection."""
    user_id: str = Field(..., description="Telegram user ID (primary key)")
    current_state: Optional[UserState] = None
    preferences: Optional[UserPreferences] = None

    # Virtual currency and economy
    besitos_balance: Optional[int] = Field(default=0, description="User's besitos balance for virtual currency")

    # Subscription and VIP management
    subscription: Optional[SubscriptionInfo] = None

    # Gamification features
    gamification: Optional[GamificationStats] = None

    # Administrative information
    admin: Optional[AdminInfo] = None

    # Emotional intelligence fields
    emotional_signature: Optional[EmotionalSignature] = None
    emotional_journey: Optional[EmotionalJourney] = None

    # Inventory and items
    inventory: Optional[Dict[str, int]] = Field(default_factory=dict, description="User's item inventory with quantities")

    # Timestamps
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


class LucienEvaluations(BaseModel):
    """Stores Lucien's evaluations of a user's progress and worthiness."""
    user_id: str = Field(..., description="The user ID this evaluation pertains to.")
    current_evaluation_level: int = Field(default=1, description="The user's current evaluation level according to Lucien.")
    relationship_state: Dict[str, Any] = Field(default_factory=dict, description="The state of the user's relationship with Lucien.")
    archetype_assessment: Dict[str, Any] = Field(default_factory=dict, description="Lucien's assessment of the user's archetype.")
    behavioral_history: List[Dict[str, Any]] = Field(default_factory=list, description="A log of significant user behaviors.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DianaEncounters(BaseModel):
    """Tracks special, earned encounters with Diana."""
    encounter_id: str = Field(..., description="Unique identifier for the encounter.")
    user_id: str = Field(..., description="The user ID who experienced the encounter.")
    trigger_condition: str = Field(..., description="The condition that triggered the encounter.")
    emotional_significance: float = Field(..., description="The calculated emotional significance of the moment.")
    encounter_time: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when the encounter occurred.")
    impact_metrics: Dict[str, Any] = Field(default_factory=dict, description="Metrics on the impact of the encounter.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
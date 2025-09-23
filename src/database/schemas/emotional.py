"""
Emotional intelligence specific schemas for MongoDB collections.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class MemoryFragment(BaseModel):
    """Emotional memory fragment for relationship continuity."""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique memory identifier")
    user_id: str = Field(..., description="Associated user ID")
    interaction_context: Dict[str, Any] = Field(..., description="Context of the memorable interaction")
    emotional_significance: float = Field(..., description="Emotional importance score (0.0-1.0)")
    memory_type: str = Field(..., description="Type of memory (vulnerability, breakthrough, etc.)")
    content_summary: str = Field(..., description="Summary of the interaction content")
    diana_response_context: str = Field(..., description="Diana's response context")
    recall_triggers: List[str] = Field(default_factory=list, description="Keywords that trigger this memory")
    relationship_stage: int = Field(..., description="Diana level when memory was created")
    reference_count: int = Field(default=0, description="Number of times memory was referenced")
    last_referenced: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MemoryCallback(BaseModel):
    """Represents a generated callback string to be used in a response."""
    callback_text: str
    source_memory_id: str
    relevance_score: float

class PersonalizedResponse(BaseModel):
    """Represents a fully personalized response to be sent to the user."""
    response_text: str
    personalization_details: Dict[str, Any]

class ContentVariant(BaseModel):
    """Represents a variant of a piece of content tailored for an archetype."""
    variant_text: str
    archetype: str

class ProgressionAssessment(BaseModel):
    """Represents the assessment of a user's readiness to progress."""
    is_ready: bool
    next_level: Optional[int] = None
    reason: str
    required_vip: bool = False

class EmotionalResponse(BaseModel):
    """Represents the outcome of an emotional analysis."""
    emotional_metrics: Dict[str, Any]
    archetype: Optional[str] = None
    progression_assessment: Optional[ProgressionAssessment] = None
    significant_moment_recorded: bool = False

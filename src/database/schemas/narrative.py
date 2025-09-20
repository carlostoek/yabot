"""
Narrative collections schema for the YABOT system.

This module provides specialized Pydantic models for narrative module collections
as required by requirements 1.1, 1.4, and 6.1. These models extend the base
patterns from src/database/schemas/mongo.py with narrative-specific functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from src.core.models import BaseModel as CoreBaseModel


class Choice(BaseModel):
    """Choice model for narrative fragment decisions."""
    choice_id: str = Field(..., description="Unique identifier for the choice")
    text: str = Field(..., description="Display text for the choice")
    next_fragment_id: Optional[str] = Field(None, description="ID of the next fragment if choice is selected")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions required to show this choice")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional choice metadata")


class NarrativeFragmentMetadata(BaseModel):
    """Extended metadata model for narrative fragments."""
    difficulty: Optional[str] = Field("medium", description="Difficulty level (easy, medium, hard)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    vip_required: bool = Field(False, description="Whether VIP access is required")
    estimated_read_time: Optional[int] = Field(None, description="Estimated reading time in seconds")
    unlock_conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions to unlock this fragment")
    rewards: Dict[str, Any] = Field(default_factory=dict, description="Rewards for completing this fragment")
    author: Optional[str] = Field(None, description="Fragment author")
    version: str = Field("1.0", description="Fragment version for content updates")


class NarrativeFragment(CoreBaseModel):
    """Enhanced narrative fragment model for the narrative_fragments collection."""
    fragment_id: str = Field(..., description="Unique identifier for the fragment")
    title: str = Field(..., description="Fragment title")
    content: str = Field(..., description="Main narrative content")
    choices: List[Choice] = Field(default_factory=list, description="Available choices")
    vip_required: bool = Field(False, description="Whether VIP access is required")
    metadata: NarrativeFragmentMetadata = Field(default_factory=NarrativeFragmentMetadata, description="Fragment metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    published: bool = Field(False, description="Whether the fragment is published")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")


class HintCondition(BaseModel):
    """Condition model for hint unlocking."""
    type: str = Field(..., description="Condition type (fragment_completed, item_collected, etc.)")
    target: str = Field(..., description="Target identifier (fragment_id, item_id, etc.)")
    operator: str = Field("equals", description="Comparison operator")
    value: Any = Field(..., description="Required value")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional condition metadata")


class Hint(CoreBaseModel):
    """Hint model for the narrative_hints collection."""
    hint_id: str = Field(..., description="Unique identifier for the hint")
    fragment_id: str = Field(..., description="Associated fragment ID")
    title: str = Field(..., description="Hint title")
    content: str = Field(..., description="Hint content/description")
    unlock_conditions: List[HintCondition] = Field(default_factory=list, description="Conditions to unlock this hint")
    reward_type: str = Field("information", description="Type of reward (information, item, besitos)")
    reward_value: Any = Field(None, description="Reward value")
    vip_required: bool = Field(False, description="Whether VIP access is required")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    active: bool = Field(True, description="Whether the hint is active")


class NarrativeProgress(CoreBaseModel):
    """User narrative progress model for the narrative_progress collection."""
    user_id: str = Field(..., description="User identifier")
    current_fragment: str = Field(..., description="Current fragment ID")
    completed_fragments: List[str] = Field(default_factory=list, description="List of completed fragment IDs")
    unlocked_hints: List[str] = Field(default_factory=list, description="List of unlocked hint IDs")
    choices_made: Dict[str, str] = Field(default_factory=dict, description="Mapping of fragment_id to choice_id")
    progress_data: Dict[str, Any] = Field(default_factory=dict, description="Additional progress data")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="When user started narrative")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last progress update")
    completion_percentage: float = Field(0.0, description="Overall completion percentage")
    active: bool = Field(True, description="Whether progress tracking is active")


class UserChoiceLog(CoreBaseModel):
    """Log of user choices for analytics and replay."""
    log_id: str = Field(..., description="Unique log identifier")
    user_id: str = Field(..., description="User identifier")
    fragment_id: str = Field(..., description="Fragment where choice was made")
    choice_id: str = Field(..., description="Choice that was selected")
    choice_text: str = Field(..., description="Text of the selected choice")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When choice was made")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Context at time of choice")
    completion_time_ms: Optional[int] = Field(None, description="Time taken to make choice in milliseconds")


class LucienMessage(CoreBaseModel):
    """Lucien dynamic message model for the lucien_messages collection."""
    message_id: str = Field(..., description="Unique message identifier")
    user_id: str = Field(..., description="Target user identifier")
    template_id: str = Field(..., description="Message template identifier")
    template_content: str = Field(..., description="Message template with placeholders")
    rendered_content: str = Field(..., description="Final rendered message content")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Data used for template rendering")
    trigger_event: str = Field(..., description="Event that triggered this message")
    trigger_data: Dict[str, Any] = Field(default_factory=dict, description="Data from triggering event")
    scheduled_time: Optional[datetime] = Field(None, description="When message should be sent")
    sent_time: Optional[datetime] = Field(None, description="When message was actually sent")
    status: str = Field("pending", description="Message status (pending, sent, failed, cancelled)")
    telegram_message_id: Optional[int] = Field(None, description="Telegram message ID after sending")
    error_message: Optional[str] = Field(None, description="Error message if sending failed")
    retry_count: int = Field(0, description="Number of retry attempts")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class NarrativeTemplate(CoreBaseModel):
    """Template model for dynamic content generation."""
    template_id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    category: str = Field(..., description="Template category (lucien_message, hint, fragment)")
    content_template: str = Field(..., description="Template content with placeholders")
    required_variables: List[str] = Field(default_factory=list, description="Required template variables")
    optional_variables: List[str] = Field(default_factory=list, description="Optional template variables")
    default_values: Dict[str, Any] = Field(default_factory=dict, description="Default values for variables")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions for template usage")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Template metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    active: bool = Field(True, description="Whether template is active")
    version: str = Field("1.0", description="Template version")


# Collection indexes for optimal performance
NARRATIVE_INDEXES = {
    "narrative_fragments": [
        {"fragment_id": 1},  # Primary key index
        {"vip_required": 1, "published": 1},  # VIP and published content queries
        {"metadata.tags": 1},  # Tag-based searches
        {"created_at": -1},  # Recent content queries
        {"published_at": -1, "published": 1},  # Published content by date
        {"metadata.difficulty": 1, "vip_required": 1}  # Difficulty and VIP filtering
    ],
    "narrative_hints": [
        {"hint_id": 1},  # Primary key index
        {"fragment_id": 1},  # Hints for specific fragments
        {"vip_required": 1, "active": 1},  # VIP and active hints
        {"created_at": -1}  # Recent hints
    ],
    "narrative_progress": [
        {"user_id": 1},  # Primary key index
        {"user_id": 1, "active": 1},  # Active user progress
        {"current_fragment": 1},  # Users on specific fragments
        {"completion_percentage": -1},  # Progress leaderboard
        {"last_updated": -1}  # Recent activity
    ],
    "user_choice_logs": [
        {"user_id": 1, "timestamp": -1},  # User choice history
        {"fragment_id": 1, "timestamp": -1},  # Fragment choice analytics
        {"choice_id": 1},  # Choice popularity analytics
        {"session_id": 1},  # Session-based analysis
        {"timestamp": -1}  # Chronological analysis
    ],
    "lucien_messages": [
        {"user_id": 1, "status": 1},  # User messages by status
        {"scheduled_time": 1, "status": 1},  # Scheduled messages
        {"trigger_event": 1, "created_at": -1},  # Messages by trigger
        {"status": 1, "created_at": -1},  # Message queue processing
        {"message_id": 1}  # Primary key index
    ],
    "narrative_templates": [
        {"template_id": 1},  # Primary key index
        {"category": 1, "active": 1},  # Templates by category
        {"name": 1},  # Template name searches
        {"created_at": -1}  # Recent templates
    ]
}

# Collection validation schemas for MongoDB
NARRATIVE_COLLECTION_SCHEMAS = {
    "narrative_fragments": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["fragment_id", "title", "content"],
            "properties": {
                "fragment_id": {"bsonType": "string"},
                "title": {"bsonType": "string"},
                "content": {"bsonType": "string"},
                "vip_required": {"bsonType": "bool"},
                "published": {"bsonType": "bool"},
                "choices": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["choice_id", "text"],
                        "properties": {
                            "choice_id": {"bsonType": "string"},
                            "text": {"bsonType": "string"},
                            "next_fragment_id": {"bsonType": ["string", "null"]}
                        }
                    }
                }
            }
        }
    },
    "narrative_progress": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "current_fragment"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "current_fragment": {"bsonType": "string"},
                "completed_fragments": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"}
                },
                "completion_percentage": {
                    "bsonType": "number",
                    "minimum": 0,
                    "maximum": 100
                }
            }
        }
    },
    "lucien_messages": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["message_id", "user_id", "template_id", "status"],
            "properties": {
                "message_id": {"bsonType": "string"},
                "user_id": {"bsonType": "string"},
                "template_id": {"bsonType": "string"},
                "status": {
                    "bsonType": "string",
                    "enum": ["pending", "sent", "failed", "cancelled"]
                },
                "retry_count": {
                    "bsonType": "number",
                    "minimum": 0
                }
            }
        }
    },
    "narrative_templates": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["template_id", "name", "category", "content_template"],
            "properties": {
                "template_id": {"bsonType": "string"},
                "name": {"bsonType": "string"},
                "category": {"bsonType": "string"},
                "content_template": {"bsonType": "string"},
                "active": {"bsonType": "bool"},
                "required_variables": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"}
                },
                "optional_variables": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"}
                }
            }
        }
    }
}
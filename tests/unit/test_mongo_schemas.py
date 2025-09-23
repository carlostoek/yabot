"""
Unit tests for the MongoDB schema definitions.
"""

import pytest
from datetime import datetime
from src.database.schemas.mongo import User, UserState, UserPreferences, NarrativeFragment, Choice, NarrativeFragmentMetadata, Item, ItemMetadata


class TestMongoSchemas:
    """Test cases for MongoDB schema definitions."""

    def test_user_model_minimal(self):
        """Test User model with minimal required fields."""
        user = User(user_id="12345")
        
        assert user.user_id == "12345"
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_model_full(self):
        """Test User model with all fields."""
        current_state = UserState(
            menu_context="main_menu",
            narrative_progress={
                "current_fragment": "fragment_001",
                "completed_fragments": ["intro_001", "intro_002"]
            },
            session_data={"last_activity": "2025-01-15T10:30:00Z"}
        )
        
        preferences = UserPreferences(
            language="es",
            notifications_enabled=True,
            theme="default"
        )
        
        user = User(
            user_id="12345",
            current_state=current_state,
            preferences=preferences
        )
        
        assert user.user_id == "12345"
        assert user.current_state.menu_context == "main_menu"
        assert user.current_state.narrative_progress["current_fragment"] == "fragment_001"
        assert "intro_001" in user.current_state.narrative_progress["completed_fragments"]
        assert user.preferences.language == "es"
        assert user.preferences.notifications_enabled is True

    def test_narrative_fragment_model(self):
        """Test NarrativeFragment model."""
        choice_a = Choice(
            id="choice_a",
            text="Explorar el bosque",
            next_fragment="forest_001"
        )
        
        choice_b = Choice(
            id="choice_b",
            text="Ir al pueblo",
            next_fragment="village_001"
        )
        
        metadata = NarrativeFragmentMetadata(
            difficulty="easy",
            tags=["intro", "adventure"],
            vip_required=False
        )
        
        fragment = NarrativeFragment(
            fragment_id="fragment_001",
            title="El Comienzo",
            content="Tu aventura comienza aquí...",
            choices=[choice_a, choice_b],
            metadata=metadata
        )
        
        assert fragment.fragment_id == "fragment_001"
        assert fragment.title == "El Comienzo"
        assert fragment.content == "Tu aventura comienza aquí..."
        assert len(fragment.choices) == 2
        assert fragment.choices[0].id == "choice_a"
        assert fragment.choices[1].text == "Ir al pueblo"
        assert fragment.metadata.difficulty == "easy"
        assert "intro" in fragment.metadata.tags
        assert fragment.metadata.vip_required is False

    def test_item_model(self):
        """Test Item model."""
        metadata = ItemMetadata(
            value=1,
            emoji="😘",
            description="Un besito virtual lleno de cariño"
        )
        
        item = Item(
            item_id="besito_001",
            name="Besito Virtual",
            type="currency",
            metadata=metadata
        )
        
        assert item.item_id == "besito_001"
        assert item.name == "Besito Virtual"
        assert item.type == "currency"
        assert item.metadata.value == 1
        assert item.metadata.emoji == "😘"
        assert item.metadata.description == "Un besito virtual lleno de cariño"

    def test_default_values(self):
        """Test default values for optional fields."""
        preferences = UserPreferences()
        assert preferences.language == "en"
        assert preferences.notifications_enabled is True
        assert preferences.theme == "default"
        
        metadata = NarrativeFragmentMetadata()
        assert metadata.difficulty == "medium"
        assert metadata.tags == []
        assert metadata.vip_required is False
        
        metadata = ItemMetadata()
        assert metadata.value == 0
        assert metadata.emoji is None
        assert metadata.description is None
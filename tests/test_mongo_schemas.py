"""
Test for the MongoDB schema definitions.
"""

from datetime import datetime
from src.database.schemas.mongo import User, UserState, UserPreferences, NarrativeFragment, Choice, NarrativeFragmentMetadata, Item, ItemMetadata


def test_user_model():
    """Test User model creation and validation."""
    # Create a user with minimal required fields
    user = User(
        user_id="12345"
    )
    
    assert user.user_id == "12345"
    assert user.created_at is not None
    assert user.updated_at is not None
    
    # Create a user with all fields
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
    assert user.preferences.language == "es"


def test_narrative_fragment_model():
    """Test NarrativeFragment model creation and validation."""
    # Create choices
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
    
    # Create metadata
    metadata = NarrativeFragmentMetadata(
        difficulty="easy",
        tags=["intro", "adventure"],
        vip_required=False
    )
    
    # Create fragment
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
    assert fragment.metadata.difficulty == "easy"
    assert "intro" in fragment.metadata.tags


def test_item_model():
    """Test Item model creation and validation."""
    # Create metadata
    metadata = ItemMetadata(
        value=1,
        emoji="😘",
        description="Un besito virtual lleno de cariño"
    )
    
    # Create item
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


if __name__ == "__main__":
    test_user_model()
    test_narrative_fragment_model()
    test_item_model()
    print("All tests passed!")
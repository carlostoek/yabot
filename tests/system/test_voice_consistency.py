
"""
System-level tests for Lucien's voice consistency.

These tests validate that Lucien's voice remains consistent and evolves correctly
across different user interaction points and states, ensuring a coherent character
presentation throughout the application.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.services.user import UserService
from src.handlers.telegram_commands import CommandHandler
from src.ui.menu_factory import MenuFactory, MenuType, UserRole
from src.database.manager import DatabaseManager

# Use mock fixtures from conftest
from tests.conftest import mock_database_manager, mock_event_bus

@pytest.fixture
async def setup_system(mock_database_manager: DatabaseManager, mock_event_bus: Mock):
    """Provides a consistent setup for system-level tests."""
    user_service = UserService(db_manager=mock_database_manager)
    command_handler = CommandHandler(user_service=user_service, event_bus=mock_event_bus)
    menu_factory = MenuFactory()
    # Mock the async connection for the menu factory's cache manager
    menu_factory.cache_manager.connect = Mock(return_value=None)
    
    # Create a test user
    user_id = "system_test_user_1"
    user_details = {
        "id": user_id,
        "username": "system_tester",
        "first_name": "System",
        "last_name": "Test"
    }
    await user_service.create_user(user_details)
    
    return user_service, command_handler, menu_factory, user_id

@pytest.mark.asyncio
async def test_voice_consistency_across_commands(setup_system):
    """Ensures Lucien's voice is formal and consistent across different basic commands."""
    user_service, command_handler, menu_factory, user_id = setup_system

    # Simulate a message from the user
    mock_message = MagicMock()
    mock_message.from_user = Mock(id=user_id)

    # Test /start command
    start_response = await command_handler.handle_start(mock_message)
    assert "usted" in start_response.text
    assert "evaluar si usted posee la sofisticación" in start_response.text

    # Test /menu command
    menu_response = await command_handler.handle_menu(mock_message)
    assert "usted" in menu_response.text
    assert "opciones considera usted apropiadas" in menu_response.text

    # Test /help command
    help_response = await command_handler.handle_help(mock_message)
    assert "usted" in help_response.text
    assert "orientarle en el uso apropiado" in help_response.text

@pytest.mark.asyncio
async def test_voice_evolves_with_relationship_level(setup_system):
    """Verifies that Lucien's tone evolves as the user's relationship level changes."""
    user_service, command_handler, menu_factory, user_id = setup_system
    mock_message = MagicMock()
    mock_message.from_user = Mock(id=user_id)

    # 1. Initial state: Formal Examiner
    response_initial = await command_handler.handle_start(mock_message)
    assert "evaluar si usted posee la sofisticación" in response_initial.text

    # 2. Evolve state: Reluctant Appreciator
    await user_service.update_user_profile(user_id, {"narrative_level": 3})
    response_appreciator = await command_handler.handle_start(mock_message)
    assert "menos decepcionantes de lo que anticipé" in response_appreciator.text

    # 3. Evolve state: Trusted Confidant
    await user_service.update_user_profile(user_id, {"narrative_level": 5, "has_vip": True})
    response_confidant = await command_handler.handle_start(mock_message)
    assert "placer genuine continuar nuestro diálogo" in response_confidant.text

@pytest.mark.asyncio
async def test_voice_consistency_in_menu_generation(setup_system):
    """Checks that menu headers and footers also use Lucien's consistent voice."""
    user_service, command_handler, menu_factory, user_id = setup_system

    # 1. Get menu for a new user (Formal Examiner)
    user_context_initial = await user_service.get_user_context(user_id)
    menu_initial = await menu_factory.create_menu(MenuType.MAIN, user_context_initial)
    
    assert "evaluar si usted posee" in menu_initial.header_text
    assert "será evaluada" in menu_initial.footer_text

    # 2. Get menu for a trusted user (Trusted Confidant)
    await user_service.update_user_profile(user_id, {"narrative_level": 5, "has_vip": True})
    user_context_vip = await user_service.get_user_context(user_id)
    menu_vip = await menu_factory.create_menu(MenuType.MAIN, user_context_vip)

    assert "placer genuine" in menu_vip.header_text
    assert "discernimiento que he llegado a appreciate" in menu_vip.footer_text

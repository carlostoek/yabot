
"""
Integration tests for the new user onboarding flow.

These tests simulate the entire process a new user goes through when they first
interact with the bot, ensuring that user creation, initial evaluation, and the
first response are all handled correctly.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.handlers.telegram_commands import CommandHandler
from src.services.user import UserService
from src.database.manager import DatabaseManager

# Use the mock database manager from conftest
from tests.conftest import mock_database_manager

@pytest.mark.asyncio
async def test_new_user_onboarding_flow(mock_database_manager: DatabaseManager):
    """
    Tests the full onboarding flow for a new user sending /start.

    This test verifies that:
    1. A new user is created in the database upon first contact.
    2. Lucien provides the correct initial, formal welcome message.
    3. The initial relationship level is set to FORMAL_EXAMINER.
    """
    # Arrange
    user_service = UserService(db_manager=mock_database_manager)
    command_handler = CommandHandler(user_service=user_service)

    # Simulate a new user message from aiogram
    new_user_id = 123456789
    mock_user = Mock()
    mock_user.id = new_user_id
    mock_user.username = "new_test_user"
    mock_user.first_name = "New"
    mock_user.last_name = "User"
    mock_user.language_code = "en"

    mock_message = MagicMock()
    mock_message.from_user = mock_user

    # Action: A new user sends the /start command
    response = await command_handler.handle_start(mock_message)

    # Assertions

    # 1. Verify user was created in the database
    created_user_context = await user_service.get_user_context(str(new_user_id))
    assert created_user_context is not None
    assert created_user_context["user_id"] == str(new_user_id)
    assert created_user_context["role"] == "free_user"
    assert created_user_context["narrative_level"] == 1

    # 2. Verify Lucien's initial welcome message is correct
    assert response is not None
    response_text = response.text.lower()
    # Check for key phrases from the FORMAL_EXAMINER level welcome
    assert "permítame presentarme" in response_text
    assert "evaluar si usted posee la sofisticación" in response_text
    assert "cada interacción será cuidadosamente evaluada" in response_text

    # 3. Verify that no informalities are present
    assert "tú" not in response_text
    assert "vos" not in response_text

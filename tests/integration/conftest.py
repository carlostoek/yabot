"""
Configuration for integration tests between modules

This file provides fixtures and setup for cross-module integration testing.
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

# Set test environment variables
os.environ.setdefault('MONGODB_DATABASE', 'yabot_integration_test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/1')  # Use different Redis DB for tests


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_bot():
    """Mock Telegram Bot for testing"""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.send_poll = AsyncMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    return bot


@pytest.fixture
def integration_test_config():
    """Configuration for integration tests"""
    return {
        'test_user_id': 'integration_test_user',
        'test_chat_id': -1001234567890,
        'test_message_id': 42,
        'besitos_reward_amount': 10,
        'hint_price': 10,
        'mission_reward': 15,
        'cooldown_seconds': 1,  # Short cooldown for testing
    }


@pytest.fixture
async def clean_test_database():
    """Clean test database before and after tests"""
    from src.database.mongodb import get_database_client

    client = get_database_client()
    test_db = client.yabot_integration_test

    # Clean before test
    collections_to_clean = [
        'users', 'besitos_transactions', 'missions', 'items',
        'user_items', 'narrative_progress', 'achievements'
    ]

    for collection_name in collections_to_clean:
        try:
            await test_db[collection_name].drop()
        except Exception:
            pass  # Collection might not exist

    yield test_db

    # Clean after test
    for collection_name in collections_to_clean:
        try:
            await test_db[collection_name].drop()
        except Exception:
            pass
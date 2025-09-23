
"""
Unit tests for the MessageManager class.

This module tests the functionality of the MessageManager, including message tracking,
deletion, main menu preservation, and scheduled cleanup.
"""

import asyncio
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, ANY

import pytest
from freezegun import freeze_time

from src.ui.message_manager import (
    MessageManager,
    MessageTrackingRecord,
    MESSAGE_TTL_CONFIG,
)

CHAT_ID = 12345
USER_ID = 67890

@pytest.fixture
def mock_bot():
    """Provides a mock aiogram Bot object."""
    bot = AsyncMock()
    bot.delete_message = AsyncMock()
    return bot

@pytest.fixture
def mock_cache_manager():
    """Provides a mock CacheManager object."""
    cache = AsyncMock()
    cache.connect = AsyncMock(return_value=True)
    cache.set_value = AsyncMock()
    cache.get_value = AsyncMock()
    cache.delete_key = AsyncMock()
    cache.get_keys_by_pattern = AsyncMock()
    return cache

@pytest.fixture
def message_manager(mock_bot, mock_cache_manager):
    """Provides a MessageManager instance with mocked dependencies."""
    manager = MessageManager(bot=mock_bot, cache=mock_cache_manager)
    # Replace the real scheduler with a MagicMock since its public methods are sync
    manager.scheduler = MagicMock()
    manager.scheduler.running = False
    yield manager
    if manager.scheduler.running:
        manager.shutdown()

@pytest.mark.asyncio
async def test_track_message(message_manager, mock_cache_manager):
    """Test that a message is correctly tracked in the cache."""
    message_id = 1
    message_type = 'system_notification' # Corrected from 'notification'
    ttl = MESSAGE_TTL_CONFIG[message_type]

    await message_manager.track_message(CHAT_ID, message_id, message_type)

    mock_cache_manager.set_value.assert_called_once()
    call_args, call_kwargs = mock_cache_manager.set_value.call_args
    key = call_args[0]
    record_dict = call_args[1]
    redis_ttl = call_kwargs['ttl']

    assert key == f"msg_track:{CHAT_ID}:{message_id}"
    assert record_dict['chat_id'] == CHAT_ID
    assert record_dict['message_id'] == message_id
    assert record_dict['message_type'] == message_type
    assert record_dict['should_delete'] is True
    assert redis_ttl == ttl + 10

@pytest.mark.asyncio
async def test_track_main_menu(message_manager, mock_cache_manager):
    """Test that a main menu message is tracked correctly and preserved."""
    message_id = 2
    await message_manager.track_message(CHAT_ID, message_id, 'main_menu', is_main_menu=True)

    # Check tracking record
    mock_cache_manager.set_value.assert_any_call(
        f"msg_track:{CHAT_ID}:{message_id}",
        ANY,
        ttl=None
    )
    # Extract the dictionary from the call arguments to inspect it
    found_record_dict = None
    for call in mock_cache_manager.set_value.call_args_list:
        if call[0][0] == f"msg_track:{CHAT_ID}:{message_id}":
            found_record_dict = call[0][1]
            break
    
    assert found_record_dict is not None
    assert found_record_dict['is_main_menu'] is True
    assert found_record_dict['should_delete'] is False

    # Check preservation
    mock_cache_manager.set_value.assert_any_call(
        f"main_menu:{CHAT_ID}",
        str(message_id),
        ttl=None
    )

@pytest.mark.asyncio
async def test_preserve_main_menu_deletes_old_one(message_manager, mock_cache_manager, mock_bot):
    """Test that preserving a new main menu deletes the old one."""
    old_menu_id = 100
    new_menu_id = 101

    mock_cache_manager.get_value.return_value = str(old_menu_id)

    await message_manager.preserve_main_menu(CHAT_ID, new_menu_id)

    # Check that the old menu was deleted
    mock_bot.delete_message.assert_called_once_with(CHAT_ID, old_menu_id)
    # Check that the old menu's tracking key was removed
    mock_cache_manager.delete_key.assert_called_once_with(f"msg_track:{CHAT_ID}:{old_menu_id}")
    # Check that the new menu ID was stored
    mock_cache_manager.set_value.assert_called_once_with(f"main_menu:{CHAT_ID}", str(new_menu_id), ttl=None)

@pytest.mark.asyncio
async def test_delete_old_messages(message_manager, mock_cache_manager, mock_bot):
    """Test that old messages are correctly identified and deleted."""
    main_menu_id = 201
    deletable_msg_id = 202
    preserved_msg_id = 203

    # Setup mock cache
    mock_cache_manager.get_value.side_effect = [
        str(main_menu_id), # For main menu lookup
        json.dumps(MessageTrackingRecord(CHAT_ID, main_menu_id, 'main_menu', is_main_menu=True, should_delete=False).__dict__, default=str),
        json.dumps(MessageTrackingRecord(CHAT_ID, deletable_msg_id, 'notification', should_delete=True).__dict__, default=str),
        json.dumps(MessageTrackingRecord(CHAT_ID, preserved_msg_id, 'system', should_delete=False).__dict__, default=str),
    ]
    mock_cache_manager.get_keys_by_pattern.return_value = [
        f"msg_track:{CHAT_ID}:{main_menu_id}",
        f"msg_track:{CHAT_ID}:{deletable_msg_id}",
        f"msg_track:{CHAT_ID}:{preserved_msg_id}",
    ]

    await message_manager.delete_old_messages(CHAT_ID)

    # Assert that only the deletable message was deleted
    mock_bot.delete_message.assert_called_once_with(CHAT_ID, deletable_msg_id)
    assert mock_bot.delete_message.call_count == 1

@patch('asyncio.gather', new_callable=AsyncMock)
@pytest.mark.asyncio
@freeze_time("2025-01-01 12:00:00")
async def test_periodic_cleanup_deletes_expired(mock_gather, message_manager, mock_cache_manager, mock_bot):
    """Test that the periodic cleanup job deletes expired messages."""
    expired_id = 301
    not_expired_id = 302
    permanent_id = 303

    # Record created 10 seconds ago with a 5 second TTL (expired)
    expired_record = MessageTrackingRecord(
        CHAT_ID, expired_id, 'notification', created_at=datetime.utcnow() - timedelta(seconds=10), ttl_seconds=5
    )
    # Record created 10 seconds ago with a 20 second TTL (not expired)
    not_expired_record = MessageTrackingRecord(
        CHAT_ID, not_expired_id, 'notification', created_at=datetime.utcnow() - timedelta(seconds=10), ttl_seconds=20
    )
    # Permanent record
    permanent_record = MessageTrackingRecord(
        CHAT_ID, permanent_id, 'main_menu', ttl_seconds=-1
    )

    mock_cache_manager.get_keys_by_pattern.return_value = [
        f"msg_track:{CHAT_ID}:{expired_id}",
        f"msg_track:{CHAT_ID}:{not_expired_id}",
        f"msg_track:{CHAT_ID}:{permanent_id}",
    ]
    mock_cache_manager.get_value.side_effect = [
        json.dumps(expired_record.__dict__, default=str),
        json.dumps(not_expired_record.__dict__, default=str),
        json.dumps(permanent_record.__dict__, default=str),
    ]

    await message_manager._cleanup_expired_messages()

    # Assert that asyncio.gather was called once
    mock_gather.assert_called_once()
    
    # Assert that it was called with a list containing exactly one coroutine
    args, kwargs = mock_gather.call_args
    assert len(args) == 1

    # Optional: Check the name of the coroutine
    assert args[0].__name__ == 'delete_message'

def test_scheduler_management(message_manager):
    """Test that the scheduler is started and shut down correctly."""
    manager = message_manager
    manager.start_periodic_cleanup(interval_seconds=30)

    manager.scheduler.add_job.assert_called_once_with(
        manager._cleanup_expired_messages,
        'interval',
        seconds=30,
        id='message_cleanup_job',
        replace_existing=True
    )
    manager.scheduler.start.assert_called_once()

    # Reset mock for shutdown test
    manager.scheduler.running = True
    manager.shutdown()
    manager.scheduler.shutdown.assert_called_once()

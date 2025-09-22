
"""
System-level performance validation tests.

These tests use pytest-benchmark to measure the end-to-end performance of
key user-facing interactions, ensuring the complete system meets the defined
non-functional requirements for response times.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock

from src.services.user import UserService
from src.handlers.telegram_commands import CommandHandler
from src.database.manager import DatabaseManager

# Use mock fixtures from conftest
from tests.conftest import mock_database_manager, mock_event_bus

@pytest.fixture
async def setup_system_for_performance(mock_database_manager: DatabaseManager, mock_event_bus: Mock):
    """Provides a consistent setup for system-level performance tests."""
    user_service = UserService(db_manager=mock_database_manager)
    command_handler = CommandHandler(user_service=user_service, event_bus=mock_event_bus)
    
    # Pre-populate users for different roles
    roles = {
        "free_user": {"id": "perf_free_user", "username": "free"},
        "vip_user": {"id": "perf_vip_user", "username": "vip"},
        "admin_user": {"id": "perf_admin_user", "username": "admin"},
    }
    for role, details in roles.items():
        await user_service.create_user(details)
        if role == "vip_user":
            await user_service.update_user_profile(details["id"], {"role": "vip_user", "has_vip": True, "narrative_level": 4})
        if role == "admin_user":
            await user_service.update_user_profile(details["id"], {"role": "admin", "has_vip": True, "narrative_level": 6})

    return command_handler, roles

@pytest.mark.asyncio
@pytest.mark.benchmark(group="system-command-response", min_rounds=20, timer=asyncio.sleep, warmup=False)
@pytest.mark.parametrize("user_role_key", ["free_user", "vip_user", "admin_user"])
async def test_system_start_command_performance(benchmark, setup_system_for_performance, user_role_key):
    """
    Benchmarks the end-to-end response time for the /start command.
    This covers command handling, user context retrieval, and voice generation.
    NFR: < 3 seconds (should be much faster in test).
    """
    command_handler, roles = setup_system_for_performance
    user_id = roles[user_role_key]["id"]
    
    mock_message = MagicMock()
    mock_message.from_user = Mock(id=user_id)

    @benchmark
    async def command_func():
        await command_handler.handle_start(mock_message)

@pytest.mark.asyncio
@pytest.mark.benchmark(group="system-menu-response", min_rounds=20, timer=asyncio.sleep, warmup=False)
@pytest.mark.parametrize("user_role_key", ["free_user", "vip_user", "admin_user"])
async def test_system_menu_command_performance(benchmark, setup_system_for_performance, user_role_key):
    """
    Benchmarks the end-to-end response time for the /menu command.
    This covers the full flow including menu generation logic.
    NFR: < 500ms.
    """
    command_handler, roles = setup_system_for_performance
    user_id = roles[user_role_key]["id"]
    
    mock_message = MagicMock()
    mock_message.from_user = Mock(id=user_id)

    @benchmark
    async def command_func():
        await command_handler.handle_menu(mock_message)

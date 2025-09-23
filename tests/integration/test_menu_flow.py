"""
Integration Tests for Menu Command to Callback Flow.

Tests the complete flow from menu command to callback processing to ensure
system integration meets requirements REQ-MENU-001.1, REQ-MENU-001.3, and
REQ-MENU-002.2.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from aiogram.types import Message, CallbackQuery, User, Chat

from src.handlers.menu_system import MenuSystemCoordinator
from src.services.user import UserService
from src.events.bus import EventBus

@pytest.mark.asyncio
class TestMenuCommandToCallbackFlow:
    """Test complete menu interaction flow."""

    @pytest.fixture
    async def menu_system(self):
        """Create menu system for testing."""
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.edit_message_text = AsyncMock()
        bot.delete_message = AsyncMock()

        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        user_service = Mock(spec=UserService)
        user_service.get_user_context = AsyncMock(return_value={
            "user_id": "test_user_123",
            "role": "vip_user",
            "has_vip": True,
            "narrative_level": 4,
            "user_archetype": "analytical",
            "worthiness_score": 0.8
        })

        coordinator = MenuSystemCoordinator(bot, event_bus, user_service)
        await coordinator.initialize()

        yield coordinator
        await coordinator.shutdown()

    @pytest.mark.asyncio
    async def test_complete_menu_interaction_flow(self, menu_system):
        """Test complete flow: command → menu → callback → response."""

        # Create mock message
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=456, type="private")
        message = Message(
            message_id=1, date=None, chat=chat, from_user=user,
            content_type="text", options={}
        )

        # Step 1: Handle menu command
        menu_result = await menu_system.handle_menu_command(message)
        assert menu_result["success"] is True
        assert "menu_id" in menu_result

        # Step 2: Handle callback query
        callback_query = CallbackQuery(
            id="test_callback", from_user=user, chat_instance="test",
            data="navigate:narrative_menu"
        )
        callback_query.message = message

        callback_result = await menu_system.handle_callback_query(callback_query)
        assert callback_result["success"] is True

        # Step 3: Verify system health
        health = await menu_system.get_system_health()
        assert health["overall_health_score"] > 80

    @pytest.mark.asyncio
    async def test_performance_under_load(self, menu_system):
        """Test system performance under concurrent load."""
        # Create multiple concurrent requests
        tasks = []
        for i in range(50):
            user = User(id=i, is_bot=False, first_name=f"User{i}")
            chat = Chat(id=i + 1000, type="private")
            message = Message(
                message_id=i, date=None, chat=chat, from_user=user,
                content_type="text", options={}
            )
            tasks.append(menu_system.handle_menu_command(message))

        # Execute concurrently and measure time
        import time
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Verify results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_results) >= 45  # 90% success rate minimum

        # Verify performance (should complete within reasonable time)
        total_time = end_time - start_time
        assert total_time < 10.0, f"Load test took too long: {total_time:.2f}s"
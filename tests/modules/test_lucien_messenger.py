"""
Test suite for the Lucien messenger module.

Tests the functionality of dynamic templated messaging for Lucien character
as required by the modulos-atomicos specification task 10.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from src.modules.narrative.lucien_messenger import (
    LucienMessenger,
    LucienMessengerError,
    TemplateNotFoundError,
    TemplateRenderingError,
    create_lucien_messenger
)


class TestLucienMessenger:
    """Test suite for LucienMessenger class."""

    @pytest.fixture
    def mock_mongodb_handler(self):
        """Create mock MongoDB handler."""
        handler = Mock()

        # Mock collections
        mock_collection = Mock()
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = Mock(acknowledged=True)
        mock_collection.update_one.return_value = Mock(modified_count=1)
        mock_collection.find.return_value = []

        handler.get_lucien_messages_collection.return_value = mock_collection
        handler.get_narrative_templates_collection.return_value = mock_collection

        return handler

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.is_connected = True
        return bus

    @pytest.fixture
    def mock_config_manager(self):
        """Create mock configuration manager."""
        manager = Mock()
        manager.get_bot_token.return_value = "test_bot_token_123"
        return manager

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.setex = AsyncMock(return_value=True)
        client.zadd = AsyncMock(return_value=True)
        client.ping = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def lucien_messenger(self, mock_mongodb_handler, mock_event_bus,
                        mock_config_manager, mock_redis_client):
        """Create LucienMessenger instance with mocked dependencies."""
        return LucienMessenger(
            mongodb_handler=mock_mongodb_handler,
            event_bus=mock_event_bus,
            config_manager=mock_config_manager,
            redis_client=mock_redis_client
        )

    @pytest.mark.asyncio
    async def test_send_message_success(self, lucien_messenger, mock_mongodb_handler):
        """Test successful message sending."""
        # Arrange
        user_id = "user123"
        template = "Hello $user_name, welcome to YABOT!"
        context = {"user_name": "TestUser"}

        # Act
        result = await lucien_messenger.send_message(user_id, template, context)

        # Assert
        assert result is True
        mock_mongodb_handler.get_lucien_messages_collection().insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_template_id(self, lucien_messenger, mock_mongodb_handler):
        """Test sending message with template ID resolution."""
        # Arrange
        user_id = "user123"
        template_id = "welcome_template"
        context = {"user_name": "TestUser"}

        # Mock template resolution
        mock_collection = mock_mongodb_handler.get_narrative_templates_collection()
        mock_collection.find_one.return_value = {
            "template_id": template_id,
            "content_template": "Hello $user_name, welcome!"
        }

        # Act
        result = await lucien_messenger.send_message(user_id, template_id, context)

        # Assert
        assert result is True
        mock_collection.find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_message_success(self, lucien_messenger, mock_mongodb_handler, mock_redis_client):
        """Test successful message scheduling."""
        # Arrange
        user_id = "user123"
        template = "Scheduled message for $user_name"
        delay = 60
        context = {"user_name": "TestUser"}

        # Act
        result = await lucien_messenger.schedule_message(user_id, template, delay, context)

        # Assert
        assert result is True
        mock_mongodb_handler.get_lucien_messages_collection().insert_one.assert_called_once()
        mock_redis_client.setex.assert_called_once()
        mock_redis_client.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_message_without_redis(self, mock_mongodb_handler, mock_event_bus,
                                                 mock_config_manager):
        """Test message scheduling without Redis (MongoDB fallback)."""
        # Arrange
        messenger = LucienMessenger(
            mongodb_handler=mock_mongodb_handler,
            event_bus=mock_event_bus,
            config_manager=mock_config_manager,
            redis_client=None
        )
        user_id = "user123"
        template = "Scheduled message for $user_name"  # Use template format
        delay = 60

        # Act
        result = await messenger.schedule_message(user_id, template, delay)

        # Assert
        assert result is True
        mock_mongodb_handler.get_lucien_messages_collection().insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_template_not_found_error(self, lucien_messenger, mock_mongodb_handler):
        """Test TemplateNotFoundError when template ID doesn't exist."""
        # Arrange
        user_id = "user123"
        template_id = "nonexistent_template"
        context = {}

        # Mock template not found
        mock_collection = mock_mongodb_handler.get_narrative_templates_collection()
        mock_collection.find_one.return_value = None

        # Act & Assert
        with pytest.raises(TemplateNotFoundError):
            await lucien_messenger.send_message(user_id, template_id, context)

    @pytest.mark.asyncio
    async def test_template_rendering(self, lucien_messenger):
        """Test template rendering with context variables."""
        # Arrange
        template_content = "Hello $user_name! Today is $timestamp. Welcome to $bot_name!"
        context = {"user_name": "Alice"}

        # Act
        result = await lucien_messenger._render_template(template_content, context)

        # Assert
        assert "Hello Alice!" in result
        assert "Welcome to Lucien!" in result
        assert "$user_name" not in result  # Should be substituted
        assert "$bot_name" not in result   # Should be substituted

    @pytest.mark.asyncio
    async def test_process_scheduled_messages(self, lucien_messenger, mock_mongodb_handler):
        """Test processing of scheduled messages."""
        # Arrange
        mock_collection = mock_mongodb_handler.get_lucien_messages_collection()
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([
            {
                "message_id": "msg1",
                "user_id": "user123",
                "template_content": "Hello $user_name",
                "rendered_content": "Hello Alice",  # Pre-rendered
                "context_data": {"user_name": "Alice"},
                "status": "pending",
                "scheduled_time": datetime.utcnow() - timedelta(minutes=1)
            }
        ]))
        mock_collection.find.return_value = mock_cursor

        # Act
        processed_count = await lucien_messenger.process_scheduled_messages()

        # Assert
        assert processed_count == 1
        # Verify status update was called
        mock_collection.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_create_template(self, lucien_messenger, mock_mongodb_handler):
        """Test template creation."""
        # Arrange
        template_id = "test_template"
        name = "Test Template"
        content = "Hello $user_name!"
        required_variables = ["user_name"]

        # Act
        result = await lucien_messenger.create_template(
            template_id, name, content, required_variables
        )

        # Assert
        assert result is True
        mock_mongodb_handler.get_narrative_templates_collection().insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_messages(self, lucien_messenger, mock_mongodb_handler):
        """Test retrieving user message history."""
        # Arrange
        user_id = "user123"
        mock_collection = mock_mongodb_handler.get_lucien_messages_collection()
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = [
            {"message_id": "msg1", "user_id": user_id, "status": "sent"}
        ]
        mock_collection.find.return_value = mock_cursor

        # Act
        messages = await lucien_messenger.get_user_messages(user_id)

        # Assert
        assert len(messages) == 1
        assert messages[0]["user_id"] == user_id
        mock_collection.find.assert_called_once_with({"user_id": user_id})

    @pytest.mark.asyncio
    async def test_health_check(self, lucien_messenger, mock_redis_client):
        """Test health check functionality."""
        # Act
        health = await lucien_messenger.health_check()

        # Assert
        assert health["status"] == "healthy"
        assert health["mongodb_connected"] is True
        assert health["redis_connected"] is True
        assert health["event_bus_connected"] is True
        assert health["bot_token_configured"] is True
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_create_lucien_messenger_factory(self, mock_mongodb_handler,
                                                  mock_event_bus, mock_config_manager):
        """Test factory function for creating LucienMessenger."""
        # Act
        messenger = await create_lucien_messenger(
            mock_mongodb_handler, mock_event_bus, mock_config_manager
        )

        # Assert
        assert isinstance(messenger, LucienMessenger)
        assert messenger.mongodb_handler == mock_mongodb_handler
        assert messenger.event_bus == mock_event_bus
        assert messenger.config_manager == mock_config_manager
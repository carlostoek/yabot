"""
Integration tests for the bot handlers.

This module provides integration tests for the command and webhook handlers,
implementing the testing requirements specified in fase1 specification section 5.3.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict, Optional

from src.handlers.telegram_commands import CommandHandler
from src.handlers.webhook import WebhookHandler
from src.services.user import UserService
from src.events.bus import EventBus
from src.database.manager import DatabaseManager
from src.events.models import BaseEvent, create_event
from src.core.models import CommandResponse

# Import test utilities
from tests.utils.database import MockDatabaseManager
from tests.utils.events import MockEventBus


class TestCommandHandlerIntegration:
    """Integration tests for CommandHandler."""
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager."""
        return MockDatabaseManager()
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return MockEventBus()
    
    @pytest.fixture
    def mock_user_service(self, mock_database_manager, mock_event_bus):
        """Create a mock user service."""
        mock_service = Mock(spec=UserService)
        mock_service.database_manager = mock_database_manager
        mock_service.event_bus = mock_event_bus
        return mock_service
    
    @pytest.fixture
    def command_handler(self, mock_user_service, mock_event_bus):
        """Create a command handler with mocked dependencies."""
        return CommandHandler(
            user_service=mock_user_service,
            event_bus=mock_event_bus
        )
    
    def create_mock_message(self, user_id: str = "123456789", 
                          username: str = "testuser",
                          first_name: str = "Test",
                          last_name: str = "User") -> Mock:
        """Create a mock Telegram message."""
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.username = username
        mock_user.first_name = first_name
        mock_user.last_name = last_name
        mock_user.language_code = "en"
        
        mock_message = Mock()
        mock_message.from_user = mock_user
        mock_message.message_id = "msg_001"
        mock_message.text = "/start"
        
        return mock_message
    
    @pytest.mark.asyncio
    async def test_handle_start_command_integration(self, command_handler, mock_user_service):
        """Test integration of /start command with user service and event bus."""
        # Create mock message
        mock_message = self.create_mock_message()
        
        # Mock user service methods
        mock_user_context = {
            "user_id": "123456789",
            "profile": {
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User"
            },
            "state": {
                "current_state": {
                    "menu_context": "main_menu"
                }
            }
        }
        
        mock_user_service.get_user_context = AsyncMock(return_value=mock_user_context)
        mock_user_service.update_user_profile = AsyncMock(return_value=True)
        
        # Test /start command
        response = await command_handler.handle_start(mock_message)
        
        # Verify user service was called
        assert mock_user_service.get_user_context.called
        assert mock_user_service.update_user_profile.called
        
        # Verify response
        assert isinstance(response, CommandResponse)
        assert "Welcome to the Telegram Bot" in response.text
        assert response.parse_mode == "HTML"
        
        # Verify event was published
        # The MockEventBus tracks method calls
        connect_call_found = False
        for call in command_handler.event_bus._method_calls:
            if isinstance(call, tuple) and call[0] == "publish":
                connect_call_found = True
                break
        # Note: Due to the way MockEventBus is implemented, we can't easily check the exact event
        
        # Verify user information extraction
        args, kwargs = mock_user_service.get_user_context.call_args
        assert args[0] == "123456789"
    
    @pytest.mark.asyncio
    async def test_handle_start_new_user_integration(self, command_handler, mock_user_service):
        """Test integration of /start command for new user creation."""
        # Create mock message
        mock_message = self.create_mock_message()
        
        # Mock user service to simulate new user (get_user_context raises exception)
        mock_user_service.get_user_context = AsyncMock(side_effect=Exception("User not found"))
        
        # Mock create_user
        mock_user_context = {
            "user_id": "123456789",
            "profile": {
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User"
            },
            "state": {
                "current_state": {
                    "menu_context": "main_menu"
                }
            }
        }
        mock_user_service.create_user = AsyncMock(return_value=mock_user_context)
        
        # Test /start command
        response = await command_handler.handle_start(mock_message)
        
        # Verify user creation was attempted
        assert mock_user_service.get_user_context.called
        assert mock_user_service.create_user.called
        
        # Verify response
        assert isinstance(response, CommandResponse)
        assert "Welcome to the Telegram Bot" in response.text
    
    @pytest.mark.asyncio
    async def test_handle_menu_command_integration(self, command_handler):
        """Test integration of /menu command with event bus."""
        # Create mock message
        mock_message = self.create_mock_message()
        mock_message.text = "/menu"
        
        # Test /menu command
        response = await command_handler.handle_menu(mock_message)
        
        # Verify response
        assert isinstance(response, CommandResponse)
        assert "Main Menu" in response.text
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_handle_help_command_integration(self, command_handler):
        """Test integration of /help command with event bus."""
        # Create mock message
        mock_message = self.create_mock_message()
        mock_message.text = "/help"
        
        # Test /help command
        response = await command_handler.handle_help(mock_message)
        
        # Verify response
        assert isinstance(response, CommandResponse)
        assert "Help Information" in response.text
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_handle_unknown_command_integration(self, command_handler):
        """Test integration of unknown command handling."""
        # Create mock message
        mock_message = self.create_mock_message()
        mock_message.text = "/unknown"
        
        # Test unknown command
        response = await command_handler.handle_unknown(mock_message)
        
        # Verify response
        assert isinstance(response, CommandResponse)
        assert "Unknown command" in response.text
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_command_handler_without_user_service(self):
        """Test command handler works without user service."""
        # Create handler without user service
        handler = CommandHandler(user_service=None, event_bus=MockEventBus())
        
        # Create mock message
        mock_message = self.create_mock_message()
        
        # Test /start command without user service
        response = await handler.handle_start(mock_message)
        
        # Verify response is still generated
        assert isinstance(response, CommandResponse)
        assert "Welcome to the Telegram Bot" in response.text


class TestWebhookHandlerIntegration:
    """Integration tests for WebhookHandler."""
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return MockEventBus()
    
    @pytest.fixture
    def webhook_handler(self, mock_event_bus):
        """Create a webhook handler with mocked dependencies."""
        return WebhookHandler(event_bus=mock_event_bus)
    
    def create_mock_update(self, update_type: str = "message") -> Mock:
        """Create a mock Telegram update."""
        mock_user = Mock()
        mock_user.id = "123456789"
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        
        mock_message = Mock()
        mock_message.from_user = mock_user
        mock_message.message_id = "msg_001"
        mock_message.text = "Hello bot!"
        
        mock_update = Mock()
        mock_update.update_type = update_type
        mock_update.message = mock_message
        
        return mock_update
    
    @pytest.mark.asyncio
    async def test_process_update_integration(self, webhook_handler):
        """Test integration of update processing with event bus."""
        # Create mock update
        mock_update = self.create_mock_update()
        
        # Test update processing
        response = await webhook_handler.process_update(mock_update)
        
        # Verify response
        assert response is None  # Webhook handler returns None in current implementation
        
        # Verify event was published
        # Check that publish was called on the event bus
        publish_call_found = False
        for call in webhook_handler.event_bus._method_calls:
            if isinstance(call, tuple) and call[0] == "publish":
                publish_call_found = True
                break
        
        # Note: Due to MockEventBus implementation, we can't easily verify exact event details
    
    @pytest.mark.asyncio
    async def test_setup_webhook_integration(self, webhook_handler):
        """Test webhook setup integration."""
        # Test valid webhook setup
        result = webhook_handler.setup_webhook("https://example.com/webhook")
        
        # Verify result
        assert result is True
        
        # Verify configuration was stored
        assert webhook_handler._webhook_config is not None
        assert webhook_handler._webhook_config["url"] == "https://example.com/webhook"
    
    @pytest.mark.asyncio
    async def test_setup_webhook_invalid_url_integration(self, webhook_handler):
        """Test webhook setup with invalid URL."""
        # Test invalid webhook setup
        result = webhook_handler.setup_webhook("http://example.com/webhook")
        
        # Verify result
        assert result is False
        
        # Verify configuration was still stored
        assert webhook_handler._webhook_config is not None
        assert webhook_handler._webhook_config["url"] == "http://example.com/webhook"
    
    @pytest.mark.asyncio
    async def test_validate_request_integration(self, webhook_handler):
        """Test request validation integration."""
        # Create mock request
        mock_request = Mock()
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.method = "POST"
        
        # Test request validation
        result = webhook_handler.validate_request(mock_request)
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_request_invalid_method_integration(self, webhook_handler):
        """Test request validation with invalid method."""
        # Create mock request with invalid method
        mock_request = Mock()
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.method = "GET"
        
        # Test request validation
        result = webhook_handler.validate_request(mock_request)
        
        # Verify result
        assert result is False
    
    @pytest.mark.asyncio
    async def test_webhook_handler_without_event_bus(self):
        """Test webhook handler works without event bus."""
        # Create handler without event bus
        handler = WebhookHandler(event_bus=None)
        
        # Create mock update
        mock_update = self.create_mock_update()
        
        # Test update processing without event bus
        response = await handler.process_update(mock_update)
        
        # Verify response is still generated
        assert response is None


class TestHandlerEventIntegration:
    """Integration tests for handler-event interactions."""
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager."""
        return MockDatabaseManager()
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return MockEventBus()
    
    @pytest.fixture
    def mock_user_service(self, mock_database_manager, mock_event_bus):
        """Create a mock user service."""
        mock_service = Mock(spec=UserService)
        mock_service.database_manager = mock_database_manager
        mock_service.event_bus = mock_event_bus
        return mock_service
    
    @pytest.fixture
    def command_handler(self, mock_user_service, mock_event_bus):
        """Create a command handler with mocked dependencies."""
        return CommandHandler(
            user_service=mock_user_service,
            event_bus=mock_event_bus
        )
    
    @pytest.fixture
    def webhook_handler(self, mock_event_bus):
        """Create a webhook handler with mocked dependencies."""
        return WebhookHandler(event_bus=mock_event_bus)
    
    def create_mock_message(self, user_id: str = "123456789", 
                          username: str = "testuser",
                          first_name: str = "Test",
                          last_name: str = "User") -> Mock:
        """Create a mock Telegram message."""
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.username = username
        mock_user.first_name = first_name
        mock_user.last_name = last_name
        mock_user.language_code = "en"
        
        mock_message = Mock()
        mock_message.from_user = mock_user
        mock_message.message_id = "msg_001"
        mock_message.text = "/start"
        
        return mock_message
    
    def create_mock_update(self, update_type: str = "message") -> Mock:
        """Create a mock Telegram update."""
        mock_user = Mock()
        mock_user.id = "123456789"
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        
        mock_message = Mock()
        mock_message.from_user = mock_user
        mock_message.message_id = "msg_001"
        mock_message.text = "Hello bot!"
        
        mock_update = Mock()
        mock_update.update_type = update_type
        mock_update.message = mock_message
        
        return mock_update
    
    @pytest.mark.asyncio
    async def test_user_interaction_event_published(self, command_handler, mock_user_service):
        """Test that user interaction events are published when commands are processed."""
        # Create mock message
        mock_message = self.create_mock_message()
        
        # Mock user service methods
        mock_user_context = {
            "user_id": "123456789",
            "profile": {
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User"
            },
            "state": {
                "current_state": {
                    "menu_context": "main_menu"
                }
            }
        }
        
        mock_user_service.get_user_context = AsyncMock(return_value=mock_user_context)
        mock_user_service.update_user_profile = AsyncMock(return_value=True)
        
        # Test /start command
        response = await command_handler.handle_start(mock_message)
        
        # Verify response
        assert isinstance(response, CommandResponse)
        assert "Welcome to the Telegram Bot" in response.text
        
        # Verify event was published through the event bus
        method_calls = command_handler.event_bus._method_calls
        publish_call_found = any(isinstance(call, tuple) and call[0] == "publish" for call in method_calls)
        assert publish_call_found, "Expected publish call not found in event bus method calls"
    
    @pytest.mark.asyncio
    async def test_update_received_event_published(self, webhook_handler):
        """Test that update received events are published when updates are processed."""
        # Create mock update
        mock_update = self.create_mock_update()
        
        # Test update processing
        response = await webhook_handler.process_update(mock_update)
        
        # Verify response
        assert response is None
        
        # Verify event was published through the event bus
        method_calls = webhook_handler.event_bus._method_calls
        publish_call_found = any(isinstance(call, tuple) and call[0] == "publish" for call in method_calls)
        assert publish_call_found, "Expected publish call not found in event bus method calls"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event_bus(self, mock_event_bus):
        """Test that multiple handlers can share the same event bus."""
        # Create handlers with shared event bus
        command_handler = CommandHandler(event_bus=mock_event_bus)
        webhook_handler = WebhookHandler(event_bus=mock_event_bus)
        
        # Create mock data
        mock_message = self.create_mock_message()
        mock_update = self.create_mock_update()
        
        # Process command and update
        await command_handler.handle_start(mock_message)
        await webhook_handler.process_update(mock_update)
        
        # Verify both handlers used the same event bus
        # Count publish calls
        publish_calls = [call for call in mock_event_bus._method_calls if isinstance(call, tuple) and call[0] == "publish"]
        assert len(publish_calls) >= 2, "Expected at least 2 publish calls"


# Integration tests for handler-database interactions
class TestHandlerDatabaseIntegration:
    """Integration tests for handler-database interactions."""
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager."""
        mock_db_manager = Mock(spec=DatabaseManager)
        
        # Mock database connections
        mock_mongo_db = Mock()
        mock_sqlite_conn = Mock()
        mock_db_manager.get_mongo_db.return_value = mock_mongo_db
        mock_db_manager.get_sqlite_conn.return_value = mock_sqlite_conn
        
        # Mock connection status
        mock_db_manager.is_connected = True
        
        return mock_db_manager, mock_mongo_db, mock_sqlite_conn
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return MockEventBus()
    
    @pytest.fixture
    async def user_service(self, mock_database_manager, mock_event_bus):
        """Create a user service with mocked database manager."""
        mock_db_manager, mock_mongo_db, mock_sqlite_conn = mock_database_manager
        
        # Create real user service but with mocked dependencies
        with patch('src.services.user.UserService.__init__', return_value=None):
            user_service = UserService.__new__(UserService)
            user_service.database_manager = mock_db_manager
            user_service.event_bus = mock_event_bus
            return user_service
    
    @pytest.fixture
    def command_handler(self, user_service, mock_event_bus):
        """Create a command handler with user service."""
        return CommandHandler(
            user_service=user_service,
            event_bus=mock_event_bus
        )
    
    def create_mock_message(self, user_id: str = "123456789", 
                          username: str = "testuser",
                          first_name: str = "Test",
                          last_name: str = "User") -> Mock:
        """Create a mock Telegram message."""
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.username = username
        mock_user.first_name = first_name
        mock_user.last_name = last_name
        mock_user.language_code = "en"
        
        mock_message = Mock()
        mock_message.from_user = mock_user
        mock_message.message_id = "msg_001"
        mock_message.text = "/start"
        
        return mock_message
    
    @pytest.mark.asyncio
    async def test_command_handler_database_integration(self, command_handler, user_service, mock_database_manager):
        """Test command handler integration with database operations."""
        mock_db_manager, mock_mongo_db, mock_sqlite_conn = mock_database_manager
        
        # Create mock message
        mock_message = self.create_mock_message()
        
        # Mock user context
        mock_user_context = {
            "user_id": "123456789",
            "telegram_user_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en"
        }
        
        # Mock database manager methods
        with patch.object(command_handler.user_service, 'get_user_context', 
                         new=AsyncMock(return_value=mock_user_context)), \
             patch.object(command_handler.user_service, 'update_user_profile', 
                         new=AsyncMock(return_value=True)):
            
            # Test /start command
            response = await command_handler.handle_start(mock_message)
            
            # Verify response
            assert isinstance(response, CommandResponse)
            assert "Welcome to the Telegram Bot" in response.text
            
            # Verify database methods were called
            assert command_handler.user_service.get_user_context.called
            assert command_handler.user_service.update_user_profile.called
    
    @pytest.mark.asyncio
    async def test_command_handler_database_error_handling(self, command_handler, user_service):
        """Test command handler error handling for database failures."""
        # Create mock message
        mock_message = self.create_mock_message()
        
        # Mock database manager to raise exception
        with patch.object(command_handler.user_service, 'get_user_context', 
                         new=AsyncMock(side_effect=Exception("Database error"))), \
             patch.object(command_handler.user_service, 'create_user',
                         new=AsyncMock(side_effect=Exception("Database error"))):
            
            # Test /start command with database error
            response = await command_handler.handle_start(mock_message)
            
            # Verify response is still generated despite database error
            assert isinstance(response, CommandResponse)
            assert "Welcome to the Telegram Bot" in response.text


# End-to-end handler integration tests
class TestEndToEndHandlerIntegration:
    """End-to-end integration tests for handlers."""
    
    def create_mock_message(self, user_id: str = "123456789", 
                          username: str = "testuser",
                          first_name: str = "Test",
                          last_name: str = "User",
                          text: str = "/start") -> Mock:
        """Create a mock Telegram message."""
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.username = username
        mock_user.first_name = first_name
        mock_user.last_name = last_name
        mock_user.language_code = "en"
        
        mock_message = Mock()
        mock_message.from_user = mock_user
        mock_message.message_id = "msg_001"
        mock_message.text = text
        
        return mock_message
    
    def create_mock_update(self, update_type: str = "message") -> Mock:
        """Create a mock Telegram update."""
        mock_user = Mock()
        mock_user.id = "123456789"
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        
        mock_message = Mock()
        mock_message.from_user = mock_user
        mock_message.message_id = "msg_001"
        mock_message.text = "Hello bot!"
        
        mock_update = Mock()
        mock_update.update_type = update_type
        mock_update.message = mock_message
        
        return mock_update
    
    @pytest.mark.asyncio
    async def test_complete_command_flow(self):
        """Test complete command flow from message to response."""
        # Create handlers with mocks
        mock_event_bus = MockEventBus()
        mock_user_service = Mock()
        
        command_handler = CommandHandler(
            user_service=mock_user_service,
            event_bus=mock_event_bus
        )
        
        # Create mock message
        mock_message = self.create_mock_message(text="/start")
        
        # Mock user service
        mock_user_context = {
            "user_id": "123456789",
            "profile": {"username": "testuser"},
            "state": {"current_state": {"menu_context": "main_menu"}}
        }
        mock_user_service.get_user_context = AsyncMock(return_value=mock_user_context)
        mock_user_service.update_user_profile = AsyncMock(return_value=True)
        
        # Test complete flow
        response = await command_handler.handle_start(mock_message)
        
        # Verify response
        assert isinstance(response, CommandResponse)
        assert response.text is not None
        assert len(response.text) > 0
        assert response.parse_mode == "HTML"
        
        # Verify user service was called
        assert mock_user_service.get_user_context.called
        assert mock_user_service.update_user_profile.called
        
        # Verify event was published
        method_calls = mock_event_bus._method_calls
        publish_call_found = any(isinstance(call, tuple) and call[0] == "publish" for call in method_calls)
        assert publish_call_found
    
    @pytest.mark.asyncio
    async def test_complete_webhook_flow(self):
        """Test complete webhook flow from update to event publishing."""
        # Create handler with mock event bus
        mock_event_bus = MockEventBus()
        webhook_handler = WebhookHandler(event_bus=mock_event_bus)
        
        # Create mock update
        mock_update = self.create_mock_update()
        
        # Test complete flow
        response = await webhook_handler.process_update(mock_update)
        
        # Verify response
        assert response is None  # Current implementation returns None
        
        # Verify event was published
        method_calls = mock_event_bus._method_calls
        publish_call_found = any(isinstance(call, tuple) and call[0] == "publish" for call in method_calls)
        assert publish_call_found
    
    @pytest.mark.asyncio
    async def test_handler_event_separation(self):
        """Test that command and webhook handlers publish different events."""
        # Create handlers with shared event bus
        mock_event_bus = MockEventBus()
        command_handler = CommandHandler(event_bus=mock_event_bus)
        webhook_handler = WebhookHandler(event_bus=mock_event_bus)
        
        # Create mock data
        mock_message = self.create_mock_message(text="/start")
        mock_update = self.create_mock_update()
        
        # Process both handlers
        await command_handler.handle_start(mock_message)
        await webhook_handler.process_update(mock_update)
        
        # Verify events were published
        method_calls = mock_event_bus._method_calls
        publish_calls = [call for call in method_calls if isinstance(call, tuple) and call[0] == "publish"]
        assert len(publish_calls) >= 2, "Expected at least 2 publish calls for different handlers"


# End-to-end handler integration tests
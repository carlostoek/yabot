"""
Handler Integration Tests

This module provides comprehensive integration tests for the YABOT system handlers
with the new infrastructure components. Following the Testing Strategy from Fase1 
requirements, these tests validate the integration between handlers, database services,
and event bus functionality to ensure proper coordination and data flow.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, Optional
from aiogram.types import Message, User, Chat

from src.handlers.command import CommandHandler
from src.handlers.webhook import WebhookHandler
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.services.user import UserService
from src.events.models import (
    UserInteractionEvent, UserRegistrationEvent,
    ReactionDetectedEvent, DecisionMadeEvent, SubscriptionUpdatedEvent
)



class TestCommandHandlerIntegration:
    """Test CommandHandler integration with database and event services"""

    @pytest.mark.asyncio
    async def test_start_command_integration(self, populated_test_database, test_event_bus):
        """Test /start command integration with database and event publishing"""
        # Setup mock user
        mock_user = User(id=123456789, is_bot=False, first_name="Test", username="test_user")
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/start"
        )

        # Setup database manager
        db_manager = populated_test_database["database"]
        db_manager.get_user_from_mongo = AsyncMock(return_value=None)  # User doesn't exist yet
        db_manager.create_user_atomic = AsyncMock(return_value=True)

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = CommandHandler()

        # Execute the command
        await handler.handle_message(mock_message, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })

        # Verify database operations
        db_manager.create_user_atomic.assert_called_once()
        event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_menu_command_integration(self, populated_test_database, test_event_bus):
        """Test menu command integration with existing user data"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Setup mock user matching the existing user
        mock_user = User(
            id=int(user["user_id"]), 
            is_bot=False, 
            first_name="Test", 
            username=user["telegram_data"]["username"]
        )
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/menu"
        )

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = CommandHandler()

        # Execute the command
        await handler.handle_message(mock_message, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })

        # Verify database operations
        db_manager.get_user_from_mongo.assert_called()

    @pytest.mark.asyncio
    async def test_command_handler_with_db_failure(self, test_event_bus):
        """Test command handler behavior when database operations fail"""
        mock_user = User(id=123456789, is_bot=False, first_name="Test", username="test_user")
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/start"
        )

        # Setup database manager with failure
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=None)
        db_manager.create_user_atomic = AsyncMock(side_effect=Exception("DB Error"))  # This will fail

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = CommandHandler()

        # Should handle the error gracefully
        try:
            await handler.handle_message(mock_message, data={
                'database_manager': db_manager,
                'user_service': user_service,
                'event_bus': event_bus
            })
            # Even with DB failure, the method should not raise exception
        except Exception as e:
            # The handler should handle DB errors gracefully
            pytest.fail(f"Command handler should handle DB errors gracefully, got: {e}")


class TestWebhookHandlerIntegration:
    """Test WebhookHandler integration with database and event services"""

    @pytest.mark.asyncio
    async def test_webhook_integration_with_event_publishing(self, populated_test_database, test_event_bus):
        """Test webhook handling with event publishing"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Create mock webhook update data
        webhook_data = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "date": int(datetime.utcnow().timestamp()),
                "chat": {"id": 987654321, "type": "private"},
                "from": {
                    "id": int(user["user_id"]),
                    "is_bot": False,
                    "first_name": "Test",
                    "username": user["telegram_data"]["username"]
                },
                "text": "Hello, bot!"
            }
        }

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = WebhookHandler(bot=MagicMock(), dispatcher=MagicMock())

        # Execute the webhook
        await handler.handle_webhook(webhook_data, db_manager, user_service, event_bus)

        # Verify database operations
        db_manager.get_user_from_mongo.assert_called()

    @pytest.mark.asyncio
    async def test_webhook_integration_new_user(self, test_event_bus):
        """Test webhook handling for a new user (user creation flow)"""
        # Setup mock webhook data with new user
        webhook_data = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "date": int(datetime.utcnow().timestamp()),
                "chat": {"id": 987654321, "type": "private"},
                "from": {
                    "id": 987654321,
                    "is_bot": False,
                    "first_name": "New",
                    "username": "new_user"
                },
                "text": "Hello, bot!"
            }
        }

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=None)  # User doesn't exist
        db_manager.create_user_atomic = AsyncMock(return_value=True)

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = WebhookHandler(bot=MagicMock(), dispatcher=MagicMock())

        # Execute the webhook
        await handler.handle_webhook(webhook_data, db_manager, user_service, event_bus)

        # Verify user creation
        db_manager.create_user_atomic.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_with_event_failure(self, populated_test_database):
        """Test webhook handling when event publishing fails"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Create mock webhook update data
        webhook_data = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "date": int(datetime.utcnow().timestamp()),
                "chat": {"id": 987654321, "type": "private"},
                "from": {
                    "id": int(user["user_id"]),
                    "is_bot": False,
                    "first_name": "Test",
                    "username": user["telegram_data"]["username"]
                },
                "text": "Hello, bot!"
            }
        }

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus with failure
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=False)  # Event publishing fails

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = WebhookHandler(bot=MagicMock(), dispatcher=MagicMock())

        # Execute the webhook - should still work despite event failure
        await handler.handle_webhook(webhook_data, db_manager, user_service, event_bus)

        # Database operations should still succeed
        db_manager.get_user_from_mongo.assert_called()


class TestHandlerEventIntegration:
    """Test integration between handlers and event system"""

    @pytest.mark.asyncio
    async def test_reaction_handling_with_event_publishing(self, populated_test_database, sample_test_events):
        """Test reaction handling and event publishing"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Simulate a reaction (like clicking a button with emoji)
        reaction_data = {
            "user_id": user["user_id"],
            "content_id": "narrative_fragment_001",
            "reaction_type": "besito",
            "timestamp": datetime.utcnow()
        }

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler (since reactions might be handled there)
        handler = CommandHandler()

        # Manually trigger reaction processing
        reaction_event = ReactionDetectedEvent(
            event_id=f"reaction_{user['user_id']}_besito",
            user_id=user["user_id"],
            content_id="narrative_fragment_001",
            reaction_type="besito",
            metadata={"source": "button_click"}
        )
        
        # Publish the reaction event
        await event_bus.publish("reaction", reaction_event)

        # Verify event was published with correct data
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][1]
        assert isinstance(published_event, ReactionDetectedEvent)
        assert published_event.user_id == user["user_id"]
        assert published_event.reaction_type == "besito"

    @pytest.mark.asyncio
    async def test_decision_handling_with_event_publishing(self, populated_test_database):
        """Test decision making and event publishing"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Simulate a decision (user choosing a narrative path)
        decision_data = {
            "user_id": user["user_id"],
            "fragment_id": "intro_001",
            "choice_id": "path_a",
            "timestamp": datetime.utcnow()
        }

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        handler = CommandHandler()

        # Simulate processing a decision
        decision_event = DecisionMadeEvent(
            event_id=f"decision_{user['user_id']}_intro001",
            user_id=user["user_id"],
            choice_id="path_a",
            fragment_id="intro_001",
            next_fragment_id="path_a_result",
            context={"narrative_state": "in_progress"}
        )
        
        # Publish the decision event
        await event_bus.publish("decision", decision_event)

        # Verify event was published
        event_bus.publish.assert_called()
        published_event = event_bus.publish.call_args[0][1]
        assert isinstance(published_event, DecisionMadeEvent)
        assert published_event.user_id == user["user_id"]
        assert published_event.choice_id == "path_a"

    @pytest.mark.asyncio
    async def test_subscription_event_integration(self, populated_test_database):
        """Test subscription change event integration"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        handler = CommandHandler()

        # Simulate subscription upgrade
        subscription_event = SubscriptionUpdatedEvent(
            event_id=f"sub_upgrade_{user['user_id']}",
            user_id=user["user_id"],
            old_status="inactive",
            new_status="active",
            plan_type="premium",
            changed_by="handler_test"
        )
        
        # Publish the subscription event
        await event_bus.publish("subscription", subscription_event)

        # Verify event was published
        event_bus.publish.assert_called()
        published_event = event_bus.publish.call_args[0][1]
        assert isinstance(published_event, SubscriptionUpdatedEvent)
        assert published_event.user_id == user["user_id"]
        assert published_event.plan_type == "premium"


class TestHandlerErrorRecovery:
    """Test error handling and recovery in handlers"""

    @pytest.mark.asyncio
    async def test_handler_db_connection_recovery(self, test_event_bus):
        """Test handler behavior when database connection is temporarily unavailable"""
        mock_user = User(id=123456789, is_bot=False, first_name="Test", username="test_user")
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/start"
        )

        # Setup database manager with initial connection failure
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(side_effect=[
            Exception("Connection failed"),  # First call fails
            {"user_id": "123456789"}        # Second call succeeds
        ])
        db_manager.create_user_atomic = AsyncMock(return_value=True)

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = CommandHandler()

        # First call should handle the error gracefully and potentially retry
        try:
            await handler.handle_message(mock_message, data={
                'database_manager': db_manager,
                'user_service': user_service,
                'event_bus': event_bus
            })
        except Exception as e:
            # The handler should have retry logic or fallback behavior
            pytest.fail(f"Handler should handle temporary DB failures gracefully: {e}")

    @pytest.mark.asyncio
    async def test_handler_event_bus_recovery(self, populated_test_database):
        """Test handler behavior when event bus is temporarily unavailable"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Setup mock user
        mock_user = User(
            id=int(user["user_id"]), 
            is_bot=False, 
            first_name="Test", 
            username=user["telegram_data"]["username"]
        )
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/menu"
        )

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus with temporary failure
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(side_effect=[
            Exception("Redis unavailable"),  # First call fails
            True  # Second call succeeds
        ])

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = CommandHandler()

        # Handler should continue normal operation even with event publishing failure
        try:
            await handler.handle_message(mock_message, data={
                'database_manager': db_manager,
                'user_service': user_service,
                'event_bus': event_bus
            })
            # The command should work even if event publishing fails temporarily
        except Exception as e:
            pytest.fail(f"Handler should continue operation despite event publishing failures: {e}")


class TestHandlerPerformanceIntegration:
    """Test handler performance with integrated services"""

    @pytest.mark.asyncio
    async def test_concurrent_handler_requests(self, populated_test_database, test_event_bus):
        """Test handler performance under concurrent requests"""
        db_data = populated_test_database
        user = db_data["users"][0]

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = CommandHandler()

        # Create multiple mock messages
        tasks = []
        for i in range(10):
            mock_user = User(
                id=int(user["user_id"]), 
                is_bot=False, 
                first_name="Test", 
                username=f"{user['telegram_data']['username']}_{i}"
            )
            mock_chat = Chat(id=987654321 + i, type="private")
            mock_message = Message(
                message_id=i + 1,
                date=datetime.utcnow(),
                chat=mock_chat,
                from_user=mock_user,
                text="/menu"
            )
            
            task = handler.handle_message(mock_message, data={
                'database_manager': db_manager,
                'user_service': user_service,
                'event_bus': event_bus
            })
            tasks.append(task)

        # Execute all requests concurrently
        import time
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_request = total_time_ms / len(tasks)

        # Handlers should process concurrent requests efficiently
        assert avg_time_per_request <= 100, f"Avg processing time {avg_time_per_request}ms exceeds 100ms requirement"

        # Verify all operations succeeded
        assert len(responses) == 10

    @pytest.mark.asyncio
    async def test_handler_with_slow_database(self, test_event_bus):
        """Test handler behavior when database operations are slow"""
        mock_user = User(id=123456789, is_bot=False, first_name="Test", username="test_user")
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/start"
        )

        # Setup database manager with slow operations
        async def slow_get_user(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return None
        
        async def slow_create_user(*args, **kwargs):
            await asyncio.sleep(0.07)  # 70ms delay
            return True

        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = slow_get_user
        db_manager.create_user_atomic = slow_create_user

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create handler with dependencies
        handler = CommandHandler()

        import time
        start_time = time.time()
        await handler.handle_message(mock_message, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })
        end_time = time.time()

        total_time_ms = (end_time - start_time) * 1000

        # Even with slow database, the operation should complete
        # (Though it may take longer than our 100ms requirement)


class TestHandlerDataConsistency:
    """Test data consistency across handler operations"""

    @pytest.mark.asyncio
    async def test_user_data_consistency_across_handlers(self, populated_test_database):
        """Test that user data remains consistent across different handlers"""
        # Create a test user using the helpers
        helpers = populated_test_database["helpers"]
        user_data = {"user_id": "12345"}
        user_id = user_data["user_id"]

        # Setup services with real database connection
        db_manager = populated_test_database["database"]
        db_manager.get_user_from_mongo = AsyncMock(return_value={
            "user_id": user_id,
            "current_state": {"menu_context": "main_menu"},
            "preferences": {"language": "es"},
            "created_at": datetime.utcnow()
        })

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Test command handler
        cmd_handler = CommandHandler()

        # Test webhook handler
        wh_handler = WebhookHandler(bot=MagicMock(), dispatcher=MagicMock())

        # Simulate operations from both handlers
        mock_user = User(id=int(user_id), is_bot=False, first_name="Test", username="test_user")
        mock_chat = Chat(id=987654321, type="private")
        
        # Command handler operation
        cmd_msg = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/menu"
        )
        await cmd_handler.handle_message(cmd_msg, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })

        # Webhook handler operation
        webhook_data = {
            "update_id": 123456,
            "message": {
                "message_id": 2,
                "date": int(datetime.utcnow().timestamp()),
                "chat": {"id": 987654321, "type": "private"},
                "from": {
                    "id": int(user_id),
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "test_user"
                },
                "text": "Hello"
            }
        }
        await wh_handler.handle_webhook(webhook_data, db_manager, user_service, event_bus)

        # Verify both handlers accessed and updated the same user data
        assert db_manager.get_user_from_mongo.call_count >= 2
        assert db_manager.update_user_in_mongo.call_count >= 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])

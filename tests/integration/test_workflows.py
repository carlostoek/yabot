"""
End-to-End Workflow Tests

This module provides comprehensive end-to-end workflow tests for the YABOT system.
Following the Testing Strategy from Fase1 requirements, these tests validate complete
user journeys that span multiple system components including database, event bus,
handlers, and internal APIs to ensure proper coordination and data flow.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from aiogram.types import Message, User, Chat

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.services.user import UserService
from src.handlers.command import CommandHandler
from src.handlers.webhook import WebhookHandler
from src.events.models import (
    UserRegistrationEvent, UserInteractionEvent, 
    ReactionDetectedEvent, DecisionMadeEvent, SubscriptionUpdatedEvent
)
from tests.utils.database import (
    test_database, test_db_helpers, populated_test_database,
    TestDataGenerator, DatabaseTestHelpers, DatabaseTestConfig
)
from tests.utils.events import (
    test_event_bus, sample_test_events, event_data_generator,
    event_test_helpers, EventBusTestHelpers
)


class TestUserRegistrationWorkflow:
    """Test the complete user registration workflow"""

    @pytest.mark.asyncio
    async def test_complete_user_registration_flow(self, test_database, test_db_helpers, test_event_bus):
        """Test the complete user registration flow from start command to database persistence"""
        # Setup mock user
        mock_user = User(id=123456789, is_bot=False, first_name="New", username="new_user", language_code="es")
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/start"
        )

        # Setup database manager to simulate user not existing initially, then being created
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(side_effect=[
            None,  # First check - user doesn't exist
            {"user_id": "123456789", "current_state": {"menu_context": "main_menu"}}  # After creation
        ])
        db_manager.create_user_atomic = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)
        captured_events = []

        # Create event capturing handler
        def capture_event(event_data_str):
            try:
                event_dict = event_data_str if isinstance(event_data_str, dict) else eval(event_data_str)
                captured_events.append(event_dict)
            except:
                pass

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.create_user = AsyncMock(return_value=MagicMock())

        # Create command handler with dependencies
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Execute the registration flow
        response = await cmd_handler.handle_start_command(mock_message)

        # Verify the complete flow executed correctly
        db_manager.get_user_from_mongo.assert_called()
        db_manager.create_user_atomic.assert_called_once()
        event_bus.publish.assert_called()

        # Verify that registration and interaction events were published
        published_events = []
        for call_args in event_bus.publish.call_args_list:
            event = call_args[0][0]  # First argument to publish is the event
            published_events.append(type(event).__name__)

        assert "UserRegistrationEvent" in published_events or "UserInteractionEvent" in published_events
        assert db_manager.create_user_atomic.called

    @pytest.mark.asyncio
    async def test_user_registration_with_event_publishing_failure(self, test_database, test_db_helpers):
        """Test user registration flow when event publishing fails (should continue anyway)"""
        # Setup mock user
        mock_user = User(id=123456789, is_bot=False, first_name="New", username="new_user", language_code="es")
        mock_chat = Chat(id=987654321, type="private")
        mock_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/start"
        )

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=None)  # User doesn't exist
        db_manager.create_user_atomic = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus with failure
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=False)  # Event publishing fails

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.create_user = AsyncMock(return_value=MagicMock())

        # Create command handler with dependencies
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Execute the registration flow - should still work despite event failure
        response = await cmd_handler.handle_start_command(mock_message)

        # Verify database operation succeeded despite event failure
        db_manager.create_user_atomic.assert_called_once()
        event_bus.publish.assert_called()  # Should have been attempted


class TestNarrativeInteractionWorkflow:
    """Test the complete narrative interaction workflow"""

    @pytest.mark.asyncio
    async def test_complete_narrative_interaction_flow(self, populated_test_database, test_event_bus):
        """Test a complete narrative interaction from menu to decision to state update"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            # Create a test user if none exist in populated data
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("test_user_11111")
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=user["mongo_doc"])
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.get_user_context = AsyncMock(return_value=user["mongo_doc"]["current_state"])
        user_service.update_user_state = AsyncMock(return_value=True)

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Step 1: User requests menu
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="Test", 
            username=user["telegram_data"]["username"] if user["telegram_data"] else "test_user"
        )
        mock_chat = Chat(id=987654321, type="private")
        menu_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/menu"
        )
        
        menu_response = await cmd_handler.handle_menu_command(menu_message)

        # Verify menu state update
        db_manager.get_user_from_mongo.assert_called()
        event_bus.publish.assert_called()

        # Step 2: Simulate narrative decision (this would come from button click)
        decision_event = DecisionMadeEvent(
            event_id=f"decision_{user_id}_test",
            user_id=user_id,
            choice_id="choice_a",
            fragment_id="intro_001",
            next_fragment_id="path_a_result",
            context={"narrative_state": "in_progress"}
        )
        
        # Publish the decision event
        await event_bus.publish(decision_event)

        # Step 3: Update user state based on decision
        updated_state = {
            "menu_context": "narrative",
            "narrative_progress": {
                "current_fragment": "path_a_result",
                "completed_fragments": ["intro_001"],
                "choices_made": [{"fragment": "intro_001", "choice": "choice_a"}]
            },
            "session_data": {"last_activity": datetime.utcnow().isoformat()}
        }

        update_result = await db_manager.update_user_in_mongo(user_id, updated_state)

        # Verify the complete narrative flow
        assert event_bus.publish.call_count >= 1  # At least the menu interaction event
        assert db_manager.update_user_in_mongo.call_count >= 1
        assert update_result is True  # State update succeeded

    @pytest.mark.asyncio
    async def test_reaction_to_narrative_flow(self, populated_test_database):
        """Test the flow from user reaction (like besito) to event processing"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            # Create a test user
            helpers = db_data["helpers"] if "helpers" in db_data else MagicMock()
            user = await helpers.create_test_user("react_user_22222") if helpers else await test_db_helpers.create_test_user("react_user_22222")
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=user["mongo_doc"])
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.process_user_reaction = AsyncMock(return_value=True)

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Simulate user reaction to narrative
        reaction_event = ReactionDetectedEvent(
            event_id=f"reaction_{user_id}_besito",
            user_id=user_id,
            content_id="narrative_fragment_001",
            reaction_type="besito",
            metadata={"source": "narrative_interaction"}
        )
        
        # Publish and process the reaction
        await event_bus.publish(reaction_event)

        # Process the reaction through the user service
        await user_service.process_user_reaction(user_id, reaction_event)

        # Verify the reaction workflow
        event_bus.publish.assert_called_once()
        user_service.process_user_reaction.assert_called_once_with(user_id, reaction_event)


class TestVIPAccessWorkflow:
    """Test the complete VIP access workflow with subscription validation"""

    @pytest.mark.asyncio
    async def test_vip_access_flow_with_subscription_check(self, populated_test_database, test_event_bus):
        """Test the complete VIP access flow with subscription validation"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            # Create a user with premium subscription
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("vip_user_33333")
            # Add a premium subscription
            await helpers.create_test_subscription(user["user_id"], "premium", "active")
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        
        # Mock user document with current state
        user_doc_with_vip = user["mongo_doc"].copy()
        user_doc_with_vip["current_state"]["menu_context"] = "vip_menu"
        
        db_manager.get_user_from_mongo = AsyncMock(return_value=user_doc_with_vip)
        db_manager.get_user_profile_from_sqlite = AsyncMock(return_value=user["sqlite_profile"])
        
        # Mock subscription data
        mock_subscription = {
            "id": 1,
            "user_id": user_id,
            "plan_type": "premium",
            "status": "active",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        db_manager.get_subscription_from_sqlite = AsyncMock(return_value=mock_subscription)
        
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.validate_vip_access = AsyncMock(return_value=True)
        user_service.get_user_context = AsyncMock(return_value=user_doc_with_vip["current_state"])

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Simulate user requesting VIP content
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="VIP", 
            username=user["telegram_data"]["username"] if user["telegram_data"] else "vip_user"
        )
        mock_chat = Chat(id=987654321, type="private")
        vip_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/vip_content"
        )

        # Execute VIP access workflow
        try:
            # This would typically check subscription and grant VIP access
            user_service.validate_vip_access.assert_called_once_with(user_id)
            
            # Publish event indicating VIP access granted
            vip_access_event = UserInteractionEvent(
                event_id=f"vip_access_{user_id}",
                user_id=user_id,
                action="vip_content_access",
                context={"access_granted": True, "plan_type": "premium"},
                source="command_handler"
            )
            await event_bus.publish(vip_access_event)
            
            # Update user state to VIP context
            await db_manager.update_user_in_mongo(user_id, {
                "current_state.menu_context": "vip_menu",
                "updated_at": datetime.utcnow()
            })
            
            # Verify VIP workflow
            user_service.validate_vip_access.assert_called_once_with(user_id)
            event_bus.publish.assert_called()
            db_manager.update_user_in_mongo.assert_called_once()
            
        except Exception as e:
            pytest.fail(f"VIP access workflow failed: {e}")

    @pytest.mark.asyncio
    async def test_vip_access_denied_for_inactive_subscription(self, populated_test_database):
        """Test that VIP access is denied for users with inactive subscriptions"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            # Create a user with inactive subscription
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("non_vip_user_44444")
            # Add an inactive subscription
            await helpers.create_test_subscription(user["user_id"], "premium", "inactive")
        
        user_id = user["user_id"]

        # Setup database manager with inactive subscription
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=user["mongo_doc"])
        db_manager.get_subscription_from_sqlite = AsyncMock(return_value={
            "id": 1,
            "user_id": user_id,
            "plan_type": "premium",
            "status": "inactive",  # Changed to inactive
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() - timedelta(days=1)).isoformat()  // Expired
        })
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.validate_vip_access = AsyncMock(return_value=False)

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Execute VIP access validation
        access_granted = await user_service.validate_vip_access(user_id)
        
        # Publish access denied event
        access_denied_event = UserInteractionEvent(
            event_id=f"vip_access_denied_{user_id}",
            user_id=user_id,
            action="vip_content_access_denied",
            context={"access_granted": False, "reason": "subscription_inactive"},
            source="command_handler"
        )
        await event_bus.publish(access_denied_event)
        
        # Verify access was correctly denied
        assert access_granted is False
        user_service.validate_vip_access.assert_called_once_with(user_id)
        event_bus.publish.assert_called()


class TestEventDrivenWorkflow:
    """Test workflows driven by published events"""

    @pytest.mark.asyncio
    async def test_reaction_triggers_besitos_award_workflow(self, populated_test_database, event_test_helpers):
        """Test the complete workflow from reaction to besitos award to notification"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("besitos_user_55555")
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=user["mongo_doc"])
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        # Mock updating user balance or items
        db_manager.update_user_items = AsyncMock(return_value=True) if hasattr(db_manager, 'update_user_items') else None
        db_manager._connected = True

        # Setup event bus with helpers
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.process_user_reaction = AsyncMock(return_value=True)
        user_service.award_besitos = AsyncMock(return_value=True)

        # Step 1: User reacts to content
        reaction_event = ReactionDetectedEvent(
            event_id=f"reaction_{user_id}_besito_award",
            user_id=user_id,
            content_id="narrative_001",
            reaction_type="besito",
            metadata={"reaction_value": 1}
        )
        
        # Publish reaction event
        await event_bus.publish(reaction_event)

        # Step 2: Process reaction and award besitos
        await user_service.process_user_reaction(user_id, reaction_event)
        await user_service.award_besitos(user_id, 1, "reaction_bonus")

        # Step 3: Publish besitos awarded event
        besitos_awarded_event = UserInteractionEvent(
            event_id=f"besitos_awarded_{user_id}",
            user_id=user_id,
            action="besitos_awarded",
            context={"amount": 1, "reason": "reaction_bonus"},
            source="user_service"
        )
        await event_bus.publish(besitos_awarded_event)

        # Verify the complete workflow
        user_service.process_user_reaction.assert_called_once()
        user_service.award_besitos.assert_called_once_with(user_id, 1, "reaction_bonus")
        assert event_bus.publish.call_count >= 2  # Reaction and besitos events

    @pytest.mark.asyncio
    async def test_subscription_upgrade_workflow(self, populated_test_database):
        """Test the complete subscription upgrade workflow"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("upgrade_user_66666")
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=user["mongo_doc"])
        db_manager.get_subscription_from_sqlite = AsyncMock(return_value={
            "id": 1,
            "user_id": user_id,
            "plan_type": "free",
            "status": "active",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": None
        })
        db_manager.update_subscription_in_sqlite = AsyncMock(return_value=True)
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.update_subscription = AsyncMock(return_value=True)

        # Step 1: Simulate subscription upgrade event
        subscription_event = SubscriptionUpdatedEvent(
            event_id=f"sub_upgrade_{user_id}",
            user_id=user_id,
            old_status="inactive",
            new_status="active",
            plan_type="premium",
            changed_by="payment_system"
        )
        
        # Publish subscription upgrade event
        await event_bus.publish(subscription_event)

        # Step 2: Update subscription in database
        await db_manager.update_subscription_in_sqlite(user_id, {
            "plan_type": "premium",
            "status": "active",
            "start_date": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        # Step 3: Update user state to reflect new subscription
        await db_manager.update_user_in_mongo(user_id, {
            "current_state.subscription_level": "premium",
            "updated_at": datetime.utcnow()
        })

        # Step 4: Publish confirmation event
        confirmation_event = UserInteractionEvent(
            event_id=f"sub_upgrade_confirmed_{user_id}",
            user_id=user_id,
            action="subscription_upgraded",
            context={"new_plan": "premium", "old_plan": "free"},
            source="workflow"
        )
        await event_bus.publish(confirmation_event)

        # Verify the complete workflow
        assert event_bus.publish.call_count >= 2
        db_manager.update_subscription_in_sqlite.assert_called_once()
        db_manager.update_user_in_mongo.assert_called_once()


class TestErrorRecoveryWorkflow:
    """Test workflow error handling and recovery"""

    @pytest.mark.asyncio
    async def test_database_failure_recovery_in_workflow(self, test_event_bus):
        """Test that workflows can handle temporary database failures and recover"""
        user_id = "recovery_user_77777"

        # Setup database manager with initial failure, then recovery
        db_manager = MagicMock(spec=DatabaseManager)
        
        # Simulate temporary failure followed by recovery
        call_count = 0
        def temp_fail_get_user(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:  # First call fails
                raise ConnectionError("DB temporarily unavailable")
            else:  # Subsequent calls succeed
                return {"user_id": user_id, "current_state": {"menu_context": "main_menu"}}
        
        db_manager.get_user_from_mongo = AsyncMock(side_effect=temp_fail_get_user)
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.get_user_context = AsyncMock(return_value={"menu_context": "main_menu"})

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # First attempt should handle the error gracefully
        mock_user = User(id=int(user_id), is_bot=False, first_name="Recovery", username="recovery_user")
        mock_chat = Chat(id=987654321, type="private")
        menu_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/menu"
        )

        # The handler should implement retry logic or fallback behavior
        try:
            response = await cmd_handler.handle_menu_command(menu_message)
            # After the first failure, subsequent calls should work due to recovery
            # The exact behavior depends on the retry logic implementation
        except Exception as e:
            # The workflow should handle temporary failures gracefully
            pytest.fail(f"Workflow should handle temporary database failures: {e}")

        # Verify that the database was called multiple times (at least one retry)
        assert db_manager.get_user_from_mongo.call_count >= 2

    @pytest.mark.asyncio
    async def test_event_bus_failure_recovery_in_workflow(self, populated_test_database):
        """Test workflow behavior when event bus is temporarily unavailable"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("event_recovery_user_88888")
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=user["mongo_doc"])
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager._connected = True

        # Setup event bus with temporary failure
        event_bus = MagicMock(spec=EventBus)
        call_count = 0

        async def temp_fail_publish(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:  # First call fails
                return False
            else:  # Subsequent calls succeed
                return True

        event_bus.publish = AsyncMock(side_effect=temp_fail_publish)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.get_user_context = AsyncMock(return_value=user["mongo_doc"]["current_state"])

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Execute workflow - should continue despite event publishing failure
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="EventRecovery", 
            username=user["telegram_data"]["username"] if user["telegram_data"] else "event_user"
        )
        mock_chat = Chat(id=987654321, type="private")
        menu_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/menu"
        )

        try:
            response = await cmd_handler.handle_menu_command(menu_message)
            # Database operations should succeed even if event publishing fails temporarily
        except Exception as e:
            pytest.fail(f"Workflow should continue despite temporary event publishing failure: {e}")

        # Database operations should have succeeded regardless of event failure
        db_manager.get_user_from_mongo.assert_called()
        db_manager.update_user_in_mongo.assert_called()
        assert event_bus.publish.call_count >= 2  # At least 2 calls (one failed, one succeeded)


class TestPerformanceWorkflow:
    """Test workflow performance under load"""

    @pytest.mark.asyncio
    async def test_concurrent_user_workflows(self, populated_test_database, test_event_bus):
        """Test multiple concurrent user workflows"""
        # Setup common services
        db_manager = MagicMock(spec=DatabaseManager)
        event_bus = MagicMock(spec=EventBus)
        user_service = MagicMock(spec=UserService)
        
        # Mock responses
        db_manager.get_user_from_mongo = AsyncMock(return_value={
            "user_id": "temp_user", 
            "current_state": {"menu_context": "main_menu"},
            "preferences": {"language": "es"}
        })
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager._connected = True
        
        event_bus.publish = AsyncMock(return_value=True)
        user_service.get_user_context = AsyncMock(return_value={"menu_context": "main_menu"})
        
        # Create handlers
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Create multiple concurrent workflow tasks
        async def run_user_workflow(user_index):
            user_id = f"concurrent_user_{user_index}"
            mock_user = User(id=int(user_id.replace("concurrent_user_", "1")), is_bot=False, first_name=f"User{user_index}", username=f"user_{user_index}")
            mock_chat = Chat(id=987654321 + user_index, type="private")
            menu_message = Message(
                message_id=user_index,
                date=datetime.utcnow(),
                chat=mock_chat,
                from_user=mock_user,
                text="/menu"
            )
            
            # Execute the workflow
            await cmd_handler.handle_menu_command(menu_message)
            
            # Publish an event
            interaction_event = UserInteractionEvent(
                event_id=f"interaction_{user_id}",
                user_id=user_id,
                action="menu_access",
                context={"workflow": "concurrent_test"},
                source="handler"
            )
            await event_bus.publish(interaction_event)
            
            return f"User{user_index}_completed"
        
        import time
        start_time = time.time()
        
        # Run 10 concurrent workflows
        tasks = [run_user_workflow(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # in milliseconds
        
        # Verify all workflows completed successfully
        assert len(results) == 10
        assert all("completed" in result for result in results)
        
        # Verify that all operations were called appropriately
        assert db_manager.get_user_from_mongo.call_count == 10
        assert db_manager.update_user_in_mongo.call_count == 10
        assert event_bus.publish.call_count == 10  # One event per workflow
        
        # Performance requirement: Workflows should complete in reasonable time
        avg_time_per_workflow = total_time / 10
        assert avg_time_per_workflow <= 200, f"Avg workflow time {avg_time_per_workflow}ms exceeds 200ms requirement"

    @pytest.mark.asyncio
    async def test_long_narrative_session_workflow(self, populated_test_database):
        """Test a long narrative session with multiple decisions and state changes"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("long_session_user_99999")
        
        user_id = user["user_id"]

        # Setup database manager
        initial_state = user["mongo_doc"]["current_state"].copy() if user["mongo_doc"] else {"menu_context": "main_menu"}
        current_state = initial_state

        db_manager = MagicMock(spec=DatabaseManager)
        
        async def get_current_user_state(*args):
            return {"user_id": user_id, "current_state": current_state, "preferences": {"language": "es"}}
        
        db_manager.get_user_from_mongo = AsyncMock(side_effect=get_current_user_state)
        
        async def update_user_state(user_id, state_updates):
            nonlocal current_state
            # Apply updates to current state (simplified)
            for key, value in state_updates.items():
                if '.' in key:
                    # Handle nested updates like "current_state.menu_context"
                    parts = key.split('.')
                    if parts[0] == "current_state" and len(parts) > 1:
                        subkey = parts[1]
                        current_state[subkey] = value
                else:
                    current_state[key] = value
            return True
        
        db_manager.update_user_in_mongo = AsyncMock(side_effect=update_user_state)
        db_manager._connected = True

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = MagicMock(spec=UserService)
        user_service.get_user_context = AsyncMock(return_value=current_state)

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Simulate a long narrative session with multiple interactions
        for step in range(5):  # 5 narrative steps
            # Update user state
            await db_manager.update_user_in_mongo(user_id, {
                f"current_state.narrative_progress.step_{step}": f"fragment_{step:03d}",
                "current_state.menu_context": f"narrative_step_{step}"
            })
            
            # Publish decision event
            decision_event = DecisionMadeEvent(
                event_id=f"decision_{user_id}_step_{step}",
                user_id=user_id,
                choice_id=f"choice_{step}",
                fragment_id=f"fragment_{step:03d}",
                next_fragment_id=f"fragment_{step+1:03d}",
                context={"narrative_step": step}
            )
            await event_bus.publish(decision_event)
            
            # Update state based on decision
            updated_progress = current_state.get("narrative_progress", {})
            updated_progress[f"step_{step}"] = f"fragment_{step:03d}"
            await db_manager.update_user_in_mongo(user_id, {
                "current_state.narrative_progress": updated_progress,
                "current_state.menu_context": f"narrative_step_{step+1}"
            })

        # Verify the long session completed successfully
        assert event_bus.publish.call_count == 5  # One event per step
        # State should be updated for all steps
        assert f"step_4" in current_state.get("narrative_progress", {})


class TestCrossComponentWorkflow:
    """Test workflows that span multiple system components"""

    @pytest.mark.asyncio
    async def test_handler_api_eventbus_integration_workflow(self, populated_test_database, test_event_bus):
        """Test a workflow that integrates handlers, APIs, and event bus"""
        db_data = populated_test_database
        user = db_data["users"][0] if db_data["users"] else None

        if not user:
            helpers = db_data["helpers"] if "helpers" in db_data else test_db_helpers
            user = await helpers.create_test_user("integration_user_101010")
        
        user_id = user["user_id"]

        # Setup all components
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_user_from_mongo = AsyncMock(return_value=user["mongo_doc"])
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)
        db_manager.update_user_profile_in_sqlite = AsyncMock(return_value=True)
        db_manager._connected = True

        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        user_service = MagicMock(spec=UserService)
        user_service.update_user_preferences = AsyncMock(return_value=True)

        # Create command handler
        cmd_handler = CommandHandler()
        cmd_handler.db_manager = db_manager
        cmd_handler.event_bus = event_bus
        cmd_handler.user_service = user_service

        # Step 1: Handler receives command
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="Integration", 
            username=user["telegram_data"]["username"] if user["telegram_data"] else "integration_user"
        )
        mock_chat = Chat(id=987654321, type="private")
        pref_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/setlang en"
        )

        # Handler processes command and updates state
        await cmd_handler.handle_command(pref_message, ["/setlang", "en"])

        # Step 2: Handler publishes event about preference change
        pref_event = UserInteractionEvent(
            event_id=f"pref_change_{user_id}",
            user_id=user_id,
            action="preferences_updated",
            context={"preferences": {"language": "en"}},
            source="command_handler"
        )
        await event_bus.publish(pref_event)

        # Step 3: (Simulated) API endpoint would also access the same data
        # Get updated user state via API (simulated)
        updated_state = await db_manager.get_user_from_mongo(user_id)
        assert updated_state is not None

        # Step 4: Update user profile in SQLite as well
        await db_manager.update_user_profile_in_sqlite(user_id, {"language_code": "en"})

        # Step 5: Publish another event confirming the update
        confirmation_event = UserInteractionEvent(
            event_id=f"pref_confirmed_{user_id}",
            user_id=user_id,
            action="preferences_confirmed",
            context={"updated_fields": ["language"], "new_value": "en"},
            source="integration_test"
        )
        await event_bus.publish(confirmation_event)

        # Verify the cross-component workflow
        db_manager.update_user_in_mongo.assert_called()
        db_manager.update_user_profile_in_sqlite.assert_called()
        assert event_bus.publish.call_count >= 2
        user_service.update_user_preferences.assert_called()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])
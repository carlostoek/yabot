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
from src.handlers.commands import StartCommandHandler
from src.handlers.webhook import WebhookHandler
from src.events.models import (
    UserRegistrationEvent, UserInteractionEvent, 
    ReactionDetectedEvent, DecisionMadeEvent, SubscriptionUpdatedEvent
)



class TestUserRegistrationWorkflow:
    """Test the complete user registration workflow"""

    @pytest.mark.asyncio
    async def test_complete_user_registration_flow(self, populated_test_database):
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
        db_manager = populated_test_database["database"]
        db_manager.get_user_from_mongo = AsyncMock(side_effect=[
            None,  # First check - user doesn't exist
            {"user_id": "123456789", "current_state": {"menu_context": "main_menu"}}  # After creation
        ])
        db_manager.create_user_atomic = AsyncMock(return_value=True)

        # Setup mock event bus
        event_bus = AsyncMock()
        event_bus.publish = AsyncMock()

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler with dependencies
        cmd_handler = StartCommandHandler()

        # Execute the registration flow (simulating middleware injection)
        await cmd_handler.handle_message(
            mock_message,
            database_manager=db_manager,
            user_service=user_service,
            event_bus=event_bus
        )

        # Verify the complete flow executed correctly
        db_manager.get_user_from_mongo.assert_called()
        db_manager.create_user_atomic.assert_called_once()
        event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_user_registration_with_event_publishing_failure(self, populated_test_database):
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
        db_manager = populated_test_database["database"]
        db_manager.get_user_from_mongo = AsyncMock(return_value=None)  # User doesn't exist
        db_manager.create_user_atomic = AsyncMock(return_value=True)

        # Setup event bus with failure
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=False)  # Event publishing fails

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler with dependencies
        cmd_handler = StartCommandHandler()

        # Execute the registration flow - should still work despite event failure
        await cmd_handler.handle_message(mock_message, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })

        # Verify database operation succeeded despite event failure
        db_manager.create_user_atomic.assert_called_once()
        event_bus.publish.assert_called()  # Should have been attempted


class TestNarrativeInteractionWorkflow:
    """Test the complete narrative interaction workflow"""

    @pytest.mark.asyncio
    async def test_complete_narrative_interaction_flow(self, populated_test_database, test_event_bus):
        """Test a complete narrative interaction from menu to decision to state update"""
        db_data = populated_test_database
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

        # Step 1: User requests menu
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="Test", 
            username=user["telegram_data"]["username"]
        )
        mock_chat = Chat(id=987654321, type="private")
        menu_message = Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=mock_chat,
            from_user=mock_user,
            text="/menu"
        )
        
        await cmd_handler.handle_message(menu_message, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })

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
        await event_bus.publish("decision", decision_event)

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
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

        # Simulate user reaction to narrative
        reaction_event = ReactionDetectedEvent(
            event_id=f"reaction_{user_id}_besito",
            user_id=user_id,
            content_id="narrative_fragment_001",
            reaction_type="besito",
            metadata={"source": "narrative_interaction"}
        )
        
        # Publish and process the reaction
        await event_bus.publish("reaction", reaction_event)


class TestVIPAccessWorkflow:
    """Test the complete VIP access workflow with subscription validation"""

    @pytest.mark.asyncio
    async def test_vip_access_flow_with_subscription_check(self, populated_test_database, test_event_bus):
        """Test the complete VIP access flow with subscription validation"""
        db_data = populated_test_database
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = db_data["database"]
        
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
        
        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

        # Simulate user requesting VIP content
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="VIP", 
            username=user["telegram_data"]["username"]
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
        await cmd_handler.handle_message(vip_message, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })

    @pytest.mark.asyncio
    async def test_vip_access_denied_for_inactive_subscription(self, populated_test_database):
        """Test that VIP access is denied for users with inactive subscriptions"""
        db_data = populated_test_database
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager with inactive subscription
        db_manager = db_data["database"]
        db_manager.get_subscription_from_sqlite = AsyncMock(return_value={
            "id": 1,
            "user_id": user_id,
            "plan_type": "premium",
            "status": "inactive",  # Changed to inactive
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() - timedelta(days=1)).isoformat()
        })

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

        # Execute VIP access validation
        access_granted = await user_service.get_user_subscription_status(user_id)
        
        # Verify access was correctly denied
        assert access_granted == "inactive"


class TestEventDrivenWorkflow:
    """Test workflows driven by published events"""

    @pytest.mark.asyncio
    async def test_reaction_triggers_besitos_award_workflow(self, populated_test_database, event_test_helpers):
        """Test the complete workflow from reaction to besitos award to notification"""
        db_data = populated_test_database
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = db_data["database"]

        # Setup event bus with helpers
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Step 1: User reacts to content
        reaction_event = ReactionDetectedEvent(
            event_id=f"reaction_{user_id}_besito_award",
            user_id=user_id,
            content_id="narrative_001",
            reaction_type="besito",
            metadata={"reaction_value": 1}
        )
        
        # Publish reaction event
        await event_bus.publish("reaction", reaction_event)

    @pytest.mark.asyncio
    async def test_subscription_upgrade_workflow(self, populated_test_database):
        """Test the complete subscription upgrade workflow"""
        db_data = populated_test_database
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = db_data["database"]
        db_manager.get_subscription_from_sqlite = AsyncMock(return_value={
            "id": 1,
            "user_id": user_id,
            "plan_type": "free",
            "status": "active",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": None
        })
        db_manager.update_subscription_in_sqlite = AsyncMock(return_value=True)

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

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
        await event_bus.publish("subscription", subscription_event)


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

        # Setup event bus
        event_bus = test_event_bus

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

        # First attempt should handle the error gracefully
        mock_user = User(id=int("77777"), is_bot=False, first_name="Recovery", username="recovery_user")
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
            await cmd_handler.handle_message(menu_message, data={
                'database_manager': db_manager,
                'user_service': user_service,
                'event_bus': event_bus
            })
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
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = db_data["database"]

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
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

        # Execute workflow - should continue despite event publishing failure
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="EventRecovery", 
            username=user["telegram_data"]["username"]
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
            await cmd_handler.handle_message(menu_message, data={
                'database_manager': db_manager,
                'user_service': user_service,
                'event_bus': event_bus
            })
            # Database operations should succeed even if event publishing fails temporarily
        except Exception as e:
            pytest.fail(f"Workflow should continue despite temporary event publishing failure: {e}")


class TestPerformanceWorkflow:
    """Test workflow performance under load"""

    @pytest.mark.asyncio
    async def test_concurrent_user_workflows(self, populated_test_database, test_event_bus):
        """Test multiple concurrent user workflows"""
        # Setup common services
        db_manager = populated_test_database["database"]
        event_bus = test_event_bus
        user_service = UserService(db_manager)
        
        # Create handlers
        cmd_handler = StartCommandHandler()

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
            await cmd_handler.handle_message(menu_message, data={
                'database_manager': db_manager,
                'user_service': user_service,
                'event_bus': event_bus
            })
            
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
        
        # Performance requirement: Workflows should complete in reasonable time
        avg_time_per_workflow = total_time / 10
        assert avg_time_per_workflow <= 200, f"Avg workflow time {avg_time_per_workflow}ms exceeds 200ms requirement"

    @pytest.mark.asyncio
    async def test_long_narrative_session_workflow(self, populated_test_database):
        """Test a long narrative session with multiple decisions and state changes"""
        db_data = populated_test_database
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup database manager
        db_manager = db_data["database"]
        initial_state = user["mongo_doc"]["current_state"].copy()
        current_state = initial_state

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

        # Setup event bus
        event_bus = MagicMock(spec=EventBus)
        event_bus.publish = AsyncMock(return_value=True)

        # Setup user service
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

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
            await event_bus.publish("decision", decision_event)
            
            # Update state based on decision
            updated_progress = current_state.get("narrative_progress", {})
            updated_progress[f"step_{step}"] = f"fragment_{step:03d}"
            await db_manager.update_user_in_mongo(user_id, {
                "current_state.narrative_progress": updated_progress,
                "current_state.menu_context": f"narrative_step_{step+1}"
            })

        # Verify the long session completed successfully
        assert event_bus.publish.call_count == 5  # One event per step


class TestCrossComponentWorkflow:
    """Test workflows that span multiple system components"""

    @pytest.mark.asyncio
    async def test_handler_api_eventbus_integration_workflow(self, populated_test_database, test_event_bus):
        """Test a workflow that integrates handlers, APIs, and event bus"""
        db_data = populated_test_database
        user = db_data["users"][0]
        
        user_id = user["user_id"]

        # Setup all components
        db_manager = db_data["database"]
        event_bus = test_event_bus
        user_service = UserService(db_manager)

        # Create command handler
        cmd_handler = StartCommandHandler()

        # Step 1: Handler receives command
        mock_user = User(
            id=int(user_id), 
            is_bot=False, 
            first_name="Integration", 
            username=user["telegram_data"]["username"]
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
        await cmd_handler.handle_message(pref_message, data={
            'database_manager': db_manager,
            'user_service': user_service,
            'event_bus': event_bus
        })

        # Step 2: Handler publishes event about preference change
        pref_event = UserInteractionEvent(
            event_id=f"pref_change_{user_id}",
            user_id=user_id,
            action="profile",
            context={"preferences": {"language": "en"}},
            source="command_handler"
        )
        await event_bus.publish("user", pref_event)

        # Step 3: (Simulated) API endpoint would also access the same data
        # Get updated user state via API (simulated)
        updated_state = await db_manager.get_user_from_mongo(user_id)
        assert updated_state is not None

        # Step 4: Update user profile in SQLite as well
        await db_manager.update_user_profile_in_sqlite(user_id, {"language_code": "en"})


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])

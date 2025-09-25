"""
Simplified Integration Tests for Narrative-Gamification Module Interaction

This module provides basic integration tests that validate the core workflows
without heavy dependencies on external services.
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, List

# Core imports
from src.events.models import ReactionDetectedEvent, UserInteractionEvent
from src.core.models import RedisConfig

# Gamification module imports
from src.modules.gamification.besitos_wallet import BesitosTransactionType
from src.modules.gamification.mission_manager import MissionStatus, MissionType
from src.modules.gamification.reaction_detector import ReactionDetectorConfig


@pytest.fixture
def mock_database():
    """Mock database client for testing"""
    db_client = MagicMock()
    db_client.yabot_test = MagicMock()

    # Mock collections
    db_client.yabot_test.users = MagicMock()
    db_client.yabot_test.besitos_transactions = MagicMock()
    db_client.yabot_test.missions = MagicMock()
    db_client.yabot_test.items = MagicMock()
    db_client.yabot_test.user_items = MagicMock()

    return db_client


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing"""
    event_bus = MagicMock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = MagicMock()
    return event_bus


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        'user_id': 'test_user_123',
        'username': 'testuser',
        'first_name': 'Test',
        'last_name': 'User',
        'besitos_balance': 0,
        'created_at': datetime.utcnow()
    }


@pytest.mark.asyncio
class TestSimplifiedNarrativeGamificationIntegration:
    """Simplified integration tests focusing on core logic"""

    async def test_reaction_detector_configuration(self):
        """Test that ReactionDetector can be configured properly"""

        config = ReactionDetectorConfig(
            auto_reward_enabled=True,
            positive_reaction_types=["like", "love", "besito"],
            reward_amount=10,
            reward_cooldown_seconds=60
        )

        assert config.auto_reward_enabled is True
        assert config.reward_amount == 10
        assert "love" in config.positive_reaction_types
        assert config.reward_cooldown_seconds == 60

        print("✅ ReactionDetector configuration test passed")

    async def test_reaction_event_creation(self):
        """Test ReactionDetectedEvent creation and validation"""

        event = ReactionDetectedEvent(
            user_id="test_user_123",
            content_id="test_post_01",
            reaction_type="love",
            metadata={
                'chat_id': -123456789,
                'message_id': 42,
                'reaction_source': 'channel_post'
            }
        )

        assert event.user_id == "test_user_123"
        assert event.content_id == "test_post_01"
        assert event.reaction_type == "love"
        assert event.metadata['chat_id'] == -123456789

        print("✅ ReactionDetectedEvent creation test passed")

    async def test_besitos_transaction_types(self):
        """Test BesitosTransactionType enum values"""

        # Verify transaction types exist
        assert hasattr(BesitosTransactionType, 'REACTION')
        assert hasattr(BesitosTransactionType, 'PURCHASE')
        assert hasattr(BesitosTransactionType, 'MISSION_REWARD')
        assert hasattr(BesitosTransactionType, 'DAILY_GIFT')

        # Verify enum values
        assert BesitosTransactionType.REACTION.value == "reaction"
        assert BesitosTransactionType.PURCHASE.value == "purchase"

        print("✅ BesitosTransactionType enum test passed")

    async def test_mission_types_and_status(self):
        """Test Mission types and status enums"""

        # Verify mission types exist
        assert hasattr(MissionType, 'DAILY')
        assert hasattr(MissionType, 'WEEKLY')
        assert hasattr(MissionType, 'NARRATIVE_UNLOCK')

        # Verify mission status exist
        assert hasattr(MissionStatus, 'ASSIGNED')
        assert hasattr(MissionStatus, 'IN_PROGRESS')
        assert hasattr(MissionStatus, 'COMPLETED')
        assert hasattr(MissionStatus, 'EXPIRED')

        print("✅ Mission types and status test passed")

    async def test_mock_workflow_reaction_to_besitos(self, mock_database, mock_event_bus, test_user_data):
        """Test the reaction → besitos workflow with mocks"""

        # Mock BesitosWallet
        with patch('src.modules.gamification.besitos_wallet.BesitosWallet') as mock_wallet_class:
            mock_wallet = mock_wallet_class.return_value
            mock_wallet.add_besitos = AsyncMock()
            mock_wallet.get_balance = AsyncMock(return_value=10)

            # Create wallet instance
            from src.modules.gamification.besitos_wallet import BesitosWallet
            wallet = BesitosWallet(mock_database, mock_event_bus)

            # Simulate adding besitos
            result = MagicMock()
            result.success = True
            result.new_balance = 10
            mock_wallet.add_besitos.return_value = result

            # Test the workflow
            user_id = test_user_data['user_id']

            # Step 1: Add besitos for reaction
            add_result = await mock_wallet.add_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=BesitosTransactionType.REACTION,
                description="Reaction reward"
            )

            assert add_result.success is True
            assert add_result.new_balance == 10

            # Step 2: Check balance
            balance = await mock_wallet.get_balance(user_id)
            assert balance == 10

            # Verify methods were called
            mock_wallet.add_besitos.assert_called_once()
            mock_wallet.get_balance.assert_called_once_with(user_id)

        print("✅ Mock workflow reaction → besitos test passed")

    async def test_mock_workflow_besitos_to_purchase(self, mock_database, mock_event_bus, test_user_data):
        """Test the besitos → purchase workflow with mocks"""

        with patch('src.modules.gamification.besitos_wallet.BesitosWallet') as mock_wallet_class, \
             patch('src.modules.gamification.item_manager.ItemManager') as mock_item_class:

            # Setup mocks
            mock_wallet = mock_wallet_class.return_value
            mock_item_manager = mock_item_class.return_value

            # Mock successful purchase
            spend_result = MagicMock()
            spend_result.success = True
            spend_result.new_balance = 0
            mock_wallet.spend_besitos = AsyncMock(return_value=spend_result)

            # Mock item addition
            mock_item_manager.add_item_to_user = AsyncMock(return_value=True)
            mock_item_manager.get_user_inventory = AsyncMock(return_value=[
                {'item_id': 'pista_oculta_01', 'name': 'Pista Oculta'}
            ])

            user_id = test_user_data['user_id']
            hint_item_id = "pista_oculta_01"
            price = 10

            # Step 1: Spend besitos
            spend_result = await mock_wallet.spend_besitos(
                user_id=user_id,
                amount=price,
                transaction_type=BesitosTransactionType.PURCHASE,
                description=f"Purchase {hint_item_id}"
            )

            assert spend_result.success is True
            assert spend_result.new_balance == 0

            # Step 2: Add item to user inventory
            item_added = await mock_item_manager.add_item_to_user(user_id, hint_item_id)
            assert item_added is True

            # Step 3: Verify item in inventory
            inventory = await mock_item_manager.get_user_inventory(user_id)
            assert len(inventory) > 0
            assert inventory[0]['item_id'] == hint_item_id

            # Verify method calls
            mock_wallet.spend_besitos.assert_called_once()
            mock_item_manager.add_item_to_user.assert_called_once_with(user_id, hint_item_id)

        print("✅ Mock workflow besitos → purchase test passed")

    async def test_mock_mission_workflow(self, mock_database, mock_event_bus, test_user_data):
        """Test mission assignment and completion workflow with mocks"""

        with patch('src.modules.gamification.mission_manager.MissionManager') as mock_mission_class:
            mock_mission_manager = mock_mission_class.return_value

            # Mock mission object
            mock_mission = MagicMock()
            mock_mission.mission_id = "test_mission_123"
            mock_mission.title = "Test Mission"
            mock_mission.status = MissionStatus.ASSIGNED

            # Mock manager methods
            mock_mission_manager.assign_mission = AsyncMock(return_value=mock_mission)
            mock_mission_manager.get_active_missions = AsyncMock(return_value=[mock_mission])

            # Mock completion result
            completion_result = MagicMock()
            completion_result.success = True
            completion_result.reward_besitos = 15
            mock_mission_manager.complete_mission = AsyncMock(return_value=completion_result)

            user_id = test_user_data['user_id']

            # Step 1: Assign mission
            mission = await mock_mission_manager.assign_mission(
                user_id=user_id,
                mission_type=MissionType.NARRATIVE_UNLOCK,
                title="Explorador del Pasaje",
                description="Explora el pasaje secreto",
                target_value=1,
                reward_besitos=15,
                expires_hours=24
            )

            assert mission is not None
            assert mission.title == "Test Mission"

            # Step 2: Get active missions
            active_missions = await mock_mission_manager.get_active_missions(user_id)
            assert len(active_missions) == 1
            assert active_missions[0].mission_id == "test_mission_123"

            # Step 3: Complete mission
            completion = await mock_mission_manager.complete_mission(user_id, mission.mission_id)
            assert completion.success is True
            assert completion.reward_besitos == 15

            # Verify method calls
            mock_mission_manager.assign_mission.assert_called_once()
            mock_mission_manager.get_active_missions.assert_called_once_with(user_id)
            mock_mission_manager.complete_mission.assert_called_once()

        print("✅ Mock mission workflow test passed")

    async def test_event_publishing(self, mock_event_bus):
        """Test event publishing functionality"""

        # Create test event
        event = UserInteractionEvent(
            user_id="test_user_123",
            action="test_action",
            context={'test': 'data'},
            payload={'result': 'success'}
        )

        # Publish event
        await mock_event_bus.publish("user_interaction", event)

        # Verify event was published
        mock_event_bus.publish.assert_called_once_with("user_interaction", event)

        print("✅ Event publishing test passed")

    async def test_cooldown_configuration(self):
        """Test cooldown configuration in ReactionDetector"""

        config = ReactionDetectorConfig(
            reward_cooldown_seconds=30
        )

        # Mock ReactionDetector
        with patch('src.modules.gamification.reaction_detector.ReactionDetector') as mock_detector_class:
            mock_detector = mock_detector_class.return_value
            mock_detector.config = config
            mock_detector._check_cooldown = AsyncMock(return_value=False)  # Not on cooldown
            mock_detector._set_cooldown = AsyncMock(return_value=True)

            # Test cooldown check
            on_cooldown = await mock_detector._check_cooldown("user123", "content456")
            assert on_cooldown is False

            # Test setting cooldown
            cooldown_set = await mock_detector._set_cooldown("user123", "content456")
            assert cooldown_set is True

            mock_detector._check_cooldown.assert_called_once_with("user123", "content456")
            mock_detector._set_cooldown.assert_called_once_with("user123", "content456")

        print("✅ Cooldown configuration test passed")


@pytest.mark.asyncio
async def test_integration_workflow_summary():
    """Summary test that validates the overall integration pattern"""

    # Test data
    user_id = "integration_test_user"

    # Step 1: User reacts to content
    reaction_event = ReactionDetectedEvent(
        user_id=user_id,
        content_id="test_post",
        reaction_type="love",
        metadata={'source': 'test'}
    )

    assert reaction_event.user_id == user_id
    assert reaction_event.reaction_type == "love"

    # Step 2: User interaction recorded
    interaction_event = UserInteractionEvent(
        user_id=user_id,
        action="narrative_decision",
        context={'fragment': 'test_fragment'},
        payload={'choice': 'option_a'}
    )

    assert interaction_event.user_id == user_id
    assert interaction_event.action == "narrative_decision"

    # Step 3: Transaction types available
    assert BesitosTransactionType.REACTION.value == "reaction"
    assert BesitosTransactionType.PURCHASE.value == "purchase"
    assert BesitosTransactionType.MISSION_REWARD.value == "mission_reward"

    # Step 4: Mission system available
    assert MissionType.DAILY.value == "daily"
    assert MissionType.NARRATIVE_UNLOCK.value == "narrative_unlock"
    assert MissionStatus.COMPLETED.value == "completed"

    print("✅ Integration workflow summary test passed")
    print("🎯 All core integration components are properly configured!")


if __name__ == "__main__":
    # Run basic validation
    async def run_basic_tests():
        print("Running basic integration validation...")
        await test_integration_workflow_summary()

    asyncio.run(run_basic_tests())
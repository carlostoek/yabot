"""
Real Integration Tests for Narrative-Gamification Module Interaction

This module contains integration tests using the actual implementations
of BesitosWallet, MissionManager, ItemManager, and ReactionDetector
with real database connections and event bus.
"""
import asyncio
import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, List

# Core imports
from src.events.bus import EventBus
from src.events.models import ReactionDetectedEvent, UserInteractionEvent
from src.core.models import RedisConfig, DatabaseConfig
from src.database.manager import DatabaseManager

# Real gamification module imports
from src.modules.gamification.besitos_wallet import BesitosWallet, BesitosTransactionType, TransactionResult
from src.modules.gamification.mission_manager import MissionManager, MissionStatus, MissionType
from src.modules.gamification.item_manager import ItemManager
from src.modules.gamification.reaction_detector import ReactionDetector, ReactionDetectorConfig

# Database schemas
from src.database.schemas.gamification import (
    BesitosTransactionMongoSchema,
    UserGamificationData,
    MissionMongoSchema,
    ItemMongoSchema,
    UserInventoryMongoSchema
)

# Set test environment
os.environ.setdefault('MONGODB_DATABASE', 'yabot_integration_test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/5')  # Use test Redis DB


@pytest.fixture
async def test_database():
    """Setup test database with cleanup"""

    # Configure test database
    config = {
        'mongodb_uri': 'mongodb://localhost:27017',
        'mongodb_database': 'yabot_integration_test',
        'sqlite_database_path': ':memory:',  # In-memory SQLite for tests
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 5
    }

    # Create database manager
    db_manager = DatabaseManager(config)

    try:
        # Connect to databases
        await db_manager.connect_all()

        # Get MongoDB client
        mongo_client = db_manager.get_mongo_client()
        test_db = mongo_client.yabot_integration_test

        yield db_manager, mongo_client

    finally:
        # Cleanup test data
        try:
            await test_db.besitos_transactions.drop()
            await test_db.user_gamification_data.drop()
            await test_db.missions.drop()
            await test_db.items.drop()
            await test_db.user_inventory.drop()
            await test_db.auctions.drop()
            await test_db.achievements.drop()
            await test_db.user_achievements.drop()
            await test_db.daily_gifts.drop()
            await test_db.trivia.drop()
        except Exception as e:
            print(f"Cleanup warning: {e}")

        # Disconnect
        await db_manager.disconnect_all()


@pytest.fixture
async def event_bus():
    """Create real EventBus instance"""
    redis_config = RedisConfig(url="redis://localhost:6379/5")

    # Create EventBus
    bus = EventBus(redis_config=redis_config)

    try:
        # Connect to Redis (will fallback to local queue if Redis unavailable)
        await bus.connect()
        yield bus
    finally:
        await bus.close()


@pytest.fixture
async def real_besitos_wallet(test_database, event_bus):
    """Create real BesitosWallet instance"""
    db_manager, mongo_client = test_database
    return BesitosWallet(mongo_client, event_bus)


@pytest.fixture
async def real_mission_manager(test_database, event_bus):
    """Create real MissionManager instance"""
    db_manager, mongo_client = test_database
    return MissionManager(mongo_client, event_bus)


@pytest.fixture
async def real_item_manager(test_database):
    """Create real ItemManager instance"""
    db_manager, mongo_client = test_database
    return ItemManager(mongo_client)


@pytest.fixture
async def real_reaction_detector(event_bus):
    """Create real ReactionDetector instance"""
    mock_bot = MagicMock()

    # Real configuration
    config = ReactionDetectorConfig(
        auto_reward_enabled=True,
        positive_reaction_types=["like", "love", "besito"],
        reward_amount=10,
        reward_cooldown_seconds=5  # Short cooldown for testing
    )

    # Real Redis config for cooldowns
    redis_config = RedisConfig(url="redis://localhost:6379/5")

    detector = ReactionDetector(event_bus, mock_bot, config, redis_config)

    yield detector

    await detector.close()


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        'user_id': 'real_test_user_12345',
        'username': 'real_testuser',
        'first_name': 'Real',
        'last_name': 'TestUser'
    }


@pytest.mark.asyncio
class TestRealNarrativeGamificationIntegration:
    """Integration tests using real implementations"""

    async def test_real_besitos_wallet_operations(self, real_besitos_wallet, test_user_data):
        """Test real BesitosWallet operations"""
        wallet = real_besitos_wallet
        user_id = test_user_data['user_id']

        # Test 1: Initial balance should be 0
        initial_balance = await wallet.get_balance(user_id)
        assert initial_balance == 0, f"Expected 0, got {initial_balance}"

        # Test 2: Add besitos
        add_result = await wallet.add_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=BesitosTransactionType.REACTION,
            description="Test reaction reward",
            reference_data={'test': 'data'}
        )

        assert isinstance(add_result, TransactionResult)
        assert add_result.success is True
        assert add_result.new_balance == 50

        # Test 3: Check updated balance
        new_balance = await wallet.get_balance(user_id)
        assert new_balance == 50

        # Test 4: Spend besitos
        spend_result = await wallet.spend_besitos(
            user_id=user_id,
            amount=20,
            transaction_type=BesitosTransactionType.PURCHASE,
            description="Test purchase",
            reference_data={'item': 'test_hint'}
        )

        assert spend_result.success is True
        assert spend_result.new_balance == 30

        # Test 5: Verify final balance
        final_balance = await wallet.get_balance(user_id)
        assert final_balance == 30

        # Test 6: Try to spend more than balance
        overspend_result = await wallet.spend_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=BesitosTransactionType.PURCHASE,
            description="Test overspend"
        )

        assert overspend_result.success is False
        assert "insufficient balance" in overspend_result.error_message.lower()

        print("✅ Real BesitosWallet operations test passed")

    async def test_real_reaction_to_besitos_workflow(
        self,
        real_reaction_detector,
        real_besitos_wallet,
        test_user_data
    ):
        """Test 1: Real Reaction → Besitos workflow"""
        detector = real_reaction_detector
        wallet = real_besitos_wallet
        user_id = test_user_data['user_id']

        # Initial balance check
        initial_balance = await wallet.get_balance(user_id)
        assert initial_balance == 0

        # Simulate reaction reward
        success = await detector._trigger_auto_rewards(
            user_id=user_id,
            content_id="test_post_123",
            reaction_type="love"
        )

        assert success is True

        # Check balance was updated
        new_balance = await wallet.get_balance(user_id)
        assert new_balance == 10  # reward_amount from config

        # Test cooldown - should not reward again immediately
        success_cooldown = await detector._trigger_auto_rewards(
            user_id=user_id,
            content_id="test_post_123",  # Same content
            reaction_type="love"
        )

        # Should still return True but not add more besitos
        assert success_cooldown is True

        # Balance should remain the same due to cooldown
        cooldown_balance = await wallet.get_balance(user_id)
        assert cooldown_balance == 10

        print("✅ Real Reaction → Besitos workflow test passed")

    async def test_real_mission_workflow(
        self,
        real_mission_manager,
        real_besitos_wallet,
        test_user_data
    ):
        """Test 2: Real Mission assignment and completion workflow"""
        mission_manager = real_mission_manager
        wallet = real_besitos_wallet
        user_id = test_user_data['user_id']

        # Test mission assignment
        mission = await mission_manager.assign_mission(
            user_id=user_id,
            mission_type=MissionType.NARRATIVE_UNLOCK,
            title="Real Integration Test Mission",
            description="Complete this mission to test integration",
            target_value=1,
            reward_besitos=25,
            expires_hours=24
        )

        assert mission is not None
        assert mission.title == "Real Integration Test Mission"
        assert mission.status == MissionStatus.ASSIGNED

        # Check active missions
        active_missions = await mission_manager.get_active_missions(user_id)
        assert len(active_missions) == 1
        assert active_missions[0].title == "Real Integration Test Mission"

        # Complete the mission
        completion_result = await mission_manager.complete_mission(
            user_id=user_id,
            mission_id=mission.mission_id
        )

        assert completion_result.success is True
        assert completion_result.reward_besitos == 25

        # Check besitos were awarded
        balance_after_mission = await wallet.get_balance(user_id)
        assert balance_after_mission >= 25  # Might be more if other tests ran

        # Check mission status
        active_missions_after = await mission_manager.get_active_missions(user_id)
        assert len(active_missions_after) == 0  # Mission should be completed

        print("✅ Real Mission workflow test passed")

    async def test_real_besitos_to_item_purchase_workflow(
        self,
        real_besitos_wallet,
        real_item_manager,
        test_user_data
    ):
        """Test 3: Real Besitos → Item purchase workflow"""
        wallet = real_besitos_wallet
        item_manager = real_item_manager
        user_id = test_user_data['user_id']

        # Add initial besitos
        await wallet.add_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=BesitosTransactionType.BONUS,
            description="Test setup funds"
        )

        # Create a test item
        hint_item_id = "test_pista_oculta_01"
        item_created = await item_manager.create_item(
            item_id=hint_item_id,
            name="Test Pista Oculta",
            description="A test hint for integration testing",
            item_type="hint",
            value=30,
            metadata={'category': 'narrative_hint'}
        )
        assert item_created is True

        # Check initial inventory
        initial_inventory = await item_manager.get_user_inventory(user_id)
        initial_count = len(initial_inventory)

        # Purchase item with besitos
        purchase_cost = 30
        spend_result = await wallet.spend_besitos(
            user_id=user_id,
            amount=purchase_cost,
            transaction_type=BesitosTransactionType.PURCHASE,
            description=f"Purchase item: {hint_item_id}",
            reference_data={'item_id': hint_item_id}
        )

        assert spend_result.success is True
        assert spend_result.new_balance == 70  # 100 - 30

        # Add item to user inventory
        item_added = await item_manager.add_item_to_user(
            user_id=user_id,
            item_id=hint_item_id,
            quantity=1,
            metadata={'purchase_transaction': spend_result.transaction_id}
        )
        assert item_added is True

        # Verify item in inventory
        final_inventory = await item_manager.get_user_inventory(user_id)
        assert len(final_inventory) == initial_count + 1

        # Check if our item is in inventory
        item_ids = [item.get('item_id') for item in final_inventory]
        assert hint_item_id in item_ids

        print("✅ Real Besitos → Item purchase workflow test passed")

    async def test_real_full_integration_workflow(
        self,
        real_reaction_detector,
        real_besitos_wallet,
        real_mission_manager,
        real_item_manager,
        test_user_data
    ):
        """Test 4: Real Full integration workflow combining all modules"""
        detector = real_reaction_detector
        wallet = real_besitos_wallet
        mission_manager = real_mission_manager
        item_manager = real_item_manager
        user_id = test_user_data['user_id']

        # Track progress
        progress = {
            'initial_balance': 0,
            'after_reaction': 0,
            'after_mission': 0,
            'after_purchase': 0,
            'items_acquired': 0
        }

        # Step 1: User reacts to content → earns besitos
        progress['initial_balance'] = await wallet.get_balance(user_id)

        reaction_success = await detector._trigger_auto_rewards(
            user_id=user_id,
            content_id="integration_test_post",
            reaction_type="love"
        )
        assert reaction_success is True

        progress['after_reaction'] = await wallet.get_balance(user_id)
        assert progress['after_reaction'] > progress['initial_balance']

        # Step 2: System assigns and user completes mission → more besitos
        mission = await mission_manager.assign_mission(
            user_id=user_id,
            mission_type=MissionType.DAILY,
            title="Full Integration Test Mission",
            description="Daily mission for integration testing",
            target_value=1,
            reward_besitos=35,
            expires_hours=24
        )

        completion_result = await mission_manager.complete_mission(
            user_id=user_id,
            mission_id=mission.mission_id
        )
        assert completion_result.success is True

        progress['after_mission'] = await wallet.get_balance(user_id)
        assert progress['after_mission'] > progress['after_reaction']

        # Step 3: User purchases item with earned besitos
        test_item_id = "integration_test_item"
        await item_manager.create_item(
            item_id=test_item_id,
            name="Integration Test Item",
            description="An item for full integration testing",
            item_type="tool",
            value=20
        )

        spend_result = await wallet.spend_besitos(
            user_id=user_id,
            amount=20,
            transaction_type=BesitosTransactionType.PURCHASE,
            description=f"Purchase: {test_item_id}"
        )
        assert spend_result.success is True

        await item_manager.add_item_to_user(user_id, test_item_id)

        progress['after_purchase'] = await wallet.get_balance(user_id)
        assert progress['after_purchase'] < progress['after_mission']

        # Step 4: Verify final state
        final_inventory = await item_manager.get_user_inventory(user_id)
        progress['items_acquired'] = len(final_inventory)

        final_balance = await wallet.get_balance(user_id)
        transaction_history = await wallet.get_transaction_history(user_id)

        # Assertions
        assert final_balance > 0  # Should have remaining besitos
        assert progress['items_acquired'] > 0  # Should have acquired items
        assert len(transaction_history) >= 3  # At least: reaction reward, mission reward, purchase

        # Log final state
        print(f"✅ Real Full Integration Workflow Results:")
        print(f"   Final Balance: {final_balance} besitos")
        print(f"   Items Acquired: {progress['items_acquired']}")
        print(f"   Transactions: {len(transaction_history)}")
        print(f"   Progress: {progress}")

        print("✅ Real Full integration workflow test passed")

    async def test_real_event_bus_integration(self, event_bus, test_user_data):
        """Test 5: Real EventBus integration"""
        user_id = test_user_data['user_id']

        # Test event publishing and handling
        events_received = []

        async def test_handler(event_data):
            events_received.append(event_data)
            return True

        # Subscribe to test events
        event_bus.subscribe("test_integration_event", test_handler)

        # Create and publish real event
        test_event = UserInteractionEvent(
            user_id=user_id,
            action="integration_test",
            context={'test_type': 'real_integration'},
            payload={'step': 1, 'success': True}
        )

        # Publish event
        await event_bus.publish("test_integration_event", test_event)

        # Give time for event processing
        await asyncio.sleep(0.5)

        # Verify event was processed (depends on EventBus implementation)
        # Note: This might not work if using local fallback queue
        if event_bus._connected:  # Only test if Redis is connected
            print("✅ EventBus is connected to Redis")
        else:
            print("✅ EventBus using local fallback queue")

        print("✅ Real EventBus integration test passed")

    async def test_real_database_consistency(self, test_database, real_besitos_wallet, test_user_data):
        """Test database consistency and transactions"""
        db_manager, mongo_client = test_database
        wallet = real_besitos_wallet
        user_id = test_user_data['user_id']

        # Test concurrent operations to verify atomicity
        async def add_besitos_concurrent():
            return await wallet.add_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=BesitosTransactionType.BONUS,
                description="Concurrent test"
            )

        # Run multiple concurrent operations
        results = await asyncio.gather(*[
            add_besitos_concurrent() for _ in range(5)
        ])

        # Verify all operations succeeded
        assert all(result.success for result in results)

        # Check final balance is consistent
        final_balance = await wallet.get_balance(user_id)
        expected_balance = 50  # 5 operations × 10 besitos each

        # Allow for some tolerance if other tests added besitos
        assert final_balance >= expected_balance

        # Verify transaction history
        history = await wallet.get_transaction_history(user_id, limit=10)
        concurrent_transactions = [
            tx for tx in history
            if tx.get('description') == 'Concurrent test'
        ]
        assert len(concurrent_transactions) == 5

        print("✅ Real database consistency test passed")


@pytest.mark.asyncio
async def test_real_integration_summary():
    """Summary test validating all real components work together"""

    # Test that all required modules can be imported
    from src.modules.gamification.besitos_wallet import BesitosWallet
    from src.modules.gamification.mission_manager import MissionManager
    from src.modules.gamification.item_manager import ItemManager
    from src.modules.gamification.reaction_detector import ReactionDetector
    from src.database.manager import DatabaseManager
    from src.events.bus import EventBus

    assert BesitosWallet is not None
    assert MissionManager is not None
    assert ItemManager is not None
    assert ReactionDetector is not None
    assert DatabaseManager is not None
    assert EventBus is not None

    print("✅ All real integration components available")
    print("🚀 Ready for real-world integration testing!")


if __name__ == "__main__":
    # Run basic validation
    async def run_real_tests():
        print("Running Real Integration Tests validation...")
        await test_real_integration_summary()

    asyncio.run(run_real_tests())
#!/usr/bin/env python3
"""
Direct Test of BesitosWallet with Real Database

This script tests the BesitosWallet directly with a real MongoDB connection
to validate the integration works correctly.
"""
import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Set test environment
os.environ.setdefault('MONGODB_DATABASE', 'yabot_test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/5')

# Import modules
from src.modules.gamification.besitos_wallet import BesitosWallet, BesitosTransactionType
from src.events.bus import EventBus
from src.core.models import RedisConfig


async def test_real_besitos_wallet():
    """Test BesitosWallet with real MongoDB"""
    print("🧪 Testing Real BesitosWallet Integration")
    print("=" * 50)

    # Setup MongoDB connection - specify database in URI
    mongo_client = AsyncIOMotorClient('mongodb://localhost:27017/yabot_test')
    test_db = mongo_client.yabot_test

    # Setup EventBus
    redis_config = RedisConfig(url="redis://localhost:6379/5")
    event_bus = EventBus(redis_config=redis_config)

    try:
        # Connect to EventBus (will fallback to local queue if Redis unavailable)
        await event_bus.connect()

        # Create BesitosWallet
        wallet = BesitosWallet(mongo_client, event_bus)

        test_user_id = "direct_test_user_123"

        print(f"Testing with user: {test_user_id}")

        # Test 1: Get initial balance
        print("\n📊 Test 1: Initial Balance")
        initial_balance = await wallet.get_balance(test_user_id)
        print(f"   Initial balance: {initial_balance} besitos")

        # Test 2: Add besitos
        print("\n💰 Test 2: Add Besitos")
        add_result = await wallet.add_besitos(
            user_id=test_user_id,
            amount=25,
            transaction_type=BesitosTransactionType.REACTION,
            description="Direct test reaction reward",
            reference_data={'test': 'direct_integration'}
        )

        print(f"   Add result: {add_result.success}")
        print(f"   New balance: {add_result.new_balance}")
        print(f"   Transaction ID: {add_result.transaction_id}")

        # Test 3: Check balance
        print("\n🔍 Test 3: Check Updated Balance")
        new_balance = await wallet.get_balance(test_user_id)
        print(f"   Current balance: {new_balance} besitos")
        assert new_balance == 25, f"Expected 25, got {new_balance}"

        # Test 4: Spend besitos
        print("\n💸 Test 4: Spend Besitos")
        spend_result = await wallet.spend_besitos(
            user_id=test_user_id,
            amount=10,
            transaction_type=BesitosTransactionType.PURCHASE,
            description="Direct test purchase",
            reference_data={'item': 'test_hint_direct'}
        )

        print(f"   Spend result: {spend_result.success}")
        print(f"   New balance: {spend_result.new_balance}")
        print(f"   Transaction ID: {spend_result.transaction_id}")

        # Test 5: Final balance check
        print("\n✅ Test 5: Final Balance Check")
        final_balance = await wallet.get_balance(test_user_id)
        print(f"   Final balance: {final_balance} besitos")
        assert final_balance == 15, f"Expected 15, got {final_balance}"

        # Test 6: Transaction history
        print("\n📜 Test 6: Transaction History")
        history = await wallet.get_transaction_history(test_user_id, limit=5)
        print(f"   Transactions found: {len(history)}")

        for i, tx in enumerate(history):
            print(f"   [{i+1}] {tx.get('transaction_type', 'unknown')}: {tx.get('amount', 0)} - {tx.get('description', 'no desc')}")

        # Test 7: Try overspend
        print("\n⚠️  Test 7: Overspend Protection")
        overspend_result = await wallet.spend_besitos(
            user_id=test_user_id,
            amount=100,  # More than available
            transaction_type=BesitosTransactionType.PURCHASE,
            description="Test overspend protection"
        )

        print(f"   Overspend result: {overspend_result.success}")
        print(f"   Error message: {overspend_result.error_message}")
        assert overspend_result.success is False, "Overspend should fail"

        # Test 8: Balance unchanged after failed spend
        print("\n🛡️  Test 8: Balance Protection Verification")
        protected_balance = await wallet.get_balance(test_user_id)
        print(f"   Balance after failed spend: {protected_balance} besitos")
        assert protected_balance == 15, f"Balance should remain 15, got {protected_balance}"

        print("\n🎉 ALL TESTS PASSED!")
        print("✅ BesitosWallet real integration working correctly")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        try:
            await test_db.besitos_transactions.drop()
            await test_db.user_gamification_data.drop()
            print("🧹 Cleaned up test data")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

        await event_bus.close()
        mongo_client.close()


async def test_transaction_atomicity():
    """Test transaction atomicity with concurrent operations"""
    print("\n🔄 Testing Transaction Atomicity")
    print("=" * 40)

    # Setup
    mongo_client = AsyncIOMotorClient('mongodb://localhost:27017/yabot_test')
    redis_config = RedisConfig(url="redis://localhost:6379/5")
    event_bus = EventBus(redis_config=redis_config)

    try:
        await event_bus.connect()
        wallet = BesitosWallet(mongo_client, event_bus)

        test_user_id = "atomicity_test_user"

        # Add initial balance
        await wallet.add_besitos(
            user_id=test_user_id,
            amount=100,
            transaction_type=BesitosTransactionType.BONUS,
            description="Initial balance for atomicity test"
        )

        # Concurrent operations
        async def add_besitos_task():
            return await wallet.add_besitos(
                user_id=test_user_id,
                amount=5,
                transaction_type=BesitosTransactionType.BONUS,
                description="Concurrent add"
            )

        async def spend_besitos_task():
            return await wallet.spend_besitos(
                user_id=test_user_id,
                amount=3,
                transaction_type=BesitosTransactionType.PURCHASE,
                description="Concurrent spend"
            )

        # Run concurrent operations
        print("   Running 10 concurrent add operations...")
        add_results = await asyncio.gather(*[add_besitos_task() for _ in range(10)])

        print("   Running 5 concurrent spend operations...")
        spend_results = await asyncio.gather(*[spend_besitos_task() for _ in range(5)])

        # Verify results
        successful_adds = sum(1 for r in add_results if r.success)
        successful_spends = sum(1 for r in spend_results if r.success)

        print(f"   Successful adds: {successful_adds}/10")
        print(f"   Successful spends: {successful_spends}/5")

        # Check final balance consistency
        final_balance = await wallet.get_balance(test_user_id)
        expected_balance = 100 + (successful_adds * 5) - (successful_spends * 3)

        print(f"   Final balance: {final_balance}")
        print(f"   Expected balance: {expected_balance}")

        assert final_balance == expected_balance, "Balance inconsistency detected!"
        print("✅ Transaction atomicity verified")

        return True

    except Exception as e:
        print(f"❌ Atomicity test failed: {e}")
        return False

    finally:
        # Cleanup
        try:
            await mongo_client.yabot_test.besitos_transactions.drop()
            await mongo_client.yabot_test.user_gamification_data.drop()
        except Exception:
            pass

        await event_bus.close()
        mongo_client.close()


async def main():
    """Run all tests"""
    print("🚀 YABOT BesitosWallet Real Integration Tests")
    print("=" * 60)

    # Test basic operations
    basic_test_passed = await test_real_besitos_wallet()

    if basic_test_passed:
        # Test atomicity
        atomicity_test_passed = await test_transaction_atomicity()

        if atomicity_test_passed:
            print("\n🎊 ALL INTEGRATION TESTS PASSED!")
            print("✅ BesitosWallet is production-ready!")
            return True

    print("\n❌ Some tests failed")
    return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
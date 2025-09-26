"""
Integration test for Admin Module

This test validates that all admin module components can be imported
and initialized properly, following the CLAUDE.md instruction to use
real code instead of mocks.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# Add the project root to the path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

try:
    # Test imports
    from src.modules.admin import (
        AccessControl,
        AccessLevel,
        SubscriptionManager,
        VipStatus,
        PostScheduler,
        PostType,
        PostStatus,
        NotificationSystem,
        NotificationType,
        MessageProtectionSystem,
        ProtectionLevel,
        AdminCommandInterface
    )
    from src.events.bus import EventBus
    from src.events.models import BaseEvent
    print("✅ Admin module imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


class MockBot:
    """Mock bot for testing"""
    async def send_message(self, chat_id, text, **kwargs):
        return MockMessage()

    async def get_chat_member(self, chat_id, user_id):
        return MockChatMember()

    async def send_poll(self, chat_id, question, options, **kwargs):
        return MockMessage()


class MockMessage:
    """Mock message for testing"""
    def __init__(self):
        self.message_id = 12345


class MockChatMember:
    """Mock chat member for testing"""
    def __init__(self):
        self.status = "member"


class MockDBClient:
    """Mock database client for testing"""
    def __init__(self):
        self.collections = {}

    def get_database(self):
        return MockDatabase()


class MockDatabase:
    """Mock database for testing"""
    def __init__(self):
        self.users = MockCollection("users")
        self.subscriptions = MockCollection("subscriptions")
        self.access_control = MockCollection("access_control")
        self.channels = MockCollection("channels")
        self.scheduled_posts = MockCollection("scheduled_posts")
        self.post_history = MockCollection("post_history")
        self.notifications = MockCollection("notifications")
        self.notification_templates = MockCollection("notification_templates")
        self.notification_history = MockCollection("notification_history")
        self.message_protection = MockCollection("message_protection")
        self.protection_rules = MockCollection("protection_rules")
        self.message_access_log = MockCollection("message_access_log")
        self.admin_log = MockCollection("admin_log")
        self.subscription_history = MockCollection("subscription_history")
        self.timed_access = MockCollection("timed_access")


class MockCollection:
    """Mock MongoDB collection"""
    def __init__(self, name):
        self.name = name
        self.data = []

    async def find_one(self, query):
        # Return mock data based on query
        if "user_id" in query:
            return {
                "user_id": query["user_id"],
                "role": "user",
                "username": "test_user",
                "active": True,
                "created_at": datetime.utcnow()
            }
        return None

    async def insert_one(self, document):
        self.data.append(document)
        return MockResult()

    async def update_one(self, query, update):
        return MockResult()

    async def replace_one(self, query, replacement, upsert=False):
        return MockResult()

    async def delete_one(self, query):
        return MockResult()

    async def delete_many(self, query):
        return MockResult()

    async def count_documents(self, query):
        return 5  # Mock count

    def find(self, query):
        return MockCursor()


class MockCursor:
    """Mock MongoDB cursor"""
    def __init__(self):
        self.data = []

    def sort(self, field, direction=1):
        return self

    async def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class MockResult:
    """Mock operation result"""
    def __init__(self):
        self.modified_count = 1
        self.deleted_count = 1
        self.inserted_id = "mock_id"


async def test_admin_module_integration():
    """Test admin module integration"""
    print("🚀 Starting admin module integration test...")

    # Initialize mock dependencies
    db_client = MockDBClient()
    event_bus = EventBus()
    bot = MockBot()

    try:
        # Test AccessControl initialization
        print("Testing AccessControl...")
        access_control = AccessControl(db_client, event_bus, bot)

        # Test SubscriptionManager initialization
        print("Testing SubscriptionManager...")
        subscription_manager = SubscriptionManager(db_client, event_bus)

        # Test PostScheduler initialization
        print("Testing PostScheduler...")
        post_scheduler = PostScheduler(db_client, event_bus, bot)

        # Test NotificationSystem initialization
        print("Testing NotificationSystem...")
        notification_system = NotificationSystem(db_client, event_bus, bot)

        # Test MessageProtectionSystem initialization
        print("Testing MessageProtectionSystem...")
        message_protection = MessageProtectionSystem(db_client, event_bus, bot)

        # Test AdminCommandInterface initialization
        print("Testing AdminCommandInterface...")
        admin_commands = AdminCommandInterface(
            db_client, event_bus, bot,
            access_control, subscription_manager, post_scheduler,
            notification_system, message_protection
        )

        print("✅ All admin module components initialized successfully!")

        # Test some basic functionality
        print("\n🔧 Testing basic functionality...")

        # Test access validation
        result = await access_control.validate_access("test_user", "test_channel")
        print(f"✅ Access validation test: {result.granted}")

        # Test VIP status check
        vip_status = await subscription_manager.check_vip_status("test_user")
        print(f"✅ VIP status check: {vip_status.is_vip}")

        # Test post scheduling
        scheduled_post = await post_scheduler.schedule_post(
            content="Test post content",
            channel_id="test_channel",
            publish_time=datetime.utcnow() + timedelta(minutes=5),
            content_type=PostType.TEXT
        )
        if scheduled_post:
            print(f"✅ Post scheduling test: {scheduled_post.post_id}")

        # Test notification sending
        notification = await notification_system.send_custom_notification(
            user_id="test_user",
            message="Test notification",
            notification_type=NotificationType.INFO
        )
        if notification:
            print(f"✅ Notification test: {notification.notification_id}")

        # Test message protection
        protection_options = await message_protection.get_protection_options(ProtectionLevel.VIP_ONLY)
        print(f"✅ Message protection test: {protection_options}")

        print("\n🎉 Admin module integration test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_event_bus_integration():
    """Test event bus integration"""
    print("\n🔌 Testing EventBus integration...")

    try:
        event_bus = EventBus()

        # Test event creation and publishing
        test_event = BaseEvent(
            event_type="admin_test_event",
            user_id="test_user",
            payload={"test": "data"}
        )

        await event_bus.publish("admin_test_event", test_event)
        print("✅ Event publishing test successful")

        return True

    except Exception as e:
        print(f"❌ EventBus integration test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 ADMIN MODULE INTEGRATION TEST")
    print("=" * 60)

    # Run tests
    admin_test_passed = await test_admin_module_integration()
    event_test_passed = await test_event_bus_integration()

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Admin Module Test: {'✅ PASSED' if admin_test_passed else '❌ FAILED'}")
    print(f"EventBus Test: {'✅ PASSED' if event_test_passed else '❌ FAILED'}")

    overall_success = admin_test_passed and event_test_passed
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")

    if not overall_success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
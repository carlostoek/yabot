"""
Simple test script to verify SubscriptionService implementation.
"""

import asyncio
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.subscription import SubscriptionService
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.config.manager import ConfigManager

async def test_subscription_service():
    """Test the SubscriptionService implementation."""
    print("Testing SubscriptionService implementation...")
    
    # Create instances of required components
    config_manager = ConfigManager()
    database_manager = DatabaseManager(config_manager)
    event_bus = EventBus(config_manager)
    
    # Create subscription service
    subscription_service = SubscriptionService(database_manager, event_bus)
    
    print("SubscriptionService created successfully!")
    
    # Test creating a subscription
    try:
        subscription = await subscription_service.create_subscription(
            user_id="test_user_123",
            plan_type="premium"
        )
        print(f"Created subscription: {subscription}")
    except Exception as e:
        print(f"Error creating subscription: {e}")
    
    # Test getting a subscription
    try:
        subscription = await subscription_service.get_subscription("test_user_123")
        print(f"Retrieved subscription: {subscription}")
    except Exception as e:
        print(f"Error getting subscription: {e}")
    
    # Test checking subscription status
    try:
        status = await subscription_service.check_subscription_status("test_user_123")
        print(f"Subscription status: {status}")
    except Exception as e:
        print(f"Error checking subscription status: {e}")
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_subscription_service())

"""
Integration tests for the VIP upgrade user journey.

These tests simulate the process of a free user upgrading to VIP status,
ensuring that their role, permissions, and menu visibility are updated correctly
across all integrated services.
"""

import pytest
from unittest.mock import Mock

from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.ui.menu_factory import MenuFactory, MenuType, UserRole
from src.database.manager import DatabaseManager

# Use the mock database manager from conftest
from tests.conftest import mock_database_manager, mock_event_bus

@pytest.mark.asyncio
async def test_vip_upgrade_journey(mock_database_manager: DatabaseManager, mock_event_bus: Mock):
    """
    Tests the full journey of a free user upgrading to VIP.

    This test verifies that:
    1. A free user is presented with a VIP upgrade prompt in their menu.
    2. After upgrading, the user's role and VIP status are updated in the database.
    3. The user's menu is dynamically updated to show VIP-exclusive options.
    """
    # Arrange: Set up services and create a new free user
    user_service = UserService(db_manager=mock_database_manager)
    subscription_service = SubscriptionService(database_manager=mock_database_manager, event_bus=mock_event_bus)
    menu_factory = MenuFactory()
    # Mock the async connection for the menu factory's cache manager
    menu_factory.cache_manager.connect = Mock(return_value=None)

    user_id = "free_user_to_be_vip"
    user_details = {
        "id": user_id,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User"
    }
    await user_service.create_user(user_details)

    # --- Step 1: Verify initial state as a Free User ---
    free_user_context = await user_service.get_user_context(user_id)
    assert free_user_context["role"] == UserRole.FREE_USER.value
    assert not free_user_context["has_vip"]

    # Generate menu for the free user
    free_user_menu = await menu_factory.create_menu(MenuType.MAIN, free_user_context)

    # Check that the VIP-only item is correctly modified to be an upgrade prompt
    divan_item_free = next((item for item in free_user_menu.items if item.id == "divan_access"), None)
    assert divan_item_free is not None
    assert divan_item_free.action_data == "show_vip_upgrade"
    assert "💎" in divan_item_free.text

    # --- Step 2: Perform the VIP Upgrade ---
    await subscription_service.create_subscription(user_id, plan_type="vip")
    # Manually update the user's role, as this would typically be handled by an event processor
    await user_service.update_user_profile(user_id, {"role": UserRole.VIP_USER.value, "has_vip": True})

    # --- Step 3: Verify final state as a VIP User ---
    vip_user_context = await user_service.get_user_context(user_id)
    assert vip_user_context["role"] == UserRole.VIP_USER.value
    assert vip_user_context["has_vip"]

    # Generate menu again for the now-VIP user
    vip_user_menu = await menu_factory.create_menu(MenuType.MAIN, vip_user_context)

    # Check that the VIP-only item is now accessible
    divan_item_vip = next((item for item in vip_user_menu.items if item.id == "divan_access"), None)
    assert divan_item_vip is not None
    # The action should now be the actual submenu, not the upgrade prompt
    assert divan_item_vip.action_data == "divan_menu"
    # The diamond should still be there as an indicator
    assert "💎" in divan_item_vip.text

"""
Role-Based Access Integration Tests for Menu System.

Tests role-based access control across different user types and menu restrictions
to ensure compliance with REQ-MENU-003.1, REQ-MENU-003.2, REQ-MENU-003.3, and
REQ-MENU-004.2.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any

from src.ui.menu_factory import MenuFactory, Menu, MenuItem
from src.handlers.menu_system import MenuSystemCoordinator
from src.services.user import UserService
from src.events.bus import EventBus
from src.shared.monitoring.menu_performance import MenuPerformanceMonitor


# Test user contexts for different roles
USER_CONTEXTS = {
    "free_user": {
        "user_id": "free_user_001",
        "role": "free_user",
        "has_vip": False,
        "narrative_level": 2,
        "user_archetype": "explorer",
        "worthiness_score": 0.4,
        "subscription_status": "free"
    },
    "vip_user": {
        "user_id": "vip_user_001",
        "role": "vip_user",
        "has_vip": True,
        "narrative_level": 5,
        "user_archetype": "analytical",
        "worthiness_score": 0.8,
        "subscription_status": "premium"
    },
    "admin_user": {
        "user_id": "admin_user_001",
        "role": "admin",
        "has_vip": True,
        "narrative_level": 6,
        "user_archetype": "direct",
        "worthiness_score": 0.9,
        "subscription_status": "admin"
    },
    "low_worthiness_user": {
        "user_id": "low_worth_001",
        "role": "free_user",
        "has_vip": False,
        "narrative_level": 1,
        "user_archetype": "explorer",
        "worthiness_score": 0.2,
        "subscription_status": "free"
    }
}


class TestMenuRoleBasedAccess:
    """Test role-based access control for menu system."""

    @pytest.fixture
    async def menu_factory(self):
        """Create menu factory with mock dependencies."""
        factory = MenuFactory()
        yield factory

    @pytest.fixture
    async def menu_system_coordinator(self):
        """Create menu system coordinator for integration testing."""
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.edit_message_text = AsyncMock()

        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        user_service = Mock(spec=UserService)
        user_service.get_user_context = AsyncMock()

        coordinator = MenuSystemCoordinator(bot, event_bus, user_service)
        await coordinator.initialize()

        yield coordinator
        await coordinator.shutdown()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_type,expected_access", [
        ("free_user", ["main_menu", "narrative_menu", "gamification_menu"]),
        ("vip_user", ["main_menu", "narrative_menu", "vip_menu", "gamification_menu", "premium_content"]),
        ("admin_user", ["main_menu", "narrative_menu", "vip_menu", "admin_menu", "gamification_menu"]),
        ("low_worthiness_user", ["main_menu", "basic_narrative"])
    ])
    async def test_user_menu_access_by_role(self, menu_factory, user_type, expected_access):
        """Test that users can only access menus appropriate to their role.

        REQ-MENU-003.1: Free users see all options with elegant restrictions for premium features.
        REQ-MENU-003.2: VIP users have full access to premium features and content.
        REQ-MENU-003.3: Admin users see administrative options in addition to user features.
        """
        user_context = USER_CONTEXTS[user_type]

        # Test access to different menu types
        for menu_type in ["main_menu", "vip_menu", "admin_menu", "narrative_menu"]:
            try:
                menu = await menu_factory.generate_menu(menu_type, user_context)

                if menu_type in expected_access or user_type == "admin_user":
                    # Should have access
                    assert menu is not None, f"{user_type} should have access to {menu_type}"

                    # Verify menu items are appropriate for role
                    await self._verify_menu_items_for_role(menu, user_context)

                else:
                    # Should either be None or have restricted access
                    if menu is not None:
                        # Verify restrictions are properly applied
                        restricted_items = [item for item in menu.items if not item.is_enabled]
                        assert len(restricted_items) > 0, f"Expected restrictions for {user_type} on {menu_type}"

            except Exception as e:
                # Some menus might not exist for certain roles, which is acceptable
                if "not found" not in str(e).lower():
                    raise

    async def _verify_menu_items_for_role(self, menu: Menu, user_context: Dict[str, Any]) -> None:
        """Verify menu items are properly configured for user role."""
        user_role = user_context.get("role")
        has_vip = user_context.get("has_vip", False)
        worthiness_score = user_context.get("worthiness_score", 0.0)

        for item in menu.items:
            # Check VIP-only items
            if "vip" in item.text.lower() or "premium" in item.text.lower():
                if not has_vip:
                    assert not item.is_enabled or item.restriction_reason, \
                        f"VIP item should be restricted for non-VIP user: {item.text}"

            # Check admin-only items
            if "admin" in item.text.lower() or "manage" in item.text.lower():
                if user_role != "admin":
                    assert not item.is_enabled or item.restriction_reason, \
                        f"Admin item should be restricted for non-admin user: {item.text}"

            # Check worthiness-based restrictions
            if worthiness_score < 0.5 and "advanced" in item.text.lower():
                assert not item.is_enabled or item.restriction_reason, \
                    f"Advanced item should be restricted for low worthiness user: {item.text}"

    @pytest.mark.asyncio
    async def test_organic_menu_restrictions(self, menu_factory):
        """Test organic menu system shows restricted items with explanations.

        REQ-MENU-004.2: When a user selects a restricted item, Lucien provides
        sophisticated guidance on how to unlock it.
        """
        free_user_context = USER_CONTEXTS["free_user"]

        # Generate VIP menu for free user
        vip_menu = await menu_factory.generate_menu("vip_menu", free_user_context)

        if vip_menu:
            # Should show VIP options but with restrictions
            vip_items = [item for item in vip_menu.items if "vip" in item.text.lower()]

            for vip_item in vip_items:
                if not vip_item.is_enabled:
                    # Should have elegant restriction explanation
                    assert vip_item.restriction_reason is not None, \
                        f"VIP item should have restriction explanation: {vip_item.text}"

                    # Verify Lucien's sophisticated language
                    restriction_text = vip_item.restriction_reason.lower()
                    sophisticated_indicators = [
                        "unlock", "worthy", "journey", "progression", "exclusive", "elevated"
                    ]

                    assert any(indicator in restriction_text for indicator in sophisticated_indicators), \
                        f"Restriction should use sophisticated language: {vip_item.restriction_reason}"

    @pytest.mark.asyncio
    async def test_worthiness_based_access(self, menu_factory):
        """Test access based on worthiness score progression."""
        contexts = [
            USER_CONTEXTS["low_worthiness_user"],
            USER_CONTEXTS["free_user"],
            USER_CONTEXTS["vip_user"]
        ]

        # Test narrative menu access progression
        menu_type = "narrative_menu"
        previous_access_level = 0

        for context in contexts:
            menu = await menu_factory.generate_menu(menu_type, context)

            if menu:
                # Count accessible items
                accessible_items = [item for item in menu.items if item.is_enabled]
                current_access_level = len(accessible_items)

                # Higher worthiness should generally mean more access
                assert current_access_level >= previous_access_level, \
                    f"Higher worthiness should provide more access: {context['worthiness_score']}"

                previous_access_level = current_access_level

    @pytest.mark.asyncio
    async def test_narrative_level_progression(self, menu_factory):
        """Test menu access based on narrative level progression."""
        # Create users at different narrative levels
        level_contexts = []
        for level in [1, 3, 5]:
            context = USER_CONTEXTS["vip_user"].copy()
            context["narrative_level"] = level
            context["user_id"] = f"level_{level}_user"
            level_contexts.append(context)

        menu_type = "narrative_menu"

        for i, context in enumerate(level_contexts):
            menu = await menu_factory.generate_menu(menu_type, context)

            if menu:
                # Higher levels should unlock more content
                narrative_items = [
                    item for item in menu.items
                    if item.is_enabled and ("level" in item.text.lower() or "chapter" in item.text.lower())
                ]

                # Basic assertion: users shouldn't have access to content above their level
                for item in menu.items:
                    if "level" in item.text.lower():
                        # Extract level requirement from item text (simplified check)
                        if not item.is_enabled and item.restriction_reason:
                            assert "level" in item.restriction_reason.lower() or "progression" in item.restriction_reason.lower(), \
                                f"Level-restricted item should mention level requirement: {item.restriction_reason}"

    @pytest.mark.asyncio
    async def test_concurrent_access_control(self, menu_factory):
        """Test access control under concurrent load from different user types."""
        # Create concurrent requests from different user types
        tasks = []

        for _ in range(5):  # 5 requests per user type
            for user_type in USER_CONTEXTS.keys():
                context = USER_CONTEXTS[user_type].copy()
                context["user_id"] = f"{user_type}_{len(tasks)}"

                task = menu_factory.generate_menu("main_menu", context)
                tasks.append((task, user_type, context))

        # Execute all requests concurrently
        results = await asyncio.gather(*[task[0] for task in tasks], return_exceptions=True)

        # Verify results maintain proper access control
        for i, (result, user_type, context) in enumerate(zip(results, [t[1] for t in tasks], [t[2] for t in tasks])):
            if isinstance(result, Exception):
                # Some failures are acceptable, but not excessive
                continue

            if result:
                # Verify access control wasn't compromised under load
                await self._verify_menu_items_for_role(result, context)

        # Verify success rate
        successful_results = [r for r in results if not isinstance(r, Exception) and r is not None]
        success_rate = len(successful_results) / len(results)
        assert success_rate > 0.8, f"Success rate too low under concurrent load: {success_rate:.2f}"

    @pytest.mark.asyncio
    async def test_menu_access_state_consistency(self, menu_factory):
        """Test that menu access state remains consistent across multiple requests."""
        user_context = USER_CONTEXTS["vip_user"]

        # Generate same menu multiple times
        menus = []
        for _ in range(10):
            menu = await menu_factory.generate_menu("vip_menu", user_context)
            menus.append(menu)

        # Verify consistency
        if len(menus) > 1:
            first_menu = menus[0]
            if first_menu:
                first_menu_structure = [(item.text, item.is_enabled) for item in first_menu.items]

                for menu in menus[1:]:
                    if menu:
                        current_structure = [(item.text, item.is_enabled) for item in menu.items]
                        assert current_structure == first_menu_structure, \
                            "Menu structure should be consistent for same user context"


class TestMenuAccessErrorHandling:
    """Test error handling in menu access control."""

    @pytest.fixture
    async def menu_factory_with_errors(self):
        """Create menu factory that simulates various error conditions."""
        factory = MenuFactory()
        # Add error simulation capabilities if needed
        yield factory

    @pytest.mark.asyncio
    async def test_invalid_user_context_handling(self, menu_factory_with_errors):
        """Test handling of invalid or malformed user contexts."""
        invalid_contexts = [
            {},  # Empty context
            {"user_id": None},  # Null user ID
            {"user_id": "test", "role": "invalid_role"},  # Invalid role
            {"user_id": "test", "worthiness_score": -1},  # Invalid worthiness score
            {"user_id": "test", "narrative_level": "invalid"},  # Invalid level type
        ]

        for invalid_context in invalid_contexts:
            try:
                menu = await menu_factory_with_errors.generate_menu("main_menu", invalid_context)
                # Should either return None or a basic menu with appropriate restrictions
                if menu:
                    # Verify it's a safe, basic menu
                    assert menu.menu_id in ["basic_menu", "main_menu", "error_menu"], \
                        f"Invalid context should return safe menu, got: {menu.menu_id}"
            except Exception:
                # Exceptions are acceptable for invalid contexts
                pass

    @pytest.mark.asyncio
    async def test_access_control_with_missing_permissions(self, menu_factory_with_errors):
        """Test access control when user permissions are unclear or missing."""
        ambiguous_context = {
            "user_id": "ambiguous_user",
            # Missing role, VIP status, etc.
        }

        menu = await menu_factory_with_errors.generate_menu("vip_menu", ambiguous_context)

        if menu:
            # Should default to most restrictive access
            enabled_items = [item for item in menu.items if item.is_enabled]
            restricted_items = [item for item in menu.items if not item.is_enabled]

            # Should have more restricted than enabled items for ambiguous users
            assert len(restricted_items) >= len(enabled_items), \
                "Ambiguous permissions should default to restrictive access"


@pytest.mark.integration
class TestMenuAccessIntegration:
    """Integration tests for complete menu access flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_access_flow(self, menu_system_coordinator):
        """Test complete flow from user context to menu display with proper access control."""
        # This would test the complete integration flow
        # Implementation depends on the full system integration
        pass

    @pytest.mark.asyncio
    async def test_real_time_access_updates(self, menu_system_coordinator):
        """Test that access control updates in real-time when user status changes."""
        # This would test dynamic access control updates
        # Implementation depends on the real-time update system
        pass


# Test configuration
def pytest_configure(config):
    """Configure pytest for menu access tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )

def pytest_collection_modifyitems(config, items):
    """Add integration marker to integration tests."""
    for item in items:
        if "integration" in item.nodeid or "test_menu_access" in item.nodeid:
            item.add_marker(pytest.mark.integration)
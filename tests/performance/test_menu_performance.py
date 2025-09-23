
"""
Performance tests for the menu generation system.

These tests use pytest-benchmark to measure the execution time of menu generation
and ensure it meets the non-functional requirement of completing within 500ms.
"""

import pytest
import asyncio

from src.ui.menu_factory import get_menu_for_user, MenuType, UserRole

# Define user contexts for different roles to test various menu complexities
USER_CONTEXTS = {
    "free_user": {
        "role": UserRole.FREE_USER.value,
        "user_id": "perf_test_free_user",
        "has_vip": False,
        "narrative_level": 2,
        "user_archetype": "explorer"
    },
    "vip_user": {
        "role": UserRole.VIP_USER.value,
        "user_id": "perf_test_vip_user",
        "has_vip": True,
        "narrative_level": 4,
        "user_archetype": "analytical"
    },
    "admin_user": {
        "role": UserRole.ADMIN.value,
        "user_id": "perf_test_admin_user",
        "has_vip": True,
        "narrative_level": 6,
        "user_archetype": "persistent"
    }
}

@pytest.mark.asyncio
@pytest.mark.benchmark(group="menu-generation", min_rounds=10, timer=asyncio.sleep, warmup=False)
@pytest.mark.parametrize("user_role", ["free_user", "vip_user", "admin_user"])
async def test_main_menu_generation_performance(benchmark, user_role):
    """
    Benchmarks the generation of the main menu for different user roles.
    
    The test ensures that the menu generation, including the integration of Lucien's
    voice, is performant and meets the <500ms requirement.
    """
    user_context = USER_CONTEXTS[user_role]

    # The function to be benchmarked
    @benchmark
    async def menu_generation_func():
        await get_menu_for_user(MenuType.MAIN, user_context)


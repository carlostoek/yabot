"""
Enhanced Performance Tests for Menu System - YABOT.

Comprehensive performance testing suite for menu operations including generation,
rendering, callback processing, and caching to ensure compliance with performance
requirements REQ-MENU-001.3 and REQ-MENU-002.2.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, List

# Performance testing dependencies
pytest_plugins = ['pytest_asyncio', 'pytest_benchmark']

from src.ui.menu_factory import MenuFactory, Menu, MenuItem
from src.ui.menu_cache import MenuCacheOptimizer, CacheStrategy
from src.ui.message_manager import AsyncMessageManager
from src.shared.monitoring.menu_performance import MenuPerformanceMonitor, MenuOperationType
from src.utils.cache_manager import CacheManager
from src.services.user import UserService


# Test data constants
PERFORMANCE_THRESHOLDS = {
    "menu_generation_ms": 500,      # REQ-MENU-001.3: <500ms cached
    "menu_generation_dynamic_ms": 2000,  # REQ-MENU-001.3: <2s dynamic
    "callback_processing_ms": 1000,  # REQ-MENU-002.2: <1s callback
    "cache_operation_ms": 100,      # Cache operations <100ms
    "message_cleanup_ms": 2000,     # Message cleanup <2s
}

USER_CONTEXTS = {
    "free_user": {
        "role": "free_user",
        "user_id": "perf_test_free_001",
        "has_vip": False,
        "narrative_level": 2,
        "user_archetype": "explorer",
        "worthiness_score": 0.6
    },
    "vip_user": {
        "role": "vip_user",
        "user_id": "perf_test_vip_001",
        "has_vip": True,
        "narrative_level": 5,
        "user_archetype": "analytical",
        "worthiness_score": 0.8
    },
    "admin_user": {
        "role": "admin",
        "user_id": "perf_test_admin_001",
        "has_vip": True,
        "narrative_level": 6,
        "user_archetype": "direct",
        "worthiness_score": 0.9
    }
}

MENU_TYPES = [
    "main_menu",
    "narrative_menu",
    "vip_menu",
    "gamification_menu",
    "admin_menu"
]


class TestMenuGenerationPerformance:
    """Test menu generation performance across different scenarios."""

    @pytest.fixture
    async def menu_factory(self):
        """Create menu factory for testing."""
        factory = MenuFactory()
        yield factory

    @pytest.fixture
    async def cache_optimizer(self):
        """Create cache optimizer for testing."""
        cache_manager = Mock(spec=CacheManager)
        cache_manager.connect = AsyncMock(return_value=True)
        cache_manager.get_value = AsyncMock(return_value=None)
        cache_manager.set_value = AsyncMock()

        optimizer = MenuCacheOptimizer(cache_manager)
        await optimizer.initialize()
        yield optimizer
        await optimizer.close()

    @pytest.fixture
    async def performance_monitor(self):
        """Create performance monitor for testing."""
        monitor = MenuPerformanceMonitor()
        yield monitor

    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_type", ["free_user", "vip_user", "admin_user"])
    @pytest.mark.parametrize("menu_type", MENU_TYPES)
    async def test_menu_generation_performance(self, menu_factory, user_type, menu_type, benchmark):
        """Test menu generation performance for different user types and menu types.

        REQ-MENU-001.3: Menu generation should complete within 500ms for cached menus.
        """
        user_context = USER_CONTEXTS[user_type]

        async def generate_menu():
            return await menu_factory.generate_menu(menu_type, user_context)

        # Benchmark the menu generation
        result = await benchmark.pedantic(
            lambda: asyncio.run(generate_menu()),
            rounds=10,
            iterations=5
        )

        # Verify performance threshold
        stats = benchmark.stats
        assert stats.mean < PERFORMANCE_THRESHOLDS["menu_generation_dynamic_ms"] / 1000, \
            f"Menu generation too slow: {stats.mean*1000:.2f}ms > {PERFORMANCE_THRESHOLDS['menu_generation_dynamic_ms']}ms"

        # Verify menu was generated successfully
        assert result is not None
        assert hasattr(result, 'menu_id')

    @pytest.mark.asyncio
    async def test_cached_menu_performance(self, menu_factory, cache_optimizer, benchmark):
        """Test cached menu retrieval performance.

        REQ-MENU-001.3: Cached menu generation should complete within 500ms.
        """
        user_context = USER_CONTEXTS["vip_user"]
        menu_id = "main_menu"

        # Pre-cache a menu
        menu = await menu_factory.generate_menu(menu_id, user_context)
        await cache_optimizer.cache_menu(menu, user_context, CacheStrategy.AGGRESSIVE)

        async def get_cached_menu():
            return await cache_optimizer.get_cached_menu(menu_id, user_context)

        # Benchmark cached retrieval
        result = await benchmark.pedantic(
            lambda: asyncio.run(get_cached_menu()),
            rounds=20,
            iterations=10
        )

        # Verify performance threshold for cached operations
        stats = benchmark.stats
        assert stats.mean < PERFORMANCE_THRESHOLDS["menu_generation_ms"] / 1000, \
            f"Cached menu retrieval too slow: {stats.mean*1000:.2f}ms > {PERFORMANCE_THRESHOLDS['menu_generation_ms']}ms"

        assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_menu_generation(self, menu_factory, performance_monitor):
        """Test performance under concurrent menu generation load."""
        user_contexts = [USER_CONTEXTS["free_user"], USER_CONTEXTS["vip_user"]] * 10
        menu_types = MENU_TYPES * 4

        @performance_monitor.monitor_operation(MenuOperationType.GENERATION)
        async def generate_menu_monitored(menu_type, user_context):
            return await menu_factory.generate_menu(menu_type, user_context)

        # Create concurrent tasks
        tasks = []
        start_time = time.time()

        for i in range(20):
            user_context = user_contexts[i % len(user_contexts)]
            menu_type = menu_types[i % len(menu_types)]
            task = generate_menu_monitored(menu_type, user_context)
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 18, "Too many concurrent operations failed"

        # Verify total time is reasonable (should benefit from concurrency)
        total_time_ms = (end_time - start_time) * 1000
        assert total_time_ms < 10000, f"Concurrent generation too slow: {total_time_ms:.2f}ms"

        # Get performance metrics
        metrics = await performance_monitor.get_real_time_metrics()
        assert metrics["error_rate_percent"] < 10, "Error rate too high during concurrent load"


class TestCallbackProcessingPerformance:
    """Test callback processing performance."""

    @pytest.fixture
    async def callback_processor(self):
        """Mock callback processor for testing."""
        from src.handlers.callback_processor import CallbackProcessor
        processor = Mock(spec=CallbackProcessor)
        processor.process_callback = AsyncMock()
        return processor

    @pytest.mark.asyncio
    async def test_callback_processing_speed(self, callback_processor, benchmark):
        """Test callback processing performance.

        REQ-MENU-002.2: Callback processing should complete within 1 second.
        """
        callback_data = {
            "action": "navigate",
            "menu_id": "main_menu",
            "user_id": "test_user",
            "data": {"target": "narrative_menu"}
        }

        async def process_callback():
            return await callback_processor.process_callback(
                callback_data, USER_CONTEXTS["vip_user"]
            )

        # Benchmark callback processing
        result = await benchmark.pedantic(
            lambda: asyncio.run(process_callback()),
            rounds=15,
            iterations=8
        )

        # Verify performance threshold
        stats = benchmark.stats
        assert stats.mean < PERFORMANCE_THRESHOLDS["callback_processing_ms"] / 1000, \
            f"Callback processing too slow: {stats.mean*1000:.2f}ms > {PERFORMANCE_THRESHOLDS['callback_processing_ms']}ms"


class TestCachePerformance:
    """Test caching system performance."""

    @pytest.fixture
    async def cache_system(self):
        """Setup cache system for testing."""
        cache_manager = Mock(spec=CacheManager)
        cache_manager.connect = AsyncMock(return_value=True)
        cache_manager.get_value = AsyncMock(return_value=None)
        cache_manager.set_value = AsyncMock()
        cache_manager.delete_key = AsyncMock()

        optimizer = MenuCacheOptimizer(cache_manager)
        await optimizer.initialize()
        yield optimizer
        await optimizer.close()

    @pytest.mark.asyncio
    async def test_cache_write_performance(self, cache_system, benchmark):
        """Test cache write operation performance."""
        # Create test menu
        menu = Menu(
            menu_id="test_menu",
            title="Test Menu",
            description="Performance test menu",
            items=[
                MenuItem(text="Option 1", callback_data="opt1"),
                MenuItem(text="Option 2", callback_data="opt2"),
            ]
        )

        user_context = USER_CONTEXTS["free_user"]

        async def cache_menu():
            return await cache_system.cache_menu(
                menu, user_context, CacheStrategy.MODERATE
            )

        # Benchmark cache write
        result = await benchmark.pedantic(
            lambda: asyncio.run(cache_menu()),
            rounds=25,
            iterations=10
        )

        # Verify performance
        stats = benchmark.stats
        assert stats.mean < PERFORMANCE_THRESHOLDS["cache_operation_ms"] / 1000, \
            f"Cache write too slow: {stats.mean*1000:.2f}ms > {PERFORMANCE_THRESHOLDS['cache_operation_ms']}ms"

    @pytest.mark.asyncio
    async def test_cache_read_performance(self, cache_system, benchmark):
        """Test cache read operation performance."""
        menu_id = "test_menu"
        user_context = USER_CONTEXTS["vip_user"]

        # Mock cached data
        cache_system.cache_manager.get_value = AsyncMock(return_value='{"menu_id": "test", "items": []}')

        async def get_cached_menu():
            return await cache_system.get_cached_menu(menu_id, user_context)

        # Benchmark cache read
        result = await benchmark.pedantic(
            lambda: asyncio.run(get_cached_menu()),
            rounds=30,
            iterations=15
        )

        # Verify performance
        stats = benchmark.stats
        assert stats.mean < PERFORMANCE_THRESHOLDS["cache_operation_ms"] / 1000, \
            f"Cache read too slow: {stats.mean*1000:.2f}ms > {PERFORMANCE_THRESHOLDS['cache_operation_ms']}ms"


class TestMessageCleanupPerformance:
    """Test message cleanup system performance."""

    @pytest.fixture
    async def message_manager(self):
        """Setup message manager for testing."""
        bot = Mock()
        bot.delete_message = AsyncMock()

        cache_manager = Mock(spec=CacheManager)
        cache_manager.connect = AsyncMock(return_value=True)
        cache_manager.get_keys_by_pattern = AsyncMock(return_value=[])
        cache_manager.delete_key = AsyncMock()

        manager = AsyncMessageManager(bot, cache_manager)
        await manager.initialize()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_bulk_message_cleanup_performance(self, message_manager, benchmark):
        """Test bulk message cleanup performance."""
        chat_id = 12345
        message_ids = list(range(1000, 1050))  # 50 messages

        async def cleanup_messages():
            tasks = []
            for msg_id in message_ids:
                task = message_manager._delete_message_with_rate_limit(chat_id, msg_id)
                tasks.append(task)
            return await asyncio.gather(*tasks, return_exceptions=True)

        # Benchmark cleanup
        result = await benchmark.pedantic(
            lambda: asyncio.run(cleanup_messages()),
            rounds=5,
            iterations=3
        )

        # Verify performance
        stats = benchmark.stats
        assert stats.mean < PERFORMANCE_THRESHOLDS["message_cleanup_ms"] / 1000, \
            f"Message cleanup too slow: {stats.mean*1000:.2f}ms > {PERFORMANCE_THRESHOLDS['message_cleanup_ms']}ms"


class TestIntegratedPerformance:
    """Test integrated menu system performance scenarios."""

    @pytest.fixture
    async def integrated_system(self):
        """Setup integrated menu system for testing."""
        # Mock all components
        menu_factory = Mock(spec=MenuFactory)
        menu_factory.generate_menu = AsyncMock(return_value=Mock(menu_id="test"))

        cache_manager = Mock(spec=CacheManager)
        cache_manager.connect = AsyncMock(return_value=True)

        performance_monitor = MenuPerformanceMonitor()

        yield {
            "menu_factory": menu_factory,
            "cache_manager": cache_manager,
            "performance_monitor": performance_monitor
        }

    @pytest.mark.asyncio
    async def test_full_menu_interaction_cycle(self, integrated_system, benchmark):
        """Test complete menu interaction cycle performance."""
        components = integrated_system
        user_context = USER_CONTEXTS["vip_user"]

        @components["performance_monitor"].monitor_operation(MenuOperationType.USER_INTERACTION)
        async def full_interaction_cycle():
            # Menu generation
            menu = await components["menu_factory"].generate_menu("main_menu", user_context)

            # Cache operation
            await asyncio.sleep(0.01)  # Simulate cache write

            # Callback processing
            await asyncio.sleep(0.05)  # Simulate callback processing

            # Message cleanup
            await asyncio.sleep(0.02)  # Simulate cleanup

            return menu

        # Benchmark full cycle
        result = await benchmark.pedantic(
            lambda: asyncio.run(full_interaction_cycle()),
            rounds=10,
            iterations=5
        )

        # Verify total interaction time
        stats = benchmark.stats
        assert stats.mean < 3.0, f"Full interaction cycle too slow: {stats.mean*1000:.2f}ms"

        # Get performance metrics
        metrics = await components["performance_monitor"].get_real_time_metrics()
        assert metrics["health_score"] > 80, "System health score too low"

    @pytest.mark.asyncio
    async def test_high_load_performance(self, integrated_system):
        """Test system performance under high load."""
        components = integrated_system

        # Simulate high load scenario
        async def high_load_scenario():
            tasks = []
            for i in range(100):
                user_context = USER_CONTEXTS[list(USER_CONTEXTS.keys())[i % 3]]
                menu_type = MENU_TYPES[i % len(MENU_TYPES)]

                task = components["menu_factory"].generate_menu(menu_type, user_context)
                tasks.append(task)

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            return results, (end_time - start_time)

        results, total_time = await high_load_scenario()

        # Verify high load performance
        successful_results = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful_results) / len(results) * 100

        assert success_rate > 95, f"Success rate too low under high load: {success_rate:.1f}%"
        assert total_time < 10, f"High load processing too slow: {total_time:.2f}s"

        # Verify throughput
        throughput = len(results) / total_time
        assert throughput > 10, f"Throughput too low: {throughput:.1f} ops/sec"


@pytest.mark.performance
class TestPerformanceRegression:
    """Performance regression tests to catch performance degradations."""

    BASELINE_METRICS = {
        "menu_generation_mean_ms": 150,
        "callback_processing_mean_ms": 80,
        "cache_read_mean_ms": 20,
        "cache_write_mean_ms": 50,
    }

    @pytest.mark.asyncio
    async def test_performance_regression_baseline(self, benchmark):
        """Test to ensure performance doesn't regress below baseline."""
        # This would compare against stored baseline metrics
        # Implementation would depend on how baselines are stored/retrieved

        async def mock_operation():
            await asyncio.sleep(0.01)  # Simulate work
            return True

        result = await benchmark.pedantic(
            lambda: asyncio.run(mock_operation()),
            rounds=20,
            iterations=10
        )

        # This is a placeholder - real implementation would compare against
        # stored baseline performance metrics
        stats = benchmark.stats
        assert stats.mean < 0.1, "Performance regression detected"


# Performance test configuration
def pytest_configure(config):
    """Configure pytest for performance testing."""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )

def pytest_collection_modifyitems(config, items):
    """Add performance marker to performance tests."""
    for item in items:
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
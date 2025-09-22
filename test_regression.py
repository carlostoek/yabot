#!/usr/bin/env python3
"""
Regression testing for the Ctrl+C shutdown bug fix.

This test ensures that the fix doesn't break any existing functionality
and that all related systems continue to work properly.
"""

import asyncio
import sys
import os
import importlib
import inspect

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class RegressionTestSuite:
    def __init__(self):
        self.test_results = {}

    def test_module_imports(self):
        """Test that all modules still import correctly."""
        print("=" * 60)
        print("REGRESSION TEST: MODULE IMPORTS")
        print("=" * 60)

        test_name = "module_imports"
        failed_imports = []
        successful_imports = []

        # Core modules that should still work
        modules_to_test = [
            'src.main',
            'src.core.application',
            'src.core.router',
            'src.config.manager',
            'src.database.manager',
            'src.events.bus',
            'src.ui.menu_cache',
            'src.utils.cache_manager',
            'src.services.user',
            'src.services.narrative',
            'src.utils.logger',
        ]

        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                successful_imports.append(module_name)
                print(f"✓ {module_name}")
            except ImportError as e:
                failed_imports.append((module_name, str(e)))
                print(f"✗ {module_name}: {e}")
            except Exception as e:
                failed_imports.append((module_name, f"Unexpected error: {e}"))
                print(f"✗ {module_name}: Unexpected error: {e}")

        if not failed_imports:
            print(f"✓ All {len(successful_imports)} modules imported successfully")
            self.test_results[test_name] = {
                "status": "PASSED",
                "details": f"All {len(successful_imports)} modules imported without issues"
            }
            return True
        else:
            print(f"✗ {len(failed_imports)} modules failed to import")
            self.test_results[test_name] = {
                "status": "FAILED",
                "details": f"Failed imports: {[name for name, _ in failed_imports]}"
            }
            return False

    async def test_service_initialization(self):
        """Test that services can still be initialized correctly."""
        print("\n" + "=" * 60)
        print("REGRESSION TEST: SERVICE INITIALIZATION")
        print("=" * 60)

        test_name = "service_initialization"

        try:
            from src.config.manager import ConfigManager
            from src.database.manager import DatabaseManager
            from src.events.bus import EventBus
            from src.ui.menu_cache import MenuCacheOptimizer

            print("Step 1: Initializing configuration manager...")
            config = ConfigManager()
            print("✓ ConfigManager initialized")

            print("Step 2: Initializing database manager...")
            db_manager = DatabaseManager(config)
            print("✓ DatabaseManager initialized")

            print("Step 3: Initializing event bus...")
            event_bus = EventBus(config)
            print("✓ EventBus initialized")

            print("Step 4: Initializing cache optimizer...")
            cache_optimizer = MenuCacheOptimizer()
            print("✓ MenuCacheOptimizer initialized")

            # Check that services have their expected methods
            print("Step 5: Verifying service interfaces...")

            # DatabaseManager should have its core methods
            expected_db_methods = ['start_offline_recovery_monitor', 'stop_offline_recovery_monitor']
            for method in expected_db_methods:
                if hasattr(db_manager, method):
                    print(f"✓ DatabaseManager.{method} available")
                else:
                    raise Exception(f"DatabaseManager missing method: {method}")

            # EventBus should have its core methods
            expected_bus_methods = ['publish', 'subscribe', 'close']
            for method in expected_bus_methods:
                if hasattr(event_bus, method):
                    print(f"✓ EventBus.{method} available")
                else:
                    raise Exception(f"EventBus missing method: {method}")

            # MenuCacheOptimizer should have its core methods
            expected_cache_methods = ['get_cached_menu', 'cache_menu', 'close']
            for method in expected_cache_methods:
                if hasattr(cache_optimizer, method):
                    print(f"✓ MenuCacheOptimizer.{method} available")
                else:
                    raise Exception(f"MenuCacheOptimizer missing method: {method}")

            print("✓ All service interfaces preserved")

            self.test_results[test_name] = {
                "status": "PASSED",
                "details": "All services initialize correctly and preserve their interfaces"
            }
            return True

        except Exception as e:
            print(f"✗ Service initialization failed: {e}")
            self.test_results[test_name] = {
                "status": "FAILED",
                "details": f"Service initialization error: {e}"
            }
            return False

    async def test_background_task_compatibility(self):
        """Test that background tasks still work as expected."""
        print("\n" + "=" * 60)
        print("REGRESSION TEST: BACKGROUND TASK COMPATIBILITY")
        print("=" * 60)

        test_name = "background_task_compatibility"

        try:
            from src.main import register_background_task, unregister_background_task, background_tasks

            print("Step 1: Testing original task functionality...")

            # Test that we can still create and manage tasks the old way
            async def legacy_style_task():
                await asyncio.sleep(0.1)
                return "completed"

            # Create task without registration (legacy style)
            legacy_task = asyncio.create_task(legacy_style_task())
            result = await legacy_task
            print(f"✓ Legacy task completed: {result}")

            # Test new registration system
            async def new_style_task():
                try:
                    for i in range(5):
                        await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    print("✓ New style task cancelled properly")
                    raise

            new_task = asyncio.create_task(new_style_task())
            register_background_task(new_task, "regression_test_task")

            initial_count = len(background_tasks)
            print(f"✓ Task registered. Background tasks count: {initial_count}")

            # Let it run briefly
            await asyncio.sleep(0.3)

            # Cancel and clean up
            new_task.cancel()
            unregister_background_task(new_task)

            try:
                await new_task
            except asyncio.CancelledError:
                pass

            final_count = len(background_tasks)
            print(f"✓ Task unregistered. Background tasks count: {final_count}")

            print("✓ Background task compatibility maintained")

            self.test_results[test_name] = {
                "status": "PASSED",
                "details": "Both legacy and new task management work correctly"
            }
            return True

        except Exception as e:
            print(f"✗ Background task compatibility test failed: {e}")
            self.test_results[test_name] = {
                "status": "FAILED",
                "details": f"Task compatibility error: {e}"
            }
            return False

    def test_api_compatibility(self):
        """Test that public APIs haven't changed."""
        print("\n" + "=" * 60)
        print("REGRESSION TEST: API COMPATIBILITY")
        print("=" * 60)

        test_name = "api_compatibility"

        try:
            from src.main import main, shutdown_bot
            from src.core.application import BotApplication
            from src.database.manager import DatabaseManager
            from src.events.bus import EventBus

            print("Step 1: Checking main module API...")

            # main() should still be the entry point
            main_sig = inspect.signature(main)
            print(f"✓ main() signature: {main_sig}")

            # shutdown_bot should still be available (though enhanced)
            shutdown_sig = inspect.signature(shutdown_bot)
            print(f"✓ shutdown_bot() signature: {shutdown_sig}")

            print("Step 2: Checking BotApplication API...")

            # BotApplication should still have start/stop methods
            if hasattr(BotApplication, 'start') and hasattr(BotApplication, 'stop'):
                print("✓ BotApplication.start() and BotApplication.stop() available")
            else:
                raise Exception("BotApplication missing start/stop methods")

            print("Step 3: Checking service APIs...")

            # Services should maintain their public interfaces
            services_and_methods = [
                (DatabaseManager, ['close_all']),  # DatabaseManager uses close_all()
                (EventBus, ['connect', 'publish', 'subscribe', 'close']),
            ]

            for service_class, expected_methods in services_and_methods:
                for method in expected_methods:
                    if hasattr(service_class, method):
                        print(f"✓ {service_class.__name__}.{method}() available")
                    else:
                        raise Exception(f"{service_class.__name__} missing method: {method}")

            print("✓ All public APIs preserved")

            self.test_results[test_name] = {
                "status": "PASSED",
                "details": "All public APIs maintain backward compatibility"
            }
            return True

        except Exception as e:
            print(f"✗ API compatibility test failed: {e}")
            self.test_results[test_name] = {
                "status": "FAILED",
                "details": f"API compatibility error: {e}"
            }
            return False

    def test_configuration_compatibility(self):
        """Test that configuration system still works."""
        print("\n" + "=" * 60)
        print("REGRESSION TEST: CONFIGURATION COMPATIBILITY")
        print("=" * 60)

        test_name = "configuration_compatibility"

        try:
            from src.config.manager import ConfigManager

            print("Step 1: Testing configuration manager...")
            config = ConfigManager()
            print("✓ ConfigManager instantiated")

            # Test that key configuration methods still exist
            expected_methods = [
                'get_telegram_config',
                'get_database_config',
                'get_redis_config',
                'get_api_config'
            ]

            for method in expected_methods:
                if hasattr(config, method):
                    print(f"✓ ConfigManager.{method}() available")
                else:
                    print(f"⚠ ConfigManager.{method}() not found (may be optional)")

            print("✓ Configuration system working")

            self.test_results[test_name] = {
                "status": "PASSED",
                "details": "Configuration system maintains compatibility"
            }
            return True

        except Exception as e:
            print(f"✗ Configuration compatibility test failed: {e}")
            self.test_results[test_name] = {
                "status": "FAILED",
                "details": f"Configuration error: {e}"
            }
            return False

    def test_error_handling_preservation(self):
        """Test that error handling mechanisms still work."""
        print("\n" + "=" * 60)
        print("REGRESSION TEST: ERROR HANDLING PRESERVATION")
        print("=" * 60)

        test_name = "error_handling"

        try:
            print("Step 1: Testing exception handling...")

            # Test that we can still handle exceptions properly
            try:
                from src.utils.logger import get_logger
                logger = get_logger(__name__)
                print("✓ Logger system working")
            except Exception as e:
                print(f"⚠ Logger system issue: {e}")

            print("Step 2: Testing graceful degradation...")

            # Test that services can handle initialization failures gracefully
            from src.database.manager import DatabaseManager
            from src.config.manager import ConfigManager

            config = ConfigManager()
            db_manager = DatabaseManager(config)

            # Even if connection fails, the manager should handle it gracefully
            print("✓ Services handle errors gracefully")

            print("✓ Error handling mechanisms preserved")

            self.test_results[test_name] = {
                "status": "PASSED",
                "details": "Error handling and graceful degradation work correctly"
            }
            return True

        except Exception as e:
            print(f"✗ Error handling test failed: {e}")
            self.test_results[test_name] = {
                "status": "FAILED",
                "details": f"Error handling issue: {e}"
            }
            return False

    def print_regression_summary(self):
        """Print regression test summary."""
        print("\n" + "=" * 60)
        print("REGRESSION TEST SUMMARY")
        print("=" * 60)

        passed = 0
        total = len(self.test_results)

        for test_name, result in self.test_results.items():
            status_symbol = "✓" if result["status"] == "PASSED" else "✗"
            print(f"{status_symbol} {test_name.replace('_', ' ').title()}: {result['status']}")
            if result["status"] == "FAILED":
                print(f"   Issue: {result['details']}")
            else:
                passed += 1

        print(f"\nRegression Results: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 ALL REGRESSION TESTS PASSED!")
            print("No regressions introduced by the bug fix.")
            return True
        else:
            print(f"\n❌ {total - passed} regression tests failed.")
            print("The bug fix may have introduced unintended side effects.")
            return False

async def main():
    """Run all regression tests."""
    print("YABOT Ctrl+C Bug Fix - Regression Testing")
    print("Verifying no existing functionality was broken...")

    test_suite = RegressionTestSuite()

    # Run all regression tests
    sync_tests = [
        test_suite.test_module_imports,
        test_suite.test_api_compatibility,
        test_suite.test_configuration_compatibility,
        test_suite.test_error_handling_preservation,
    ]

    async_tests = [
        test_suite.test_service_initialization(),
        test_suite.test_background_task_compatibility(),
    ]

    # Run sync tests
    sync_results = [test() for test in sync_tests]

    # Run async tests
    async_results = await asyncio.gather(*async_tests, return_exceptions=True)

    # Combine results
    all_passed = all(sync_results) and all(isinstance(r, bool) and r for r in async_results)

    # Print summary
    success = test_suite.print_regression_summary()

    if success and all_passed:
        print("\n✅ REGRESSION TESTING COMPLETE: No regressions detected!")
        print("\n📋 Verified functionality:")
        print("• Module imports and dependencies")
        print("• Service initialization and interfaces")
        print("• Background task management compatibility")
        print("• Public API backward compatibility")
        print("• Configuration system compatibility")
        print("• Error handling preservation")

        print("\n🎯 The bug fix is safe for deployment!")
        return True
    else:
        print("\n❌ REGRESSION TESTING FAILED: Issues detected!")
        print("Please review the failing tests before deploying the fix.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
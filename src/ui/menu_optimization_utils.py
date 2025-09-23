"""
Menu System Optimization Utilities for YABOT

This module provides utilities for optimizing menu performance, navigation,
and user experience across the entire menu system.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.ui.menu_config import menu_system_config, MENU_SYSTEM_SETTINGS
from src.ui.message_manager import MessageManager

logger = logging.getLogger(__name__)


class MenuOptimizationManager:
    """
    Manager for menu system optimizations including performance monitoring,
    navigation enhancements, and intelligent cleanup strategies.
    """

    def __init__(self, message_manager: MessageManager):
        self.message_manager = message_manager
        self.navigation_cache = {}
        self.optimization_metrics = {
            "edit_operations": 0,
            "send_operations": 0,
            "cleanup_operations": 0,
            "navigation_optimizations": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    async def optimize_menu_delivery(self, chat_id: int, menu_data: Dict[str, Any],
                                   existing_message_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Optimize menu delivery by choosing between edit or send operations.

        Args:
            chat_id: The chat ID to send the menu to.
            menu_data: The menu data to send.
            existing_message_id: ID of existing message to edit if available.

        Returns:
            Result dictionary with operation details.
        """
        try:
            # Always prefer editing when possible
            if existing_message_id:
                try:
                    # Attempt to edit existing message
                    edit_result = await self._attempt_message_edit(
                        chat_id, existing_message_id, menu_data
                    )
                    if edit_result["success"]:
                        self.optimization_metrics["edit_operations"] += 1
                        return edit_result

                except Exception as edit_error:
                    logger.warning(f"Edit failed, falling back to send: {edit_error}")

            # If edit failed or no existing message, send new
            send_result = await self._send_new_menu_message(chat_id, menu_data)
            self.optimization_metrics["send_operations"] += 1
            return send_result

        except Exception as e:
            logger.error(f"Error optimizing menu delivery: {e}")
            return {"success": False, "error": str(e)}

    async def _attempt_message_edit(self, chat_id: int, message_id: int,
                                   menu_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to edit an existing message."""
        # This would be implemented with the actual bot instance
        # For now, return success simulation
        return {
            "success": True,
            "operation": "edit",
            "message_id": message_id,
            "chat_id": chat_id
        }

    async def _send_new_menu_message(self, chat_id: int,
                                   menu_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a new menu message."""
        # This would be implemented with the actual bot instance
        # For now, return success simulation
        new_message_id = 12345  # Simulated message ID
        return {
            "success": True,
            "operation": "send",
            "message_id": new_message_id,
            "chat_id": chat_id
        }

    def optimize_navigation_path(self, current_menu_id: str,
                               target_menu_id: str,
                               user_context: Dict[str, Any]) -> List[str]:
        """
        Calculate the optimal navigation path between menus.

        Args:
            current_menu_id: Current menu identifier.
            target_menu_id: Target menu identifier.
            user_context: User context for access control.

        Returns:
            Optimized navigation path as list of menu IDs.
        """
        # Define menu hierarchy for optimal navigation
        menu_hierarchy = {
            "main_menu": {
                "level": 0,
                "children": ["narrative_menu", "experiences_menu", "organic_store_menu",
                           "personal_universe_menu", "divan_menu", "admin_menu"]
            },
            "narrative_menu": {"level": 1, "parent": "main_menu"},
            "experiences_menu": {"level": 1, "parent": "main_menu"},
            "organic_store_menu": {"level": 1, "parent": "main_menu"},
            "personal_universe_menu": {"level": 1, "parent": "main_menu"},
            "divan_menu": {"level": 1, "parent": "main_menu"},
            "admin_menu": {"level": 1, "parent": "main_menu"}
        }

        # Calculate shortest path
        if target_menu_id == current_menu_id:
            return []

        current_level = menu_hierarchy.get(current_menu_id, {}).get("level", 0)
        target_level = menu_hierarchy.get(target_menu_id, {}).get("level", 0)

        # Direct navigation if both are top-level or direct parent-child
        if current_level == target_level == 1:
            # Both are children of main_menu, go through main
            return ["main_menu", target_menu_id]
        elif target_menu_id == "main_menu":
            return ["main_menu"]
        else:
            # Default path through main menu
            return ["main_menu", target_menu_id]

    async def schedule_intelligent_cleanup(self, chat_id: int,
                                         message_types: List[str]) -> None:
        """
        Schedule intelligent cleanup for multiple message types.

        Args:
            chat_id: The chat ID to clean up.
            message_types: List of message types to clean up.
        """
        try:
            cleanup_delays = MENU_SYSTEM_SETTINGS.get("message_ttl_config", {})

            for message_type in message_types:
                delay = cleanup_delays.get(message_type, cleanup_delays.get("default", 60))

                # Schedule cleanup with appropriate delay
                asyncio.create_task(
                    self._delayed_cleanup_by_type(chat_id, message_type, delay)
                )

            self.optimization_metrics["cleanup_operations"] += len(message_types)

        except Exception as e:
            logger.error(f"Error scheduling intelligent cleanup: {e}")

    async def _delayed_cleanup_by_type(self, chat_id: int, message_type: str,
                                     delay: float) -> None:
        """Execute delayed cleanup for specific message type."""
        try:
            await asyncio.sleep(delay)

            # Use message manager's cleanup functionality
            if hasattr(self.message_manager, '_delayed_cleanup'):
                await self.message_manager._delayed_cleanup(chat_id, [message_type], 0)

        except Exception as e:
            logger.error(f"Error in delayed cleanup for {message_type}: {e}")

    def cache_navigation_context(self, user_id: str, menu_id: str,
                               navigation_path: List[str]) -> None:
        """
        Cache navigation context for better user experience.

        Args:
            user_id: User identifier.
            menu_id: Current menu identifier.
            navigation_path: Current navigation path.
        """
        try:
            cache_key = f"nav_context:{user_id}"
            context_data = {
                "current_menu": menu_id,
                "navigation_path": navigation_path,
                "timestamp": datetime.utcnow().isoformat(),
                "access_count": self.navigation_cache.get(cache_key, {}).get("access_count", 0) + 1
            }

            self.navigation_cache[cache_key] = context_data
            self.optimization_metrics["cache_hits"] += 1

            # Cleanup old cache entries (keep only last 100)
            if len(self.navigation_cache) > 100:
                # Remove oldest entries
                sorted_cache = sorted(
                    self.navigation_cache.items(),
                    key=lambda x: x[1].get("timestamp", "")
                )
                for key, _ in sorted_cache[:10]:  # Remove 10 oldest
                    del self.navigation_cache[key]

        except Exception as e:
            logger.error(f"Error caching navigation context: {e}")

    def get_navigation_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached navigation context for user.

        Args:
            user_id: User identifier.

        Returns:
            Navigation context if available, None otherwise.
        """
        try:
            cache_key = f"nav_context:{user_id}"
            context = self.navigation_cache.get(cache_key)

            if context:
                # Check if cache is still valid (within 30 minutes)
                timestamp = datetime.fromisoformat(context["timestamp"])
                if datetime.utcnow() - timestamp < timedelta(minutes=30):
                    self.optimization_metrics["cache_hits"] += 1
                    return context
                else:
                    # Remove expired cache
                    del self.navigation_cache[cache_key]

            self.optimization_metrics["cache_misses"] += 1
            return None

        except Exception as e:
            logger.error(f"Error getting navigation context: {e}")
            return None

    def get_optimization_metrics(self) -> Dict[str, Any]:
        """
        Get current optimization metrics.

        Returns:
            Dictionary containing optimization performance metrics.
        """
        total_operations = (
            self.optimization_metrics["edit_operations"] +
            self.optimization_metrics["send_operations"]
        )

        edit_ratio = (
            self.optimization_metrics["edit_operations"] / total_operations * 100
            if total_operations > 0 else 0
        )

        cache_total = (
            self.optimization_metrics["cache_hits"] +
            self.optimization_metrics["cache_misses"]
        )

        cache_hit_ratio = (
            self.optimization_metrics["cache_hits"] / cache_total * 100
            if cache_total > 0 else 0
        )

        return {
            "total_operations": total_operations,
            "edit_ratio_percent": round(edit_ratio, 2),
            "cache_hit_ratio_percent": round(cache_hit_ratio, 2),
            "cleanup_operations": self.optimization_metrics["cleanup_operations"],
            "navigation_optimizations": self.optimization_metrics["navigation_optimizations"],
            "active_cache_entries": len(self.navigation_cache),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def optimize_menu_for_user(self, menu_data: Dict[str, Any],
                                   user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply user-specific optimizations to menu data.

        Args:
            menu_data: Original menu data.
            user_context: User context for optimization.

        Returns:
            Optimized menu data.
        """
        try:
            optimized_menu = menu_data.copy()

            # Sort menu items by priority and user preferences
            if "items" in optimized_menu:
                items = optimized_menu["items"]

                # Sort by navigation priority if available
                items.sort(key=lambda x: x.get("metadata", {}).get("navigation_priority", 50), reverse=True)

                # Group navigation items at the bottom
                regular_items = [item for item in items if not item.get("metadata", {}).get("is_navigation", False)]
                nav_items = [item for item in items if item.get("metadata", {}).get("is_navigation", False)]

                optimized_menu["items"] = regular_items + nav_items

            # Add optimization metadata
            optimized_menu["optimization_applied"] = True
            optimized_menu["optimization_timestamp"] = datetime.utcnow().isoformat()

            self.optimization_metrics["navigation_optimizations"] += 1
            return optimized_menu

        except Exception as e:
            logger.error(f"Error optimizing menu for user: {e}")
            return menu_data


# Global optimization manager instance
menu_optimization_manager = None


def get_optimization_manager(message_manager: MessageManager) -> MenuOptimizationManager:
    """Get or create global optimization manager instance."""
    global menu_optimization_manager
    if menu_optimization_manager is None:
        menu_optimization_manager = MenuOptimizationManager(message_manager)
    return menu_optimization_manager
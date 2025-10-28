
"""
Menu Template Caching System for YABOT.

This module provides a caching mechanism for menu templates to improve performance,
leveraging Redis as the cache store. It is designed to meet the non-functional
requirement of <500ms menu generation time.
"""

import asyncio
import json
import hashlib
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from redis import asyncio as aioredis

from src.config.manager import ConfigManager

if TYPE_CHECKING:
    from src.ui.menu_factory import Menu

logger = logging.getLogger(__name__)

class CacheError(Exception):
    """Base exception for cache-related errors."""
    pass

class CacheConnectionError(CacheError):
    """Raised when the connection to the cache server fails."""
    pass

class CacheManager:
    """Manages caching of menu templates and other data using Redis."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the CacheManager.

        Args:
            config_manager: The configuration manager instance.
        """
        self.config_manager = config_manager or ConfigManager()
        self._redis_client: Optional[aioredis.Redis] = None
        self._is_connected = False

    async def connect(self) -> bool:
        """Establish connection to Redis.

        Returns:
            True if connection is successful, False otherwise.
        """
        if self._is_connected:
            return True

        logger.info("Connecting to Redis for caching...")
        try:
            redis_config = self.config_manager.get_redis_config()
            self._redis_client = aioredis.from_url(
                redis_config.redis_url,
                password=redis_config.redis_password,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                max_connections=10,  # Separate pool for caching
                decode_responses=True # Decode responses to strings
            )

            await self._redis_client.ping()
            self._is_connected = True
            logger.info("Successfully connected to Redis for caching.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis for caching: {e}", exc_info=True)
            self._is_connected = False
            return False

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._is_connected = False
            logger.info("Redis cache connection closed.")

    def _generate_menu_cache_key(self, menu_id: str, user_context: Dict[str, Any]) -> str:
        """Generate a unique cache key for a menu based on user context."""
        user_role = user_context.get('role', 'guest')
        has_vip = user_context.get('has_vip', False)
        narrative_level = user_context.get('narrative_level', 0)
        user_archetype = user_context.get('user_archetype', 'unknown')

        key_material = (
            f"{menu_id}:{user_role}:{has_vip}:{narrative_level}:{user_archetype}"
        )
        
        # Use a hash to keep the key length manageable
        return f"menu_cache:{hashlib.md5(key_material.encode()).hexdigest()}"

    async def get_menu(self, menu_id: str, user_context: Dict[str, Any]) -> Optional['Menu']:
        """Get a cached menu.

        Args:
            menu_id: The ID of the menu.
            user_context: The user's context dictionary.

        Returns:
            A Menu object if found in cache, otherwise None.
        """
        if not self._is_connected:
            return None

        cache_key = self._generate_menu_cache_key(menu_id, user_context)
        try:
            cached_data = await self._redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Menu cache hit for key: {cache_key}")
                # Here we would deserialize the Menu object. 
                # For now, we assume it's stored as JSON and we return the dict.
                # A full implementation would use a proper serializer.
                menu_dict = json.loads(cached_data)
                # This is a simplified deserialization.
                # A real implementation would need to reconstruct the Menu and MenuItem objects.
                return Menu(**menu_dict) 
            logger.debug(f"Menu cache miss for key: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Error getting menu from cache: {e}", exc_info=True)
            return None

    async def set_menu(self, menu: 'Menu', user_context: Dict[str, Any], ttl: int = 300) -> None:
        """Cache a menu.

        Args:
            menu: The Menu object to cache.
            user_context: The user's context dictionary.
            ttl: Time-to-live for the cache entry in seconds.
        """
        if not self._is_connected:
            return

        cache_key = self._generate_menu_cache_key(menu.menu_id, user_context)
        try:
            # A simple JSON serialization. A more robust solution might use
            # a library like Pydantic for serialization.
            menu_dict = menu.__dict__
            # The 'items' are MenuItem objects, need to convert them to dicts too.
            menu_dict['items'] = [item.__dict__ for item in menu.items]
            
            serialized_data = json.dumps(menu_dict, default=str)
            
            await self._redis_client.set(cache_key, serialized_data, ex=ttl)
            logger.debug(f"Cached menu with key: {cache_key}")
        except Exception as e:
            logger.error(f"Error setting menu in cache: {e}", exc_info=True)

    async def get_value(self, key: str) -> Optional[str]:
        """Get a value from the cache by key.

        Args:
            key: The key to retrieve.

        Returns:
            The value if found, otherwise None.
        """
        if not self._is_connected or not self._redis_client:
            return None
        try:
            return await self._redis_client.get(key)
        except Exception as e:
            logger.error(f"Error getting value from cache for key '{key}': {e}", exc_info=True)
            return None

    async def set_value(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache.

        Args:
            key: The key to set.
            value: The value to store (will be JSON serialized).
            ttl: Time-to-live in seconds.
        """
        if not self._is_connected or not self._redis_client:
            return
        try:
            serialized_value = json.dumps(value, default=str)
            await self._redis_client.set(key, serialized_value, ex=ttl)
        except Exception as e:
            logger.error(f"Error setting value in cache for key '{key}': {e}", exc_info=True)

    async def delete_key(self, key: str) -> None:
        """Delete a key from the cache.

        Args:
            key: The key to delete.
        """
        if not self._is_connected or not self._redis_client:
            return
        try:
            await self._redis_client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key from cache: {key}: {e}", exc_info=True)

    async def get_keys_by_pattern(self, pattern: str) -> list[str]:
        """Get a list of keys matching a pattern.

        Args:
            pattern: The glob-style pattern to match.

        Returns:
            A list of matching keys.
        """
        if not self._is_connected or not self._redis_client:
            return []
        try:
            return await self._redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Error getting keys by pattern '{pattern}': {e}", exc_info=True)
            return []


# Global instance
cache_manager = CacheManager()

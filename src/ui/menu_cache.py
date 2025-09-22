"""
Menu Caching Optimization System for YABOT.

This module provides advanced caching strategies for menu generation with multi-tier
optimization, intelligent invalidation, and performance analytics to meet the
REQ-MENU-006.3 requirement of utilizing existing cache manager for menu optimization.
"""

import asyncio
import json
import hashlib
import time
import pickle
from typing import Dict, Any, Optional, List, Set, Union, TYPE_CHECKING
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from src.utils.cache_manager import CacheManager
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.ui.menu_factory import Menu, MenuItem

logger = get_logger(__name__)


class CacheLayer(str, Enum):
    """Cache layers for menu optimization."""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"


class CacheStrategy(str, Enum):
    """Caching strategies for different menu types."""
    AGGRESSIVE = "aggressive"     # Long TTL, high cache hit rate
    MODERATE = "moderate"         # Balanced TTL, moderate invalidation
    CONSERVATIVE = "conservative" # Short TTL, frequent updates
    DYNAMIC = "dynamic"          # Context-dependent TTL


@dataclass
class CacheMetrics:
    """Cache performance metrics for analytics."""
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    generation_time_saved: float = 0.0
    last_accessed: Optional[datetime] = None
    access_frequency: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


@dataclass
class CacheEntry:
    """Cache entry with metadata and optimization info."""
    menu_data: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    generation_time: float = 0.0
    context_hash: str = ""
    dependencies: Set[str] = field(default_factory=set)
    strategy: CacheStrategy = CacheStrategy.MODERATE

    def update_access(self) -> None:
        """Update access statistics."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class MenuCacheOptimizer:
    """Advanced menu caching system with multi-tier optimization."""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """Initialize the Menu Cache Optimizer.

        Args:
            cache_manager: Existing cache manager instance to leverage.
        """
        self.cache_manager = cache_manager or CacheManager()

        # Memory cache for ultra-fast access
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._cache_metrics: Dict[str, CacheMetrics] = {}

        # Cache configuration
        self._max_memory_entries = 1000
        self._default_ttl = 300  # 5 minutes
        self._memory_cleanup_interval = 60  # 1 minute

        # Strategy configurations
        self._strategy_ttl = {
            CacheStrategy.AGGRESSIVE: 1800,    # 30 minutes
            CacheStrategy.MODERATE: 600,       # 10 minutes
            CacheStrategy.CONSERVATIVE: 180,   # 3 minutes
            CacheStrategy.DYNAMIC: 300,        # 5 minutes (base)
        }

        # Context dependency tracking
        self._dependency_graph: Dict[str, Set[str]] = {}

        # Performance tracking
        self._performance_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "generation_time_saved": 0.0,
            "average_generation_time": 0.0
        }

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        logger.info("MenuCacheOptimizer initialized with multi-tier optimization")

    async def initialize(self) -> bool:
        """Initialize the cache system and connect to Redis.

        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # Connect to Redis through cache manager
            redis_connected = await self.cache_manager.connect()
            if redis_connected:
                logger.info("MenuCacheOptimizer connected to Redis successfully")
            else:
                logger.warning("MenuCacheOptimizer running without Redis (memory-only)")

            # Start background cleanup task
            await self._start_cleanup_task()

            return True
        except Exception as e:
            logger.error(f"Failed to initialize MenuCacheOptimizer: {e}")
            return False

    async def get_cached_menu(self, menu_id: str, user_context: Dict[str, Any],
                            use_layers: List[CacheLayer] = None) -> Optional['Menu']:
        """Retrieve cached menu with multi-tier optimization.

        Args:
            menu_id: Identifier for the menu.
            user_context: User context for cache key generation.
            use_layers: Cache layers to search (ordered by preference).

        Returns:
            Cached Menu object if found, None otherwise.
        """
        if use_layers is None:
            use_layers = [CacheLayer.MEMORY, CacheLayer.REDIS]

        cache_key = self._generate_cache_key(menu_id, user_context)
        start_time = time.time()

        # Update request statistics
        self._performance_stats["total_requests"] += 1

        try:
            # Try each cache layer in order
            for layer in use_layers:
                menu = await self._get_from_layer(cache_key, layer)
                if menu:
                    # Update metrics and statistics
                    self._update_cache_hit_metrics(cache_key, layer, time.time() - start_time)

                    # Promote to faster layers if found in slower layer
                    if layer != CacheLayer.MEMORY:
                        await self._promote_to_memory(cache_key, menu, user_context)

                    logger.debug(f"Cache hit for menu {menu_id} in {layer.value} layer")
                    return menu

            # Cache miss
            self._update_cache_miss_metrics(cache_key)
            logger.debug(f"Cache miss for menu {menu_id}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving cached menu {menu_id}: {e}")
            return None

    async def cache_menu(self, menu: 'Menu', user_context: Dict[str, Any],
                        strategy: CacheStrategy = CacheStrategy.MODERATE,
                        generation_time: float = 0.0,
                        dependencies: Set[str] = None) -> bool:
        """Cache menu with optimization strategy.

        Args:
            menu: Menu object to cache.
            user_context: User context for cache key generation.
            strategy: Caching strategy to use.
            generation_time: Time taken to generate the menu.
            dependencies: Context dependencies for invalidation.

        Returns:
            True if caching successful, False otherwise.
        """
        if not hasattr(menu, 'menu_id'):
            logger.warning("Menu object missing menu_id, cannot cache")
            return False

        cache_key = self._generate_cache_key(menu.menu_id, user_context)
        dependencies = dependencies or set()

        try:
            # Serialize menu to cacheable format
            menu_data = await self._serialize_menu(menu)

            # Create cache entry with metadata
            cache_entry = CacheEntry(
                menu_data=menu_data,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                generation_time=generation_time,
                context_hash=self._generate_context_hash(user_context),
                dependencies=dependencies,
                strategy=strategy
            )

            # Determine TTL based on strategy and context
            ttl = self._calculate_dynamic_ttl(strategy, user_context, menu)

            # Cache in memory layer
            await self._cache_in_memory(cache_key, cache_entry)

            # Cache in Redis layer
            await self._cache_in_redis(cache_key, cache_entry, ttl)

            # Update dependency graph
            self._update_dependency_graph(cache_key, dependencies)

            # Update performance statistics
            self._performance_stats["generation_time_saved"] += generation_time

            logger.debug(f"Cached menu {menu.menu_id} with {strategy.value} strategy (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error caching menu {menu.menu_id}: {e}")
            return False

    async def invalidate_cache(self, invalidation_key: str,
                             cascade: bool = True) -> int:
        """Invalidate cached menus based on key pattern.

        Args:
            invalidation_key: Key or pattern for invalidation.
            cascade: Whether to cascade invalidation to dependent entries.

        Returns:
            Number of entries invalidated.
        """
        invalidated_count = 0

        try:
            # Find matching keys in memory cache
            memory_keys = [
                key for key in self._memory_cache.keys()
                if self._key_matches_pattern(key, invalidation_key)
            ]

            # Invalidate memory cache entries
            for key in memory_keys:
                del self._memory_cache[key]
                if key in self._cache_metrics:
                    self._cache_metrics[key].invalidations += 1
                invalidated_count += 1

            # Invalidate Redis cache entries
            redis_keys = await self.cache_manager.get_keys_by_pattern(f"*{invalidation_key}*")
            for key in redis_keys:
                await self.cache_manager.delete_key(key)
                invalidated_count += 1

            # Cascade invalidation to dependent entries
            if cascade:
                cascade_count = await self._cascade_invalidation(invalidation_key)
                invalidated_count += cascade_count

            logger.info(f"Invalidated {invalidated_count} cache entries for pattern: {invalidation_key}")
            return invalidated_count

        except Exception as e:
            logger.error(f"Error during cache invalidation: {e}")
            return 0

    async def warm_cache(self, menu_configs: List[Dict[str, Any]]) -> int:
        """Pre-warm cache with frequently accessed menus.

        Args:
            menu_configs: List of menu configurations to pre-generate and cache.

        Returns:
            Number of menus successfully warmed.
        """
        warmed_count = 0

        try:
            from src.ui.menu_factory import MenuFactory

            # Initialize menu factory for pre-generation
            menu_factory = MenuFactory()

            for config in menu_configs:
                try:
                    menu_id = config.get("menu_id")
                    user_contexts = config.get("user_contexts", [])
                    strategy = CacheStrategy(config.get("strategy", "moderate"))

                    for user_context in user_contexts:
                        # Generate menu
                        start_time = time.time()
                        menu = await menu_factory.generate_menu(menu_id, user_context)
                        generation_time = time.time() - start_time

                        if menu:
                            # Cache the generated menu
                            cached = await self.cache_menu(
                                menu, user_context, strategy, generation_time
                            )
                            if cached:
                                warmed_count += 1

                except Exception as e:
                    logger.warning(f"Failed to warm cache for menu config {config}: {e}")

            logger.info(f"Cache warming completed: {warmed_count} menus cached")
            return warmed_count

        except Exception as e:
            logger.error(f"Error during cache warming: {e}")
            return 0

    async def optimize_cache_performance(self) -> Dict[str, Any]:
        """Analyze and optimize cache performance.

        Returns:
            Performance analysis and optimization recommendations.
        """
        try:
            analysis = {
                "overall_performance": self._calculate_overall_performance(),
                "memory_usage": self._analyze_memory_usage(),
                "hit_rate_analysis": self._analyze_hit_rates(),
                "strategy_effectiveness": self._analyze_strategy_effectiveness(),
                "recommendations": self._generate_optimization_recommendations()
            }

            # Apply automatic optimizations
            await self._apply_automatic_optimizations(analysis)

            logger.info("Cache performance optimization analysis completed")
            return analysis

        except Exception as e:
            logger.error(f"Error during cache performance optimization: {e}")
            return {}

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:
            Dictionary containing cache performance statistics.
        """
        total_requests = self._performance_stats["total_requests"]
        cache_hits = self._performance_stats["cache_hits"]

        return {
            "performance": {
                "total_requests": total_requests,
                "cache_hits": cache_hits,
                "hit_rate": (cache_hits / total_requests * 100) if total_requests > 0 else 0.0,
                "total_time_saved": self._performance_stats["generation_time_saved"],
                "average_generation_time": self._performance_stats["average_generation_time"]
            },
            "memory_cache": {
                "entries": len(self._memory_cache),
                "max_entries": self._max_memory_entries,
                "utilization": len(self._memory_cache) / self._max_memory_entries * 100
            },
            "strategies": {
                strategy.value: self._get_strategy_stats(strategy)
                for strategy in CacheStrategy
            },
            "dependencies": {
                "tracked_dependencies": len(self._dependency_graph),
                "average_dependencies_per_entry": self._calculate_average_dependencies()
            }
        }

    async def _get_from_layer(self, cache_key: str, layer: CacheLayer) -> Optional['Menu']:
        """Retrieve menu from specific cache layer."""
        if layer == CacheLayer.MEMORY:
            return await self._get_from_memory(cache_key)
        elif layer == CacheLayer.REDIS:
            return await self._get_from_redis(cache_key)
        else:
            return None

    async def _get_from_memory(self, cache_key: str) -> Optional['Menu']:
        """Retrieve menu from memory cache."""
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            entry.update_access()
            return await self._deserialize_menu(entry.menu_data)
        return None

    async def _get_from_redis(self, cache_key: str) -> Optional['Menu']:
        """Retrieve menu from Redis cache."""
        cached_data = await self.cache_manager.get_value(cache_key)
        if cached_data:
            try:
                menu_data = json.loads(cached_data)
                return await self._deserialize_menu(menu_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize menu from Redis: {e}")
        return None

    async def _cache_in_memory(self, cache_key: str, cache_entry: CacheEntry) -> None:
        """Cache entry in memory with LRU eviction."""
        # Evict old entries if at capacity
        if len(self._memory_cache) >= self._max_memory_entries:
            await self._evict_lru_entries()

        self._memory_cache[cache_key] = cache_entry

    async def _cache_in_redis(self, cache_key: str, cache_entry: CacheEntry, ttl: int) -> None:
        """Cache entry in Redis with TTL."""
        try:
            serialized_data = json.dumps(cache_entry.menu_data, default=str)
            await self.cache_manager.set_value(cache_key, serialized_data, ttl)
        except Exception as e:
            logger.warning(f"Failed to cache in Redis: {e}")

    async def _promote_to_memory(self, cache_key: str, menu: 'Menu', user_context: Dict[str, Any]) -> None:
        """Promote frequently accessed menu to memory cache."""
        try:
            menu_data = await self._serialize_menu(menu)
            cache_entry = CacheEntry(
                menu_data=menu_data,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                context_hash=self._generate_context_hash(user_context)
            )
            await self._cache_in_memory(cache_key, cache_entry)
        except Exception as e:
            logger.warning(f"Failed to promote menu to memory cache: {e}")

    def _generate_cache_key(self, menu_id: str, user_context: Dict[str, Any]) -> str:
        """Generate optimized cache key with context awareness."""
        # Extract key context elements
        user_id = user_context.get('user_id', 'anonymous')
        role = user_context.get('role', 'guest')
        vip_status = user_context.get('has_vip', False)
        narrative_level = user_context.get('narrative_level', 0)
        archetype = user_context.get('user_archetype', 'unknown')
        worthiness_score = user_context.get('worthiness_score', 0.0)

        # Create context-aware key components
        context_components = [
            menu_id,
            role,
            str(vip_status),
            str(narrative_level),
            archetype,
            f"{worthiness_score:.1f}"  # Round to 1 decimal for cache efficiency
        ]

        # Generate hash for compact key
        key_material = ":".join(context_components)
        context_hash = hashlib.blake2b(key_material.encode(), digest_size=16).hexdigest()

        return f"menu_opt:{context_hash}"

    def _generate_context_hash(self, user_context: Dict[str, Any]) -> str:
        """Generate hash of user context for dependency tracking."""
        relevant_context = {
            key: value for key, value in user_context.items()
            if key in ['role', 'has_vip', 'narrative_level', 'user_archetype', 'worthiness_score']
        }
        context_str = json.dumps(relevant_context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()

    def _calculate_dynamic_ttl(self, strategy: CacheStrategy, user_context: Dict[str, Any], menu: 'Menu') -> int:
        """Calculate dynamic TTL based on strategy and context."""
        base_ttl = self._strategy_ttl[strategy]

        if strategy == CacheStrategy.DYNAMIC:
            # Adjust TTL based on context factors
            narrative_level = user_context.get('narrative_level', 0)
            has_vip = user_context.get('has_vip', False)

            # Higher level users get longer cache (more stable menus)
            level_multiplier = 1 + (narrative_level * 0.2)

            # VIP users get longer cache (premium experience)
            vip_multiplier = 1.5 if has_vip else 1.0

            # Menu complexity affects cache duration
            menu_complexity = len(getattr(menu, 'items', [])) if hasattr(menu, 'items') else 1
            complexity_multiplier = 1 + (menu_complexity * 0.1)

            dynamic_ttl = int(base_ttl * level_multiplier * vip_multiplier * complexity_multiplier)
            return min(dynamic_ttl, 3600)  # Cap at 1 hour

        return base_ttl

    async def _serialize_menu(self, menu: 'Menu') -> Dict[str, Any]:
        """Serialize menu object for caching."""
        try:
            # Convert menu to serializable format
            menu_dict = {
                'menu_id': getattr(menu, 'menu_id', ''),
                'title': getattr(menu, 'title', ''),
                'description': getattr(menu, 'description', ''),
                'items': []
            }

            # Serialize menu items
            if hasattr(menu, 'items'):
                for item in menu.items:
                    item_dict = {
                        'text': getattr(item, 'text', ''),
                        'callback_data': getattr(item, 'callback_data', ''),
                        'url': getattr(item, 'url', None),
                        'description': getattr(item, 'description', ''),
                        'is_enabled': getattr(item, 'is_enabled', True),
                        'restriction_reason': getattr(item, 'restriction_reason', None)
                    }
                    menu_dict['items'].append(item_dict)

            return menu_dict
        except Exception as e:
            logger.error(f"Failed to serialize menu: {e}")
            return {}

    async def _deserialize_menu(self, menu_data: Dict[str, Any]) -> Optional['Menu']:
        """Deserialize menu data back to Menu object."""
        try:
            from src.ui.menu_factory import Menu, MenuItem

            # Create menu items
            items = []
            for item_data in menu_data.get('items', []):
                item = MenuItem(
                    text=item_data.get('text', ''),
                    callback_data=item_data.get('callback_data', ''),
                    url=item_data.get('url'),
                    description=item_data.get('description', ''),
                    is_enabled=item_data.get('is_enabled', True),
                    restriction_reason=item_data.get('restriction_reason')
                )
                items.append(item)

            # Create menu object
            menu = Menu(
                menu_id=menu_data.get('menu_id', ''),
                title=menu_data.get('title', ''),
                description=menu_data.get('description', ''),
                items=items
            )

            return menu
        except Exception as e:
            logger.error(f"Failed to deserialize menu: {e}")
            return None

    def _update_cache_hit_metrics(self, cache_key: str, layer: CacheLayer, response_time: float) -> None:
        """Update cache hit metrics and statistics."""
        self._performance_stats["cache_hits"] += 1

        if cache_key not in self._cache_metrics:
            self._cache_metrics[cache_key] = CacheMetrics()

        metrics = self._cache_metrics[cache_key]
        metrics.hits += 1
        metrics.last_accessed = datetime.utcnow()
        metrics.access_frequency += 1

    def _update_cache_miss_metrics(self, cache_key: str) -> None:
        """Update cache miss metrics."""
        if cache_key not in self._cache_metrics:
            self._cache_metrics[cache_key] = CacheMetrics()

        self._cache_metrics[cache_key].misses += 1

    def _update_dependency_graph(self, cache_key: str, dependencies: Set[str]) -> None:
        """Update dependency graph for cascade invalidation."""
        self._dependency_graph[cache_key] = dependencies

        # Add reverse dependencies
        for dep in dependencies:
            if dep not in self._dependency_graph:
                self._dependency_graph[dep] = set()

    async def _cascade_invalidation(self, invalidation_key: str) -> int:
        """Cascade invalidation to dependent cache entries."""
        invalidated_count = 0

        # Find entries that depend on the invalidated key
        dependent_keys = []
        for cache_key, dependencies in self._dependency_graph.items():
            if invalidation_key in dependencies:
                dependent_keys.append(cache_key)

        # Invalidate dependent entries
        for key in dependent_keys:
            if key in self._memory_cache:
                del self._memory_cache[key]
                invalidated_count += 1

            await self.cache_manager.delete_key(key)

        return invalidated_count

    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if cache key matches invalidation pattern."""
        return pattern in key

    async def _evict_lru_entries(self, count: int = None) -> None:
        """Evict least recently used entries from memory cache."""
        if count is None:
            count = max(1, len(self._memory_cache) // 10)  # Evict 10% by default

        # Sort by last accessed time
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: x[1].last_accessed
        )

        # Evict oldest entries
        for key, _ in sorted_entries[:count]:
            del self._memory_cache[key]

    def _calculate_overall_performance(self) -> Dict[str, Any]:
        """Calculate overall cache performance metrics."""
        total_requests = self._performance_stats["total_requests"]
        cache_hits = self._performance_stats["cache_hits"]

        return {
            "hit_rate": (cache_hits / total_requests * 100) if total_requests > 0 else 0.0,
            "total_time_saved": self._performance_stats["generation_time_saved"],
            "efficiency_score": self._calculate_efficiency_score()
        }

    def _calculate_efficiency_score(self) -> float:
        """Calculate cache efficiency score (0-100)."""
        hit_rate = self._calculate_overall_performance()["hit_rate"]
        memory_utilization = len(self._memory_cache) / self._max_memory_entries * 100

        # Weighted efficiency score
        efficiency = (hit_rate * 0.7) + (min(memory_utilization, 80) * 0.3)
        return min(efficiency, 100.0)

    def _analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze memory cache usage patterns."""
        return {
            "current_entries": len(self._memory_cache),
            "max_entries": self._max_memory_entries,
            "utilization_percentage": len(self._memory_cache) / self._max_memory_entries * 100,
            "average_access_count": self._calculate_average_access_count()
        }

    def _analyze_hit_rates(self) -> Dict[str, Any]:
        """Analyze cache hit rates by different dimensions."""
        total_hits = sum(metrics.hits for metrics in self._cache_metrics.values())
        total_misses = sum(metrics.misses for metrics in self._cache_metrics.values())

        return {
            "overall_hit_rate": (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0.0,
            "best_performing_entries": self._get_best_performing_entries(),
            "worst_performing_entries": self._get_worst_performing_entries()
        }

    def _analyze_strategy_effectiveness(self) -> Dict[str, Any]:
        """Analyze effectiveness of different caching strategies."""
        strategy_stats = {}
        for strategy in CacheStrategy:
            strategy_stats[strategy.value] = self._get_strategy_stats(strategy)
        return strategy_stats

    def _get_strategy_stats(self, strategy: CacheStrategy) -> Dict[str, Any]:
        """Get statistics for a specific caching strategy."""
        strategy_entries = [
            entry for entry in self._memory_cache.values()
            if entry.strategy == strategy
        ]

        if not strategy_entries:
            return {"entries": 0, "hit_rate": 0.0, "average_generation_time": 0.0}

        total_access = sum(entry.access_count for entry in strategy_entries)
        total_generation_time = sum(entry.generation_time for entry in strategy_entries)

        return {
            "entries": len(strategy_entries),
            "total_accesses": total_access,
            "average_generation_time": total_generation_time / len(strategy_entries),
            "ttl": self._strategy_ttl[strategy]
        }

    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []

        hit_rate = self._calculate_overall_performance()["hit_rate"]
        memory_utilization = len(self._memory_cache) / self._max_memory_entries * 100

        if hit_rate < 70:
            recommendations.append("Consider increasing cache TTL for frequently accessed menus")

        if memory_utilization > 90:
            recommendations.append("Increase memory cache size or implement more aggressive eviction")

        if memory_utilization < 30:
            recommendations.append("Consider reducing memory cache size to optimize resource usage")

        return recommendations

    async def _apply_automatic_optimizations(self, analysis: Dict[str, Any]) -> None:
        """Apply automatic optimizations based on analysis."""
        try:
            hit_rate = analysis["overall_performance"]["hit_rate"]

            # Adjust cleanup interval based on performance
            if hit_rate > 80:
                self._memory_cleanup_interval = 90  # Reduce cleanup frequency
            elif hit_rate < 50:
                self._memory_cleanup_interval = 30  # Increase cleanup frequency

            logger.debug(f"Applied automatic optimizations based on {hit_rate:.1f}% hit rate")
        except Exception as e:
            logger.warning(f"Failed to apply automatic optimizations: {e}")

    def _calculate_average_access_count(self) -> float:
        """Calculate average access count across all cached entries."""
        if not self._memory_cache:
            return 0.0

        total_access = sum(entry.access_count for entry in self._memory_cache.values())
        return total_access / len(self._memory_cache)

    def _calculate_average_dependencies(self) -> float:
        """Calculate average number of dependencies per cache entry."""
        if not self._dependency_graph:
            return 0.0

        total_deps = sum(len(deps) for deps in self._dependency_graph.values())
        return total_deps / len(self._dependency_graph)

    def _get_best_performing_entries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get best performing cache entries by hit rate."""
        sorted_metrics = sorted(
            self._cache_metrics.items(),
            key=lambda x: x[1].hit_rate,
            reverse=True
        )

        return [
            {"key": key, "hit_rate": metrics.hit_rate, "hits": metrics.hits}
            for key, metrics in sorted_metrics[:limit]
        ]

    def _get_worst_performing_entries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get worst performing cache entries by hit rate."""
        sorted_metrics = sorted(
            self._cache_metrics.items(),
            key=lambda x: x[1].hit_rate
        )

        return [
            {"key": key, "hit_rate": metrics.hit_rate, "misses": metrics.misses}
            for key, metrics in sorted_metrics[:limit]
        ]

    async def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._register_background_task(self._cleanup_task, "MenuCache cleanup task")

    def _register_background_task(self, task: asyncio.Task, task_name: str) -> None:
        """Register background task with the main application for proper shutdown."""
        try:
            # Import here to avoid circular imports
            from src.main import register_background_task
            register_background_task(task, task_name)
        except ImportError:
            logger.warning(f"Could not register background task {task_name} - main module not available")

    def _unregister_background_task(self, task: asyncio.Task) -> None:
        """Unregister background task from the main application."""
        try:
            # Import here to avoid circular imports
            from src.main import unregister_background_task
            unregister_background_task(task)
        except ImportError:
            pass  # Main module not available

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for cache maintenance."""
        while True:
            try:
                await asyncio.sleep(self._memory_cleanup_interval)
                await self._perform_maintenance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")

    async def _perform_maintenance(self) -> None:
        """Perform cache maintenance operations."""
        try:
            # Clean up expired entries
            current_time = datetime.utcnow()
            expired_keys = []

            for key, entry in self._memory_cache.items():
                # Simple time-based expiration (could be enhanced with TTL tracking)
                age = (current_time - entry.created_at).total_seconds()
                if age > self._strategy_ttl[entry.strategy]:
                    expired_keys.append(key)

            # Remove expired entries
            for key in expired_keys:
                del self._memory_cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            # Evict LRU entries if approaching capacity
            if len(self._memory_cache) > self._max_memory_entries * 0.9:
                await self._evict_lru_entries()

        except Exception as e:
            logger.error(f"Error during cache maintenance: {e}")

    async def close(self) -> None:
        """Close cache system and cleanup resources."""
        try:
            # Cancel and unregister cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                self._unregister_background_task(self._cleanup_task)
                try:
                    await asyncio.wait_for(self._cleanup_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.debug("Cleanup task cancelled/timed out during shutdown")
                except Exception as e:
                    logger.warning(f"Error during cleanup task cancellation: {e}")

            # Close cache manager connection
            await self.cache_manager.close()

            # Clear memory cache
            self._memory_cache.clear()
            self._cache_metrics.clear()
            self._dependency_graph.clear()

            logger.info("MenuCacheOptimizer closed successfully")
        except Exception as e:
            logger.error(f"Error closing MenuCacheOptimizer: {e}")


# Global instance for easy access
menu_cache_optimizer = MenuCacheOptimizer()
"""
Menu Performance Monitoring System for YABOT.

This module provides comprehensive performance monitoring specifically for menu operations,
tracking generation times, callback processing, user interaction patterns, and system
health metrics to ensure menu system meets performance requirements REQ-MENU-001.3 and
REQ-MENU-002.2.
"""

import time
import asyncio
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Callable, Coroutine, Union
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel

from src.shared.monitoring.performance import PerformanceMonitor, PerformanceMetrics
from src.utils.logger import get_logger
from src.events.bus import EventBus

logger = get_logger(__name__)


class MenuOperationType(str, Enum):
    """Types of menu operations to monitor."""
    GENERATION = "generation"
    RENDERING = "rendering"
    CALLBACK_PROCESSING = "callback_processing"
    NAVIGATION = "navigation"
    CACHING = "caching"
    VALIDATION = "validation"
    USER_INTERACTION = "user_interaction"
    MESSAGE_CLEANUP = "message_cleanup"
    PERMISSION_CHECK = "permission_check"


class PerformanceThreshold(str, Enum):
    """Performance threshold levels for alerting."""
    OPTIMAL = "optimal"      # < 200ms
    ACCEPTABLE = "acceptable" # 200ms - 500ms
    SLOW = "slow"           # 500ms - 2000ms
    CRITICAL = "critical"    # > 2000ms


@dataclass
class MenuOperationMetrics:
    """Extended metrics for menu operations."""
    operation_type: MenuOperationType
    duration_ms: float
    timestamp: datetime
    user_id: Optional[str] = None
    menu_id: Optional[str] = None
    cache_hit: bool = False
    error_occurred: bool = False
    error_type: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    performance_threshold: PerformanceThreshold = PerformanceThreshold.OPTIMAL
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Calculate performance threshold based on duration."""
        if self.duration_ms < 200:
            self.performance_threshold = PerformanceThreshold.OPTIMAL
        elif self.duration_ms < 500:
            self.performance_threshold = PerformanceThreshold.ACCEPTABLE
        elif self.duration_ms < 2000:
            self.performance_threshold = PerformanceThreshold.SLOW
        else:
            self.performance_threshold = PerformanceThreshold.CRITICAL


@dataclass
class UserInteractionPattern:
    """Pattern analysis for user menu interactions."""
    user_id: str
    session_start: datetime
    menu_transitions: List[str] = field(default_factory=list)
    callback_response_times: List[float] = field(default_factory=list)
    error_count: int = 0
    cache_hit_ratio: float = 0.0
    total_operations: int = 0

    def add_operation(self, menu_id: str, response_time: float, cache_hit: bool, error: bool) -> None:
        """Add operation to pattern analysis."""
        self.menu_transitions.append(menu_id)
        self.callback_response_times.append(response_time)
        self.total_operations += 1

        if error:
            self.error_count += 1

        # Update cache hit ratio
        cache_hits = sum(1 for _ in self.menu_transitions if cache_hit)  # Simplified calculation
        self.cache_hit_ratio = cache_hits / self.total_operations if self.total_operations > 0 else 0.0

    def get_average_response_time(self) -> float:
        """Calculate average response time for user interactions."""
        return sum(self.callback_response_times) / len(self.callback_response_times) if self.callback_response_times else 0.0

    def get_error_rate(self) -> float:
        """Calculate error rate percentage."""
        return (self.error_count / self.total_operations * 100) if self.total_operations > 0 else 0.0


@dataclass
class SystemHealthMetrics:
    """System-wide health metrics for menu operations."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_operations_per_minute: int = 0
    average_generation_time: float = 0.0
    average_callback_time: float = 0.0
    cache_hit_ratio: float = 0.0
    error_rate: float = 0.0
    active_users: int = 0
    concurrent_operations: int = 0
    memory_usage_mb: float = 0.0
    redis_connection_healthy: bool = True
    database_connection_healthy: bool = True

    def calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        score = 100.0

        # Deduct for poor performance
        if self.average_generation_time > 2000:
            score -= 30
        elif self.average_generation_time > 500:
            score -= 15

        # Deduct for errors
        if self.error_rate > 10:
            score -= 25
        elif self.error_rate > 5:
            score -= 10

        # Deduct for poor cache performance
        if self.cache_hit_ratio < 0.5:
            score -= 15

        # Deduct for connection issues
        if not self.redis_connection_healthy:
            score -= 20
        if not self.database_connection_healthy:
            score -= 20

        return max(0.0, score)


class MenuPerformanceMonitor:
    """Enhanced performance monitor specialized for menu operations."""

    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize the Menu Performance Monitor.

        Args:
            event_bus: Optional event bus for publishing performance events.
        """
        self.base_monitor = PerformanceMonitor("menu_system")
        self.event_bus = event_bus

        # Performance data storage
        self.operation_metrics: deque[MenuOperationMetrics] = deque(maxlen=10000)
        self.user_patterns: Dict[str, UserInteractionPattern] = {}
        self.system_health = SystemHealthMetrics()

        # Real-time tracking
        self.concurrent_operations = 0
        self.operations_per_minute: deque[datetime] = deque(maxlen=1000)

        # Threshold configurations
        self.performance_thresholds = {
            MenuOperationType.GENERATION: 500,  # 500ms for menu generation
            MenuOperationType.RENDERING: 200,   # 200ms for rendering
            MenuOperationType.CALLBACK_PROCESSING: 1000,  # 1s for callback processing
            MenuOperationType.NAVIGATION: 300,  # 300ms for navigation
            MenuOperationType.CACHING: 100,     # 100ms for cache operations
            MenuOperationType.VALIDATION: 50,   # 50ms for validation
            MenuOperationType.USER_INTERACTION: 3000,  # 3s total user interaction
            MenuOperationType.MESSAGE_CLEANUP: 2000,   # 2s for message cleanup
            MenuOperationType.PERMISSION_CHECK: 100,   # 100ms for permission checks
        }

        # Alerting configurations
        self.alert_thresholds = {
            "error_rate_percent": 5.0,
            "avg_generation_time_ms": 1000.0,
            "cache_hit_ratio_min": 0.7,
            "health_score_min": 80.0
        }

        logger.info("MenuPerformanceMonitor initialized with comprehensive tracking")

    def monitor_operation(self, operation_type: MenuOperationType,
                         menu_id: Optional[str] = None,
                         user_id: Optional[str] = None,
                         correlation_id: Optional[str] = None) -> Callable:
        """Decorator to monitor menu operations with detailed metrics.

        Args:
            operation_type: Type of menu operation being monitored.
            menu_id: Identifier of the menu being operated on.
            user_id: User performing the operation.
            correlation_id: Correlation ID for tracking related operations.

        Returns:
            Decorator function for monitoring the operation.
        """
        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                self.concurrent_operations += 1
                cache_hit = False
                error_occurred = False
                error_type = None

                try:
                    # Extract cache hit information from kwargs if available
                    cache_hit = kwargs.get('_cache_hit', False)

                    # Execute the operation
                    result = await func(*args, **kwargs)

                    # Check if result indicates cache hit
                    if hasattr(result, 'from_cache'):
                        cache_hit = getattr(result, 'from_cache', False)

                    return result

                except Exception as e:
                    error_occurred = True
                    error_type = type(e).__name__
                    raise

                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    self.concurrent_operations = max(0, self.concurrent_operations - 1)

                    # Create detailed metrics
                    metrics = MenuOperationMetrics(
                        operation_type=operation_type,
                        duration_ms=duration_ms,
                        timestamp=datetime.utcnow(),
                        user_id=user_id,
                        menu_id=menu_id,
                        cache_hit=cache_hit,
                        error_occurred=error_occurred,
                        error_type=error_type,
                        correlation_id=correlation_id
                    )

                    # Store metrics and update patterns
                    await self._record_operation_metrics(metrics)

                    # Check for performance alerts
                    await self._check_performance_alerts(metrics)

            return wrapper
        return decorator

    async def _record_operation_metrics(self, metrics: MenuOperationMetrics) -> None:
        """Record operation metrics and update tracking data."""
        try:
            # Store metrics
            self.operation_metrics.append(metrics)
            self.operations_per_minute.append(metrics.timestamp)

            # Update user interaction patterns
            if metrics.user_id:
                await self._update_user_pattern(metrics)

            # Update system health metrics
            await self._update_system_health()

            # Publish performance event
            if self.event_bus:
                await self._publish_performance_event(metrics)

            # Log performance data
            self._log_performance_metrics(metrics)

        except Exception as e:
            logger.error(f"Error recording operation metrics: {e}")

    async def _update_user_pattern(self, metrics: MenuOperationMetrics) -> None:
        """Update user interaction pattern analysis."""
        user_id = metrics.user_id
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = UserInteractionPattern(
                user_id=user_id,
                session_start=metrics.timestamp
            )

        pattern = self.user_patterns[user_id]
        pattern.add_operation(
            menu_id=metrics.menu_id or "unknown",
            response_time=metrics.duration_ms,
            cache_hit=metrics.cache_hit,
            error=metrics.error_occurred
        )

        # Clean up old patterns (older than 1 hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        if pattern.session_start < cutoff_time:
            del self.user_patterns[user_id]

    async def _update_system_health(self) -> None:
        """Update system-wide health metrics."""
        try:
            current_time = datetime.utcnow()
            one_minute_ago = current_time - timedelta(minutes=1)

            # Calculate operations per minute
            recent_operations = [
                op for op in self.operations_per_minute
                if op > one_minute_ago
            ]
            self.system_health.total_operations_per_minute = len(recent_operations)

            # Get recent metrics (last 100 operations)
            recent_metrics = list(self.operation_metrics)[-100:] if self.operation_metrics else []

            if recent_metrics:
                # Calculate average times by operation type
                generation_times = [
                    m.duration_ms for m in recent_metrics
                    if m.operation_type == MenuOperationType.GENERATION
                ]
                callback_times = [
                    m.duration_ms for m in recent_metrics
                    if m.operation_type == MenuOperationType.CALLBACK_PROCESSING
                ]

                self.system_health.average_generation_time = (
                    sum(generation_times) / len(generation_times) if generation_times else 0.0
                )
                self.system_health.average_callback_time = (
                    sum(callback_times) / len(callback_times) if callback_times else 0.0
                )

                # Calculate cache hit ratio
                cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
                self.system_health.cache_hit_ratio = cache_hits / len(recent_metrics)

                # Calculate error rate
                errors = sum(1 for m in recent_metrics if m.error_occurred)
                self.system_health.error_rate = (errors / len(recent_metrics)) * 100

            # Update other metrics
            self.system_health.active_users = len(self.user_patterns)
            self.system_health.concurrent_operations = self.concurrent_operations
            self.system_health.timestamp = current_time

        except Exception as e:
            logger.error(f"Error updating system health metrics: {e}")

    async def _check_performance_alerts(self, metrics: MenuOperationMetrics) -> None:
        """Check if performance metrics trigger alerts."""
        try:
            alerts = []

            # Check operation duration against thresholds
            threshold = self.performance_thresholds.get(metrics.operation_type, 1000)
            if metrics.duration_ms > threshold:
                alerts.append({
                    "type": "slow_operation",
                    "operation": metrics.operation_type.value,
                    "duration_ms": metrics.duration_ms,
                    "threshold_ms": threshold,
                    "user_id": metrics.user_id,
                    "menu_id": metrics.menu_id
                })

            # Check system health thresholds
            health_score = self.system_health.calculate_health_score()
            if health_score < self.alert_thresholds["health_score_min"]:
                alerts.append({
                    "type": "low_health_score",
                    "health_score": health_score,
                    "threshold": self.alert_thresholds["health_score_min"]
                })

            # Check error rate
            if self.system_health.error_rate > self.alert_thresholds["error_rate_percent"]:
                alerts.append({
                    "type": "high_error_rate",
                    "error_rate": self.system_health.error_rate,
                    "threshold": self.alert_thresholds["error_rate_percent"]
                })

            # Publish alerts
            for alert in alerts:
                await self._publish_alert(alert)

        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")

    async def _publish_performance_event(self, metrics: MenuOperationMetrics) -> None:
        """Publish performance event to event bus."""
        if not self.event_bus:
            return

        try:
            event_data = {
                "operation_type": metrics.operation_type.value,
                "duration_ms": metrics.duration_ms,
                "performance_threshold": metrics.performance_threshold.value,
                "user_id": metrics.user_id,
                "menu_id": metrics.menu_id,
                "cache_hit": metrics.cache_hit,
                "error_occurred": metrics.error_occurred,
                "timestamp": metrics.timestamp.isoformat(),
                "correlation_id": metrics.correlation_id
            }

            await self.event_bus.publish("menu_performance_metrics", event_data)

        except Exception as e:
            logger.error(f"Error publishing performance event: {e}")

    async def _publish_alert(self, alert: Dict[str, Any]) -> None:
        """Publish performance alert."""
        if not self.event_bus:
            return

        try:
            alert_data = {
                **alert,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "menu_performance_monitor"
            }

            await self.event_bus.publish("performance_alert", alert_data)
            logger.warning(f"Performance alert: {alert}")

        except Exception as e:
            logger.error(f"Error publishing performance alert: {e}")

    def _log_performance_metrics(self, metrics: MenuOperationMetrics) -> None:
        """Log performance metrics with appropriate level."""
        log_data = {
            "operation": metrics.operation_type.value,
            "duration_ms": metrics.duration_ms,
            "threshold": metrics.performance_threshold.value,
            "user_id": metrics.user_id,
            "menu_id": metrics.menu_id,
            "cache_hit": metrics.cache_hit,
            "error": metrics.error_occurred
        }

        if metrics.performance_threshold == PerformanceThreshold.CRITICAL:
            logger.error(f"CRITICAL performance: {log_data}")
        elif metrics.performance_threshold == PerformanceThreshold.SLOW:
            logger.warning(f"SLOW performance: {log_data}")
        else:
            logger.debug(f"Performance: {log_data}")

    async def get_performance_report(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Generate comprehensive performance report.

        Args:
            time_window_minutes: Time window for analysis in minutes.

        Returns:
            Comprehensive performance report dictionary.
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            recent_metrics = [
                m for m in self.operation_metrics
                if m.timestamp > cutoff_time
            ]

            if not recent_metrics:
                return {"message": "No metrics available for the specified time window"}

            # Aggregate metrics by operation type
            operation_stats = defaultdict(lambda: {
                "count": 0,
                "total_duration": 0.0,
                "error_count": 0,
                "cache_hits": 0
            })

            for metric in recent_metrics:
                stats = operation_stats[metric.operation_type.value]
                stats["count"] += 1
                stats["total_duration"] += metric.duration_ms
                if metric.error_occurred:
                    stats["error_count"] += 1
                if metric.cache_hit:
                    stats["cache_hits"] += 1

            # Calculate averages and rates
            for op_type, stats in operation_stats.items():
                if stats["count"] > 0:
                    stats["average_duration_ms"] = stats["total_duration"] / stats["count"]
                    stats["error_rate_percent"] = (stats["error_count"] / stats["count"]) * 100
                    stats["cache_hit_ratio"] = stats["cache_hits"] / stats["count"]

            # User interaction analysis
            user_analysis = {}
            for user_id, pattern in self.user_patterns.items():
                user_analysis[user_id] = {
                    "total_operations": pattern.total_operations,
                    "average_response_time_ms": pattern.get_average_response_time(),
                    "error_rate_percent": pattern.get_error_rate(),
                    "cache_hit_ratio": pattern.cache_hit_ratio,
                    "session_duration_minutes": (
                        datetime.utcnow() - pattern.session_start
                    ).total_seconds() / 60
                }

            # System health summary
            health_summary = {
                "health_score": self.system_health.calculate_health_score(),
                "operations_per_minute": self.system_health.total_operations_per_minute,
                "average_generation_time_ms": self.system_health.average_generation_time,
                "average_callback_time_ms": self.system_health.average_callback_time,
                "cache_hit_ratio": self.system_health.cache_hit_ratio,
                "error_rate_percent": self.system_health.error_rate,
                "active_users": self.system_health.active_users,
                "concurrent_operations": self.system_health.concurrent_operations
            }

            # Performance distribution
            threshold_distribution = defaultdict(int)
            for metric in recent_metrics:
                threshold_distribution[metric.performance_threshold.value] += 1

            return {
                "time_window_minutes": time_window_minutes,
                "total_operations": len(recent_metrics),
                "operation_statistics": dict(operation_stats),
                "user_interaction_analysis": user_analysis,
                "system_health": health_summary,
                "performance_distribution": dict(threshold_distribution),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {"error": f"Failed to generate report: {e}"}

    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics."""
        return {
            "concurrent_operations": self.concurrent_operations,
            "operations_last_minute": len([
                op for op in self.operations_per_minute
                if op > datetime.utcnow() - timedelta(minutes=1)
            ]),
            "active_users": len(self.user_patterns),
            "health_score": self.system_health.calculate_health_score(),
            "cache_hit_ratio": self.system_health.cache_hit_ratio,
            "error_rate_percent": self.system_health.error_rate,
            "average_generation_time_ms": self.system_health.average_generation_time,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def reset_metrics(self) -> None:
        """Reset all performance metrics and patterns."""
        try:
            self.operation_metrics.clear()
            self.user_patterns.clear()
            self.operations_per_minute.clear()
            self.system_health = SystemHealthMetrics()
            self.concurrent_operations = 0

            logger.info("Performance metrics reset successfully")

        except Exception as e:
            logger.error(f"Error resetting performance metrics: {e}")

    def configure_thresholds(self, operation_thresholds: Dict[str, float],
                           alert_thresholds: Dict[str, float]) -> None:
        """Configure performance and alert thresholds.

        Args:
            operation_thresholds: Duration thresholds for operations (ms).
            alert_thresholds: Alert trigger thresholds.
        """
        try:
            # Update operation thresholds
            for op_type_str, threshold in operation_thresholds.items():
                try:
                    op_type = MenuOperationType(op_type_str)
                    self.performance_thresholds[op_type] = threshold
                except ValueError:
                    logger.warning(f"Unknown operation type: {op_type_str}")

            # Update alert thresholds
            self.alert_thresholds.update(alert_thresholds)

            logger.info("Performance thresholds updated successfully")

        except Exception as e:
            logger.error(f"Error configuring thresholds: {e}")


# Global instance for easy access
menu_performance_monitor = MenuPerformanceMonitor()
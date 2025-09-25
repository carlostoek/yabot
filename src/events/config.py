"""
Event Bus Configuration

This module provides configuration utilities for the event bus system.
"""
from typing import Dict, Any, Optional
from src.core.models import RedisConfig


def get_redis_config() -> Dict[str, Any]:
    """
    Get Redis configuration for the event bus
    
    Returns:
        Dictionary containing Redis configuration
    """
    # Create default Redis config
    redis_config = RedisConfig()
    
    return {
        'url': redis_config.url,
        'password': redis_config.password,
        'max_connections': redis_config.max_connections,
        'retry_on_timeout': redis_config.retry_on_timeout,
        'socket_connect_timeout': redis_config.socket_connect_timeout,
        'socket_timeout': redis_config.socket_timeout,
        'local_queue_max_size': redis_config.local_queue_max_size,
        'local_queue_persistence_file': redis_config.local_queue_persistence_file
    }
"""
Menu System Configuration for YABOT.

Configuration management for menu system settings, performance thresholds,
and operational parameters as per REQ-MENU-002.4 and REQ-MENU-006.4.
"""

from pydantic import BaseSettings, validator
from typing import Dict, Any, Optional
from src.config.manager import ConfigManager

class MenuSystemConfig(BaseSettings):
    """Menu system configuration settings."""

    # Performance thresholds (ms)
    menu_generation_timeout_ms: int = 2000
    cached_menu_timeout_ms: int = 500
    callback_processing_timeout_ms: int = 1000

    # Cache settings
    menu_cache_ttl_seconds: int = 300
    max_cached_menus: int = 1000
    cache_strategy: str = "adaptive"

    # Message cleanup settings
    cleanup_interval_seconds: int = 30
    message_ttl_config: Dict[str, int] = {
        'main_menu': -1,
        'system_notification': 5,
        'error_message': 10,
        'success_feedback': 3,
        'loading_message': 2,
        'temporary_info': 8,
        'lucien_response': 6,
        'callback_response': 4,
        'admin_notification': 15,
        'debug_message': 30,
        'default': 60
    }

    # Rate limiting
    telegram_rate_limit_per_second: int = 30
    telegram_rate_limit_per_minute: int = 20
    burst_limit: int = 100

    # Circuit breaker settings
    menu_generation_failure_threshold: int = 5
    menu_generation_recovery_timeout: int = 30
    callback_processing_failure_threshold: int = 3
    callback_processing_recovery_timeout: int = 20

    class Config:
        env_prefix = "MENU_"
        case_sensitive = False

# Global configuration instance
menu_config = MenuSystemConfig()
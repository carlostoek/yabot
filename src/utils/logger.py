"""
Logging utilities for the Telegram bot framework.
"""

import structlog
import logging
import sys
from typing import Any, Dict, Optional
from src.config.manager import ConfigManager


def get_logger(name: str):
    """Get a structured logger instance.
    
    Args:
        name (str): The name of the logger
        
    Returns:
        structlog.BoundLogger: A configured structured logger
    """
    return structlog.get_logger(name)


def configure_logging(config_manager: Optional[ConfigManager] = None):
    """Configure structured logging for the application.
    
    Args:
        config_manager (ConfigManager, optional): Configuration manager instance
    """
    # Get logging configuration
    if config_manager:
        log_config = config_manager.get_logging_config()
        log_level = getattr(logging, log_config.level.upper(), logging.INFO)
    else:
        log_level = logging.INFO
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
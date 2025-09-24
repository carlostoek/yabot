"""
Core Bot Framework - Logging Utilities

This module provides structured logging functionality for the application
using structlog for better observability.
"""
import logging
import logging.config
import structlog
import sys
import os
from typing import Optional
from pathlib import Path


def setup_basic_logging():
    """
    Setup basic logging for the application without config dependencies.
    This is used during initial startup to avoid circular import issues.
    """
    # Configure structlog with default settings
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
            # Default to key-value format
            structlog.processors.KeyValueRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set the root logger level to INFO by default
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )


def setup_logging_with_config(logging_config):
    """
    Setup structured logging for the application using the provided config.
    """
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
            # Choose your output format based on config
            structlog.processors.JSONRenderer() if logging_config.format == "json" 
            else structlog.processors.KeyValueRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set the root logger level
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, logging_config.level.upper()),
    )
    
    # If a file path is specified, add a file handler
    if logging_config.file_path:
        setup_file_logging(logging_config)


def setup_logging():
    """
    Setup structured logging for the application
    """
    # Import config manager here to avoid circular import
    from src.config.manager import get_config_manager
    config_manager = get_config_manager()
    logging_config = config_manager.get_logging_config()
    
    setup_logging_with_config(logging_config)


def setup_file_logging(logging_config):
    """
    Setup file-based logging with rotation
    """
    from logging.handlers import RotatingFileHandler
    
    # Create log directory if it doesn't exist
    log_dir = Path(logging_config.file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a custom logger
    logger = logging.getLogger()
    
    # Create handler for file output with rotation
    file_handler = RotatingFileHandler(
        filename=logging_config.file_path,
        maxBytes=logging_config.max_file_size,
        backupCount=logging_config.backup_count
    )
    
    # Create formatter
    if logging_config.format == "json":
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def get_logger(name: Optional[str] = None):
    """
    Get a configured logger instance
    
    Args:
        name: Optional name for the logger. If None, returns the root logger.
    
    Returns:
        Configured logger instance
    """
    if name:
        return structlog.get_logger(name)
    else:
        return structlog.get_logger()


def log_exception(logger, message: str = "An exception occurred"):
    """
    Log an exception with traceback
    
    Args:
        logger: The logger instance to use
        message: Custom message to include with the exception
    """
    logger.exception(message)


def add_log_context(**kwargs):
    """
    Add context to the current log context
    
    Args:
        **kwargs: Key-value pairs to add to the log context
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_log_context():
    """
    Clear the current log context
    """
    structlog.contextvars.clear_contextvars()


class LoggerMixin:
    """
    Mixin class to add logging capabilities to other classes
    """
    
    @property
    def logger(self):
        """
        Get a logger instance for this class
        """
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def log_debug(self, message: str, **kwargs):
        """
        Log a debug message
        """
        self.logger.debug(message, **kwargs)
    
    def log_info(self, message: str, **kwargs):
        """
        Log an info message
        """
        self.logger.info(message, **kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """
        Log a warning message
        """
        self.logger.warning(message, **kwargs)
    
    def log_error(self, message: str, **kwargs):
        """
        Log an error message
        """
        self.logger.error(message, **kwargs)
    
    def log_critical(self, message: str, **kwargs):
        """
        Log a critical message
        """
        self.logger.critical(message, **kwargs)



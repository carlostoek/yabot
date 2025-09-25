"""
Database module for YABOT

This module provides database connection management for both MongoDB and SQLite.
It handles connection pooling, configuration loading, and provides access to
database instances throughout the application.
"""
from .manager import DatabaseManager
from .mongodb import MongoDBHandler
from .sqlite import SQLiteHandler


__all__ = [
    'DatabaseManager',
    'MongoDBHandler', 
    'SQLiteHandler'
]
"""
Database connection manager for the YABOT system.

This module provides a unified interface for managing connections to both
MongoDB and SQLite databases, implementing connection pooling, health checks,
and reconnection logic as required by the fase1 specification.
"""

from .manager import DatabaseManager

__all__ = ["DatabaseManager"]
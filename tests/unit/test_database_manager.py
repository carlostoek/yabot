"""
Unit tests for the DatabaseManager class.
"""

import asyncio
import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from src.database.manager import DatabaseManager
from src.config.manager import ConfigManager


class TestDatabaseManager:
    """Test cases for the DatabaseManager class."""

    def test_init(self):
        """Test DatabaseManager initialization."""
        # Test with default config manager
        db_manager = DatabaseManager()
        assert hasattr(db_manager, '_mongo_client')
        assert hasattr(db_manager, '_sqlite_conn')
        assert hasattr(db_manager, '_mongo_db_name')
        assert hasattr(db_manager, '_is_connected')
        assert db_manager._is_connected is False

        # Test with custom config manager
        mock_config = Mock(spec=ConfigManager)
        db_manager = DatabaseManager(config_manager=mock_config)
        assert db_manager.config_manager == mock_config

    def test_is_connected_property(self):
        """Test the is_connected property."""
        db_manager = DatabaseManager()
        assert db_manager.is_connected is False

        # Manually set the connected flag
        db_manager._is_connected = True
        assert db_manager.is_connected is True

    def test_get_mongo_db_not_connected(self):
        """Test get_mongo_db when not connected."""
        db_manager = DatabaseManager()
        with pytest.raises(ValueError, match="MongoDB is not connected"):
            db_manager.get_mongo_db()

    def test_get_sqlite_conn_not_connected(self):
        """Test get_sqlite_conn when not connected."""
        db_manager = DatabaseManager()
        with pytest.raises(ValueError, match="SQLite is not connected"):
            db_manager.get_sqlite_conn()


if __name__ == "__main__":
    pytest.main([__file__])
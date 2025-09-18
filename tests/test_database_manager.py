"""
Test for the DatabaseManager class.
"""

import asyncio
import os
import sys
import tempfile
from src.database.manager import DatabaseManager


async def test_database_manager():
    """Test the DatabaseManager class."""
    # Create a temporary directory for the SQLite database
    with tempfile.TemporaryDirectory() as temp_dir:
        sqlite_path = os.path.join(temp_dir, "test.db")
        
        # Set environment variables for testing
        os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
        os.environ["MONGODB_DATABASE"] = "test_db"
        os.environ["SQLITE_DATABASE_PATH"] = sqlite_path
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Test that the manager was initialized correctly
        assert hasattr(db_manager, '_mongo_client')
        assert hasattr(db_manager, '_sqlite_conn')
        assert hasattr(db_manager, '_mongo_db_name')
        assert hasattr(db_manager, '_is_connected')
        
        # Test connection methods exist
        assert hasattr(db_manager, 'connect_all')
        assert hasattr(db_manager, 'get_mongo_db')
        assert hasattr(db_manager, 'get_sqlite_conn')
        assert hasattr(db_manager, 'health_check')
        assert hasattr(db_manager, 'close_all')
        assert hasattr(db_manager, 'is_connected')
        
        print("All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_database_manager())
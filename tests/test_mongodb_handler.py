"""
Test for the MongoDBHandler class.
"""

import asyncio
from unittest.mock import Mock
from src.database.mongodb import MongoDBHandler


def test_mongodb_handler_initialization():
    """Test MongoDBHandler initialization."""
    # Create a mock database
    mock_db = Mock()
    
    # Create handler
    handler = MongoDBHandler(mock_db)
    
    # Verify initialization
    assert handler._db == mock_db


def test_collection_access_methods():
    """Test collection access methods."""
    # Create a mock database
    mock_db = Mock()
    
    # Create handler
    handler = MongoDBHandler(mock_db)
    
    # Test users collection access
    mock_users_collection = Mock()
    mock_db.__getitem__ = Mock(return_value=mock_users_collection)
    
    users_collection = handler.get_users_collection()
    assert users_collection == mock_users_collection
    mock_db.__getitem__.assert_called_with("users")
    
    # Test narrative fragments collection access
    mock_narrative_collection = Mock()
    mock_db.__getitem__ = Mock(return_value=mock_narrative_collection)
    
    narrative_collection = handler.get_narrative_fragments_collection()
    assert narrative_collection == mock_narrative_collection
    mock_db.__getitem__.assert_called_with("narrative_fragments")
    
    # Test items collection access
    mock_items_collection = Mock()
    mock_db.__getitem__ = Mock(return_value=mock_items_collection)
    
    items_collection = handler.get_items_collection()
    assert items_collection == mock_items_collection
    mock_db.__getitem__.assert_called_with("items")


async def test_initialize_collections():
    """Test collection initialization."""
    # Create a mock database and collections
    mock_db = Mock()
    mock_users_collection = Mock()
    mock_narrative_collection = Mock()
    mock_items_collection = Mock()
    
    # Set up mock return values
    mock_db.__getitem__ = Mock(side_effect=[
        mock_users_collection,
        mock_narrative_collection,
        mock_items_collection
    ])
    
    # Create handler
    handler = MongoDBHandler(mock_db)
    
    # Mock the index creation methods to do nothing
    mock_users_collection.create_index = Mock()
    mock_narrative_collection.create_index = Mock()
    mock_items_collection.create_index = Mock()
    
    # Test initialization
    result = await handler.initialize_collections()
    
    # Verify success
    assert result is True
    
    # Verify that indexes were created 
    # Users collection has 5 indexes
    assert mock_users_collection.create_index.call_count == 5
    # NarrativeFragments and Items collections have 4 indexes each
    assert mock_narrative_collection.create_index.call_count == 4
    assert mock_items_collection.create_index.call_count == 4


async def test_initialize_collections_error():
    """Test collection initialization with error."""
    # Create a mock database
    mock_db = Mock()
    
    # Create handler
    handler = MongoDBHandler(mock_db)
    
    # Mock get_users_collection to raise an exception
    handler.get_users_collection = Mock(side_effect=Exception("Test error"))
    
    # Test initialization
    result = await handler.initialize_collections()
    
    # Verify failure
    assert result is False


if __name__ == "__main__":
    test_mongodb_handler_initialization()
    test_collection_access_methods()
    asyncio.run(test_initialize_collections())
    asyncio.run(test_initialize_collections_error())
    print("All tests passed!")
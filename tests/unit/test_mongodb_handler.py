"""
Unit tests for the MongoDBHandler class.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from src.database.mongodb import MongoDBHandler


class TestMongoDBHandler:
    """Test cases for the MongoDBHandler class."""

    def test_init(self):
        """Test MongoDBHandler initialization."""
        mock_db = Mock()
        handler = MongoDBHandler(mock_db)
        assert handler._db == mock_db

    def test_get_users_collection(self):
        """Test getting Users collection."""
        mock_db = MagicMock()
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        handler = MongoDBHandler(mock_db)
        collection = handler.get_users_collection()
        
        assert collection == mock_collection
        mock_db.__getitem__.assert_called_with("users")

    def test_get_narrative_fragments_collection(self):
        """Test getting NarrativeFragments collection."""
        mock_db = MagicMock()
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        handler = MongoDBHandler(mock_db)
        collection = handler.get_narrative_fragments_collection()
        
        assert collection == mock_collection
        mock_db.__getitem__.assert_called_with("narrative_fragments")

    def test_get_items_collection(self):
        """Test getting Items collection."""
        mock_db = MagicMock()
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        handler = MongoDBHandler(mock_db)
        collection = handler.get_items_collection()
        
        assert collection == mock_collection
        mock_db.__getitem__.assert_called_with("items")

    @pytest.mark.asyncio
    async def test_initialize_collections_success(self):
        """Test successful collection initialization."""
        mock_db = MagicMock()
        mock_users_collection = Mock()
        mock_narrative_collection = Mock()
        mock_items_collection = Mock()
        
        # Set up mock return values for collections
        mock_db.__getitem__.side_effect = [
            mock_users_collection,
            mock_narrative_collection,
            mock_items_collection
        ]
        
        # Mock the index creation methods
        mock_users_collection.create_index = Mock()
        mock_narrative_collection.create_index = Mock()
        mock_items_collection.create_index = Mock()
        
        handler = MongoDBHandler(mock_db)
        result = await handler.initialize_collections()
        
        assert result is True
        # Users collection has 5 indexes
        assert mock_users_collection.create_index.call_count == 5
        # NarrativeFragments and Items collections have 4 indexes each
        assert mock_narrative_collection.create_index.call_count == 4
        assert mock_items_collection.create_index.call_count == 4

    @pytest.mark.asyncio
    async def test_initialize_collections_error(self):
        """Test collection initialization with error."""
        mock_db = Mock()
        handler = MongoDBHandler(mock_db)
        
        # Mock get_users_collection to raise an exception
        handler.get_users_collection = Mock(side_effect=Exception("Test error"))
        
        result = await handler.initialize_collections()
        assert result is False
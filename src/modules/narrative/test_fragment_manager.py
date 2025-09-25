"""
Test suite for NarrativeFragmentManager
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.modules.narrative.fragment_manager import NarrativeFragmentManager
from src.database.mongodb import MongoDBHandler


class TestNarrativeFragmentManager:
    
    @pytest.fixture
    def mock_db_handler(self):
        """Create a mock database handler for testing"""
        mock_db = AsyncMock(spec=MongoDBHandler)
        mock_db.get_narrative_fragment = AsyncMock()
        mock_db.get_user = AsyncMock()
        mock_db.update_user = AsyncMock()
        mock_db.create_user = AsyncMock()
        mock_db.push_to_user_array = AsyncMock()
        mock_db.increment_user_stat = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def fragment_manager(self, mock_db_handler):
        """Create a NarrativeFragmentManager instance for testing"""
        return NarrativeFragmentManager(mock_db_handler)
    
    @pytest.mark.asyncio
    async def test_get_fragment_success(self, fragment_manager, mock_db_handler):
        """Test successful retrieval of a narrative fragment"""
        expected_fragment = {
            "fragment_id": "test_fragment",
            "content": "Test content",
            "choices": ["choice1", "choice2"]
        }
        mock_db_handler.get_narrative_fragment.return_value = expected_fragment
        
        result = await fragment_manager.get_fragment("test_fragment")
        
        assert result == expected_fragment
        mock_db_handler.get_narrative_fragment.assert_called_once_with("test_fragment")
    
    @pytest.mark.asyncio
    async def test_get_fragment_not_found(self, fragment_manager, mock_db_handler):
        """Test retrieval of a non-existent narrative fragment"""
        mock_db_handler.get_narrative_fragment.return_value = None
        
        result = await fragment_manager.get_fragment("nonexistent")
        
        assert result is None
        mock_db_handler.get_narrative_fragment.assert_called_once_with("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_user_progress_success(self, fragment_manager, mock_db_handler):
        """Test successful retrieval of user progress"""
        expected_user = {
            "user_id": "test_user",
            "narrative_progress": {
                "current_fragment": "fragment_1",
                "completed_fragments": ["fragment_0"],
                "unlocked_hints": []
            }
        }
        mock_db_handler.get_user.return_value = expected_user
        
        result = await fragment_manager.get_user_progress("test_user")
        
        assert result == expected_user
        mock_db_handler.get_user.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_get_user_progress_not_found_create_default(self, fragment_manager, mock_db_handler):
        """Test retrieval of user progress when user doesn't exist (creates default)"""
        mock_db_handler.get_user.return_value = None
        mock_db_handler.create_user.return_value = True
        
        result = await fragment_manager.get_user_progress("new_user")
        
        assert result is not None
        assert "user_id" in result
        assert "narrative_progress" in result
        mock_db_handler.get_user.assert_called_once_with("new_user")
        mock_db_handler.create_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_progress_success(self, fragment_manager, mock_db_handler):
        """Test successful update of user progress"""
        progress_update = {
            "current_fragment": "fragment_2",
            "completed_fragments": ["fragment_0", "fragment_1"]
        }
        mock_db_handler.update_user.return_value = True
        
        result = await fragment_manager.update_progress("test_user", progress_update)
        
        assert result is True
        mock_db_handler.update_user.assert_called_once()
        # Verify the update data includes the progress and timestamp
        call_args = mock_db_handler.update_user.call_args
        assert "narrative_progress" in call_args[0][1]
        assert "updated_at" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_append_to_completed_fragments_success(self, fragment_manager, mock_db_handler):
        """Test successful appending to completed fragments"""
        mock_db_handler.push_to_user_array.return_value = True
        
        result = await fragment_manager.append_to_completed_fragments("test_user", "fragment_1")
        
        assert result is True
        mock_db_handler.push_to_user_array.assert_called_once_with(
            "test_user", 
            "narrative_progress.completed_fragments", 
            "fragment_1"
        )


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__])
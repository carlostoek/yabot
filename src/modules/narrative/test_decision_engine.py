"""
Tests for Decision Engine in src/modules/narrative/decision_engine.py

This test suite validates the implementation of requirements 1.2, 1.5, 4.4
from the modulos-atomicos specification for the narrative decision engine.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.modules.narrative.decision_engine import DecisionEngine, DecisionResult, NarrativeFragmentManager
from src.events.models import DecisionMadeEvent


@pytest.fixture
def mock_fragment_manager():
    """Mock fragment manager for testing"""
    manager = Mock(spec=NarrativeFragmentManager)
    manager.get_fragment = AsyncMock()
    return manager


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing"""
    bus = Mock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def decision_engine(mock_fragment_manager, mock_event_bus):
    """Create decision engine instance with mocked dependencies"""
    return DecisionEngine(
        event_bus=mock_event_bus,
        fragment_manager=mock_fragment_manager
    )


class TestDecisionEngine:
    """Test cases for the DecisionEngine class"""
    
    @pytest.mark.asyncio
    async def test_validate_choice_valid_choice(self, decision_engine, mock_fragment_manager):
        """Test validating a valid choice based on current fragment"""
        # Setup
        user_id = "test_user_123"
        fragment_id = "fragment_001"
        choice_id = "choice_001"
        
        mock_fragment_manager.get_fragment.return_value = {
            "fragment_id": fragment_id,
            "choices": [
                {"choice_id": choice_id, "text": "Go left", "next_fragment_id": "fragment_002"}
            ]
        }
        
        # Mock the database methods on the fragment manager
        mock_fragment_manager.db = Mock()
        mock_fragment_manager.db.get_user = AsyncMock(return_value={"user_id": user_id, "vip_status": False})
        
        # Execute
        result = await decision_engine.validate_choice(user_id, fragment_id, choice_id)
        
        # Assert
        assert result is True
        mock_fragment_manager.get_fragment.assert_called_once_with(fragment_id)
    
    @pytest.mark.asyncio
    async def test_validate_choice_invalid_choice(self, decision_engine, mock_fragment_manager):
        """Test validating an invalid choice"""
        # Setup
        user_id = "test_user_123"
        fragment_id = "fragment_001"
        choice_id = "invalid_choice"
        
        mock_fragment_manager.get_fragment.return_value = {
            "fragment_id": fragment_id,
            "choices": [
                {"choice_id": "choice_001", "text": "Go left", "next_fragment_id": "fragment_002"}
            ]
        }
        
        # Execute
        result = await decision_engine.validate_choice(user_id, fragment_id, choice_id)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_choice_vip_required(self, decision_engine, mock_fragment_manager):
        """Test validating a choice that requires VIP status"""
        # Setup
        user_id = "test_user_123"
        fragment_id = "fragment_001"
        choice_id = "vip_choice"
        
        mock_fragment_manager.get_fragment.return_value = {
            "fragment_id": fragment_id,
            "choices": [
                {
                    "choice_id": choice_id, 
                    "text": "VIP exclusive", 
                    "next_fragment_id": "vip_fragment",
                    "conditions": {"vip_required": True}
                }
            ]
        }
        
        # Mock the database methods on the fragment manager
        mock_fragment_manager.db = Mock()
        mock_fragment_manager.db.get_user = AsyncMock(return_value={"user_id": user_id, "vip_status": False})
        
        # Execute
        result = await decision_engine.validate_choice(user_id, fragment_id, choice_id)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_decision_success(self, decision_engine, mock_fragment_manager, mock_event_bus):
        """Test processing a valid decision successfully"""
        # Setup
        user_id = "test_user_123"
        fragment_id = "fragment_001"
        choice_id = "choice_001"
        
        mock_fragment_manager.get_fragment.return_value = {
            "fragment_id": fragment_id,
            "choices": [
                {"choice_id": choice_id, "text": "Go left", "next_fragment_id": "fragment_002"}
            ]
        }
        
        # Mock the database methods on the fragment manager
        mock_fragment_manager.db = Mock()
        mock_fragment_manager.db.get_user = AsyncMock(return_value={
            "user_id": user_id, 
            "vip_status": False,
            "narrative_progress": {"current_fragment": fragment_id}
        })
        mock_fragment_manager.db.update_user = AsyncMock(return_value=True)
        mock_fragment_manager.append_to_completed_fragments = AsyncMock(return_value=True)
        
        # Execute
        result = await decision_engine.process_decision(user_id, fragment_id, choice_id)
        
        # Assert
        assert result.success is True
        assert result.next_fragment_id == "fragment_002"
        assert result.error is None
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "decision_made"
        assert isinstance(call_args[0][1], DecisionMadeEvent)
        
        # Verify update operations were called
        mock_fragment_manager.db.update_user.assert_called()
        mock_fragment_manager.append_to_completed_fragments.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_decision_invalid_choice(self, decision_engine):
        """Test processing an invalid decision"""
        # Setup
        user_id = "test_user_123"
        fragment_id = "fragment_001"
        choice_id = "invalid_choice"
        
        # Execute
        result = await decision_engine.process_decision(user_id, fragment_id, choice_id)
        
        # Assert
        assert result.success is False
        assert result.next_fragment_id is None
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_process_decision_fragment_not_found(self, decision_engine, mock_fragment_manager):
        """Test processing a decision for a non-existent fragment"""
        # Setup
        user_id = "test_user_123"
        fragment_id = "nonexistent_fragment"
        choice_id = "choice_001"
        
        mock_fragment_manager.get_fragment.return_value = None
        
        # Execute
        result = await decision_engine.process_decision(user_id, fragment_id, choice_id)
        
        # Assert - when fragment doesn't exist, validate_choice will return false first
        assert result.success is False
        assert result.next_fragment_id is None
        assert "invalid choice" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_progression_conditions_vip_required(self, decision_engine, mock_fragment_manager):
        """Test progression validation with VIP requirement"""
        # Setup
        user_id = "test_user_123"
        current_fragment_id = "fragment_001"
        choice_id = "choice_001"
        next_fragment_id = "vip_fragment"
        
        mock_fragment_manager.get_fragment.return_value = {
            "fragment_id": next_fragment_id,
            "vip_required": True
        }
        
        # Mock the database methods on the fragment manager
        mock_fragment_manager.db = Mock()
        mock_fragment_manager.db.get_user = AsyncMock(return_value={"user_id": user_id, "vip_status": False})
        
        # Execute
        result = await decision_engine._validate_progression_conditions(
            user_id, current_fragment_id, choice_id, next_fragment_id
        )
        
        # Assert
        assert result["valid"] is False
        assert "VIP" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_available_choices(self, decision_engine, mock_fragment_manager):
        """Test getting available choices for a user"""
        # Setup
        user_id = "test_user_123"
        fragment_id = "fragment_001"
        
        mock_fragment_manager.get_fragment.return_value = {
            "fragment_id": fragment_id,
            "choices": [
                {"choice_id": "choice_1", "text": "Normal choice", "next_fragment_id": "fragment_002"},
                {
                    "choice_id": "choice_2", 
                    "text": "VIP choice", 
                    "next_fragment_id": "vip_fragment",
                    "conditions": {"vip_required": True}
                }
            ]
        }
        
        # Mock the database methods on the fragment manager
        mock_fragment_manager.db = Mock()
        mock_fragment_manager.db.get_user = AsyncMock(return_value={"user_id": user_id, "vip_status": False})
        
        # Execute
        choices = await decision_engine.get_available_choices(user_id, fragment_id)
        
        # Assert
        assert len(choices) == 1  # Only non-VIP choice should be available
        assert choices[0].choice_id == "choice_1"
    
    @pytest.mark.asyncio
    async def test_rollback_decision_placeholder(self, decision_engine):
        """Test rollback decision (placeholder implementation)"""
        # Setup
        user_id = "test_user_123"
        decision_id = "decision_001"
        
        # Execute
        result = await decision_engine.rollback_decision(user_id, decision_id)
        
        # Assert - just testing the placeholder implementation works
        assert result is True  # Placeholder returns True
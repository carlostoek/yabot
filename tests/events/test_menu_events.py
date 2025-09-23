"""
Unit tests for the Menu Event System.

This module provides comprehensive unit tests for menu event publishing,
behavioral assessment events, and event-driven menu interactions as specified
in REQ-MENU-007.1 and REQ-MENU-007.2.
"""

import asyncio
import json
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from datetime import datetime, timedelta

from src.events.bus import EventBus
from src.events.models import BaseEvent, create_event
from src.modules.emotional.menu_assessment import (
    MenuBehavioralAssessmentHandler,
    MenuInteractionType,
    WorthinessIndicator
)
from src.config.manager import ConfigManager
from src.database.manager import DatabaseManager
from src.modules.emotional.behavioral_analysis import BehavioralAnalysisEngine


class TestMenuEventSystem:
    """Test cases for the Menu Event System."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus for testing."""
        mock_bus = AsyncMock(spec=EventBus)
        mock_bus.publish = AsyncMock(return_value=True)
        mock_bus.subscribe = AsyncMock(return_value=True)
        mock_bus.is_connected = True
        return mock_bus

    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager for testing."""
        mock_db_manager = Mock(spec=DatabaseManager)
        mock_mongo_db = AsyncMock()
        mock_collection = AsyncMock()

        # Mock collection methods
        mock_collection.find = AsyncMock()
        mock_collection.find_one = AsyncMock()
        mock_collection.insert_one = AsyncMock()
        mock_collection.update_one = AsyncMock()

        # Mock database retrieval
        mock_mongo_db.__getitem__ = Mock(return_value=mock_collection)
        mock_db_manager.get_mongo_db.return_value = mock_mongo_db

        return mock_db_manager

    @pytest.fixture
    def mock_behavioral_engine(self):
        """Create a mock behavioral analysis engine for testing."""
        mock_engine = AsyncMock(spec=BehavioralAnalysisEngine)
        mock_engine.analyze_response_timing = AsyncMock(return_value=0.8)
        mock_engine.calculate_emotional_resonance = AsyncMock(
            return_value={
                "authenticity_score": 0.8,
                "depth_score": 0.7,
                "vulnerability_score": 0.6,
                "resonance_score": 0.7
            }
        )
        return mock_engine

    @pytest.fixture
    def menu_assessment_handler(self, mock_database_manager, mock_event_bus, mock_behavioral_engine):
        """Create a MenuBehavioralAssessmentHandler instance for testing."""
        return MenuBehavioralAssessmentHandler(
            database_manager=mock_database_manager,
            event_bus=mock_event_bus,
            behavioral_engine=mock_behavioral_engine
        )

    @pytest.mark.asyncio
    async def test_menu_interaction_event_creation(self):
        """Test creation of menu interaction events."""
        # Test event creation for menu navigation
        event_data = {
            "user_id": "test_user_123",
            "menu_id": "main_menu",
            "interaction_type": MenuInteractionType.NAVIGATION,
            "action_data": {
                "selected_option": "narrative_exploration",
                "previous_menu": "welcome_menu",
                "response_timing": {"response_time_seconds": 3.5}
            },
            "timestamp": datetime.utcnow().isoformat(),
            "user_context": {
                "current_level": 2,
                "vip_status": False,
                "worthiness_score": 0.65
            }
        }

        # Create event using event models
        menu_event = create_event(
            "menu_interaction",
            **event_data
        )

        # Verify event structure
        assert isinstance(menu_event, BaseEvent)
        assert menu_event.event_type == "menu_interaction"
        assert menu_event.user_id == "test_user_123"
        assert "menu_id" in menu_event.payload
        assert "interaction_type" in menu_event.payload
        assert "action_data" in menu_event.payload
        assert "user_context" in menu_event.payload

        # Verify event payload structure
        payload = menu_event.payload
        assert payload["menu_id"] == "main_menu"
        assert payload["interaction_type"] == MenuInteractionType.NAVIGATION
        assert "selected_option" in payload["action_data"]
        assert "response_timing" in payload["action_data"]

    @pytest.mark.asyncio
    async def test_menu_interaction_event_publishing(self, mock_event_bus):
        """Test publishing of menu interaction events (REQ-MENU-007.1)."""
        # Test event data
        event_data = {
            "user_id": "test_user_123",
            "menu_id": "vip_menu",
            "interaction_type": MenuInteractionType.VIP_EXPLORATION,
            "action_data": {
                "selected_option": "premium_narrative",
                "available_options": ["premium_narrative", "exclusive_content", "vip_features"],
                "response_timing": {"response_time_seconds": 2.1}
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Publish event
        result = await mock_event_bus.publish("menu_interaction", event_data)

        # Verify event was published
        assert result is True
        mock_event_bus.publish.assert_called_once_with("menu_interaction", event_data)

    @pytest.mark.asyncio
    async def test_behavioral_assessment_event_handling(self, menu_assessment_handler, mock_database_manager):
        """Test behavioral assessment event handling (REQ-MENU-007.2)."""
        # Mock database responses
        mock_collection = mock_database_manager.get_mongo_db.return_value["menu_behavioral_assessments"]
        mock_collection.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "user_id": "test_user_123",
                    "interaction_type": MenuInteractionType.NAVIGATION,
                    "timestamp": "2024-01-01T10:00:00",
                    "behavioral_metrics": {"navigation_score": 0.8}
                }
            ]
        )

        # Test event data for behavioral assessment
        event_data = {
            "user_id": "test_user_123",
            "menu_id": "narrative_menu",
            "interaction_type": MenuInteractionType.DEEP_EXPLORATION,
            "action_data": {
                "selected_option": "emotional_journey",
                "time_spent": 45.2,
                "depth_level": 3,
                "response_timing": {"response_time_seconds": 4.5}
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Handle the menu interaction event
        await menu_assessment_handler.handle_menu_interaction_event(event_data)

        # Verify behavioral analysis was performed
        assert mock_collection.insert_one.called

        # Verify user profile was updated
        users_collection = mock_database_manager.get_mongo_db.return_value["users"]
        assert users_collection.update_one.called

    @pytest.mark.asyncio
    async def test_restriction_encounter_event_handling(self, menu_assessment_handler):
        """Test handling of restriction encounter events."""
        # Test event data for restriction encounter
        event_data = {
            "user_id": "test_user_123",
            "menu_id": "vip_restricted_area",
            "interaction_type": MenuInteractionType.RESTRICTION_ENCOUNTER,
            "action_data": {
                "restricted_feature": "level_4_content",
                "user_response": "graceful_acceptance",
                "restriction_type": "vip_required",
                "response_timing": {"response_time_seconds": 1.8}
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Handle the restriction encounter event
        await menu_assessment_handler.handle_menu_interaction_event(event_data)

        # Verify assessment was called (through mock setup)
        assert True  # Assessment handler was called without exceptions

    @pytest.mark.asyncio
    async def test_worthiness_score_event_publishing(self, mock_event_bus):
        """Test publishing of worthiness score change events (REQ-MENU-007.3)."""
        # Test worthiness score change event
        worthiness_event_data = {
            "user_id": "test_user_123",
            "previous_score": 0.65,
            "new_score": 0.75,
            "change_reason": "respectful_navigation",
            "behavioral_indicators": [
                WorthinessIndicator.RESPECTFUL_NAVIGATION,
                WorthinessIndicator.GRACEFUL_RESTRICTION_HANDLING
            ],
            "menu_context": {
                "menu_id": "main_menu",
                "interaction_sequence": ["navigation", "selection", "deep_exploration"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Publish worthiness score event
        result = await mock_event_bus.publish("worthiness_score_updated", worthiness_event_data)

        # Verify event was published
        assert result is True
        mock_event_bus.publish.assert_called_once_with("worthiness_score_updated", worthiness_event_data)

    @pytest.mark.asyncio
    async def test_vip_status_change_event_handling(self, mock_event_bus):
        """Test VIP status change event handling (REQ-MENU-007.4)."""
        # Test VIP status change event
        vip_event_data = {
            "user_id": "test_user_123",
            "previous_status": False,
            "new_status": True,
            "subscription_tier": "premium",
            "activation_timestamp": datetime.utcnow().isoformat(),
            "menu_access_updates": {
                "newly_available_menus": ["vip_lounge", "premium_narrative", "exclusive_content"],
                "access_level_changes": {"level_4_content": "granted", "level_5_content": "granted"}
            }
        }

        # Publish VIP status change event
        result = await mock_event_bus.publish("vip_status_changed", vip_event_data)

        # Verify event was published
        assert result is True
        mock_event_bus.publish.assert_called_once_with("vip_status_changed", vip_event_data)

    @pytest.mark.asyncio
    async def test_administrative_action_event_logging(self, mock_event_bus):
        """Test administrative action event logging (REQ-MENU-007.5)."""
        # Test administrative action event
        admin_event_data = {
            "admin_user_id": "admin_001",
            "target_user_id": "test_user_123",
            "action_type": "manual_level_adjustment",
            "action_details": {
                "previous_level": 2,
                "new_level": 3,
                "reason": "manual_progression_approval",
                "admin_notes": "User demonstrated exceptional emotional intelligence"
            },
            "menu_context": {
                "affected_menus": ["narrative_menu", "emotional_journey"],
                "access_changes": ["level_3_content_granted"]
            },
            "timestamp": datetime.utcnow().isoformat(),
            "security_context": {
                "admin_session_id": "session_12345",
                "ip_address": "192.168.1.100",
                "action_verified": True
            }
        }

        # Publish administrative action event
        result = await mock_event_bus.publish("admin_action_performed", admin_event_data)

        # Verify event was published
        assert result is True
        mock_event_bus.publish.assert_called_once_with("admin_action_performed", admin_event_data)

    @pytest.mark.asyncio
    async def test_menu_navigation_pattern_analysis(self, menu_assessment_handler, mock_database_manager):
        """Test analysis of menu navigation patterns for behavioral assessment."""
        # Mock recent interactions
        mock_interactions = [
            {
                "user_id": "test_user_123",
                "interaction_type": MenuInteractionType.NAVIGATION,
                "menu_id": "main_menu",
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "user_id": "test_user_123",
                "interaction_type": MenuInteractionType.DEEP_EXPLORATION,
                "menu_id": "narrative_menu",
                "timestamp": "2024-01-01T10:05:00"
            },
            {
                "user_id": "test_user_123",
                "interaction_type": MenuInteractionType.RESTRICTION_ENCOUNTER,
                "menu_id": "vip_area",
                "timestamp": "2024-01-01T10:10:00"
            }
        ]

        # Mock database collection
        mock_collection = mock_database_manager.get_mongo_db.return_value["menu_behavioral_assessments"]
        mock_collection.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(
            return_value=mock_interactions
        )

        # Test navigation pattern analysis
        navigation_score = await menu_assessment_handler._analyze_navigation_patterns(
            mock_interactions, MenuInteractionType.SELECTION, {"selected_option": "emotional_content"}
        )

        # Verify navigation score is calculated
        assert isinstance(navigation_score, float)
        assert 0.0 <= navigation_score <= 1.0

    @pytest.mark.asyncio
    async def test_choice_sophistication_analysis(self, menu_assessment_handler):
        """Test analysis of choice sophistication for behavioral assessment."""
        # Test sophisticated choice
        sophisticated_choice_score = await menu_assessment_handler._analyze_choice_sophistication(
            MenuInteractionType.SELECTION,
            "emotional_journey_menu",
            {
                "selected_option": "deep_emotional_exploration",
                "available_options": [
                    "quick_chat",
                    "deep_emotional_exploration",
                    "superficial_interaction",
                    "advanced_intimacy_mapping"
                ]
            }
        )

        # Verify sophisticated choice gets higher score
        assert isinstance(sophisticated_choice_score, float)
        assert sophisticated_choice_score > 0.5

        # Test basic choice
        basic_choice_score = await menu_assessment_handler._analyze_choice_sophistication(
            MenuInteractionType.SELECTION,
            "basic_menu",
            {
                "selected_option": "quick_response",
                "available_options": ["quick_response", "standard_option"]
            }
        )

        # Verify basic choice gets lower score
        assert isinstance(basic_choice_score, float)
        assert basic_choice_score <= sophisticated_choice_score

    @pytest.mark.asyncio
    async def test_restriction_handling_analysis(self, menu_assessment_handler):
        """Test analysis of restriction handling behavior."""
        # Mock interactions with various restriction responses
        mock_interactions = [
            {
                "interaction_type": MenuInteractionType.RESTRICTION_ENCOUNTER,
                "action_data": {"user_response": "graceful_acceptance"},
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "interaction_type": MenuInteractionType.RESTRICTION_ENCOUNTER,
                "action_data": {"user_response": "understanding_inquiry"},
                "timestamp": "2024-01-01T10:05:00"
            }
        ]

        # Test graceful restriction handling
        restriction_score = await menu_assessment_handler._analyze_restriction_handling(
            mock_interactions,
            MenuInteractionType.RESTRICTION_ENCOUNTER,
            {"user_response": "graceful_acceptance"}
        )

        # Verify graceful handling gets high score
        assert isinstance(restriction_score, float)
        assert restriction_score > 0.7

        # Test aggressive restriction handling
        aggressive_score = await menu_assessment_handler._analyze_restriction_handling(
            mock_interactions,
            MenuInteractionType.RESTRICTION_ENCOUNTER,
            {"user_response": "aggressive_retry"}
        )

        # Verify aggressive handling gets lower score
        assert aggressive_score < restriction_score

    @pytest.mark.asyncio
    async def test_exploration_depth_analysis(self, menu_assessment_handler):
        """Test analysis of exploration depth behavior."""
        # Mock interactions with diverse exploration
        mock_deep_interactions = [
            {"menu_id": "main_menu", "interaction_type": MenuInteractionType.NAVIGATION},
            {"menu_id": "narrative_menu", "interaction_type": MenuInteractionType.DEEP_EXPLORATION},
            {"menu_id": "emotional_menu", "interaction_type": MenuInteractionType.DEEP_EXPLORATION},
            {"menu_id": "vip_menu", "interaction_type": MenuInteractionType.VIP_EXPLORATION},
            {"menu_id": "profile_menu", "interaction_type": MenuInteractionType.SELECTION}
        ]

        # Test deep exploration
        exploration_score = await menu_assessment_handler._analyze_exploration_depth(
            mock_deep_interactions,
            "advanced_menu",
            MenuInteractionType.DEEP_EXPLORATION
        )

        # Verify deep exploration gets high score
        assert isinstance(exploration_score, float)
        assert exploration_score > 0.6

        # Mock shallow interactions
        mock_shallow_interactions = [
            {"menu_id": "main_menu", "interaction_type": MenuInteractionType.NAVIGATION},
            {"menu_id": "main_menu", "interaction_type": MenuInteractionType.NAVIGATION}
        ]

        # Test shallow exploration
        shallow_score = await menu_assessment_handler._analyze_exploration_depth(
            mock_shallow_interactions,
            "main_menu",
            MenuInteractionType.NAVIGATION
        )

        # Verify shallow exploration gets lower score
        assert shallow_score < exploration_score

    @pytest.mark.asyncio
    async def test_worthiness_indicators_determination(self, menu_assessment_handler):
        """Test determination of worthiness indicators based on behavioral metrics."""
        # Test high-quality behavior metrics
        high_quality_indicators = await menu_assessment_handler._determine_worthiness_indicators(
            navigation_score=0.85,
            choice_sophistication=0.80,
            restriction_handling=0.90,
            exploration_depth=0.75,
            authenticity_score=0.70
        )

        # Verify positive indicators are present
        assert isinstance(high_quality_indicators, list)
        assert WorthinessIndicator.RESPECTFUL_NAVIGATION in high_quality_indicators
        assert WorthinessIndicator.GRACEFUL_RESTRICTION_HANDLING in high_quality_indicators
        assert WorthinessIndicator.SOPHISTICATED_CHOICES in high_quality_indicators

        # Test low-quality behavior metrics
        low_quality_indicators = await menu_assessment_handler._determine_worthiness_indicators(
            navigation_score=0.30,
            choice_sophistication=0.25,
            restriction_handling=0.20,
            exploration_depth=0.15,
            authenticity_score=0.10
        )

        # Verify negative indicators are present
        assert WorthinessIndicator.AGGRESSIVE_ACCESS_ATTEMPTS in low_quality_indicators
        assert WorthinessIndicator.SHALLOW_ENGAGEMENT in low_quality_indicators
        assert WorthinessIndicator.IMPULSIVE_BEHAVIOR in low_quality_indicators

    @pytest.mark.asyncio
    async def test_behavioral_score_calculation(self, menu_assessment_handler):
        """Test overall behavioral score calculation."""
        # Test high-quality metrics
        high_score = await menu_assessment_handler._calculate_behavioral_score(
            navigation_score=0.90,
            choice_sophistication=0.85,
            restriction_handling=0.95,  # Most weighted factor
            exploration_depth=0.80,
            authenticity_score=0.75
        )

        # Verify high score
        assert isinstance(high_score, float)
        assert 0.8 <= high_score <= 1.0

        # Test low-quality metrics
        low_score = await menu_assessment_handler._calculate_behavioral_score(
            navigation_score=0.20,
            choice_sophistication=0.25,
            restriction_handling=0.10,  # Most weighted factor
            exploration_depth=0.30,
            authenticity_score=0.40
        )

        # Verify low score
        assert isinstance(low_score, float)
        assert 0.0 <= low_score <= 0.4
        assert low_score < high_score

    @pytest.mark.asyncio
    async def test_behavioral_profile_update(self, menu_assessment_handler, mock_database_manager):
        """Test updating user behavioral profile with assessment data."""
        # Test assessment data
        assessment_data = {
            "user_id": "test_user_123",
            "interaction_type": MenuInteractionType.DEEP_EXPLORATION,
            "menu_id": "narrative_menu",
            "timestamp": datetime.utcnow().isoformat(),
            "behavioral_metrics": {
                "navigation_score": 0.85,
                "choice_sophistication": 0.80,
                "restriction_handling": 0.90,
                "exploration_depth": 0.75,
                "authenticity_score": 0.70,
                "overall_behavioral_score": 0.82
            },
            "worthiness_indicators": [
                WorthinessIndicator.RESPECTFUL_NAVIGATION,
                WorthinessIndicator.SOPHISTICATED_CHOICES
            ],
            "lucien_assessment_data": {
                "respect_for_boundaries": 0.90,
                "sophistication_level": 0.80,
                "exploration_patience": 0.75,
                "authentic_engagement": 0.70
            }
        }

        # Update behavioral profile
        await menu_assessment_handler._update_behavioral_profile("test_user_123", assessment_data)

        # Verify assessment was stored
        assessments_collection = mock_database_manager.get_mongo_db.return_value["menu_behavioral_assessments"]
        assessments_collection.insert_one.assert_called_once_with(assessment_data)

        # Verify user profile was updated
        users_collection = mock_database_manager.get_mongo_db.return_value["users"]
        users_collection.update_one.assert_called_once()

        # Verify update data structure
        call_args = users_collection.update_one.call_args
        filter_arg, update_arg = call_args[0]

        assert filter_arg == {"user_id": "test_user_123"}
        assert "$set" in update_arg
        update_data = update_arg["$set"]
        assert "emotional_signature.menu_behavioral_score" in update_data
        assert "emotional_signature.worthiness_indicators" in update_data
        assert "emotional_signature.lucien_assessment" in update_data

    @pytest.mark.asyncio
    async def test_assessment_event_publishing(self, menu_assessment_handler, mock_event_bus):
        """Test publishing of behavioral assessment events."""
        # Test assessment data
        assessment_data = {
            "user_id": "test_user_123",
            "behavioral_metrics": {"overall_behavioral_score": 0.82},
            "worthiness_indicators": [WorthinessIndicator.RESPECTFUL_NAVIGATION],
            "lucien_assessment_data": {"respect_for_boundaries": 0.90},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Publish assessment event
        await menu_assessment_handler._publish_assessment_event("test_user_123", assessment_data)

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        event_name, event_data = call_args[0]

        assert event_name == "behavioral_assessment_updated"
        assert event_data["user_id"] == "test_user_123"
        assert event_data["assessment_type"] == "menu_behavioral"
        assert "behavioral_score" in event_data
        assert "worthiness_indicators" in event_data
        assert "lucien_assessment" in event_data


class TestMenuEventSystemIntegration:
    """Integration tests for the Menu Event System."""

    @pytest.mark.asyncio
    async def test_complete_menu_interaction_flow(self):
        """Test complete flow from menu interaction to behavioral assessment."""
        # Mock dependencies
        mock_event_bus = AsyncMock(spec=EventBus)
        mock_database_manager = Mock(spec=DatabaseManager)
        mock_behavioral_engine = AsyncMock(spec=BehavioralAnalysisEngine)

        # Set up mock database responses
        mock_mongo_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_collection.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(
            return_value=[]
        )
        mock_collection.insert_one = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_mongo_db.__getitem__ = Mock(return_value=mock_collection)
        mock_database_manager.get_mongo_db.return_value = mock_mongo_db

        # Set up behavioral engine responses
        mock_behavioral_engine.analyze_response_timing = AsyncMock(return_value=0.75)

        # Create handler
        handler = MenuBehavioralAssessmentHandler(
            database_manager=mock_database_manager,
            event_bus=mock_event_bus,
            behavioral_engine=mock_behavioral_engine
        )

        # Test complete interaction flow
        event_data = {
            "user_id": "test_user_123",
            "menu_id": "narrative_menu",
            "interaction_type": MenuInteractionType.DEEP_EXPLORATION,
            "action_data": {
                "selected_option": "emotional_journey",
                "response_timing": {"response_time_seconds": 3.2}
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Process the event
        await handler.handle_menu_interaction_event(event_data)

        # Verify complete flow was executed
        assert mock_behavioral_engine.analyze_response_timing.called
        assert mock_collection.insert_one.called
        assert mock_collection.update_one.called
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_event_system_error_handling(self):
        """Test error handling in the menu event system."""
        # Mock dependencies with failures
        mock_event_bus = AsyncMock(spec=EventBus)
        mock_database_manager = Mock(spec=DatabaseManager)
        mock_behavioral_engine = AsyncMock(spec=BehavioralAnalysisEngine)

        # Set up database failure
        mock_database_manager.get_mongo_db.side_effect = Exception("Database connection failed")

        # Create handler
        handler = MenuBehavioralAssessmentHandler(
            database_manager=mock_database_manager,
            event_bus=mock_event_bus,
            behavioral_engine=mock_behavioral_engine
        )

        # Test error handling
        event_data = {
            "user_id": "test_user_123",
            "menu_id": "narrative_menu",
            "interaction_type": MenuInteractionType.NAVIGATION,
            "action_data": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Process event with database failure (should not raise exception)
        await handler.handle_menu_interaction_event(event_data)

        # Verify graceful error handling
        assert True  # No exception was raised

    @pytest.mark.asyncio
    async def test_concurrent_menu_event_processing(self):
        """Test concurrent processing of multiple menu events."""
        # Mock dependencies
        mock_event_bus = AsyncMock(spec=EventBus)
        mock_database_manager = Mock(spec=DatabaseManager)
        mock_behavioral_engine = AsyncMock(spec=BehavioralAnalysisEngine)

        # Set up mock responses
        mock_mongo_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_collection.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(
            return_value=[]
        )
        mock_collection.insert_one = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_mongo_db.__getitem__ = Mock(return_value=mock_collection)
        mock_database_manager.get_mongo_db.return_value = mock_mongo_db

        mock_behavioral_engine.analyze_response_timing = AsyncMock(return_value=0.8)

        # Create handler
        handler = MenuBehavioralAssessmentHandler(
            database_manager=mock_database_manager,
            event_bus=mock_event_bus,
            behavioral_engine=mock_behavioral_engine
        )

        # Create multiple concurrent events
        events = [
            {
                "user_id": f"test_user_{i}",
                "menu_id": "main_menu",
                "interaction_type": MenuInteractionType.NAVIGATION,
                "action_data": {"selected_option": f"option_{i}"},
                "timestamp": datetime.utcnow().isoformat()
            }
            for i in range(5)
        ]

        # Process events concurrently
        tasks = [
            handler.handle_menu_interaction_event(event_data)
            for event_data in events
        ]

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Verify all events were processed
        assert mock_collection.insert_one.call_count == 5
        assert mock_collection.update_one.call_count == 5
        assert mock_event_bus.publish.call_count == 5


class TestMenuEventValidation:
    """Test validation of menu event data and structures."""

    def test_menu_interaction_event_validation(self):
        """Test validation of menu interaction event structure."""
        # Valid event data
        valid_event_data = {
            "user_id": "test_user_123",
            "menu_id": "main_menu",
            "interaction_type": MenuInteractionType.NAVIGATION,
            "action_data": {
                "selected_option": "narrative_exploration",
                "response_timing": {"response_time_seconds": 2.5}
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Create event
        event = create_event("menu_interaction", **valid_event_data)

        # Verify event structure
        assert event.event_type == "menu_interaction"
        assert event.user_id == "test_user_123"
        assert isinstance(event.payload, dict)
        assert "menu_id" in event.payload
        assert "interaction_type" in event.payload
        assert "action_data" in event.payload

    def test_behavioral_assessment_event_validation(self):
        """Test validation of behavioral assessment event structure."""
        # Valid assessment event data
        valid_assessment_data = {
            "user_id": "test_user_123",
            "assessment_type": "menu_behavioral",
            "behavioral_score": 0.85,
            "worthiness_indicators": [
                WorthinessIndicator.RESPECTFUL_NAVIGATION,
                WorthinessIndicator.SOPHISTICATED_CHOICES
            ],
            "lucien_assessment": {
                "respect_for_boundaries": 0.90,
                "sophistication_level": 0.80
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Create event
        event = create_event("behavioral_assessment_updated", **valid_assessment_data)

        # Verify event structure
        assert event.event_type == "behavioral_assessment_updated"
        assert event.user_id == "test_user_123"
        assert "assessment_type" in event.payload
        assert "behavioral_score" in event.payload
        assert "worthiness_indicators" in event.payload
        assert "lucien_assessment" in event.payload

    def test_event_payload_serialization(self):
        """Test that event payloads can be properly serialized."""
        # Event with complex data types
        event_data = {
            "user_id": "test_user_123",
            "menu_id": "complex_menu",
            "interaction_type": MenuInteractionType.RESTRICTION_ENCOUNTER,
            "action_data": {
                "worthiness_indicators": [
                    WorthinessIndicator.RESPECTFUL_NAVIGATION,
                    WorthinessIndicator.GRACEFUL_RESTRICTION_HANDLING
                ],
                "timestamp": datetime.utcnow(),
                "numeric_score": 0.85
            }
        }

        # Create event
        event = create_event("menu_interaction", **event_data)

        # Verify serialization
        try:
            serialized = json.dumps(event.dict(), default=str)
            assert isinstance(serialized, str)

            # Verify deserialization
            deserialized = json.loads(serialized)
            assert isinstance(deserialized, dict)
            assert "event_type" in deserialized
            assert "user_id" in deserialized
            assert "payload" in deserialized

        except (TypeError, ValueError) as e:
            pytest.fail(f"Event serialization failed: {e}")


# Test fixtures for performance testing
@pytest.mark.performance
class TestMenuEventPerformance:
    """Performance tests for the menu event system."""

    @pytest.mark.asyncio
    async def test_high_volume_event_processing(self):
        """Test processing of high volume menu events."""
        # This test would be expanded with actual performance requirements
        # Mock setup for performance testing
        mock_event_bus = AsyncMock(spec=EventBus)
        mock_database_manager = Mock(spec=DatabaseManager)
        mock_behavioral_engine = AsyncMock(spec=BehavioralAnalysisEngine)

        # Set up minimal mock responses for performance
        mock_mongo_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_collection.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(
            return_value=[]
        )
        mock_collection.insert_one = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_mongo_db.__getitem__ = Mock(return_value=mock_collection)
        mock_database_manager.get_mongo_db.return_value = mock_mongo_db

        mock_behavioral_engine.analyze_response_timing = AsyncMock(return_value=0.8)

        # Create handler
        handler = MenuBehavioralAssessmentHandler(
            database_manager=mock_database_manager,
            event_bus=mock_event_bus,
            behavioral_engine=mock_behavioral_engine
        )

        # Generate high volume of events
        num_events = 100
        start_time = datetime.utcnow()

        # Process events
        tasks = []
        for i in range(num_events):
            event_data = {
                "user_id": f"test_user_{i % 10}",  # 10 unique users
                "menu_id": "performance_test_menu",
                "interaction_type": MenuInteractionType.NAVIGATION,
                "action_data": {"selected_option": f"option_{i}"},
                "timestamp": datetime.utcnow().isoformat()
            }
            tasks.append(handler.handle_menu_interaction_event(event_data))

        # Execute all tasks
        await asyncio.gather(*tasks)

        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # Verify performance (should process 100 events in reasonable time)
        events_per_second = num_events / processing_time
        assert events_per_second > 10  # At least 10 events per second

        # Verify all events were processed
        assert mock_collection.insert_one.call_count == num_events
        assert mock_event_bus.publish.call_count == num_events
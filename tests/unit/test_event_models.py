"""
Unit tests for the event models.
"""

import pytest
import uuid
from datetime import datetime
from src.events.models import (
    BaseEvent,
    UserInteractionEvent,
    ReactionDetectedEvent,
    DecisionMadeEvent,
    SubscriptionUpdatedEvent,
    BesitosAwardedEvent,
    NarrativeHintUnlockedEvent,
    VipAccessGrantedEvent,
    UserDeletedEvent,
    UpdateReceivedEvent,
    create_event,
    EVENT_MODELS
)


class TestEventModels:
    """Test cases for event models."""

    def test_base_event_creation(self):
        """Test BaseEvent creation with all required fields."""
        event_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        event = BaseEvent(
            event_id=event_id,
            event_type="test_event",
            timestamp=timestamp,
            correlation_id=correlation_id,
            user_id="12345",
            payload={"key": "value"}
        )
        
        assert event.event_id == event_id
        assert event.event_type == "test_event"
        assert event.timestamp == timestamp
        assert event.correlation_id == correlation_id
        assert event.user_id == "12345"
        assert event.payload == {"key": "value"}

    def test_base_event_defaults(self):
        """Test BaseEvent creation with default values."""
        event_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        event = BaseEvent(
            event_id=event_id,
            event_type="test_event",
            timestamp=timestamp,
            correlation_id=correlation_id
        )
        
        assert event.user_id is None
        assert event.payload == {}

    def test_user_interaction_event(self):
        """Test UserInteractionEvent model."""
        event = UserInteractionEvent(
            event_id=str(uuid.uuid4()),
            event_type="user_interaction",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            action="start",
            context={"source": "telegram"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "user_interaction"
        assert event.action == "start"
        assert event.context == {"source": "telegram"}

    def test_reaction_detected_event(self):
        """Test ReactionDetectedEvent model."""
        event = ReactionDetectedEvent(
            event_id=str(uuid.uuid4()),
            event_type="reaction_detected",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            content_id="content_001",
            reaction_type="like",
            metadata={"source": "telegram"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "reaction_detected"
        assert event.content_id == "content_001"
        assert event.reaction_type == "like"
        assert event.metadata == {"source": "telegram"}

    def test_decision_made_event(self):
        """Test DecisionMadeEvent model."""
        event = DecisionMadeEvent(
            event_id=str(uuid.uuid4()),
            event_type="decision_made",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            choice_id="choice_a",
            context={"fragment": "fragment_001"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "decision_made"
        assert event.choice_id == "choice_a"
        assert event.context == {"fragment": "fragment_001"}

    def test_subscription_updated_event(self):
        """Test SubscriptionUpdatedEvent model."""
        start_date = datetime.utcnow()
        end_date = datetime.utcnow()
        
        event = SubscriptionUpdatedEvent(
            event_id=str(uuid.uuid4()),
            event_type="subscription_updated",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date=start_date,
            end_date=end_date
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "subscription_updated"
        assert event.plan_type == "premium"
        assert event.status == "active"
        assert event.start_date == start_date
        assert event.end_date == end_date

    def test_besitos_awarded_event(self):
        """Test BesitosAwardedEvent model."""
        event = BesitosAwardedEvent(
            event_id=str(uuid.uuid4()),
            event_type="besitos_awarded",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            amount=10,
            reason="reaction_reward",
            metadata={"content_id": "content_001"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "besitos_awarded"
        assert event.amount == 10
        assert event.reason == "reaction_reward"
        assert event.metadata == {"content_id": "content_001"}

    def test_narrative_hint_unlocked_event(self):
        """Test NarrativeHintUnlockedEvent model."""
        event = NarrativeHintUnlockedEvent(
            event_id=str(uuid.uuid4()),
            event_type="narrative_hint_unlocked",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            hint_id="hint_001",
            fragment_id="fragment_001",
            metadata={"source": "besitos_award"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "narrative_hint_unlocked"
        assert event.hint_id == "hint_001"
        assert event.fragment_id == "fragment_001"
        assert event.metadata == {"source": "besitos_award"}

    def test_vip_access_granted_event(self):
        """Test VipAccessGrantedEvent model."""
        event = VipAccessGrantedEvent(
            event_id=str(uuid.uuid4()),
            event_type="vip_access_granted",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            reason="subscription_upgrade",
            metadata={"plan_type": "vip"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "vip_access_granted"
        assert event.reason == "subscription_upgrade"
        assert event.metadata == {"plan_type": "vip"}

    def test_user_deleted_event(self):
        """Test UserDeletedEvent model."""
        event = UserDeletedEvent(
            event_id=str(uuid.uuid4()),
            event_type="user_deleted",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            deletion_reason="user_request",
            metadata={"source": "telegram"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "user_deleted"
        assert event.deletion_reason == "user_request"
        assert event.metadata == {"source": "telegram"}

    def test_update_received_event(self):
        """Test UpdateReceivedEvent model."""
        event = UpdateReceivedEvent(
            event_id=str(uuid.uuid4()),
            event_type="update_received",
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid.uuid4()),
            user_id="12345",
            update_type="message",
            update_data={"text": "Hello world"},
            metadata={"source": "telegram"}
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "update_received"
        assert event.update_type == "message"
        assert event.update_data == {"text": "Hello world"}
        assert event.metadata == {"source": "telegram"}

    def test_event_models_dict(self):
        """Test EVENT_MODELS dictionary."""
        assert isinstance(EVENT_MODELS, dict)
        assert len(EVENT_MODELS) >= 9  # At least the 9 defined event types
        
        # Check that all expected event types are present
        expected_types = [
            "user_interaction",
            "reaction_detected", 
            "decision_made",
            "subscription_updated",
            "besitos_awarded",
            "narrative_hint_unlocked",
            "vip_access_granted",
            "user_deleted",
            "update_received"
        ]
        
        for event_type in expected_types:
            assert event_type in EVENT_MODELS
            assert issubclass(EVENT_MODELS[event_type], BaseEvent)

    def test_create_event_valid(self):
        """Test create_event factory function with valid event type."""
        event = create_event(
            "user_interaction",
            user_id="12345",
            action="start",
            context={"source": "telegram"}
        )
        
        assert isinstance(event, UserInteractionEvent)
        assert event.event_type == "user_interaction"
        assert event.user_id == "12345"
        assert event.action == "start"
        
        # Check that common fields are auto-generated
        assert event.event_id is not None
        assert isinstance(event.event_id, str)
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
        assert event.correlation_id is not None
        assert isinstance(event.correlation_id, str)

    def test_create_event_invalid_type(self):
        """Test create_event factory function with invalid event type."""
        with pytest.raises(ValueError, match="Unsupported event type"):
            create_event("invalid_event_type")

    def test_event_inheritance(self):
        """Test that all event models inherit from BaseEvent."""
        event_classes = [
            UserInteractionEvent,
            ReactionDetectedEvent,
            DecisionMadeEvent,
            SubscriptionUpdatedEvent,
            BesitosAwardedEvent,
            NarrativeHintUnlockedEvent,
            VipAccessGrantedEvent,
            UserDeletedEvent,
            UpdateReceivedEvent
        ]
        
        for event_class in event_classes:
            assert issubclass(event_class, BaseEvent)
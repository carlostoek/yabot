"""
Test for the event models.
"""

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


def test_base_event():
    """Test BaseEvent model."""
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


def test_user_interaction_event():
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
    
    assert event.event_type == "user_interaction"
    assert event.action == "start"
    assert event.context == {"source": "telegram"}


def test_reaction_detected_event():
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
    
    assert event.event_type == "reaction_detected"
    assert event.content_id == "content_001"
    assert event.reaction_type == "like"
    assert event.metadata == {"source": "telegram"}


def test_decision_made_event():
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
    
    assert event.event_type == "decision_made"
    assert event.choice_id == "choice_a"
    assert event.context == {"fragment": "fragment_001"}


def test_subscription_updated_event():
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
    
    assert event.event_type == "subscription_updated"
    assert event.plan_type == "premium"
    assert event.status == "active"
    assert event.start_date == start_date
    assert event.end_date == end_date


def test_besitos_awarded_event():
    """Test BesitosAwardedEvent model."""
    event = BesitosAwardedEvent(
        event_id=str(uuid.uuid4()),
        event_type="besitos_awarded",
        timestamp=datetime.utcnow(),
        correlation_id=str(uuid.uuid4()),
        user_id="12345",
        amount=10,
        reason="reaction_reward",
        source="reaction",
        balance_after=100,
        transaction_id="txn_001",
        metadata={"content_id": "content_001"}
    )
    
    assert event.event_type == "besitos_awarded"
    assert event.amount == 10
    assert event.reason == "reaction_reward"
    assert event.metadata == {"content_id": "content_001"}


def test_narrative_hint_unlocked_event():
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
    
    assert event.event_type == "narrative_hint_unlocked"
    assert event.hint_id == "hint_001"
    assert event.fragment_id == "fragment_001"
    assert event.metadata == {"source": "besitos_award"}


def test_vip_access_granted_event():
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
    
    assert event.event_type == "vip_access_granted"
    assert event.reason == "subscription_upgrade"
    assert event.metadata == {"plan_type": "vip"}


def test_user_deleted_event():
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
    
    assert event.event_type == "user_deleted"
    assert event.deletion_reason == "user_request"
    assert event.metadata == {"source": "telegram"}


def test_update_received_event():
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
    
    assert event.event_type == "update_received"
    assert event.update_type == "message"
    assert event.update_data == {"text": "Hello world"}
    assert event.metadata == {"source": "telegram"}


def test_event_models_dict():
    """Test EVENT_MODELS dictionary."""
    assert isinstance(EVENT_MODELS, dict)
    assert len(EVENT_MODELS) == 34
    
    # Check that some key models are present
    expected_types = [
        "user_interaction",
        "reaction_detected", 
        "decision_made",
        "subscription_updated",
        "besitos_awarded",
        "narrative_hint_unlocked",
        "vip_access_granted",
        "user_registered",
        "user_deleted",
        "update_received",
        "event_processing_failed"
    ]
    
    for event_type in expected_types:
        assert event_type in EVENT_MODELS


def test_create_event():
    """Test create_event factory function."""
    # Test creating a valid event
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
    
    # Test that common fields are auto-generated
    assert event.event_id is not None
    assert event.timestamp is not None
    assert event.correlation_id is not None


def test_create_event_invalid_type():
    """Test create_event with invalid event type."""
    try:
        create_event("invalid_event_type")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported event type" in str(e)


if __name__ == "__main__":
    test_base_event()
    test_user_interaction_event()
    test_reaction_detected_event()
    test_decision_made_event()
    test_subscription_updated_event()
    test_besitos_awarded_event()
    test_narrative_hint_unlocked_event()
    test_vip_access_granted_event()
    test_user_deleted_event()
    test_update_received_event()
    test_event_models_dict()
    test_create_event()
    test_create_event_invalid_type()
    print("All tests passed!")
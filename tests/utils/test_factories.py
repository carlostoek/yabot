"""
Test data factories for creating test objects.
"""

import factory
from unittest.mock import Mock
from src.core.models import CommandResponse


class MockUpdateFactory(factory.Factory):
    """Factory for creating mock Telegram updates."""
    
    class Meta:
        model = Mock
    
    message = factory.SubFactory('tests.utils.test_factories.MockMessageFactory')
    update_id = factory.Sequence(lambda n: n)
    

class MockMessageFactory(factory.Factory):
    """Factory for creating mock Telegram messages."""
    
    class Meta:
        model = Mock
    
    message_id = factory.Sequence(lambda n: n)
    text = factory.Faker('sentence')
    chat = factory.SubFactory('tests.utils.test_factories.MockChatFactory')
    from_user = factory.SubFactory('tests.utils.test_factories.MockUserFactory')


class MockChatFactory(factory.Factory):
    """Factory for creating mock Telegram chats."""
    
    class Meta:
        model = Mock
    
    id = factory.Sequence(lambda n: n)
    type = 'private'
    username = factory.Faker('user_name')


class MockUserFactory(factory.Factory):
    """Factory for creating mock Telegram users."""
    
    class Meta:
        model = Mock
    
    id = factory.Sequence(lambda n: n)
    username = factory.Faker('user_name')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_bot = False


class CommandResponseFactory(factory.Factory):
    """Factory for creating CommandResponse objects."""
    
    class Meta:
        model = CommandResponse
    
    text = factory.Faker('sentence')
    parse_mode = 'HTML'
    reply_markup = None
    disable_notification = False


class SecureTestDataFactory:
    """Factory for creating secure test data."""
    
    @staticmethod
    def create_sanitized_message(text="Test message"):
        """Create a message with sanitized content."""
        return MockMessageFactory(text=text)
    
    @staticmethod
    def create_test_user(user_id=None):
        """Create a test user with safe data."""
        return MockUserFactory(
            id=user_id or factory.Sequence(lambda n: 1000 + n),
            username=f"test_user_{factory.Faker('uuid4')}"
        )
    
    @staticmethod
    def create_test_webhook_payload():
        """Create a safe webhook payload for testing."""
        return {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": 123456,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1640995200,
                "text": "Test message"
            }
        }
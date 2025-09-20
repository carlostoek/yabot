"""
Unit tests for the besitos wallet module.
Implements tests for requirements 2.1, 2.2, and 6.5 from the modulos-atomicos specification.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from pymongo.errors import PyMongoError

from src.modules.gamification.besitos_wallet import (
    BesitosWallet,
    BesitosWalletError,
    InsufficientFundsError,
    TransactionError,
    Transaction
)
from src.database.mongodb import MongoDBHandler
from src.events.bus import EventBus
from src.database.schemas.gamification import TransactionStatus


@pytest.fixture
def mock_mongodb_handler():
    """Create a mock MongoDB handler for testing."""
    mock_handler = Mock(spec=MongoDBHandler)
    mock_handler.get_users_collection.return_value = Mock()
    mock_handler.get_besitos_transactions_collection.return_value = Mock()
    mock_handler._db = Mock()
    mock_handler._db.client = Mock()
    mock_handler._db.client.start_session = AsyncMock()
    return mock_handler


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    mock_bus = Mock(spec=EventBus)
    mock_bus.publish = AsyncMock()
    return mock_bus


@pytest.fixture
def besitos_wallet(mock_mongodb_handler, mock_event_bus):
    """Create a besitos wallet instance for testing."""
    return BesitosWallet(mock_mongodb_handler, mock_event_bus)


@pytest.fixture
def mock_session():
    """Create a mock MongoDB session for testing."""
    mock_session = Mock()
    mock_session.start_transaction.return_value = MagicMock()
    return mock_session


class TestBesitosWallet:
    """Test suite for the BesitosWallet class."""

    # Test requirement 2.1: WHEN besitos are awarded THEN the system
    # SHALL perform atomic transactions in the database and publish besitos_added events
    @pytest.mark.asyncio
    async def test_add_besitos_success(self, besitos_wallet, mock_mongodb_handler, mock_event_bus, mock_session):
        """Test successful addition of besitos to user wallet."""
        # Arrange
        user_id = "test_user_123"
        amount = 100
        reason = "Test reward"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        mock_transactions_collection = mock_mongodb_handler.get_besitos_transactions_collection.return_value
        
        # Mock user document with existing balance
        mock_users_collection.find_one.return_value = {"besitos_balance": 50}
        
        # Mock session context manager
        mock_mongodb_handler._db.client.start_session.return_value.__aenter__.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        
        # Act
        result = await besitos_wallet.add_besitos(user_id, amount, reason)

        # Assert
        assert isinstance(result, Transaction)
        assert result.user_id == user_id
        assert result.amount == amount
        assert result.balance_before == 50
        assert result.balance_after == 150
        assert result.status == TransactionStatus.COMPLETED
        
        # Check that database operations were called
        mock_users_collection.find_one.assert_called_once()
        mock_users_collection.update_one.assert_called()
        mock_transactions_collection.insert_one.assert_called_once()
        
        # Check that event was published
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_besitos_new_user(self, besitos_wallet, mock_mongodb_handler, mock_event_bus, mock_session):
        """Test adding besitos to a new user (user document doesn't exist)."""
        # Arrange
        user_id = "new_user_456"
        amount = 50
        reason = "Welcome bonus"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        mock_transactions_collection = mock_mongodb_handler.get_besitos_transactions_collection.return_value
        
        # Mock user document not found
        mock_users_collection.find_one.return_value = None
        
        # Mock session context manager
        mock_mongodb_handler._db.client.start_session.return_value.__aenter__.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        
        # Act
        result = await besitos_wallet.add_besitos(user_id, amount, reason)

        # Assert
        assert isinstance(result, Transaction)
        assert result.user_id == user_id
        assert result.amount == amount
        assert result.balance_before == 0
        assert result.balance_after == 50
        assert result.status == TransactionStatus.COMPLETED
        
        # Check that database operations were called
        mock_users_collection.find_one.assert_called_once()
        mock_users_collection.update_one.assert_called()
        mock_transactions_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_besitos_invalid_amount(self, besitos_wallet):
        """Test adding invalid amount of besitos."""
        # Arrange
        user_id = "test_user_123"
        amount = -10  # Invalid negative amount
        reason = "Test reward"

        # Act & Assert
        with pytest.raises(ValueError, match="Amount must be positive"):
            await besitos_wallet.add_besitos(user_id, amount, reason)

    @pytest.mark.asyncio
    async def test_add_besitos_database_error(self, besitos_wallet, mock_mongodb_handler, mock_session):
        """Test handling of database errors when adding besitos."""
        # Arrange
        user_id = "test_user_123"
        amount = 100
        reason = "Test reward"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        
        # Mock user document
        mock_users_collection.find_one.return_value = {"besitos_balance": 50}
        
        # Mock session context manager
        mock_mongodb_handler._db.client.start_session.return_value.__aenter__.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        
        # Mock database error
        mock_users_collection.update_one.side_effect = PyMongoError("Database error")
        
        # Act & Assert
        with pytest.raises(TransactionError):
            await besitos_wallet.add_besitos(user_id, amount, reason)

    # Test requirement 2.2: WHEN besitos are spent THEN the system
    # SHALL validate balance and publish besitos_spent events
    @pytest.mark.asyncio
    async def test_spend_besitos_success(self, besitos_wallet, mock_mongodb_handler, mock_event_bus, mock_session):
        """Test successful spending of besitos from user wallet."""
        # Arrange
        user_id = "test_user_123"
        amount = 30
        reason = "Item purchase"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        mock_transactions_collection = mock_mongodb_handler.get_besitos_transactions_collection.return_value
        
        # Mock user document with sufficient balance
        mock_users_collection.find_one.return_value = {"besitos_balance": 100}
        
        # Mock session context manager
        mock_mongodb_handler._db.client.start_session.return_value.__aenter__.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        
        # Act
        result = await besitos_wallet.spend_besitos(user_id, amount, reason)

        # Assert
        assert isinstance(result, Transaction)
        assert result.user_id == user_id
        assert result.amount == -amount  # Negative for spending
        assert result.balance_before == 100
        assert result.balance_after == 70
        assert result.status == TransactionStatus.COMPLETED
        
        # Check that database operations were called
        mock_users_collection.find_one.assert_called_once()
        mock_users_collection.update_one.assert_called()
        mock_transactions_collection.insert_one.assert_called_once()
        
        # Check that event was published
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_spend_besitos_insufficient_funds(self, besitos_wallet, mock_mongodb_handler, mock_session):
        """Test spending besitos when user has insufficient balance."""
        # Arrange
        user_id = "test_user_123"
        amount = 150  # More than available balance
        reason = "Item purchase"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        
        # Mock user document with insufficient balance
        mock_users_collection.find_one.return_value = {"besitos_balance": 100}
        
        # Mock session context manager
        mock_mongodb_handler._db.client.start_session.return_value.__aenter__.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        
        # Act & Assert
        with pytest.raises(InsufficientFundsError):
            await besitos_wallet.spend_besitos(user_id, amount, reason)

    @pytest.mark.asyncio
    async def test_spend_besitos_user_not_found(self, besitos_wallet, mock_mongodb_handler, mock_session):
        """Test spending besitos for non-existent user."""
        # Arrange
        user_id = "nonexistent_user"
        amount = 50
        reason = "Item purchase"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        
        # Mock user document not found
        mock_users_collection.find_one.return_value = None
        
        # Mock session context manager
        mock_mongodb_handler._db.client.start_session.return_value.__aenter__.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        
        # Act & Assert
        with pytest.raises(InsufficientFundsError):
            await besitos_wallet.spend_besitos(user_id, amount, reason)

    @pytest.mark.asyncio
    async def test_spend_besitos_invalid_amount(self, besitos_wallet):
        """Test spending invalid amount of besitos."""
        # Arrange
        user_id = "test_user_123"
        amount = -20  # Invalid negative amount
        reason = "Item purchase"

        # Act & Assert
        with pytest.raises(ValueError, match="Amount must be positive"):
            await besitos_wallet.spend_besitos(user_id, amount, reason)

    # Test requirement 6.5: Database transactions SHALL ensure atomicity for critical operations
    @pytest.mark.asyncio
    async def test_atomic_transaction_handling(self, besitos_wallet, mock_mongodb_handler, mock_session):
        """Test that operations use atomic transactions."""
        # Arrange
        user_id = "test_user_123"
        amount = 100
        reason = "Atomic test"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        
        # Mock user document
        mock_users_collection.find_one.return_value = {"besitos_balance": 50}
        
        # Mock session context manager correctly
        mock_mongodb_handler._db.client.start_session.return_value = AsyncMock()
        mock_mongodb_handler._db.client.start_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
        # Act
        result = await besitos_wallet.add_besitos(user_id, amount, reason)

        # Assert
        # Verify that session was properly used for atomic transaction
        mock_mongodb_handler._db.client.start_session.assert_called()
        mock_session.start_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_balance_success(self, besitos_wallet, mock_mongodb_handler):
        """Test successful retrieval of user balance."""
        # Arrange
        user_id = "test_user_123"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        
        # Mock user document with balance
        mock_users_collection.find_one.return_value = {"besitos_balance": 250}

        # Act
        balance = await besitos_wallet.get_balance(user_id)

        # Assert
        assert balance == 250
        mock_users_collection.find_one.assert_called_once_with(
            {"user_id": user_id},
            {"besitos_balance": 1}
        )

    @pytest.mark.asyncio
    async def test_get_balance_user_not_found(self, besitos_wallet, mock_mongodb_handler):
        """Test getting balance for non-existent user."""
        # Arrange
        user_id = "nonexistent_user"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        
        # Mock user document not found
        mock_users_collection.find_one.return_value = None

        # Act
        balance = await besitos_wallet.get_balance(user_id)

        # Assert
        assert balance == 0
        mock_users_collection.find_one.assert_called_once_with(
            {"user_id": user_id},
            {"besitos_balance": 1}
        )

    @pytest.mark.asyncio
    async def test_get_balance_database_error(self, besitos_wallet, mock_mongodb_handler):
        """Test handling of database errors when getting balance."""
        # Arrange
        user_id = "test_user_123"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        
        # Mock database error
        mock_users_collection.find_one.side_effect = PyMongoError("Database error")

        # Act & Assert
        with pytest.raises(BesitosWalletError):
            await besitos_wallet.get_balance(user_id)


if __name__ == "__main__":
    pytest.main([__file__])
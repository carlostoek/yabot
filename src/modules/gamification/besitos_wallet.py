"""
Besitos wallet module for the YABOT system.

This module provides atomic virtual currency transaction management for besitos,
implementing requirements 2.1, 2.2, and 6.5 from the modulos-atomicos specification.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from pymongo.collection import Collection
from pymongo.client_session import ClientSession
from pymongo.errors import PyMongoError

from src.database.mongodb import MongoDBHandler
from src.database.schemas.gamification import (
    BesitosTransaction, TransactionType, TransactionStatus
)
from src.events.bus import EventBus
from src.events.models import BesitosAwardedEvent, BesitosSpentEvent, create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BesitosWalletError(Exception):
    """Base exception for besitos wallet operations."""
    pass


class InsufficientFundsError(BesitosWalletError):
    """Exception raised when user has insufficient besitos balance."""
    pass


class TransactionError(BesitosWalletError):
    """Exception raised when transaction processing fails."""
    pass


class Transaction:
    """Represents a besitos transaction with its details and status."""

    def __init__(self, transaction_id: str, user_id: str, amount: int,
                 balance_before: int, balance_after: int, status: TransactionStatus):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.amount = amount
        self.balance_before = balance_before
        self.balance_after = balance_after
        self.status = status
        self.created_at = datetime.utcnow()


class BesitosWallet:
    """Manages virtual currency transactions with atomicity.

    This class implements atomic besitos transactions using MongoDB sessions
    and publishes appropriate events to the event bus for integration with
    the rest of the YABOT system.
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus):
        """Initialize the besitos wallet.

        Args:
            mongodb_handler: MongoDB handler for database operations
            event_bus: Event bus for publishing transaction events
        """
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.users_collection: Collection = mongodb_handler.get_users_collection()
        self.transactions_collection: Collection = mongodb_handler.get_besitos_transactions_collection()

        logger.info("BesitosWallet initialized")

    async def add_besitos(self, user_id: str, amount: int, reason: str,
                         source: str = "system", reference_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Transaction:
        """Add besitos to user's wallet with atomic transaction.

        Implements requirement 2.1: WHEN besitos are awarded THEN the system
        SHALL perform atomic transactions in the database and publish besitos_added events.

        Args:
            user_id: User ID to add besitos to
            amount: Amount of besitos to add (must be positive)
            reason: Reason for adding besitos
            source: Source of the besitos (default: "system")
            reference_id: Optional reference to related entity
            metadata: Optional additional metadata

        Returns:
            Transaction: Transaction object with details

        Raises:
            BesitosWalletError: If transaction fails
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        logger.info("Adding %d besitos to user %s for reason: %s", amount, user_id, reason)

        transaction_id = str(uuid.uuid4())
        metadata = metadata or {}

        # Start MongoDB transaction for atomicity (requirement 6.5)
        async with await self.mongodb_handler._db.client.start_session() as session:
            try:
                async with session.start_transaction():
                    # Get current user balance
                    user_doc = await self.users_collection.find_one(
                        {"user_id": user_id},
                        {"besitos_balance": 1},
                        session=session
                    )

                    if not user_doc:
                        # Create user if doesn't exist
                        balance_before = 0
                        await self.users_collection.update_one(
                            {"user_id": user_id},
                            {
                                "$setOnInsert": {
                                    "user_id": user_id,
                                    "besitos_balance": 0,
                                    "created_at": datetime.utcnow(),
                                    "updated_at": datetime.utcnow()
                                }
                            },
                            upsert=True,
                            session=session
                        )
                    else:
                        balance_before = user_doc.get("besitos_balance", 0)

                    balance_after = balance_before + amount

                    # Update user balance
                    await self.users_collection.update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "besitos_balance": balance_after,
                                "updated_at": datetime.utcnow()
                            }
                        },
                        session=session
                    )

                    # Create transaction record
                    transaction_doc = BesitosTransaction(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        type=TransactionType.AWARDED,
                        amount=amount,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        status=TransactionStatus.COMPLETED,
                        reason=reason,
                        source=source,
                        reference_id=reference_id,
                        metadata=metadata,
                        completed_at=datetime.utcnow()
                    )

                    await self.transactions_collection.insert_one(
                        transaction_doc.dict(),
                        session=session
                    )

                    # Transaction completed successfully
                    transaction = Transaction(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        amount=amount,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        status=TransactionStatus.COMPLETED
                    )

                logger.info("Successfully added %d besitos to user %s (balance: %d -> %d)",
                           amount, user_id, balance_before, balance_after)

                # Publish besitos_added event (requirement 2.1)
                await self._publish_besitos_added_event(
                    user_id, transaction_id, amount, reason, source, balance_after
                )

                return transaction

            except PyMongoError as e:
                logger.error("Database error adding besitos to user %s: %s", user_id, str(e))
                raise TransactionError(f"Failed to add besitos: {str(e)}")
            except Exception as e:
                logger.error("Unexpected error adding besitos to user %s: %s", user_id, str(e))
                raise BesitosWalletError(f"Unexpected error: {str(e)}")

    async def spend_besitos(self, user_id: str, amount: int, reason: str,
                           item_id: Optional[str] = None, reference_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Transaction:
        """Spend besitos from user's wallet with atomic transaction.

        Implements requirement 2.2: WHEN besitos are spent THEN the system
        SHALL validate balance and publish besitos_spent events.

        Args:
            user_id: User ID to spend besitos from
            amount: Amount of besitos to spend (must be positive)
            reason: Reason for spending besitos
            item_id: Optional item ID if spending on an item
            reference_id: Optional reference to related entity
            metadata: Optional additional metadata

        Returns:
            Transaction: Transaction object with details

        Raises:
            InsufficientFundsError: If user doesn't have enough besitos
            BesitosWalletError: If transaction fails
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        logger.info("Spending %d besitos from user %s for reason: %s", amount, user_id, reason)

        transaction_id = str(uuid.uuid4())
        metadata = metadata or {}

        # Start MongoDB transaction for atomicity (requirement 6.5)
        async with await self.mongodb_handler._db.client.start_session() as session:
            try:
                async with session.start_transaction():
                    # Get current user balance and validate
                    user_doc = await self.users_collection.find_one(
                        {"user_id": user_id},
                        {"besitos_balance": 1},
                        session=session
                    )

                    if not user_doc:
                        logger.warning("User %s not found for spending transaction", user_id)
                        raise InsufficientFundsError(f"User {user_id} not found")

                    balance_before = user_doc.get("besitos_balance", 0)

                    # Validate balance (requirement 2.2)
                    if balance_before < amount:
                        logger.warning("Insufficient funds for user %s: has %d, needs %d",
                                     user_id, balance_before, amount)
                        raise InsufficientFundsError(
                            f"Insufficient funds: has {balance_before}, needs {amount}"
                        )

                    balance_after = balance_before - amount

                    # Update user balance
                    await self.users_collection.update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "besitos_balance": balance_after,
                                "updated_at": datetime.utcnow()
                            }
                        },
                        session=session
                    )

                    # Create transaction record
                    transaction_doc = BesitosTransaction(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        type=TransactionType.SPENT,
                        amount=-amount,  # Negative for spending
                        balance_before=balance_before,
                        balance_after=balance_after,
                        status=TransactionStatus.COMPLETED,
                        reason=reason,
                        source="spending",
                        reference_id=reference_id or item_id,
                        metadata=metadata,
                        completed_at=datetime.utcnow()
                    )

                    await self.transactions_collection.insert_one(
                        transaction_doc.dict(),
                        session=session
                    )

                    # Transaction completed successfully
                    transaction = Transaction(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        amount=-amount,  # Negative for spending
                        balance_before=balance_before,
                        balance_after=balance_after,
                        status=TransactionStatus.COMPLETED
                    )

                logger.info("Successfully spent %d besitos from user %s (balance: %d -> %d)",
                           amount, user_id, balance_before, balance_after)

                # Publish besitos_spent event (requirement 2.2)
                await self._publish_besitos_spent_event(
                    user_id, transaction_id, amount, reason, item_id, balance_after
                )

                return transaction

            except InsufficientFundsError:
                # Re-raise insufficient funds error without wrapping
                raise
            except PyMongoError as e:
                logger.error("Database error spending besitos for user %s: %s", user_id, str(e))
                raise TransactionError(f"Failed to spend besitos: {str(e)}")
            except Exception as e:
                logger.error("Unexpected error spending besitos for user %s: %s", user_id, str(e))
                raise BesitosWalletError(f"Unexpected error: {str(e)}")

    async def get_balance(self, user_id: str) -> int:
        """Get user's current besitos balance.

        Args:
            user_id: User ID to get balance for

        Returns:
            int: Current besitos balance
        """
        logger.debug("Getting balance for user %s", user_id)

        try:
            user_doc = await self.users_collection.find_one(
                {"user_id": user_id},
                {"besitos_balance": 1}
            )

            if not user_doc:
                logger.debug("User %s not found, returning balance 0", user_id)
                return 0

            balance = user_doc.get("besitos_balance", 0)
            logger.debug("User %s balance: %d", user_id, balance)
            return balance

        except PyMongoError as e:
            logger.error("Database error getting balance for user %s: %s", user_id, str(e))
            raise BesitosWalletError(f"Failed to get balance: {str(e)}")

    async def get_transaction_history(self, user_id: str, limit: int = 50) -> list[Dict[str, Any]]:
        """Get user's transaction history.

        Args:
            user_id: User ID to get history for
            limit: Maximum number of transactions to return

        Returns:
            list: List of transaction documents
        """
        logger.debug("Getting transaction history for user %s (limit: %d)", user_id, limit)

        try:
            cursor = self.transactions_collection.find(
                {"user_id": user_id},
                {"_id": 0}  # Exclude MongoDB ObjectId
            ).sort("created_at", -1).limit(limit)

            transactions = []
            async for doc in cursor:
                transactions.append(doc)

            logger.debug("Retrieved %d transactions for user %s", len(transactions), user_id)
            return transactions

        except PyMongoError as e:
            logger.error("Database error getting transaction history for user %s: %s", user_id, str(e))
            raise BesitosWalletError(f"Failed to get transaction history: {str(e)}")

    async def _publish_besitos_added_event(self, user_id: str, transaction_id: str,
                                          amount: int, reason: str, source: str,
                                          balance_after: int) -> None:
        """Publish besitos_added event to event bus.

        Args:
            user_id: User ID
            transaction_id: Transaction ID
            amount: Amount added
            reason: Reason for adding
            source: Source of besitos
            balance_after: User balance after transaction
        """
        try:
            event = create_event(
                "besitos_awarded",
                user_id=user_id,
                amount=amount,
                reason=reason,
                source=source,
                balance_after=balance_after,
                transaction_id=transaction_id
            )

            await self.event_bus.publish("besitos_awarded", event.dict())
            logger.debug("Published besitos_awarded event for user %s", user_id)

        except Exception as e:
            # Don't fail the transaction for event publishing errors
            logger.warning("Failed to publish besitos_awarded event for user %s: %s", user_id, str(e))

    async def _publish_besitos_spent_event(self, user_id: str, transaction_id: str,
                                          amount: int, reason: str, item_id: Optional[str],
                                          balance_after: int) -> None:
        """Publish besitos_spent event to event bus.

        Args:
            user_id: User ID
            transaction_id: Transaction ID
            amount: Amount spent
            reason: Reason for spending
            item_id: Optional item ID
            balance_after: User balance after transaction
        """
        try:
            event = create_event(
                "besitos_spent",
                user_id=user_id,
                amount=amount,
                reason=reason,
                item_id=item_id,
                balance_after=balance_after,
                transaction_id=transaction_id
            )

            await self.event_bus.publish("besitos_spent", event.dict())
            logger.debug("Published besitos_spent event for user %s", user_id)

        except Exception as e:
            # Don't fail the transaction for event publishing errors
            logger.warning("Failed to publish besitos_spent event for user %s: %s", user_id, str(e))


# Factory function for dependency injection consistency with other modules
async def create_besitos_wallet(mongodb_handler: MongoDBHandler, event_bus: EventBus) -> BesitosWallet:
    """Factory function to create a BesitosWallet instance.

    Args:
        mongodb_handler: MongoDB handler instance
        event_bus: Event bus instance

    Returns:
        BesitosWallet: Initialized besitos wallet instance
    """
    return BesitosWallet(mongodb_handler, event_bus)
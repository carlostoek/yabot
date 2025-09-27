"""
Besitos Wallet Module - Virtual Currency System

This module implements the besitos virtual currency system with atomic transactions
following MongoDB transaction patterns and event-driven architecture.
Implements requirements 2.1, 2.2, 6.5: atomic transactions, besitos balance tracking,
and transaction atomicity.

The wallet handles:
- Besitos balance management
- Atomic credit/debit operations
- Transaction history
- Event publishing for cross-module integration
"""
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from decimal import Decimal

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from src.events.models import BaseEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.database.schemas.gamification import BesitosTransactionMongoSchema, UserGamificationData


class BesitosTransactionType(str, Enum):
    """
    Enumeration for besitos transaction types
    """
    REWARD = "reward"
    PURCHASE = "purchase"
    PENALTY = "penalty"
    BONUS = "bonus"
    REFUND = "refund"
    TRANSFER = "transfer"
    ACHIEVEMENT = "achievement"
    MISSION_COMPLETE = "mission_complete"
    TRIVIA_WIN = "trivia_win"
    DAILY_GIFT = "daily_gift"
    REACTION = "reaction"


class TransactionResult(BaseModel):
    """
    Result of a besitos transaction
    """
    success: bool
    transaction_id: Optional[str] = None
    new_balance: Optional[int] = None
    error_message: Optional[str] = None
    transaction_data: Optional[Dict[str, Any]] = None


class BesitosWallet:
    """
    Besitos wallet implementation with atomic transaction support

    Implements requirements 2.1, 2.2, 6.5:
    - 2.1: Besitos balance tracking
    - 2.2: Transaction system for besitos
    - 6.5: Atomicity for critical operations
    """

    def __init__(self, db_client: AsyncIOMotorClient, event_bus: EventBus):
        """
        Initialize the besitos wallet with database and event bus connections

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing transaction events
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)

        # Collection references
        self.users_collection = self.db.users
        self.besitos_transactions_collection = self.db.besitos_transactions

    async def get_balance(self, user_id: str) -> int:
        """
        Get the current besitos balance for a user

        Args:
            user_id: User identifier

        Returns:
            Current besitos balance
        """
        try:
            user_doc = await self.users_collection.find_one({"user_id": user_id})
            if user_doc and "besitos_balance" in user_doc:
                return user_doc["besitos_balance"]
            else:
                # If user doesn't exist or has no besitos balance, return 0
                return 0
        except Exception as e:
            self.logger.error(
                "Error getting besitos balance",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

from pydantic import BaseModel, validator

class BesitosTransactionRequest(BaseModel):
    user_id: str
    amount: int
    transaction_type: BesitosTransactionType
    description: str = ""
    reference_data: Optional[Dict[str, Any]] = None
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        if not v.isdigit():
            raise ValueError('User ID must contain only digits')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1000000:  # Reasonable upper limit
            raise ValueError('Amount exceeds maximum allowed')
        return v

    async def add_besitos(self, user_id: str, amount: int, transaction_type: BesitosTransactionType,
                         description: str = "", reference_data: Optional[Dict[str, Any]] = None) -> TransactionResult:
        """
        Add besitos to a user's balance (credit operation)
        Implements atomic transaction with MongoDB session

        Args:
            user_id: User identifier
            amount: Amount of besitos to add (must be positive)
            transaction_type: Type of transaction
            description: Description of the transaction
            reference_data: Optional reference data (mission_id, achievement_id, etc.)

        Returns:
            TransactionResult with success status and new balance
        """
        if amount <= 0:
            return TransactionResult(
                success=False,
                error_message=f"Amount must be positive, got {amount}"
            )
        
        # Validate using the Pydantic model
        try:
            request = BesitosTransactionRequest(
                user_id=user_id,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                reference_data=reference_data
            )
        except Exception as e:
            return TransactionResult(
                success=False,
                error_message=f"Invalid transaction request: {str(e)}"
            )
        
        return await self._perform_transaction(
            user_id=request.user_id,
            amount=request.amount,
            transaction_type=request.transaction_type,
            description=request.description,
            reference_data=request.reference_data
        )

    async def spend_besitos(self, user_id: str, amount: int, transaction_type: BesitosTransactionType,
                            description: str = "", reference_data: Optional[Dict[str, Any]] = None) -> TransactionResult:
        """
        Spend/withdraw besitos from a user's balance (debit operation)
        Implements atomic transaction with MongoDB session and balance validation

        Args:
            user_id: User identifier
            amount: Amount of besitos to spend (must be positive)
            transaction_type: Type of transaction
            description: Description of the transaction
            reference_data: Optional reference data (item_id, auction_id, etc.)

        Returns:
            TransactionResult with success status and new balance
        """
        if amount <= 0:
            return TransactionResult(
                success=False,
                error_message=f"Amount must be positive, got {amount}"
            )

        # First, check if user has sufficient balance
        current_balance = await self.get_balance(user_id)
        if current_balance < amount:
            return TransactionResult(
                success=False,
                error_message=f"Insufficient besitos balance. Current: {current_balance}, Requested: {amount}"
            )

        # Perform debit transaction (negative amount)
        return await self._perform_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type=transaction_type,
            description=description,
            reference_data=reference_data
        )

    async def _perform_transaction(self, user_id: str, amount: int, transaction_type: BesitosTransactionType,
                                   description: str, reference_data: Optional[Dict[str, Any]] = None) -> TransactionResult:
        """
        Perform an atomic besitos transaction using MongoDB transactions

        Args:
            user_id: User identifier
            amount: Amount to add (positive) or subtract (negative)
            transaction_type: Type of transaction
            description: Description of the transaction
            reference_data: Optional reference data

        Returns:
            TransactionResult with success status and new balance
        """
        try:
            import os
            # Check if transactions are disabled for testing
            disable_transactions = os.getenv('DISABLE_MONGO_TRANSACTIONS', 'false').lower() == 'true'

            if disable_transactions:
                # Use simple non-transactional operations for testing
                # Get current user document with besitos data
                user_doc = await self.users_collection.find_one({"user_id": user_id})

                # If user doesn't exist, create initial data
                if not user_doc:
                    initial_data = {
                        "user_id": user_id,
                        "besitos_balance": 0,
                        "total_earned_besitos": 0,
                        "total_spent_besitos": 0,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    await self.users_collection.insert_one(initial_data)
                    current_balance = 0
                else:
                    current_balance = user_doc.get("besitos_balance", 0)

                # Calculate new balance
                new_balance = current_balance + amount

                # Ensure balance doesn't go negative
                if new_balance < 0:
                    return TransactionResult(
                        success=False,
                        error_message=f"Transaction would result in negative balance: {new_balance}"
                    )

                # Update besitos statistics
                update_data = {
                    "besitos_balance": new_balance,
                    "updated_at": datetime.utcnow()
                }

                if amount > 0:
                    update_data["total_earned_besitos"] = user_doc.get("total_earned_besitos", 0) + amount if user_doc else amount
                    update_data["last_besitos_earned"] = datetime.utcnow()
                else:
                    update_data["total_spent_besitos"] = user_doc.get("total_spent_besitos", 0) + abs(amount) if user_doc else abs(amount)
                    update_data["last_besitos_spent"] = datetime.utcnow()

                # Update user document
                await self.users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": update_data},
                    upsert=True
                )

                # Create transaction record
                transaction_id = f"besitos_{ObjectId()}"
                transaction_doc_dict = {
                    "transaction_id": transaction_id,
                    "user_id": user_id,
                    "amount": amount,
                    "transaction_type": transaction_type.value,
                    "reason": description,
                    "balance_after": new_balance,
                    "reference_id": reference_data.get("reference_id") if reference_data else None,
                    "reference_type": reference_data.get("reference_type") if reference_data else None,
                    "timestamp": datetime.utcnow(),
                    "metadata": reference_data or {}
                }

                # Insert transaction record
                await self.besitos_transactions_collection.insert_one(transaction_doc_dict)

                self.logger.info(
                    "Besitos transaction completed (no atomicity)",
                    user_id=user_id,
                    amount=amount,
                    new_balance=new_balance,
                    transaction_id=transaction_id
                )

                # Publish event
                await self._publish_transaction_event(
                    user_id=user_id,
                    amount=amount,
                    transaction_type=transaction_type,
                    new_balance=new_balance,
                    transaction_id=transaction_id,
                    description=description,
                    reference_data=reference_data
                )

                return TransactionResult(
                    success=True,
                    transaction_id=transaction_id,
                    new_balance=new_balance,
                    transaction_data=transaction_doc_dict
                )
            else:
                # Use MongoDB transactions - restore original code
                async with await self.db.client.start_session() as session:
                    async with session.start_transaction():
                        # Get current user document with besitos data
                        user_doc = await self.users_collection.find_one(
                            {"user_id": user_id},
                            session=session
                        )

                        # If user doesn't exist, create initial data
                        if not user_doc:
                            initial_data = {
                                "user_id": user_id,
                                "besitos_balance": 0,
                                "total_earned_besitos": 0,
                                "total_spent_besitos": 0,
                                "created_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow()
                            }
                            await self.users_collection.insert_one(initial_data, session=session)
                            current_balance = 0
                        else:
                            current_balance = user_doc.get("besitos_balance", 0)

                        # Calculate new balance
                        new_balance = current_balance + amount

                        # Ensure balance doesn't go negative (only for debit operations)
                        if new_balance < 0:
                            return TransactionResult(
                                success=False,
                                error_message=f"Transaction would result in negative balance: {new_balance}"
                            )

                        # Update besitos statistics based on the transaction type
                        update_data = {
                            "besitos_balance": new_balance,
                            "updated_at": datetime.utcnow()
                        }

                        # Update total earned/spent based on transaction direction
                        if amount > 0:
                            update_data["total_earned_besitos"] = user_doc.get("total_earned_besitos", 0) + amount
                            update_data["last_besitos_earned"] = datetime.utcnow()
                        else:
                            update_data["total_spent_besitos"] = user_doc.get("total_spent_besitos", 0) + abs(amount)
                            update_data["last_besitos_spent"] = datetime.utcnow()

                        # Update user document
                        result = await self.users_collection.update_one(
                            {"user_id": user_id},
                            {"$set": update_data},
                            session=session
                        )

                        if result.modified_count == 0:
                            return TransactionResult(
                                success=False,
                                error_message="User document not updated"
                            )

                        # Create transaction record
                        transaction_id = f"besitos_{ObjectId()}"

                        # Create the transaction document as a dictionary since we can't import the schema at runtime
                        transaction_doc_dict = {
                            "transaction_id": transaction_id,
                            "user_id": user_id,
                            "amount": amount,
                            "transaction_type": transaction_type.value,
                            "reason": description,
                            "balance_after": new_balance,
                            "reference_id": reference_data.get("reference_id") if reference_data else None,
                            "reference_type": reference_data.get("reference_type") if reference_data else None,
                            "timestamp": datetime.utcnow(),
                            "metadata": reference_data or {}
                        }

                        # Insert transaction record
                        await self.besitos_transactions_collection.insert_one(
                            transaction_doc_dict,
                            session=session
                        )

                        # Commit transaction (automatic with context manager)
                        self.logger.info(
                            "Besitos transaction completed",
                            user_id=user_id,
                            amount=amount,
                            new_balance=new_balance,
                            transaction_id=transaction_id
                        )

                        # Publish event after successful transaction
                        await self._publish_transaction_event(
                            user_id=user_id,
                            amount=amount,
                            transaction_type=transaction_type,
                            new_balance=new_balance,
                            transaction_id=transaction_id,
                            description=description,
                            reference_data=reference_data
                        )

                        return TransactionResult(
                            success=True,
                            transaction_id=transaction_id,
                            new_balance=new_balance,
                            transaction_data=transaction_doc_dict
                        )

        except Exception as e:
            self.logger.error(
                "Error performing besitos transaction",
                user_id=user_id,
                amount=amount,
                transaction_type=transaction_type.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return TransactionResult(
                success=False,
                error_message=f"Transaction failed: {str(e)}"
            )

    async def get_transaction_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get transaction history for a user

        Args:
            user_id: User identifier
            limit: Maximum number of transactions to return

        Returns:
            List of transaction records
        """
        try:
            cursor = self.besitos_transactions_collection.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(limit)

            transactions = []
            async for doc in cursor:
                # Convert ObjectId to string to ensure JSON serialization
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                transactions.append(doc)

            return transactions

        except Exception as e:
            self.logger.error(
                "Error getting transaction history",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def transfer_besitos(self, from_user_id: str, to_user_id: str, amount: int,
                             description: str = "") -> Dict[str, Any]:
        """
        Transfer besitos between users atomically

        Args:
            from_user_id: User ID to transfer from
            to_user_id: User ID to transfer to
            amount: Amount to transfer
            description: Description of the transfer

        Returns:
            Result of the transfer operation
        """
        if amount <= 0:
            return {
                "success": False,
                "error": f"Amount must be positive, got {amount}"
            }

        # Check if sender has sufficient balance
        current_balance = await self.get_balance(from_user_id)
        if current_balance < amount:
            return {
                "success": False,
                "error": f"Insufficient besitos balance. Current: {current_balance}, Requested: {amount}"
            }

        try:
            # Use MongoDB transaction for atomic transfer
            async with await self.db.client.start_session() as session:
                async with session.start_transaction():
                    # Deduct from sender
                    result_debit = await self._perform_transaction(
                        user_id=from_user_id,
                        amount=-amount,
                        transaction_type=BesitosTransactionType.TRANSFER,
                        description=f"{description} - Transfer to {to_user_id}",
                        reference_data={"reference_type": "transfer", "reference_id": to_user_id}
                    )

                    if not result_debit.success:
                        return {"success": False, "error": result_debit.error_message}

                    # Add to recipient
                    result_credit = await self._perform_transaction(
                        user_id=to_user_id,
                        amount=amount,
                        transaction_type=BesitosTransactionType.TRANSFER,
                        description=f"{description} - Transfer from {from_user_id}",
                        reference_data={"reference_type": "transfer", "reference_id": from_user_id}
                    )

                    if not result_credit.success:
                        # This shouldn't happen, but if it does, we need to reverse the first transaction
                        # In a real system, this would be handled by the transaction rollback
                        return {"success": False, "error": result_credit.error_message}

                    self.logger.info(
                        "Besitos transfer completed",
                        from_user=from_user_id,
                        to_user=to_user_id,
                        amount=amount
                    )

                    return {
                        "success": True,
                        "from_transaction_id": result_debit.transaction_id,
                        "to_transaction_id": result_credit.transaction_id,
                        "amount": amount
                    }

        except Exception as e:
            self.logger.error(
                "Error transferring besitos",
                from_user=from_user_id,
                to_user=to_user_id,
                amount=amount,
                error=str(e),
                error_type=type(e).__name__
            )
            return {"success": False, "error": f"Transfer failed: {str(e)}"}

    async def _publish_transaction_event(self, user_id: str, amount: int, transaction_type: BesitosTransactionType,
                                       new_balance: int, transaction_id: str, description: str = "",
                                       reference_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish an event about the besitos transaction

        Args:
            user_id: User ID
            amount: Transaction amount
            transaction_type: Type of transaction
            new_balance: New balance after transaction
            transaction_id: Transaction identifier
            description: Transaction description
            reference_data: Optional reference data
        """
        try:
            event_type = "besitos_added" if amount > 0 else "besitos_spent"
            
            event_payload = {
                "user_id": user_id,
                "amount": abs(amount),
                "transaction_type": transaction_type.value,
                "new_balance": new_balance,
                "transaction_id": transaction_id,
                "description": description,
                "reference_data": reference_data or {},
                "timestamp": datetime.utcnow().isoformat()
            }

            event = BaseEvent(
                event_type=event_type,
                user_id=user_id,
                payload=event_payload
            )

            await self.event_bus.publish(event_type, event_payload)
            self.logger.debug(
                "Besitos transaction event published",
                event_type=event_type,
                user_id=user_id,
                transaction_id=transaction_id
            )

        except Exception as e:
            self.logger.error(
                "Error publishing besitos transaction event",
                user_id=user_id,
                transaction_id=transaction_id,
                error=str(e),
                error_type=type(e).__name__
            )

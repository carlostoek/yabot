"""
Auction system module for the YABOT system.

This module provides auction management with Redis-based timers for automatic expiration,
implementing requirement 2.8 from the modulos-atomicos specification.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from redis import asyncio as aioredis
from pymongo.collection import Collection
from pymongo.client_session import ClientSession
from pymongo.errors import PyMongoError

from src.database.mongodb import MongoDBHandler
from src.database.schemas.gamification import (
    Auction, AuctionStatus, Bid,
    BidPlacedEvent, AuctionClosedEvent
)
from src.modules.gamification.besitos_wallet import BesitosWallet, InsufficientFundsError
from src.events.bus import EventBus
from src.config.manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuctionSystemError(Exception):
    """Base exception for auction system operations."""
    pass


class AuctionNotFoundError(AuctionSystemError):
    """Exception raised when auction is not found."""
    pass


class AuctionExpiredError(AuctionSystemError):
    """Exception raised when attempting to operate on expired auction."""
    pass


class BidTooLowError(AuctionSystemError):
    """Exception raised when bid amount is too low."""
    pass


class AuctionResult:
    """Represents the result of a closed auction."""

    def __init__(self, auction_id: str, winner_id: Optional[str], final_price: int,
                 total_bids: int, status: str):
        self.auction_id = auction_id
        self.winner_id = winner_id
        self.final_price = final_price
        self.total_bids = total_bids
        self.status = status


class AuctionSystem:
    """
    Manages timed auctions with Redis-based timers and automatic expiration.

    This class provides the core auction functionality including:
    - Creating auctions with Redis TTL timers
    - Placing bids with besitos wallet integration
    - Automatic auction closing with event publishing
    - Auction state tracking and validation
    """

    def __init__(self, db_handler: MongoDBHandler, event_bus: EventBus,
                 besitos_wallet: BesitosWallet, config_manager: ConfigManager):
        """
        Initialize the auction system.

        Args:
            db_handler: MongoDB handler for auction persistence
            event_bus: Event bus for publishing auction events
            besitos_wallet: Besitos wallet for bid transactions
            config_manager: Configuration manager for Redis connection
        """
        self.db_handler = db_handler
        self.event_bus = event_bus
        self.besitos_wallet = besitos_wallet
        self.config_manager = config_manager
        self._redis_client: Optional[aioredis.Redis] = None
        self._auction_timers: Dict[str, asyncio.Task] = {}

    async def initialize(self) -> None:
        """Initialize Redis connection and set up auction monitoring."""
        try:
            redis_config = self.config_manager.get_redis_config()
            self._redis_client = aioredis.from_url(
                redis_config.redis_url,
                password=redis_config.redis_password,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=10,
                decode_responses=True
            )

            # Test connection
            await self._redis_client.ping()
            logger.info("Auction system Redis connection established")

            # Restore active auction timers
            await self._restore_auction_timers()

        except Exception as e:
            logger.error(f"Failed to initialize auction system: {e}")
            raise AuctionSystemError(f"Initialization failed: {e}")

    async def shutdown(self) -> None:
        """Gracefully shutdown the auction system."""
        # Cancel all running timers
        for timer_task in self._auction_timers.values():
            timer_task.cancel()

        if self._auction_timers:
            await asyncio.gather(*self._auction_timers.values(), return_exceptions=True)

        # Close Redis connection
        if self._redis_client:
            await self._redis_client.close()

    async def create_auction(self, seller_id: str, item_id: str, item_name: str,
                           starting_price: int, duration: int,
                           buyout_price: Optional[int] = None,
                           item_quantity: int = 1) -> Auction:
        """
        Create a new auction with Redis TTL timer.

        Args:
            seller_id: ID of the user selling the item
            item_id: ID of the item being auctioned
            item_name: Name of the item
            starting_price: Starting bid price in besitos
            duration: Auction duration in seconds
            buyout_price: Optional immediate purchase price
            item_quantity: Quantity of items being auctioned

        Returns:
            Auction: The created auction object

        Raises:
            AuctionSystemError: If auction creation fails
        """
        try:
            auction_id = str(uuid.uuid4())
            now = datetime.utcnow()
            end_time = now + timedelta(seconds=duration)

            auction = Auction(
                auction_id=auction_id,
                seller_id=seller_id,
                item_id=item_id,
                item_name=item_name,
                item_quantity=item_quantity,
                starting_price=starting_price,
                current_price=starting_price,
                buyout_price=buyout_price,
                status=AuctionStatus.ACTIVE,
                bids=[],
                current_winner_id=None,
                start_time=now,
                end_time=end_time,
                completed_at=None,
                metadata={},
                created_at=now,
                updated_at=now
            )

            # Store auction in database
            collection = self.db_handler.get_collection('auctions')
            auction_dict = auction.model_dump()
            await collection.insert_one(auction_dict)

            # Set up Redis TTL timer
            await self._set_auction_timer(auction_id, duration)

            # Start monitoring task
            self._auction_timers[auction_id] = asyncio.create_task(
                self._monitor_auction(auction_id, duration)
            )

            logger.info(f"Created auction {auction_id} for item {item_id} by user {seller_id}")
            return auction

        except Exception as e:
            logger.error(f"Failed to create auction: {e}")
            raise AuctionSystemError(f"Auction creation failed: {e}")

    async def place_bid(self, user_id: str, auction_id: str, amount: int) -> bool:
        """
        Place a bid on an auction with wallet integration and validation.

        Args:
            user_id: ID of the bidding user
            auction_id: ID of the auction
            amount: Bid amount in besitos

        Returns:
            bool: True if bid was successfully placed

        Raises:
            AuctionNotFoundError: If auction doesn't exist
            AuctionExpiredError: If auction has expired
            BidTooLowError: If bid amount is too low
            InsufficientFundsError: If user has insufficient besitos
            AuctionSystemError: If bid placement fails
        """
        try:
            # Get auction
            auction = await self._get_auction(auction_id)
            if not auction:
                raise AuctionNotFoundError(f"Auction {auction_id} not found")

            # Check auction status
            if auction.status != AuctionStatus.ACTIVE:
                raise AuctionExpiredError(f"Auction {auction_id} is not active")

            # Check if auction has expired
            if datetime.utcnow() >= auction.end_time:
                await self.close_auction(auction_id)
                raise AuctionExpiredError(f"Auction {auction_id} has expired")

            # Validate bid amount
            min_bid = auction.current_price + 1  # Minimum increment of 1 besito
            if amount < min_bid:
                raise BidTooLowError(f"Bid must be at least {min_bid} besitos")

            # Check if user has sufficient balance
            balance = await self.besitos_wallet.get_balance(user_id)
            if balance < amount:
                raise InsufficientFundsError(f"Insufficient balance: {balance} < {amount}")

            # Create bid
            bid_id = str(uuid.uuid4())
            bid = Bid(
                bid_id=bid_id,
                bidder_id=user_id,
                amount=amount,
                timestamp=datetime.utcnow(),
                metadata={}
            )

            # Reserve besitos (temporary hold)
            transaction = await self.besitos_wallet.spend_besitos(
                user_id=user_id,
                amount=amount,
                reason=f"Bid on auction {auction_id}",
                reference_id=auction_id,
                source="auction_bid"
            )

            # Update auction
            previous_price = auction.current_price
            previous_winner_id = auction.current_winner_id

            auction.bids.append(bid)
            auction.current_price = amount
            auction.current_winner_id = user_id
            auction.updated_at = datetime.utcnow()

            # Save to database
            collection = self.db_handler.get_collection('auctions')
            await collection.replace_one(
                {"auction_id": auction_id},
                auction.model_dump()
            )

            # Refund previous highest bidder if any
            if previous_winner_id and previous_winner_id != user_id:
                await self.besitos_wallet.add_besitos(
                    user_id=previous_winner_id,
                    amount=previous_price,
                    reason=f"Bid refund for auction {auction_id}",
                    reference_id=auction_id,
                    source="auction_refund"
                )

            # Publish bid placed event
            bid_event = BidPlacedEvent(
                auction_id=auction_id,
                bidder_id=user_id,
                bid_id=bid_id,
                bid_amount=amount,
                previous_price=previous_price,
                new_current_price=amount,
                previous_winner_id=previous_winner_id,
                auction_end_time=auction.end_time
            )

            await self.event_bus.publish("bid_placed", bid_event.model_dump())

            logger.info(f"Bid placed: {amount} besitos by user {user_id} on auction {auction_id}")
            return True

        except (AuctionNotFoundError, AuctionExpiredError, BidTooLowError, InsufficientFundsError):
            raise
        except Exception as e:
            logger.error(f"Failed to place bid: {e}")
            raise AuctionSystemError(f"Bid placement failed: {e}")

    async def close_auction(self, auction_id: str) -> AuctionResult:
        """
        Close an auction and handle final transaction.

        Args:
            auction_id: ID of the auction to close

        Returns:
            AuctionResult: Result of the closed auction

        Raises:
            AuctionNotFoundError: If auction doesn't exist
            AuctionSystemError: If auction closing fails
        """
        try:
            # Get auction
            auction = await self._get_auction(auction_id)
            if not auction:
                raise AuctionNotFoundError(f"Auction {auction_id} not found")

            # Skip if already closed
            if auction.status != AuctionStatus.ACTIVE:
                return AuctionResult(
                    auction_id=auction_id,
                    winner_id=auction.current_winner_id,
                    final_price=auction.current_price,
                    total_bids=len(auction.bids),
                    status=auction.status.value
                )

            # Determine final status
            final_status = AuctionStatus.COMPLETED if auction.current_winner_id else AuctionStatus.EXPIRED

            # Update auction
            auction.status = final_status
            auction.completed_at = datetime.utcnow()
            auction.updated_at = datetime.utcnow()

            # Save to database
            collection = self.db_handler.get_collection('auctions')
            await collection.replace_one(
                {"auction_id": auction_id},
                auction.model_dump()
            )

            # Handle final transactions if there was a winner
            if auction.current_winner_id:
                # Winner's besitos are already spent, now transfer to seller
                await self.besitos_wallet.add_besitos(
                    user_id=auction.seller_id,
                    amount=auction.current_price,
                    reason=f"Auction sale {auction_id}",
                    reference_id=auction_id,
                    source="auction_sale"
                )

            # Clean up Redis timer
            await self._clear_auction_timer(auction_id)

            # Cancel monitoring task
            if auction_id in self._auction_timers:
                self._auction_timers[auction_id].cancel()
                del self._auction_timers[auction_id]

            # Publish auction closed event
            closed_event = AuctionClosedEvent(
                auction_id=auction_id,
                seller_id=auction.seller_id,
                item_id=auction.item_id,
                item_name=auction.item_name,
                final_price=auction.current_price,
                winner_id=auction.current_winner_id,
                total_bids=len(auction.bids),
                status=final_status.value
            )

            await self.event_bus.publish("auction_closed", closed_event.model_dump())

            result = AuctionResult(
                auction_id=auction_id,
                winner_id=auction.current_winner_id,
                final_price=auction.current_price,
                total_bids=len(auction.bids),
                status=final_status.value
            )

            logger.info(f"Auction {auction_id} closed with status {final_status.value}")
            return result

        except AuctionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to close auction: {e}")
            raise AuctionSystemError(f"Auction closing failed: {e}")

    async def get_auction(self, auction_id: str) -> Optional[Auction]:
        """
        Get auction by ID.

        Args:
            auction_id: ID of the auction

        Returns:
            Optional[Auction]: The auction if found, None otherwise
        """
        return await self._get_auction(auction_id)

    async def get_active_auctions(self, limit: int = 50) -> List[Auction]:
        """
        Get list of active auctions.

        Args:
            limit: Maximum number of auctions to return

        Returns:
            List[Auction]: List of active auctions
        """
        try:
            collection = self.db_handler.get_collection('auctions')
            cursor = collection.find(
                {"status": AuctionStatus.ACTIVE.value}
            ).sort("end_time", 1).limit(limit)

            auctions = []
            async for doc in cursor:
                auctions.append(Auction(**doc))

            return auctions

        except Exception as e:
            logger.error(f"Failed to get active auctions: {e}")
            return []

    async def get_user_auctions(self, user_id: str, status: Optional[AuctionStatus] = None) -> List[Auction]:
        """
        Get auctions for a specific user (as seller or bidder).

        Args:
            user_id: ID of the user
            status: Optional status filter

        Returns:
            List[Auction]: List of user's auctions
        """
        try:
            collection = self.db_handler.get_collection('auctions')

            query = {
                "$or": [
                    {"seller_id": user_id},
                    {"current_winner_id": user_id},
                    {"bids.bidder_id": user_id}
                ]
            }

            if status:
                query["status"] = status.value

            cursor = collection.find(query).sort("created_at", -1)

            auctions = []
            async for doc in cursor:
                auctions.append(Auction(**doc))

            return auctions

        except Exception as e:
            logger.error(f"Failed to get user auctions: {e}")
            return []

    # Private helper methods

    async def _get_auction(self, auction_id: str) -> Optional[Auction]:
        """Get auction from database."""
        try:
            collection = self.db_handler.get_collection('auctions')
            doc = await collection.find_one({"auction_id": auction_id})

            if doc:
                return Auction(**doc)
            return None

        except Exception as e:
            logger.error(f"Failed to get auction {auction_id}: {e}")
            return None

    async def _set_auction_timer(self, auction_id: str, duration: int) -> None:
        """Set Redis TTL timer for auction."""
        if self._redis_client:
            try:
                await self._redis_client.setex(
                    f"auction_timer:{auction_id}",
                    duration,
                    "active"
                )
            except Exception as e:
                logger.error(f"Failed to set auction timer for {auction_id}: {e}")

    async def _clear_auction_timer(self, auction_id: str) -> None:
        """Clear Redis timer for auction."""
        if self._redis_client:
            try:
                await self._redis_client.delete(f"auction_timer:{auction_id}")
            except Exception as e:
                logger.error(f"Failed to clear auction timer for {auction_id}: {e}")

    async def _monitor_auction(self, auction_id: str, duration: int) -> None:
        """Monitor auction and auto-close when timer expires."""
        try:
            await asyncio.sleep(duration)

            # Check if auction still exists and is active
            auction = await self._get_auction(auction_id)
            if auction and auction.status == AuctionStatus.ACTIVE:
                await self.close_auction(auction_id)

        except asyncio.CancelledError:
            # Timer was cancelled, auction was closed manually
            pass
        except Exception as e:
            logger.error(f"Error monitoring auction {auction_id}: {e}")

    async def _restore_auction_timers(self) -> None:
        """Restore timers for active auctions on system restart."""
        try:
            active_auctions = await self.get_active_auctions()
            now = datetime.utcnow()

            for auction in active_auctions:
                if auction.end_time <= now:
                    # Auction should have ended, close it
                    await self.close_auction(auction.auction_id)
                else:
                    # Restore timer
                    remaining_time = (auction.end_time - now).total_seconds()
                    await self._set_auction_timer(auction.auction_id, int(remaining_time))

                    self._auction_timers[auction.auction_id] = asyncio.create_task(
                        self._monitor_auction(auction.auction_id, int(remaining_time))
                    )

            logger.info(f"Restored timers for {len(self._auction_timers)} active auctions")

        except Exception as e:
            logger.error(f"Failed to restore auction timers: {e}")
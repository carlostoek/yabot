"""
Trivia engine module for the YABOT system.

This module provides trivia management with Telegram poll integration and
automatic reward distribution, implementing requirement 2.9 from the
modulos-atomicos specification.
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
    Trivia, TriviaStatus, TriviaQuestion, TriviaParticipant
)
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.events.bus import EventBus
from src.config.manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TriviaEngineError(Exception):
    """Base exception for trivia engine operations."""
    pass


class TriviaNotFoundError(TriviaEngineError):
    """Exception raised when trivia is not found."""
    pass


class TriviaExpiredError(TriviaEngineError):
    """Exception raised when attempting to operate on expired trivia."""
    pass


class TriviaAlreadyAnsweredError(TriviaEngineError):
    """Exception raised when user has already answered the trivia."""
    pass


class TriviaResult:
    """Represents the result of a user's trivia answer."""

    def __init__(self, trivia_id: str, user_id: str, question_id: str,
                 is_correct: bool, points_earned: int, total_score: int):
        self.trivia_id = trivia_id
        self.user_id = user_id
        self.question_id = question_id
        self.is_correct = is_correct
        self.points_earned = points_earned
        self.total_score = total_score
        self.timestamp = datetime.utcnow()


class TriviaStats:
    """Represents statistics for a trivia session."""

    def __init__(self, trivia_id: str, total_participants: int,
                 questions_answered: int, leaderboard: List[Dict[str, Any]]):
        self.trivia_id = trivia_id
        self.total_participants = total_participants
        self.questions_answered = questions_answered
        self.leaderboard = leaderboard
        self.timestamp = datetime.utcnow()


class TriviaEngine:
    """
    Manages Telegram polls and trivia question processing with automatic rewards.

    This class provides the core trivia functionality including:
    - Creating trivia questions using Telegram poll API patterns
    - Processing user answers from Telegram polls
    - Publishing trivia_answered events when users respond
    - Awarding besitos for correct answers through wallet integration
    - Supporting trivia statistics and leaderboards
    - Automatic trivia expiration and closing
    """

    def __init__(self, db_handler: MongoDBHandler, event_bus: EventBus,
                 besitos_wallet: BesitosWallet, config_manager: ConfigManager):
        """
        Initialize the trivia engine.

        Args:
            db_handler: MongoDB handler for trivia persistence
            event_bus: Event bus for publishing trivia events
            besitos_wallet: Besitos wallet for reward distribution
            config_manager: Configuration manager for Redis connection
        """
        self.db_handler = db_handler
        self.event_bus = event_bus
        self.besitos_wallet = besitos_wallet
        self.config_manager = config_manager
        self._redis_client: Optional[aioredis.Redis] = None
        self._trivia_timers: Dict[str, asyncio.Task] = {}

        # Collections
        self.trivias_collection: Collection = db_handler.get_trivias_collection()

        logger.info("TriviaEngine initialized")

    async def initialize(self) -> None:
        """Initialize Redis connection and set up trivia monitoring."""
        try:
            redis_config = self.config_manager.get_redis_config()
            self._redis_client = aioredis.from_url(
                redis_config.redis_url,
                password=redis_config.redis_password,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=10
            )

            await self._redis_client.ping()
            logger.info("TriviaEngine Redis connection established")

            # Restore any active trivias that need timers
            await self._restore_active_trivias()

        except Exception as e:
            logger.error("Failed to initialize TriviaEngine Redis: %s", str(e))
            raise TriviaEngineError(f"Redis initialization failed: {str(e)}")

    async def create_trivia(self, question: str, options: List[str],
                          correct_answer: int, title: str = "Trivia Question",
                          duration_minutes: int = 5, points: int = 10,
                          max_participants: Optional[int] = None) -> Trivia:
        """
        Create a new trivia question.

        Args:
            question: The trivia question text
            options: List of answer options
            correct_answer: Index of the correct answer (0-based)
            title: Title for the trivia session
            duration_minutes: How long the trivia stays active
            points: Points awarded for correct answers
            max_participants: Maximum number of participants (None for unlimited)

        Returns:
            Trivia: Created trivia object

        Raises:
            TriviaEngineError: If trivia creation fails
            ValueError: If parameters are invalid
        """
        if len(options) < 2:
            raise ValueError("Trivia must have at least 2 options")
        if correct_answer < 0 or correct_answer >= len(options):
            raise ValueError("correct_answer must be a valid option index")
        if duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if points <= 0:
            raise ValueError("points must be positive")

        logger.info("Creating trivia: %s", title)

        trivia_id = str(uuid.uuid4())
        question_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        end_time = current_time + timedelta(minutes=duration_minutes)

        # Create trivia question
        trivia_question = TriviaQuestion(
            question_id=question_id,
            question=question,
            options=options,
            correct_answer=correct_answer,
            points=points,
            time_limit=duration_minutes * 60  # Convert to seconds
        )

        # Create trivia document
        trivia_doc = Trivia(
            trivia_id=trivia_id,
            title=title,
            description=f"Answer the question correctly to earn {points} besitos!",
            status=TriviaStatus.ACTIVE,
            questions=[trivia_question],
            participants=[],
            max_participants=max_participants,
            reward_pool=points,  # For single question trivias
            reward_distribution={"correct": points},
            start_time=current_time,
            end_time=end_time,
            metadata={
                "duration_minutes": duration_minutes,
                "poll_created": False,
                "telegram_poll_id": None
            }
        )

        try:
            # Insert trivia into database
            await self.trivias_collection.insert_one(trivia_doc.dict())

            # Set up Redis timer for automatic expiration
            await self._set_trivia_timer(trivia_id, duration_minutes)

            logger.info("Trivia created successfully: %s (ID: %s)", title, trivia_id)

            return trivia_doc

        except PyMongoError as e:
            logger.error("Database error creating trivia: %s", str(e))
            raise TriviaEngineError(f"Failed to create trivia: {str(e)}")

    async def process_answer(self, user_id: str, trivia_id: str,
                           answer: int, telegram_poll_id: Optional[str] = None) -> TriviaResult:
        """
        Process a user's answer to a trivia question.

        Implements requirement 2.9: WHEN trivias are answered THEN the system
        SHALL process Telegram polls and publish trivia_answered events.

        Args:
            user_id: User ID who answered
            trivia_id: Trivia session ID
            answer: Index of the selected answer (0-based)
            telegram_poll_id: Optional Telegram poll ID for validation

        Returns:
            TriviaResult: Result of the answer processing

        Raises:
            TriviaNotFoundError: If trivia doesn't exist
            TriviaExpiredError: If trivia has expired
            TriviaAlreadyAnsweredError: If user already answered
            ValueError: If answer is invalid
        """
        logger.info("Processing trivia answer: user=%s, trivia=%s, answer=%d",
                   user_id, trivia_id, answer)

        # Get trivia from database
        trivia_doc = await self.trivias_collection.find_one({"trivia_id": trivia_id})
        if not trivia_doc:
            raise TriviaNotFoundError(f"Trivia {trivia_id} not found")

        trivia = Trivia(**trivia_doc)

        # Check if trivia is still active
        if trivia.status != TriviaStatus.ACTIVE:
            raise TriviaExpiredError(f"Trivia {trivia_id} is no longer active")

        # Check if trivia has expired
        if trivia.end_time and datetime.utcnow() > trivia.end_time:
            await self._close_trivia(trivia_id, "expired")
            raise TriviaExpiredError(f"Trivia {trivia_id} has expired")

        # Check if user already answered
        existing_participant = next(
            (p for p in trivia.participants if p.user_id == user_id), None
        )
        if existing_participant and existing_participant.completed:
            raise TriviaAlreadyAnsweredError(f"User {user_id} already answered trivia {trivia_id}")

        # Validate answer
        if len(trivia.questions) == 0:
            raise TriviaEngineError("Trivia has no questions")

        question = trivia.questions[0]  # For single-question trivias
        if answer < 0 or answer >= len(question.options):
            raise ValueError(f"Invalid answer index: {answer}")

        # Check if correct
        is_correct = answer == question.correct_answer
        points_earned = question.points if is_correct else 0

        try:
            # Start MongoDB transaction for atomicity
            async with await self.db_handler._db.client.start_session() as session:
                async with session.start_transaction():
                    # Update or create participant record
                    if existing_participant:
                        # Update existing participant
                        participant_index = trivia.participants.index(existing_participant)
                        trivia.participants[participant_index].score = points_earned
                        trivia.participants[participant_index].answers.append({
                            "question_id": question.question_id,
                            "answer": answer,
                            "is_correct": is_correct,
                            "points": points_earned,
                            "timestamp": datetime.utcnow()
                        })
                        trivia.participants[participant_index].completed = True
                    else:
                        # Create new participant
                        participant = TriviaParticipant(
                            user_id=user_id,
                            score=points_earned,
                            answers=[{
                                "question_id": question.question_id,
                                "answer": answer,
                                "is_correct": is_correct,
                                "points": points_earned,
                                "timestamp": datetime.utcnow()
                            }],
                            joined_at=datetime.utcnow(),
                            completed=True
                        )
                        trivia.participants.append(participant)

                    # Check participant limit
                    if (trivia.max_participants and
                        len([p for p in trivia.participants if p.completed]) >= trivia.max_participants):
                        # Auto-close if max participants reached
                        trivia.status = TriviaStatus.COMPLETED
                        trivia.completed_at = datetime.utcnow()

                    # Update trivia in database
                    await self.trivias_collection.update_one(
                        {"trivia_id": trivia_id},
                        {
                            "$set": {
                                "participants": [p.dict() for p in trivia.participants],
                                "status": trivia.status.value,
                                "completed_at": trivia.completed_at,
                                "updated_at": datetime.utcnow()
                            }
                        },
                        session=session
                    )

                    # Award besitos if correct
                    if is_correct and points_earned > 0:
                        await self.besitos_wallet.add_besitos(
                            user_id=user_id,
                            amount=points_earned,
                            reason=f"Correct trivia answer: {trivia.title}",
                            source="trivia",
                            reference_id=trivia_id,
                            metadata={
                                "trivia_id": trivia_id,
                                "question_id": question.question_id,
                                "telegram_poll_id": telegram_poll_id
                            }
                        )

            # Create result
            total_score = points_earned  # For single-question trivias
            result = TriviaResult(
                trivia_id=trivia_id,
                user_id=user_id,
                question_id=question.question_id,
                is_correct=is_correct,
                points_earned=points_earned,
                total_score=total_score
            )

            # Publish trivia_answered event (requirement 2.9)
            await self._publish_trivia_answered_event(
                user_id=user_id,
                trivia_id=trivia_id,
                question_id=question.question_id,
                answer=answer,
                is_correct=is_correct,
                points_earned=points_earned,
                telegram_poll_id=telegram_poll_id
            )

            logger.info("Trivia answer processed: user=%s, correct=%s, points=%d",
                       user_id, is_correct, points_earned)

            return result

        except Exception as e:
            logger.error("Error processing trivia answer: %s", str(e))
            raise TriviaEngineError(f"Failed to process answer: {str(e)}")

    async def get_trivia_results(self, trivia_id: str) -> TriviaStats:
        """
        Get statistics and results for a trivia session.

        Args:
            trivia_id: Trivia session ID

        Returns:
            TriviaStats: Statistics and leaderboard for the trivia

        Raises:
            TriviaNotFoundError: If trivia doesn't exist
        """
        logger.debug("Getting trivia results for: %s", trivia_id)

        trivia_doc = await self.trivias_collection.find_one({"trivia_id": trivia_id})
        if not trivia_doc:
            raise TriviaNotFoundError(f"Trivia {trivia_id} not found")

        trivia = Trivia(**trivia_doc)

        # Calculate statistics
        total_participants = len([p for p in trivia.participants if p.completed])
        questions_answered = sum(len(p.answers) for p in trivia.participants if p.completed)

        # Create leaderboard sorted by score (descending)
        leaderboard = []
        for participant in trivia.participants:
            if participant.completed:
                leaderboard.append({
                    "user_id": participant.user_id,
                    "score": participant.score,
                    "answers": len(participant.answers),
                    "joined_at": participant.joined_at,
                    "last_answer_time": max(
                        (ans.get("timestamp", participant.joined_at)
                         for ans in participant.answers),
                        default=participant.joined_at
                    ) if participant.answers else participant.joined_at
                })

        # Sort by score (descending), then by completion time (ascending)
        leaderboard.sort(key=lambda x: (-x["score"], x["last_answer_time"]))

        stats = TriviaStats(
            trivia_id=trivia_id,
            total_participants=total_participants,
            questions_answered=questions_answered,
            leaderboard=leaderboard
        )

        logger.debug("Trivia results: %d participants, %d answers",
                    total_participants, questions_answered)

        return stats

    async def get_active_trivias(self) -> List[Dict[str, Any]]:
        """
        Get all currently active trivia sessions.

        Returns:
            List[Dict[str, Any]]: List of active trivia sessions
        """
        logger.debug("Getting active trivias")

        try:
            cursor = self.trivias_collection.find(
                {"status": TriviaStatus.ACTIVE.value},
                {"_id": 0}  # Exclude MongoDB ObjectId
            ).sort("start_time", -1)

            active_trivias = []
            async for doc in cursor:
                # Check if trivia has actually expired
                if doc.get("end_time") and datetime.utcnow() > doc["end_time"]:
                    # Auto-close expired trivia
                    await self._close_trivia(doc["trivia_id"], "expired")
                else:
                    active_trivias.append(doc)

            logger.debug("Found %d active trivias", len(active_trivias))
            return active_trivias

        except PyMongoError as e:
            logger.error("Database error getting active trivias: %s", str(e))
            raise TriviaEngineError(f"Failed to get active trivias: {str(e)}")

    async def close_trivia(self, trivia_id: str, reason: str = "manual") -> bool:
        """
        Manually close a trivia session.

        Args:
            trivia_id: Trivia session ID
            reason: Reason for closing

        Returns:
            bool: True if closed successfully

        Raises:
            TriviaNotFoundError: If trivia doesn't exist
        """
        logger.info("Manually closing trivia: %s (reason: %s)", trivia_id, reason)
        return await self._close_trivia(trivia_id, reason)

    async def _close_trivia(self, trivia_id: str, reason: str) -> bool:
        """
        Internal method to close a trivia session.

        Args:
            trivia_id: Trivia session ID
            reason: Reason for closing

        Returns:
            bool: True if closed successfully
        """
        try:
            # Update trivia status
            result = await self.trivias_collection.update_one(
                {"trivia_id": trivia_id, "status": TriviaStatus.ACTIVE.value},
                {
                    "$set": {
                        "status": TriviaStatus.COMPLETED.value,
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "metadata.close_reason": reason
                    }
                }
            )

            if result.modified_count > 0:
                # Cancel timer if exists
                if trivia_id in self._trivia_timers:
                    self._trivia_timers[trivia_id].cancel()
                    del self._trivia_timers[trivia_id]

                # Clear Redis timer
                if self._redis_client:
                    await self._redis_client.delete(f"trivia_timer:{trivia_id}")

                # Publish trivia_closed event
                await self._publish_trivia_closed_event(trivia_id, reason)

                logger.info("Trivia closed successfully: %s", trivia_id)
                return True
            else:
                logger.warning("Trivia not found or already closed: %s", trivia_id)
                return False

        except PyMongoError as e:
            logger.error("Database error closing trivia: %s", str(e))
            raise TriviaEngineError(f"Failed to close trivia: {str(e)}")

    async def _set_trivia_timer(self, trivia_id: str, duration_minutes: int) -> None:
        """
        Set up Redis timer for automatic trivia expiration.

        Args:
            trivia_id: Trivia session ID
            duration_minutes: Duration in minutes
        """
        if not self._redis_client:
            logger.warning("Redis not available, skipping timer setup for trivia %s", trivia_id)
            return

        try:
            # Set Redis key with TTL
            await self._redis_client.setex(
                f"trivia_timer:{trivia_id}",
                duration_minutes * 60,  # Convert to seconds
                "active"
            )

            # Create async timer task
            timer_task = asyncio.create_task(
                self._trivia_timer_task(trivia_id, duration_minutes * 60)
            )
            self._trivia_timers[trivia_id] = timer_task

            logger.debug("Timer set for trivia %s: %d minutes", trivia_id, duration_minutes)

        except Exception as e:
            logger.warning("Failed to set trivia timer: %s", str(e))

    async def _trivia_timer_task(self, trivia_id: str, duration_seconds: int) -> None:
        """
        Async timer task for trivia expiration.

        Args:
            trivia_id: Trivia session ID
            duration_seconds: Duration in seconds
        """
        try:
            await asyncio.sleep(duration_seconds)
            await self._close_trivia(trivia_id, "expired")
        except asyncio.CancelledError:
            logger.debug("Timer cancelled for trivia %s", trivia_id)
        except Exception as e:
            logger.error("Error in trivia timer task: %s", str(e))

    async def _restore_active_trivias(self) -> None:
        """Restore timers for active trivias after restart."""
        try:
            cursor = self.trivias_collection.find({"status": TriviaStatus.ACTIVE.value})
            current_time = datetime.utcnow()

            async for doc in cursor:
                trivia_id = doc["trivia_id"]
                end_time = doc.get("end_time")

                if end_time:
                    if current_time >= end_time:
                        # Trivia has expired, close it
                        await self._close_trivia(trivia_id, "expired_on_restart")
                    else:
                        # Set up timer for remaining time
                        remaining_seconds = int((end_time - current_time).total_seconds())
                        if remaining_seconds > 0:
                            timer_task = asyncio.create_task(
                                self._trivia_timer_task(trivia_id, remaining_seconds)
                            )
                            self._trivia_timers[trivia_id] = timer_task
                            logger.debug("Restored timer for trivia %s: %d seconds remaining",
                                       trivia_id, remaining_seconds)

        except Exception as e:
            logger.error("Error restoring active trivias: %s", str(e))

    async def _publish_trivia_answered_event(self, user_id: str, trivia_id: str,
                                           question_id: str, answer: int, is_correct: bool,
                                           points_earned: int, telegram_poll_id: Optional[str]) -> None:
        """
        Publish trivia_answered event to event bus.

        Args:
            user_id: User ID who answered
            trivia_id: Trivia session ID
            question_id: Question ID
            answer: Answer index selected
            is_correct: Whether answer was correct
            points_earned: Points earned for the answer
            telegram_poll_id: Optional Telegram poll ID
        """
        try:
            event_data = {
                "user_id": user_id,
                "trivia_id": trivia_id,
                "question_id": question_id,
                "answer": answer,
                "is_correct": is_correct,
                "points_earned": points_earned,
                "telegram_poll_id": telegram_poll_id,
                "timestamp": datetime.utcnow()
            }

            await self.event_bus.publish("trivia_answered", event_data)
            logger.debug("Published trivia_answered event for user %s", user_id)

        except Exception as e:
            # Don't fail the transaction for event publishing errors
            logger.warning("Failed to publish trivia_answered event: %s", str(e))

    async def _publish_trivia_closed_event(self, trivia_id: str, reason: str) -> None:
        """
        Publish trivia_closed event to event bus.

        Args:
            trivia_id: Trivia session ID
            reason: Reason for closing
        """
        try:
            event_data = {
                "trivia_id": trivia_id,
                "reason": reason,
                "timestamp": datetime.utcnow()
            }

            await self.event_bus.publish("trivia_closed", event_data)
            logger.debug("Published trivia_closed event for trivia %s", trivia_id)

        except Exception as e:
            logger.warning("Failed to publish trivia_closed event: %s", str(e))

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the trivia engine.

        Returns:
            Dict[str, Any]: Health status information
        """
        health_status = {
            "redis_connected": self._redis_client is not None,
            "active_timers": len(self._trivia_timers),
            "collection_accessible": True
        }

        try:
            # Test Redis connection
            if self._redis_client:
                await self._redis_client.ping()
                health_status["redis_healthy"] = True
            else:
                health_status["redis_healthy"] = False

            # Test database access
            await self.trivias_collection.count_documents({"status": TriviaStatus.ACTIVE.value})

        except Exception as e:
            logger.warning("Health check failed: %s", str(e))
            health_status["collection_accessible"] = False
            health_status["redis_healthy"] = False

        return health_status

    async def cleanup(self) -> None:
        """Clean up resources and connections."""
        logger.info("Cleaning up TriviaEngine resources")

        # Cancel all timer tasks
        for trivia_id, task in self._trivia_timers.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._trivia_timers.clear()

        # Close Redis connection
        if self._redis_client:
            try:
                await self._redis_client.close()
            except Exception as e:
                logger.error("Error closing Redis connection: %s", str(e))

        logger.info("TriviaEngine cleanup completed")


# Factory function for dependency injection consistency with other modules
async def create_trivia_engine(db_handler: MongoDBHandler, event_bus: EventBus,
                             besitos_wallet: BesitosWallet, config_manager: ConfigManager) -> TriviaEngine:
    """
    Factory function to create a TriviaEngine instance.

    Args:
        db_handler: MongoDB handler instance
        event_bus: Event bus instance
        besitos_wallet: Besitos wallet instance
        config_manager: Configuration manager instance

    Returns:
        TriviaEngine: Initialized trivia engine instance
    """
    trivia_engine = TriviaEngine(db_handler, event_bus, besitos_wallet, config_manager)
    await trivia_engine.initialize()
    return trivia_engine
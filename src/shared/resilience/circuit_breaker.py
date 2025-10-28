# src/shared/resilience/circuit_breaker.py

import time
from typing import Optional
import redis.asyncio as redis

from src.events.bus import EventBus
from src.events.models import create_event

class CircuitBreaker:
    def __init__(
        self,
        redis_client: redis.Redis,
        event_bus: EventBus,
        service_name: str,
        failure_threshold: int = 5,
        timeout: int = 30,
    ):
        self.redis = redis_client
        self.event_bus = event_bus
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state_key = f"circuit_breaker:{self.service_name}:state"
        self.failure_count_key = f"circuit_breaker:{self.service_name}:failure_count"
        self.last_failure_time_key = f"circuit_breaker:{self.service_name}:last_failure_time"

    async def _get_state(self) -> str:
        state = await self.redis.get(self.state_key)
        return state.decode("utf-8") if state else "CLOSED"

    async def _get_failure_count(self) -> int:
        count = await self.redis.get(self.failure_count_key)
        return int(count) if count else 0

    async def is_open(self) -> bool:
        """Checks if the circuit is open."""
        state = await self._get_state()
        if state == "OPEN":
            last_failure_time = await self.redis.get(self.last_failure_time_key)
            if last_failure_time and (time.time() - float(last_failure_time)) > self.timeout:
                await self.redis.set(self.state_key, "HALF_OPEN")
                return False
            return True
        return False

    async def record_failure(self):
        """Records a failure and opens the circuit if the threshold is reached."""
        failure_count = await self.redis.incr(self.failure_count_key)
        if failure_count >= self.failure_threshold:
            await self.redis.set(self.state_key, "OPEN")
            await self.redis.set(self.last_failure_time_key, time.time())
            event = create_event(
                "circuit_breaker_opened",
                service_name=self.service_name,
                failure_count=failure_count,
                failure_threshold=self.failure_threshold,
                timeout_seconds=self.timeout,
            )
            await self.event_bus.publish(event)

    async def record_success(self):
        """Records a success and closes the circuit if it was half-open."""
        state = await self._get_state()
        if state == "HALF_OPEN":
            open_duration = 0
            last_failure_time = await self.redis.get(self.last_failure_time_key)
            if last_failure_time:
                open_duration = time.time() - float(last_failure_time)
            await self.reset()
            event = create_event(
                "circuit_breaker_closed",
                service_name=self.service_name,
                open_duration_seconds=open_duration,
                test_request_success=True,
            )
            await self.event_bus.publish(event)
        elif state == "CLOSED":
            await self.redis.delete(self.failure_count_key)

    async def reset(self):
        """Resets the circuit breaker to a closed state."""
        await self.redis.delete(self.state_key, self.failure_count_key, self.last_failure_time_key)

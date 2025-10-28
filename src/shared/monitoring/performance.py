# src/shared/monitoring/performance.py

import time
from functools import wraps
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Any, Callable, Coroutine

from src.utils.logger import get_logger

logger = get_logger(__name__)

class PerformanceMetrics(BaseModel):
    operation: str
    duration_ms: float
    timestamp: datetime
    module: str
    success: bool
    correlation_id: Optional[str] = None

class PerformanceMonitor:
    def __init__(self, module_name: str):
        self.module_name = module_name

    def measure(self, operation: str, correlation_id: Optional[str] = None) -> Callable[..., Coroutine[Any, Any, Any]]:
        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                success = True
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception:
                    success = False
                    raise
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    metrics = PerformanceMetrics(
                        operation=operation,
                        duration_ms=duration_ms,
                        timestamp=datetime.utcnow(),
                        module=self.module_name,
                        success=success,
                        correlation_id=correlation_id,
                    )
                    logger.info(f"Performance: {metrics.json()}")
            return wrapper
        return decorator

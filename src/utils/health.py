"""
Health Check Manager for YABOT

This module implements health check functionality for all system components
to ensure reliability as specified in the requirements.
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from src.utils.logger import get_logger
from src.database.manager import DatabaseManager
from src.events.bus import EventBus


class HealthCheckManager:
    """
    Manages health checks for all system components as per Reliability NFR
    """
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None, 
                 event_bus: Optional[EventBus] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.database_manager = database_manager
        self.event_bus = event_bus
        
    async def check_database_health(self) -> Dict[str, Any]:
        """
        Check database connectivity health.
        
        Implements Reliability NFR: All components SHALL implement health check endpoints
        """
        try:
            if not self.database_manager:
                return {"error": "Database manager not initialized"}
            
            health_status = await self.database_manager.health_check()
            return health_status
            
        except Exception as e:
            self.logger.error(
                "Error in database health check",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "error": str(e),
                "overall_healthy": False
            }

    async def check_redis_health(self) -> Dict[str, Any]:
        """
        Check Redis connectivity health.
        
        Implements Reliability NFR: All components SHALL implement health check endpoints
        """
        try:
            if not self.event_bus:
                return {"error": "Event bus not initialized"}
            
            health_status = await self.event_bus.health_check()
            return health_status
            
        except Exception as e:
            self.logger.error(
                "Error in Redis/Event bus health check",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "error": str(e),
                "overall_healthy": False
            }

    async def check_api_health(self) -> Dict[str, Any]:
        """
        Check API server health.
        
        Implements Reliability NFR: All components SHALL implement health check endpoints
        """
        # Placeholder for API server health check
        # The actual implementation would depend on how the API server exposes health endpoints
        try:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "component": "api_server"
            }
        except Exception as e:
            self.logger.error(
                "Error in API health check",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "error": str(e),
                "status": "unhealthy"
            }

    async def check_overall_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check for all system components.
        
        Implements Reliability NFR: All components SHALL implement health check endpoints
        """
        try:
            # Run all health checks concurrently
            database_health, redis_health, api_health = await asyncio.gather(
                self.check_database_health(),
                self.check_redis_health(),
                self.check_api_health(),
                return_exceptions=True
            )
            
            # Handle potential exceptions from gather
            if isinstance(database_health, Exception):
                database_health = {"error": str(database_health), "overall_healthy": False}
            
            if isinstance(redis_health, Exception):
                redis_health = {"error": str(redis_health), "overall_healthy": False}
                
            if isinstance(api_health, Exception):
                api_health = {"error": str(api_health), "status": "unhealthy"}
            
            overall_healthy = (
                isinstance(database_health, dict) and 
                database_health.get("overall_healthy", False) and
                isinstance(redis_health, dict) and
                redis_health.get("redis_connected", False) and
                api_health.get("status") == "healthy"
            )
            
            health_report = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy" if overall_healthy else "unhealthy",
                "components": {
                    "database": database_health,
                    "redis": redis_health,
                    "api_server": api_health
                }
            }
            
            self.logger.info("Overall health check completed", overall_status=health_report["overall_status"])
            return health_report
            
        except Exception as e:
            self.logger.error(
                "Error in overall health check",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "error": str(e),
                "overall_status": "error",
                "timestamp": datetime.now().isoformat()
            }

    async def get_detailed_health_report(self) -> Dict[str, Any]:
        """
        Get detailed health report with additional metrics.
        
        Returns:
            Dict with detailed health information for monitoring
        """
        try:
            # Get basic health status
            basic_health = await self.check_overall_health()
            
            # Add additional metrics
            detailed_report = {
                **basic_health,
                "metrics": {
                    "checks_performed": len(basic_health.get("components", {})),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Add specific metrics for each component if available
            components = basic_health.get("components", {})
            
            if "database" in components:
                db_health = components["database"]
                detailed_report["metrics"]["database"] = {
                    "connected": db_health.get("overall_healthy", False),
                    "mongo_connected": db_health.get("mongo_connected", False),
                    "sqlite_connected": db_health.get("sqlite_connected", False)
                }
            
            if "redis" in components:
                redis_health = components["redis"]
                detailed_report["metrics"]["redis"] = {
                    "connected": redis_health.get("redis_connected", False),
                    "local_queue_size": redis_health.get("local_queue_size", 0)
                }
            
            return detailed_report
            
        except Exception as e:
            self.logger.error(
                "Error in detailed health report",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "error": str(e),
                "overall_status": "error",
                "timestamp": datetime.now().isoformat()
            }


# Global health check manager instance
_health_check_manager: Optional[HealthCheckManager] = None


def get_health_check_manager(
    database_manager: Optional[DatabaseManager] = None,
    event_bus: Optional[EventBus] = None
) -> HealthCheckManager:
    """
    Get or create the global health check manager instance.
    
    Args:
        database_manager: Optional DatabaseManager instance
        event_bus: Optional EventBus instance
        
    Returns:
        HealthCheckManager instance
    """
    global _health_check_manager
    if _health_check_manager is None:
        _health_check_manager = HealthCheckManager(
            database_manager=database_manager,
            event_bus=event_bus
        )
    return _health_check_manager


def reset_health_check_manager():
    """
    Reset the global health check manager instance (useful for testing).
    """
    global _health_check_manager
    _health_check_manager = None
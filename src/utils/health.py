"""
Health check manager for the YABOT system.

This module provides a centralized health check manager that can check the health
of all system components including databases, event bus, and other services,
implementing the reliability requirements specified in the fase1 specification.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HealthCheckManager:
    """Centralized health check manager for all system components."""
    
    def __init__(self, 
                 database_manager: Optional[DatabaseManager] = None,
                 event_bus: Optional[EventBus] = None):
        """Initialize the health check manager.
        
        Args:
            database_manager (DatabaseManager, optional): Database manager instance
            event_bus (EventBus, optional): Event bus instance
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        logger.info("HealthCheckManager initialized")
    
    async def check_all_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all system components.
        
        Returns:
            Dict[str, Any]: Health status for all system components
        """
        logger.debug("Performing comprehensive health check")
        
        # Run all health checks concurrently
        tasks = []
        
        # Database health check
        if self.database_manager:
            tasks.append(self.check_database_health())
        else:
            tasks.append(asyncio.sleep(0, result={"mongodb": False, "sqlite": False, "error": "Database manager not initialized"}))
        
        # Event bus health check
        if self.event_bus:
            tasks.append(self.check_event_bus_health())
        else:
            tasks.append(asyncio.sleep(0, result={"connected": False, "error": "Event bus not initialized"}))
        
        # API server health check (placeholder for future implementation)
        tasks.append(asyncio.sleep(0, result={"status": "unknown", "details": "API health check not implemented"}))
        
        # Run all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        health_status = {
            "overall_status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "components": {}
        }
        
        component_names = ["database", "event_bus", "api_server"]
        for i, result in enumerate(results):
            component_name = component_names[i]
            
            if isinstance(result, Exception):
                logger.error("Health check for %s failed: %s", component_name, str(result))
                health_status["components"][component_name] = {
                    "status": "unhealthy",
                    "error": str(result)
                }
                health_status["overall_status"] = "degraded"
            else:
                health_status["components"][component_name] = result
                # Check if this component is unhealthy
                if self._is_component_unhealthy(result):
                    health_status["overall_status"] = "degraded"
        
        logger.debug("Comprehensive health check results: %s", health_status)
        return health_status
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check the health of database connections.
        
        Returns:
            Dict[str, Any]: Database health status
        """
        logger.debug("Checking database health")
        
        if not self.database_manager:
            return {"status": "unhealthy", "error": "Database manager not initialized"}
        
        try:
            db_health = await self.database_manager.health_check()
            return {
                "status": "healthy" if all(db_health.values()) else "degraded",
                "details": db_health
            }
        except Exception as e:
            logger.error("Database health check failed: %s", str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_event_bus_health(self) -> Dict[str, Any]:
        """Check the health of the event bus.
        
        Returns:
            Dict[str, Any]: Event bus health status
        """
        logger.debug("Checking event bus health")
        
        if not self.event_bus:
            return {"status": "unhealthy", "error": "Event bus not initialized"}
        
        try:
            event_bus_health = await self.event_bus.health_check()
            # Determine overall status based on connection and Redis health
            is_healthy = event_bus_health.get("connected", False)
            if event_bus_health.get("redis_healthy") is False:
                is_healthy = False
                
            return {
                "status": "healthy" if is_healthy else "degraded",
                "details": event_bus_health
            }
        except Exception as e:
            logger.error("Event bus health check failed: %s", str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Check the health of the API server.
        
        Returns:
            Dict[str, Any]: API server health status
        """
        logger.debug("Checking API server health")
        
        # Placeholder implementation - in a real implementation this would
        # make an HTTP request to the API health endpoint
        return {
            "status": "unknown",
            "details": "API health check not yet implemented"
        }
    
    def _is_component_unhealthy(self, component_result: Dict[str, Any]) -> bool:
        """Check if a component result indicates an unhealthy state.
        
        Args:
            component_result (Dict[str, Any]): Component health check result
            
        Returns:
            bool: True if component is unhealthy, False otherwise
        """
        status = component_result.get("status", "unknown")
        return status in ["unhealthy", "critical"]
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get a simplified health summary.
        
        Returns:
            Dict[str, Any]: Simplified health summary
        """
        full_health = await self.check_all_health()
        
        return {
            "status": full_health["overall_status"],
            "timestamp": full_health["timestamp"],
            "database": full_health["components"]["database"]["status"],
            "event_bus": full_health["components"]["event_bus"]["status"],
            "api_server": full_health["components"]["api_server"]["status"]
        }


# Convenience function for easy usage
async def create_health_check_manager(database_manager: DatabaseManager = None,
                                    event_bus: EventBus = None) -> HealthCheckManager:
    """Create and initialize a health check manager instance.
    
    Args:
        database_manager (DatabaseManager, optional): Database manager instance
        event_bus (EventBus, optional): Event bus instance
        
    Returns:
        HealthCheckManager: Initialized health check manager instance
    """
    health_manager = HealthCheckManager(database_manager, event_bus)
    return health_manager
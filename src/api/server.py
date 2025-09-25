"""
API Endpoints Module

This module initializes the API endpoints layer of the application,
providing the base structure for internal REST API endpoints.
"""
from fastapi import FastAPI, HTTPException, Depends
from typing import Optional
import asyncio

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.utils.logger import get_logger


def create_api_server(
    database_manager: Optional[DatabaseManager] = None,
    event_bus: Optional[EventBus] = None
) -> FastAPI:
    """
    Create and configure the FastAPI server with dependencies
    
    Args:
        database_manager: Database manager instance
        event_bus: Event bus instance
        
    Returns:
        Configured FastAPI application
    """
    logger = get_logger(__name__)
    
    # Create FastAPI application
    app = FastAPI(
        title="YABOT Internal API",
        description="Internal REST API for YABOT system components",
        version="1.0.0",
        openapi_url="/openapi.json"
    )
    
    # Store dependencies in app state
    app.state.database_manager = database_manager
    app.state.event_bus = event_bus
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("Internal API server starting up")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Internal API server shutting down")
        # Close connections if needed
        if database_manager:
            await database_manager.close_connections()
        if event_bus:
            await event_bus.close()
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        health_status = {
            "status": "healthy",
            "component": "internal-api",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        
        # Check database connectivity if available
        if database_manager:
            try:
                db_health = await database_manager.health_check()
                # Ensure we return only JSON-serializable data
                if isinstance(db_health, dict):
                    # Filter out any non-serializable values
                    safe_db_health = {}
                    for key, value in db_health.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            safe_db_health[key] = value
                        else:
                            safe_db_health[key] = str(value)
                    health_status["database"] = safe_db_health
                else:
                    health_status["database"] = {"status": "healthy"}
            except Exception as e:
                health_status["database"] = {"error": str(e), "status": "unhealthy"}

        # Check event bus connectivity if available
        if event_bus:
            try:
                bus_health = await event_bus.health_check()
                # Ensure we return only JSON-serializable data
                if isinstance(bus_health, dict):
                    safe_bus_health = {}
                    for key, value in bus_health.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            safe_bus_health[key] = value
                        else:
                            safe_bus_health[key] = str(value)
                    health_status["event_bus"] = safe_bus_health
                else:
                    health_status["event_bus"] = {"status": "healthy"}
            except Exception as e:
                health_status["event_bus"] = {"error": str(e), "status": "unhealthy"}
        
        return health_status
    
    # Example endpoint for getting user state from MongoDB
    @app.get("/api/v1/user/{user_id}/state")
    async def get_user_state(user_id: str):
        if not database_manager:
            raise HTTPException(status_code=500, detail="Database manager not available")
        
        try:
            user_doc = await database_manager.get_user_from_mongo(user_id)
            if not user_doc:
                raise HTTPException(status_code=404, detail="User not found")
                
            return user_doc
        except Exception as e:
            logger.error(f"Error retrieving user state: {e}")
            raise HTTPException(status_code=500, detail="Error retrieving user state")
    
    # Example endpoint for getting subscription status from SQLite
    @app.get("/api/v1/user/{user_id}/subscription")
    async def get_user_subscription(user_id: str):
        if not database_manager:
            raise HTTPException(status_code=500, detail="Database manager not available")
        
        try:
            subscription = await database_manager.get_subscription_from_sqlite(user_id)
            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")
                
            return subscription
        except Exception as e:
            logger.error(f"Error retrieving user subscription: {e}")
            raise HTTPException(status_code=500, detail="Error retrieving user subscription")
    
    # Example endpoint for updating user preferences in MongoDB
    @app.put("/api/v1/user/{user_id}/preferences")
    async def update_user_preferences(user_id: str, preferences: dict):
        if not database_manager:
            raise HTTPException(status_code=500, detail="Database manager not available")
        
        try:
            # Update user in MongoDB
            result = await database_manager.update_user_in_mongo(
                user_id, 
                {"$set": {"preferences": preferences, "updated_at": "2025-01-15T10:30:00Z"}}
            )
            
            if not result:
                raise HTTPException(status_code=404, detail="User not found or update failed")
                
            # Publish event if event bus is available
            if event_bus:
                from src.events.models import BaseEvent
                from datetime import datetime
                event = BaseEvent(
                    event_id=f"preferences_updated_{user_id}_{int(datetime.utcnow().timestamp())}",
                    event_type="user_preferences_updated",
                    timestamp=datetime.utcnow(),
                    correlation_id=f"user_{user_id}",
                    user_id=user_id,
                    payload={"user_id": user_id, "preferences": preferences}
                )
                await event_bus.publish(event)
            
            return {"user_id": user_id, "preferences": preferences, "status": "updated"}
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            raise HTTPException(status_code=500, detail="Error updating user preferences")
    
    logger.info("Internal API server configured with dependencies")
    return app

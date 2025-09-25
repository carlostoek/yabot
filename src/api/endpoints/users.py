"""
User API Endpoints

Implements user-related API endpoints as specified in Requirement 4.2
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import asyncio

from src.services.user import UserService
from src.api.auth import JWTService
from src.utils.logger import get_logger
from src.database.manager import get_db_manager
from src.events.bus import get_event_bus


# Create a router for these endpoints
router = APIRouter(prefix="/api/v1", tags=["users"])

# Initialize dependencies
logger = get_logger(__name__)
jwt_service = JWTService()


async def get_user_service():
    """Dependency to get user service instance"""
    db_manager = get_db_manager()
    event_bus = get_event_bus()
    return UserService(db_manager, event_bus)


@router.get("/user/{user_id}/state")
async def get_user_state(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user state from MongoDB as specified in requirement 4.2.1
    """
    logger.info(f"Retrieving user state for user {user_id}")
    
    try:
        user_context = await user_service.get_user_context(user_id)
        
        if not user_context:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Return complete user context from MongoDB
        return {
            "user_id": user_id,
            "current_state": user_context["mongo_data"]["current_state"],
            "preferences": user_context["mongo_data"]["preferences"],
            "last_activity": user_context["mongo_data"]["current_state"]["session_data"]["last_activity"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user state: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/user/{user_id}/preferences")
async def update_user_preferences(
    user_id: str,
    preferences: Dict[str, Any],
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user preferences in MongoDB as specified in requirement 4.2.3
    """
    logger.info(f"Updating user preferences for user {user_id}")
    
    try:
        # Get current state to merge with new preferences
        current_context = await user_service.get_user_context(user_id)
        if not current_context:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update the current state with new preferences
        current_state = current_context["mongo_data"]["current_state"]
        current_state["preferences"].update(preferences)
        
        # Update user state in MongoDB
        success = await user_service.update_user_state(user_id, current_state)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update user preferences")
        
        return {
            "user_id": user_id,
            "status": "updated",
            "preferences": current_state["preferences"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}/subscription")
async def get_user_subscription(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Query user subscription status from SQLite as specified in requirement 4.2.4
    """
    logger.info(f"Querying user subscription for user {user_id}")
    
    try:
        subscription_status = await user_service.get_user_subscription_status(user_id)
        
        if subscription_status is None:
            raise HTTPException(status_code=404, detail="User subscription not found")
        
        return {
            "user_id": user_id,
            "subscription_status": subscription_status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying user subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Additional endpoints would go here


__all__ = ["router"]

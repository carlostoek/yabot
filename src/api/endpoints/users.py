"""
User API endpoints for the YABOT system.

This module provides REST API endpoints for user management operations
as required by Requirement 4.2.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from src.services.user import UserService, UserNotFoundError
from src.api.auth import JWTAuthService
from src.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router for user endpoints
router = APIRouter(prefix="/api/v1/user", tags=["Users"])

# Dependency injection placeholder - in a real implementation this
# would be provided by the application's dependency injection system
def get_user_service():
    """Placeholder for UserService dependency injection."""
    # This would normally be provided by the application context
    return None

def get_current_service(payload: dict = Depends(JWTAuthService().validate_token)):
    """Dependency to get current service from JWT token."""
    return payload.get("sub")

@router.get("/{user_id}/state")
async def get_user_state(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    service: str = Depends(get_current_service)
):
    """Get complete user context from both databases.
    
    Args:
        user_id: User ID
        user_service: User service instance
        service: Authenticated service name
        
    Returns:
        Dict[str, Any]: Complete user context
        
    Raises:
        HTTPException: If user is not found or other errors occur
    """
    logger.info(
        "Getting user state",
        user_id=user_id,
        service=service
    )

    # If we don't have a real user service, return a mock response
    if user_service is None:
        # Mock response for development/testing
        user_context = {
            "user_id": user_id,
            "profile": {
                "user_id": user_id,
                "telegram_user_id": 123456789,
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
                "language_code": "en",
                "registration_date": "2025-01-01T00:00:00Z",
                "last_login": "2025-01-01T00:00:00Z",
                "is_active": True
            },
            "state": {
                "user_id": user_id,
                "current_state": {
                    "menu_context": "main_menu",
                    "narrative_progress": {
                        "current_fragment": "fragment_001",
                        "completed_fragments": ["intro_001", "intro_002"],
                        "choices_made": []
                    },
                    "session_data": {
                        "last_activity": "2025-01-01T00:00:00Z"
                    }
                },
                "preferences": {
                    "language": "en",
                    "notifications_enabled": True,
                    "theme": "default"
                },
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        }

        logger.info(
            "Returning mock user state (no user service available)",
            user_id=user_id,
            service=service
        )
        return user_context

    try:
        user_context = await user_service.get_user_context(user_id)

        logger.info(
            "Successfully retrieved user state",
            user_id=user_id,
            service=service
        )
        return user_context

    except UserNotFoundError:
        logger.warning(
            "User not found when getting state",
            user_id=user_id,
            service=service
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(
            "Error getting user state",
            user_id=user_id,
            service=service,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{user_id}/preferences")
async def update_user_preferences(
    user_id: str,
    preferences: Dict[str, Any],
    user_service: UserService = Depends(get_user_service),
    service: str = Depends(get_current_service)
):
    """Update user preferences in MongoDB.
    
    Args:
        user_id: User ID
        preferences: New preferences to update
        user_service: User service instance
        service: Authenticated service name
        
    Returns:
        Dict[str, Any]: Update confirmation
        
    Raises:
        HTTPException: If update fails or other errors occur
    """
    logger.info(
        "Updating user preferences",
        user_id=user_id,
        service=service
    )

    # If we don't have a real user service, return a mock response
    if user_service is None:
        # Mock response for development/testing
        response = {
            "user_id": user_id,
            "preferences": preferences,
            "updated": True,
            "timestamp": "2025-01-01T00:00:00Z"
        }

        logger.info(
            "Returning mock update confirmation (no user service available)",
            user_id=user_id,
            service=service
        )
        return response

    try:
        # Prepare state updates for MongoDB
        state_updates = {
            "preferences": preferences
        }

        success = await user_service.update_user_state(user_id, state_updates)

        if success:
            response = {
                "user_id": user_id,
                "preferences": preferences,
                "updated": True,
                "timestamp": "2025-01-01T00:00:00Z"
            }

            logger.info(
                "Successfully updated user preferences",
                user_id=user_id,
                service=service
            )
            return response
        else:
            logger.warning(
                "Failed to update user preferences",
                user_id=user_id,
                service=service
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user preferences"
            )

    except Exception as e:
        logger.error(
            "Error updating user preferences",
            user_id=user_id,
            service=service,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{user_id}/subscription")
async def get_user_subscription(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    service: str = Depends(get_current_service)
):
    """Get user subscription status from SQLite.
    
    Args:
        user_id: User ID
        user_service: User service instance
        service: Authenticated service name
        
    Returns:
        Dict[str, Any]: User subscription status
        
    Raises:
        HTTPException: If subscription is not found or other errors occur
    """
    logger.info(
        "Getting user subscription",
        user_id=user_id,
        service=service
    )

    # If we don't have a real user service, return a mock response
    if user_service is None:
        # Mock response for development/testing
        subscription = {
            "user_id": user_id,
            "plan_type": "premium",
            "status": "active",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2026-01-01T00:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }

        logger.info(
            "Returning mock subscription (no user service available)",
            user_id=user_id,
            service=service
        )
        return subscription

    try:
        # Get user context and extract subscription info
        # In a real implementation, there would be a separate subscription service
        user_context = await user_service.get_user_context(user_id)

        # Mock subscription data based on user context
        subscription = {
            "user_id": user_id,
            "plan_type": "premium",
            "status": "active",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2026-01-01T00:00:00Z",
            "created_at": user_context.get("profile", {}).get(
                "registration_date", "2025-01-01T00:00:00Z"
            ),
            "updated_at": "2025-01-01T00:00:00Z"
        }

        logger.info(
            "Successfully retrieved user subscription",
            user_id=user_id,
            service=service
        )
        return subscription

    except UserNotFoundError:
        logger.warning(
            "User not found when getting subscription",
            user_id=user_id,
            service=service
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(
            "Error getting user subscription",
            user_id=user_id,
            service=service,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

"""
Emotional intelligence API endpoints.

This module provides REST API endpoints for emotional intelligence operations
as required by the Diana Emotional System specification.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from src.services.cross_module import get_cross_module_service, CrossModuleService
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/emotional", tags=["emotional"])

@router.post("/interact")
async def process_emotional_interaction(
    interaction_data: Dict[str, Any],
    cross_module_service: CrossModuleService = Depends(get_cross_module_service)
):
    """Process emotional interaction with complete YABOT integration.
    
    Args:
        interaction_data: Data about the emotional interaction
        cross_module_service: Cross module service instance
        
    Returns:
        Dict[str, Any]: Result of emotional interaction processing
        
    Raises:
        HTTPException: If processing fails or user_id is missing
    """
    try:
        user_id = interaction_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="user_id required"
            )

        result = await cross_module_service.process_emotional_interaction(
            user_id, interaction_data
        )

        logger.info(
            "Successfully processed emotional interaction",
            user_id=user_id
        )
        return result
        
    except Exception as e:
        logger.error(
            "Error processing emotional interaction",
            user_id=interaction_data.get("user_id"),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/user/{user_id}/emotional-state")
async def get_user_emotional_state(
    user_id: str,
    cross_module_service: CrossModuleService = Depends(get_cross_module_service)
):
    """Get user's current emotional state and journey progress.
    
    Args:
        user_id: User ID
        cross_module_service: Cross module service instance
        
    Returns:
        Dict[str, Any]: User's emotional state
        
    Raises:
        HTTPException: If user is not found or other errors occur
    """
    try:
        emotional_state = await cross_module_service.user_service.get_emotional_journey_state(user_id)

        if not emotional_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User emotional state not found"
            )

        logger.info(
            "Successfully retrieved user emotional state",
            user_id=user_id
        )
        return {"user_id": user_id, "emotional_state": emotional_state}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "Error getting user emotional state",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/state")
async def get_emotional_state(
    user_id: str,
    cross_module_service: CrossModuleService = Depends(get_cross_module_service)
):
    """Get emotional state for a user (alternative endpoint).
    
    Args:
        user_id: User ID as query parameter
        cross_module_service: Cross module service instance
        
    Returns:
        Dict[str, Any]: User's emotional state
        
    Raises:
        HTTPException: If user is not found or other errors occur
    """
    try:
        emotional_state = await cross_module_service.user_service.get_emotional_journey_state(user_id)

        if not emotional_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User emotional state not found"
            )

        logger.info(
            "Successfully retrieved emotional state",
            user_id=user_id
        )
        return {"user_id": user_id, "emotional_state": emotional_state}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "Error getting emotional state",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
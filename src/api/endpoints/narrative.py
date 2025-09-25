"""
Narrative API Endpoints

Implements narrative-related API endpoints as specified in Requirement 4.2
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import asyncio

from src.services.narrative import NarrativeService
from src.api.auth import JWTService
from src.utils.logger import get_logger
from src.database.manager import get_db_manager
from src.events.bus import get_event_bus


# Create a router for these endpoints
router = APIRouter(prefix="/api/v1", tags=["narrative"])

# Initialize dependencies
logger = get_logger(__name__)
jwt_service = JWTService()


async def get_narrative_service():
    """Dependency to get narrative service instance"""
    db_manager = get_db_manager()
    event_bus = get_event_bus()
    return NarrativeService(db_manager, event_bus)


@router.get("/narrative/{fragment_id}")
async def get_narrative_fragment(
    fragment_id: str,
    narrative_service: NarrativeService = Depends(get_narrative_service)
):
    """
    Get narrative content from MongoDB as specified in requirement 4.2.2
    """
    logger.info(f"Retrieving narrative fragment {fragment_id}")
    
    try:
        fragment = await narrative_service.get_narrative_fragment(fragment_id)
        
        if not fragment:
            raise HTTPException(status_code=404, detail="Narrative fragment not found")
        
        # Return story fragment with metadata
        return {
            "fragment_id": fragment_id,
            "title": fragment.get("title"),
            "content": fragment.get("content"),
            "choices": fragment.get("choices", []),
            "metadata": fragment.get("metadata", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving narrative fragment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/narrative/{fragment_id}/metadata")
async def get_narrative_metadata(
    fragment_id: str,
    narrative_service: NarrativeService = Depends(get_narrative_service)
):
    """
    Get metadata for a narrative fragment
    """
    logger.info(f"Retrieving metadata for narrative fragment {fragment_id}")
    
    try:
        fragment = await narrative_service.get_narrative_fragment(fragment_id)
        
        if not fragment:
            raise HTTPException(status_code=404, detail="Narrative fragment not found")
        
        return fragment.get("metadata", {})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving narrative metadata: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/narrative/{user_id}/progress")
async def update_narrative_progress(
    user_id: str,
    progress_data: Dict[str, Any],
    narrative_service: NarrativeService = Depends(get_narrative_service)
):
    """
    Update user's narrative progress
    """
    logger.info(f"Updating narrative progress for user {user_id}")
    
    try:
        success = await narrative_service.update_user_narrative_progress(user_id, progress_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update narrative progress")
        
        return {
            "user_id": user_id,
            "status": "updated",
            "progress_data": progress_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating narrative progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Additional endpoints would go here


__all__ = ["router"]

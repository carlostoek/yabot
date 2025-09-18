"""
Narrative API endpoints for the YABOT system.

This module provides REST API endpoints for narrative management operations
as required by Requirement 4.2.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.services.narrative import (
    NarrativeService, 
    NarrativeFragmentNotFoundError
)
from src.api.auth import JWTAuthService
from src.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router for narrative endpoints
router = APIRouter(prefix="/api/v1/narrative", tags=["Narrative"])


# Dependency injection placeholder - in a real implementation this
# would be provided by the application's dependency injection system
def get_narrative_service():
    """Placeholder for NarrativeService dependency injection."""
    # This would normally be provided by the application context
    return None


def get_current_service(payload: dict = Depends(JWTAuthService().validate_token)):
    """Dependency to get current service from JWT token."""
    return payload.get("sub")


@router.get("/{fragment_id}")
async def get_narrative_fragment(
    fragment_id: str,
    narrative_service: NarrativeService = Depends(get_narrative_service),
    service: str = Depends(get_current_service)
):
    """Get narrative fragment by ID.
    
    Args:
        fragment_id: Narrative fragment ID
        narrative_service: Narrative service instance
        service: Authenticated service name
        
    Returns:
        Dict[str, Any]: Narrative fragment data
        
    Raises:
        HTTPException: If fragment is not found or other errors occur
    """
    logger.info(
        "Getting narrative fragment",
        fragment_id=fragment_id,
        service=service
    )

    # If we don't have a real narrative service, return a mock response
    if narrative_service is None:
        # Mock response for development/testing
        if fragment_id == "fragment_001":
            fragment = {
                "fragment_id": "fragment_001",
                "title": "El Comienzo",
                "content": "Tu aventura comienza aquí...",
                "choices": [
                    {
                        "id": "choice_a", 
                        "text": "Explorar el bosque", 
                        "next_fragment": "forest_001"
                    },
                    {
                        "id": "choice_b", 
                        "text": "Ir al pueblo", 
                        "next_fragment": "village_001"
                    }
                ],
                "metadata": {
                    "difficulty": "easy",
                    "tags": ["intro", "adventure"],
                    "vip_required": False
                },
                "created_at": "2025-01-01T00:00:00Z"
            }

            logger.info(
                "Returning mock narrative fragment (no narrative service available)",
                fragment_id=fragment_id,
                service=service
            )
            return fragment
        else:
            logger.warning(
                "Narrative fragment not found (mock response)",
                fragment_id=fragment_id,
                service=service
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Narrative fragment not found"
            )

    try:
        fragment = await narrative_service.get_narrative_fragment(fragment_id)

        logger.info(
            "Successfully retrieved narrative fragment",
            fragment_id=fragment_id,
            service=service
        )
        return fragment

    except NarrativeFragmentNotFoundError:
        logger.warning(
            "Narrative fragment not found",
            fragment_id=fragment_id,
            service=service
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Narrative fragment not found"
        )
    except Exception as e:
        logger.error(
            "Error getting narrative fragment",
            fragment_id=fragment_id,
            service=service,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
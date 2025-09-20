# src/api/endpoints/narrative.py

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict

from src.modules.narrative.fragment_manager import NarrativeFragmentManager, FragmentNotFoundError
from src.shared.api.auth import authenticate_module_request
from src.dependencies import get_narrative_fragment_manager

router = APIRouter()

@router.get("/narrative/progress/{user_id}", response_model=Dict[str, Any])
async def get_narrative_progress(
    user_id: str,
    fragment_manager: NarrativeFragmentManager = Depends(get_narrative_fragment_manager),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Retrieves the narrative progress for a given user.
    """
    try:
        progress = await fragment_manager.get_user_progress(user_id)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/narrative/fragment/{fragment_id}", response_model=Dict[str, Any])
async def get_narrative_fragment(
    fragment_id: str,
    user_id: str, # user_id is required for VIP check
    fragment_manager: NarrativeFragmentManager = Depends(get_narrative_fragment_manager),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Retrieves a narrative fragment by its ID.
    """
    try:
        fragment = await fragment_manager.get_fragment(fragment_id, user_id)
        return fragment
    except FragmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

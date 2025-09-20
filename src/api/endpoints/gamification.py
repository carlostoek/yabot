# src/api/endpoints/gamification.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from src.modules.gamification.mission_manager import MissionManager
from src.database.schemas.gamification import Mission
from src.shared.api.auth import authenticate_module_request
from src.dependencies import get_mission_manager

router = APIRouter()

@router.get("/gamification/missions/{user_id}", response_model=List[Mission])
async def get_user_missions(
    user_id: str,
    mission_manager: MissionManager = Depends(get_mission_manager),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Retrieves the missions for a given user.
    """
    try:
        missions = await mission_manager.get_user_missions(user_id)
        return missions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

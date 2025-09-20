from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from src.services.cross_module import CrossModuleService
from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.modules.gamification.item_manager import ItemManager
from src.services.narrative import NarrativeService
from src.shared.api.auth import authenticate_module_request

router = APIRouter()

@router.post("/narrative/check-access/{user_id}/{fragment_id}")
async def check_narrative_access(
    user_id: str,
    fragment_id: str,
    cross_module_service: CrossModuleService = Depends(),
    auth: str = Depends(authenticate_module_request)
):
    """Check if a user can access specific narrative content"""
    can_access = await cross_module_service.can_access_narrative_content(user_id, fragment_id)
    return {"can_access": can_access, "user_id": user_id, "fragment_id": fragment_id}

@router.post("/narrative/make-choice/{user_id}/{fragment_id}")
async def make_narrative_choice(
    user_id: str,
    fragment_id: str,
    choice_data: Dict[str, Any],
    cross_module_service: CrossModuleService = Depends(),
    auth: str = Depends(authenticate_module_request)
):
    """Process a narrative choice and update all relevant systems"""
    try:
        result = await cross_module_service.process_narrative_choice(user_id, fragment_id, choice_data)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reaction/{user_id}")
async def handle_user_reaction(
    user_id: str,
    reaction_data: Dict[str, Any],
    cross_module_service: CrossModuleService = Depends(),
    auth: str = Depends(authenticate_module_request)
):
    """Handle user reactions that impact multiple modules"""
    try:
        message_id = reaction_data.get("message_id")
        reaction_type = reaction_data.get("reaction_type")
        await cross_module_service.handle_reaction(user_id, message_id, reaction_type)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# src/api/endpoints/admin.py

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.modules.admin.access_control import AccessControl
from src.modules.admin.subscription_manager import SubscriptionManager
from src.modules.admin.notification_system import NotificationSystem
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.modules.gamification.mission_manager import MissionManager
from src.shared.api.auth import authenticate_module_request
from src.dependencies import get_access_control, get_besitos_wallet, get_subscription_manager, get_notification_system, get_mission_manager

router = APIRouter()

@router.get("/admin/user/{user_id}/besitos")
async def get_user_besitos_balance(
    user_id: str,
    access_control: AccessControl = Depends(get_access_control),
    besitos_wallet: BesitosWallet = Depends(get_besitos_wallet),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Retrieves the besitos balance for a given user.
    Requires admin privileges.
    """
    # A real implementation would check for admin privileges from the request
    # For now, we assume the inter-module authentication is enough.
    
    try:
        balance = await besitos_wallet.get_balance(user_id)
        return {"user_id": user_id, "besitos_balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/user/{user_id}/besitos/add")
async def add_user_besitos(
    user_id: str,
    amount: int,
    reason: str = "Admin adjustment",
    access_control: AccessControl = Depends(get_access_control),
    besitos_wallet: BesitosWallet = Depends(get_besitos_wallet),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Adds besitos to a user's balance.
    Requires admin privileges.
    """
    try:
        transaction = await besitos_wallet.add_besitos(user_id, amount, reason)
        return {
            "user_id": user_id,
            "amount_added": amount,
            "new_balance": await besitos_wallet.get_balance(user_id),
            "transaction_id": transaction.transaction_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/user/{user_id}/besitos/deduct")
async def deduct_user_besitos(
    user_id: str,
    amount: int,
    reason: str = "Admin adjustment",
    access_control: AccessControl = Depends(get_access_control),
    besitos_wallet: BesitosWallet = Depends(get_besitos_wallet),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Deducts besitos from a user's balance.
    Requires admin privileges.
    """
    try:
        transaction = await besitos_wallet.spend_besitos(user_id, amount, reason)
        return {
            "user_id": user_id,
            "amount_deducted": amount,
            "new_balance": await besitos_wallet.get_balance(user_id),
            "transaction_id": transaction.transaction_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/user/{user_id}/subscription")
async def get_user_subscription(
    user_id: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    access_control: AccessControl = Depends(get_access_control),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Retrieves subscription status for a given user.
    Requires admin privileges.
    """
    try:
        subscription_status = await subscription_manager.check_vip_status(user_id)
        return {
            "user_id": user_id,
            "is_vip": subscription_status.is_vip,
            "subscription_end_date": subscription_status.end_date,
            "subscription_plan": subscription_status.plan_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/user/{user_id}/subscription/grant")
async def grant_user_subscription(
    user_id: str,
    plan_type: str,
    duration_days: int,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    access_control: AccessControl = Depends(get_access_control),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Grants a subscription to a user.
    Requires admin privileges.
    """
    try:
        subscription = await subscription_manager.create_subscription(
            user_id, plan_type, duration_days
        )
        return {
            "user_id": user_id,
            "subscription_id": subscription.subscription_id,
            "plan_type": subscription.plan_type,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/notification/send")
async def send_notification(
    user_id: str,
    message: str,
    notification_type: str = "info",
    notification_system: NotificationSystem = Depends(get_notification_system),
    access_control: AccessControl = Depends(get_access_control),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Sends a notification to a user.
    Requires admin privileges.
    """
    try:
        await notification_system.send_notification(user_id, message, notification_type)
        return {
            "status": "success",
            "message": "Notification sent successfully",
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/user/{user_id}/missions")
async def get_user_missions(
    user_id: str,
    mission_manager: MissionManager = Depends(get_mission_manager),
    access_control: AccessControl = Depends(get_access_control),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Retrieves all missions for a given user.
    Requires admin privileges.
    """
    try:
        # This would require implementing a method to get all missions for a user
        # For now, we'll return a placeholder
        return {
            "user_id": user_id,
            "missions": []  # Placeholder - would need to implement in mission_manager
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/mission/assign")
async def assign_mission_to_user(
    user_id: str,
    mission_type: str,
    mission_manager: MissionManager = Depends(get_mission_manager),
    access_control: AccessControl = Depends(get_access_control),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Assigns a mission to a user.
    Requires admin privileges.
    """
    try:
        mission = await mission_manager.assign_mission(user_id, mission_type)
        return {
            "user_id": user_id,
            "mission_id": mission.mission_id,
            "mission_type": mission.mission_type,
            "status": "assigned"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/command")
async def execute_admin_command(
    command: Dict[str, Any],
    access_control: AccessControl = Depends(get_access_control),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    notification_system: NotificationSystem = Depends(get_notification_system),
    module_name: str = Depends(authenticate_module_request),
):
    """
    Executes an admin command.
    Requires admin privileges.
    """
    # A real implementation would check for admin privileges from the request
    # For now, we assume the inter-module authentication is enough.
    
    # This is a placeholder for a more complex command processing logic
    # that would be implemented in a dedicated AdminCommandProcessor.
    command_name = command.get("name")
    args = command.get("args", {})
    
    if command_name == "grant_vip":
        user_id = args.get("user_id")
        plan_type = args.get("plan_type", "premium")
        duration_days = args.get("duration_days", 30)
        
        try:
            subscription = await subscription_manager.create_subscription(
                user_id, plan_type, duration_days
            )
            return {
                "status": "success", 
                "message": f"VIP granted to {user_id}",
                "subscription_id": subscription.subscription_id
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    elif command_name == "send_notification":
        user_id = args.get("user_id")
        message = args.get("message")
        notification_type = args.get("type", "info")
        
        try:
            await notification_system.send_notification(user_id, message, notification_type)
            return {"status": "success", "message": f"Notification sent to {user_id}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    raise HTTPException(status_code=400, detail=f"Unknown command: {command_name}")

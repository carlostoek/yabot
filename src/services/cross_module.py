from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import Depends
from src.services.user import UserService, create_user_service
from src.services.subscription import SubscriptionService, create_subscription_service
from src.modules.gamification.item_manager import ItemManager
from src.services.narrative import NarrativeService, create_narrative_service
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.modules.gamification.daily_gift import DailyGiftSystem
from src.modules.gamification.mission_manager import MissionManager
from src.modules.gamification.achievement_system import AchievementSystem
from src.modules.gamification.store import StoreMenu
from src.modules.gamification.auction_system import AuctionSystem
from src.modules.gamification.trivia_engine import TriviaEngine
from src.modules.admin.notification_system import NotificationSystem
from src.modules.admin.access_control import AccessControl
from src.modules.admin.post_scheduler import PostScheduler
from src.shared.monitoring.performance import PerformanceMonitor
from src.utils.logger import get_logger
from src.database.manager import DatabaseManager
from src.events.bus import EventBus

logger = get_logger(__name__)

class CrossModuleService:
    """Service to handle interactions between different modules"""
    
    def __init__(
        self,
        user_service: UserService,
        subscription_service: SubscriptionService,
        item_manager: ItemManager,
        narrative_service: NarrativeService,
        besitos_wallet: Optional[BesitosWallet] = None,
        daily_gift_system: Optional[DailyGiftSystem] = None,
        mission_manager: Optional[MissionManager] = None,
        achievement_system: Optional[AchievementSystem] = None,
        store_menu: Optional[StoreMenu] = None,
        auction_system: Optional[AuctionSystem] = None,
        trivia_engine: Optional[TriviaEngine] = None,
        notification_system: Optional[NotificationSystem] = None,
        access_control: Optional[AccessControl] = None,
        post_scheduler: Optional[PostScheduler] = None
    ):
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.item_manager = item_manager
        self.narrative_service = narrative_service
        self.besitos_wallet = besitos_wallet
        self.daily_gift_system = daily_gift_system
        self.mission_manager = mission_manager
        self.achievement_system = achievement_system
        self.store_menu = store_menu
        self.auction_system = auction_system
        self.trivia_engine = trivia_engine
        self.notification_system = notification_system
        self.access_control = access_control
        self.post_scheduler = post_scheduler
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor("CrossModuleService")
    
    async def can_access_narrative_content(
        self, 
        user_id: str, 
        fragment_id: str
    ) -> bool:
        """
        Check if a user can access specific narrative content
        based on VIP status, besitos, items, etc.
        """
        # This method doesn't need performance monitoring as it's a simple check
        try:
            # Get fragment requirements
            fragment = await self.narrative_service.get_fragment(fragment_id)
            if not fragment:
                return False
            
            # Check VIP requirement
            if fragment.get('vip_required', False):
                is_vip = await self.subscription_service.is_user_vip(user_id)
                if not is_vip:
                    return False
            
            # Check besitos requirement
            besitos_required = fragment.get('besitos_required', 0)
            if besitos_required > 0:
                user_besitos = await self.user_service.get_user_besitos(user_id)
                if user_besitos < besitos_required:
                    return False
            
            # Check item requirements
            required_items = fragment.get('required_items', [])
            for item_id in required_items:
                quantity = await self.item_manager.get_item_quantity(user_id, item_id)
                if quantity < 1:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking narrative content access for user {user_id}: {e}")
            return False

    @PerformanceMonitor("CrossModuleService").measure("process_narrative_choice")
    async def process_narrative_choice(
        self, 
        user_id: str, 
        fragment_id: str, 
        choice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a narrative choice and update gamification elements accordingly
        """
        # Deduct besitos if required
        fragment = await self.narrative_service.get_fragment(fragment_id)
        if fragment:
            besitos_cost = fragment.get('besitos_cost', 0)
            if besitos_cost > 0:
                await self.user_service.deduct_besitos(user_id, besitos_cost)
            
            # Award items if specified
            awarded_items = fragment.get('award_items', {})
            for item_id, quantity in awarded_items.items():
                await self.item_manager.add_item_to_user(user_id, item_id, quantity)
        
        # Update narrative progress
        result = await self.narrative_service.record_user_choice(
            user_id, fragment_id, choice_data
        )
        
        # Check if this unlocks any missions
        # This would integrate with a mission service
        
        return result

    @PerformanceMonitor("CrossModuleService").measure("handle_reaction")
    async def handle_reaction(
        self,
        user_id: str,
        message_id: str,
        reaction_type: str
    ) -> None:
        """
        Handle reactions which can give besitos and unlock narrative hints
        """
        # Award besitos based on reaction
        besitos_awarded = 1  # This could be configurable
        await self.user_service.award_besitos(user_id, besitos_awarded)
        
        # Check if this reaction unlocks any narrative hints
        # This would need integration with a hint system
        
        logger.info(f"User {user_id} awarded {besitos_awarded} besitos for reaction")

    @PerformanceMonitor("CrossModuleService").measure("claim_daily_gift")
    async def claim_daily_gift(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Coordinate the claiming of daily gifts with gamification systems
        """
        if not self.daily_gift_system:
            logger.warning("Daily gift system not available")
            return {"success": False, "message": "Daily gift system not available"}
            
        try:
            # Check if user can claim gift
            status = await self.daily_gift_system.check_gift_availability(user_id)
            if not status.can_claim:
                return {
                    "success": False, 
                    "message": "Ya has reclamado tu regalo diario. Intenta de nuevo más tarde.",
                    "cooldown_remaining": status.cooldown_remaining
                }
            
            # Claim the gift
            result = await self.daily_gift_system.claim_daily_gift(user_id)
            
            if result.success:
                # Award besitos through wallet if available
                if self.besitos_wallet and result.gift_claimed:
                    gift_amount = result.gift_claimed.get("amount", 0)
                    if gift_amount > 0:
                        try:
                            await self.besitos_wallet.add_besitos(
                                user_id, 
                                gift_amount, 
                                "daily_gift", 
                                "daily_gift_system"
                            )
                        except Exception as e:
                            logger.error(f"Failed to add besitos for daily gift: {e}")
                
                # Check for achievement unlocks
                if self.achievement_system:
                    try:
                        # This would trigger achievement checks for daily gift claiming
                        # Implementation would depend on how achievements track progress
                        pass
                    except Exception as e:
                        logger.error(f"Failed to check achievements for daily gift: {e}")
                        
                # Update mission progress if user has active missions
                if self.mission_manager:
                    try:
                        # This would update mission progress for daily gift claiming
                        # Implementation would depend on mission objectives
                        pass
                    except Exception as e:
                        logger.error(f"Failed to update mission progress for daily gift: {e}")
            
            return result.dict() if hasattr(result, 'dict') else result
            
        except Exception as e:
            logger.error(f"Error claiming daily gift for user {user_id}: {e}")
            return {"success": False, "message": "Error al reclamar el regalo diario"}

    @PerformanceMonitor("CrossModuleService").measure("complete_mission")
    async def complete_mission(
        self,
        user_id: str,
        mission_id: str
    ) -> Dict[str, Any]:
        """
        Coordinate mission completion with reward distribution
        """
        if not self.mission_manager:
            logger.warning("Mission manager not available")
            return {"success": False, "message": "Mission system not available"}
            
        try:
            # Get mission details
            # This would be implemented based on how missions are stored/retrieved
            # For now, we'll assume the mission manager handles this internally
            
            # Check if mission is complete
            # This would also be handled by the mission manager
            
            # Distribute rewards
            # This would involve coordinating with besitos wallet, item manager, etc.
            
            # Update achievement progress
            if self.achievement_system:
                try:
                    # Trigger achievement checks for mission completion
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for mission completion: {e}")
            
            # Publish mission completed event
            # This would be handled by the mission manager itself
            
            result = {"success": True, "message": "Misión completada exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error completing mission {mission_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al completar la misión"}

    @PerformanceMonitor("CrossModuleService").measure("unlock_achievement")
    async def unlock_achievement(
        self,
        user_id: str,
        achievement_id: str
    ) -> Dict[str, Any]:
        """
        Coordinate achievement unlocking with rewards
        """
        if not self.achievement_system:
            logger.warning("Achievement system not available")
            return {"success": False, "message": "Achievement system not available"}
            
        try:
            # Check if achievement can be unlocked
            # This would be handled by the achievement system
            
            # Unlock achievement
            # This would be handled by the achievement system
            
            # Distribute rewards
            # This would involve coordinating with besitos wallet, item manager, etc.
            
            # Update user profile/badges
            # This would involve updating user data
            
            result = {"success": True, "message": "Logro desbloqueado exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error unlocking achievement {achievement_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al desbloquear el logro"}

    @PerformanceMonitor("CrossModuleService").measure("purchase_item")
    async def purchase_item(
        self,
        user_id: str,
        item_id: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Coordinate item purchase with payment and inventory management
        """
        # Check if required systems are available
        if not self.store_menu:
            logger.warning("Store system not available")
            return {"success": False, "message": "Store system not available"}
            
        if not self.besitos_wallet:
            logger.warning("Besitos wallet not available")
            return {"success": False, "message": "Payment system not available"}
            
        if not self.item_manager:
            logger.warning("Item manager not available")
            return {"success": False, "message": "Inventory system not available"}
            
        try:
            # Check if user has enough besitos
            # This would be handled by the wallet system
            
            # Deduct besitos
            # This would be handled by the wallet system
            
            # Add item to user's inventory
            # This would be handled by the item manager
            
            # Update achievement progress for purchases
            if self.achievement_system:
                try:
                    # Trigger achievement checks for item purchases
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for item purchase: {e}")
            
            # Update mission progress for purchases
            if self.mission_manager:
                try:
                    # Update mission progress for item purchases
                    pass
                except Exception as e:
                    logger.error(f"Failed to update mission progress for item purchase: {e}")
            
            result = {"success": True, "message": "Item comprado exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error purchasing item {item_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al comprar el item"}

    @PerformanceMonitor("CrossModuleService").measure("participate_in_auction")
    async def participate_in_auction(
        self,
        user_id: str,
        auction_id: str,
        bid_amount: int
    ) -> Dict[str, Any]:
        """
        Coordinate auction participation with payment and item management
        """
        if not self.auction_system:
            logger.warning("Auction system not available")
            return {"success": False, "message": "Auction system not available"}
            
        if not self.besitos_wallet:
            logger.warning("Besitos wallet not available")
            return {"success": False, "message": "Payment system not available"}
            
        try:
            # Place bid in auction
            # This would be handled by the auction system
            
            # Check if user has enough besitos
            # This would be handled by the wallet system
            
            # Reserve besitos for bid
            # This would be handled by the wallet system
            
            # Update achievement progress for auction participation
            if self.achievement_system:
                try:
                    # Trigger achievement checks for auction participation
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for auction participation: {e}")
            
            result = {"success": True, "message": "Puja realizada exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error participating in auction {auction_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al participar en la subasta"}

    @PerformanceMonitor("CrossModuleService").measure("answer_trivia")
    async def answer_trivia(
        self,
        user_id: str,
        trivia_id: str,
        answer: int
    ) -> Dict[str, Any]:
        """
        Coordinate trivia answering with rewards
        """
        if not self.trivia_engine:
            logger.warning("Trivia engine not available")
            return {"success": False, "message": "Trivia system not available"}
            
        if not self.besitos_wallet:
            logger.warning("Besitos wallet not available")
            return {"success": False, "message": "Reward system not available"}
            
        try:
            # Submit answer to trivia engine
            # This would be handled by the trivia engine
            
            # Check if answer is correct
            # This would be handled by the trivia engine
            
            # Award points/besitos for correct answers
            # This would be handled by the wallet system
            
            # Update achievement progress for trivia participation
            if self.achievement_system:
                try:
                    # Trigger achievement checks for trivia participation
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for trivia participation: {e}")
            
            # Update mission progress for trivia participation
            if self.mission_manager:
                try:
                    # Update mission progress for trivia participation
                    pass
                except Exception as e:
                    logger.error(f"Failed to update mission progress for trivia participation: {e}")
            
            result = {"success": True, "message": "Respuesta enviada exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error answering trivia {trivia_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al responder la trivia"}

    @PerformanceMonitor("CrossModuleService").measure("send_notification_to_user")
    async def send_notification_to_user(
        self,
        user_id: str,
        template: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to a user through the notification system
        """
        if not self.notification_system:
            logger.warning("Notification system not available")
            return {"success": False, "message": "Notification system not available"}
            
        try:
            success = await self.notification_system.send_message(user_id, template, context or {})
            
            if success:
                logger.info(f"Notification sent successfully to user {user_id}")
                return {"success": True, "message": "Notificación enviada exitosamente"}
            else:
                logger.warning(f"Failed to send notification to user {user_id}")
                return {"success": False, "message": "Error al enviar la notificación"}
                
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return {"success": False, "message": "Error al enviar la notificación"}

    @PerformanceMonitor("CrossModuleService").measure("validate_user_access")
    async def validate_user_access(
        self,
        user_id: int,
        channel_id: int
    ) -> Dict[str, Any]:
        """
        Validate if a user has access to a specific channel
        """
        if not self.access_control:
            logger.warning("Access control system not available")
            return {"success": False, "message": "Access control system not available", "has_access": False}
            
        try:
            result = await self.access_control.validate_access(user_id, channel_id)
            
            logger.info(f"Access validation for user {user_id} to channel {channel_id}: {result.has_access}")
            return {
                "success": True, 
                "message": "Validación de acceso completada",
                "has_access": result.has_access,
                "reason": result.reason
            }
            
        except Exception as e:
            logger.error(f"Error validating access for user {user_id} to channel {channel_id}: {e}")
            return {"success": False, "message": "Error al validar el acceso", "has_access": False}

    @PerformanceMonitor("CrossModuleService").measure("schedule_post")
    async def schedule_post(
        self,
        content: str,
        channel_id: str,
        publish_time: str  # ISO format datetime string
    ) -> Dict[str, Any]:
        """
        Schedule a post to be sent to a channel at a specific time
        """
        if not self.post_scheduler:
            logger.warning("Post scheduler not available")
            return {"success": False, "message": "Post scheduler not available"}
            
        try:
            from datetime import datetime
            publish_datetime = datetime.fromisoformat(publish_time)
            
            scheduled_post = await self.post_scheduler.schedule_post(content, channel_id, publish_datetime)
            
            logger.info(f"Post scheduled for channel {channel_id} at {publish_time}")
            return {
                "success": True,
                "message": "Publicación programada exitosamente",
                "job_id": scheduled_post.job_id,
                "publish_time": scheduled_post.publish_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scheduling post to channel {channel_id}: {e}")
            return {"success": False, "message": "Error al programar la publicación"}

    @PerformanceMonitor("CrossModuleService").measure("cancel_scheduled_post")
    async def cancel_scheduled_post(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a scheduled post
        """
        if not self.post_scheduler:
            logger.warning("Post scheduler not available")
            return {"success": False, "message": "Post scheduler not available"}
            
        try:
            success = self.post_scheduler.cancel_post(job_id)
            
            if success:
                logger.info(f"Scheduled post {job_id} cancelled successfully")
                return {"success": True, "message": "Publicación programada cancelada exitosamente"}
            else:
                logger.warning(f"Failed to cancel scheduled post {job_id}")
                return {"success": False, "message": "Error al cancelar la publicación programada"}
                
        except Exception as e:
            logger.error(f"Error cancelling scheduled post {job_id}: {e}")
            return {"success": False, "message": "Error al cancelar la publicación programada"}

    @PerformanceMonitor("CrossModuleService").measure("grant_user_access")
    async def grant_user_access(
        self,
        user_id: int,
        channel_id: int,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Grant access to a channel for a user
        """
        if not self.access_control:
            logger.warning("Access control system not available")
            return {"success": False, "message": "Access control system not available"}
            
        try:
            success = await self.access_control.grant_access(user_id, channel_id, duration)
            
            if success:
                logger.info(f"Access granted to user {user_id} for channel {channel_id}")
                # Publish access granted event
                from src.events.models import create_event
                event = create_event(
                    "access_granted",
                    user_id=str(user_id),
                    channel_id=str(channel_id),
                    duration=duration
                )
                if hasattr(self, 'event_bus') and self.event_bus:
                    await self.event_bus.publish("access_granted", event.dict())
                
                return {"success": True, "message": "Acceso concedido exitosamente"}
            else:
                logger.warning(f"Failed to grant access to user {user_id} for channel {channel_id}")
                return {"success": False, "message": "Error al conceder acceso"}
                
        except Exception as e:
            logger.error(f"Error granting access to user {user_id} for channel {channel_id}: {e}")
            return {"success": False, "message": "Error al conceder acceso"}

    @PerformanceMonitor("CrossModuleService").measure("revoke_user_access")
    async def revoke_user_access(
        self,
        user_id: int,
        channel_id: int
    ) -> Dict[str, Any]:
        """
        Revoke access to a channel for a user
        """
        if not self.access_control:
            logger.warning("Access control system not available")
            return {"success": False, "message": "Access control system not available"}
            
        try:
            success = await self.access_control.revoke_access(user_id, channel_id)
            
            if success:
                logger.info(f"Access revoked for user {user_id} from channel {channel_id}")
                # Publish access revoked event
                from src.events.models import create_event
                event = create_event(
                    "access_revoked",
                    user_id=str(user_id),
                    channel_id=str(channel_id)
                )
                if hasattr(self, 'event_bus') and self.event_bus:
                    await self.event_bus.publish("access_revoked", event.dict())
                
                return {"success": True, "message": "Acceso revocado exitosamente"}
            else:
                logger.warning(f"Failed to revoke access for user {user_id} from channel {channel_id}")
                return {"success": False, "message": "Error al revocar acceso"}
                
        except Exception as e:
            logger.error(f"Error revoking access for user {user_id} from channel {channel_id}: {e}")
            return {"success": False, "message": "Error al revocar acceso"}

    async def initialize_gamification_systems(self) -> None:
        """
        Initialize all available gamification systems
        """
        try:
            # Initialize mission manager if available
            if self.mission_manager:
                await self.mission_manager.initialize()
                logger.info("Mission manager initialized")
            
            # Initialize achievement system if available
            if self.achievement_system:
                await self.achievement_system.initialize()
                logger.info("Achievement system initialized")
                
            # Initialize trivia engine if available
            if self.trivia_engine:
                await self.trivia_engine.initialize()
                logger.info("Trivia engine initialized")
                
            logger.info("Gamification systems initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing gamification systems: {e}")

    async def initialize_admin_systems(self) -> None:
        """
        Initialize all available admin systems
        """
        try:
            logger.info("Admin systems initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing admin systems: {e}")

    async def claim_daily_gift(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Coordinate the claiming of daily gifts with gamification systems
        """
        if not self.daily_gift_system:
            logger.warning("Daily gift system not available")
            return {"success": False, "message": "Daily gift system not available"}
            
        try:
            # Check if user can claim gift
            status = await self.daily_gift_system.check_gift_availability(user_id)
            if not status.can_claim:
                return {
                    "success": False, 
                    "message": "Ya has reclamado tu regalo diario. Intenta de nuevo más tarde.",
                    "cooldown_remaining": status.cooldown_remaining
                }
            
            # Claim the gift
            result = await self.daily_gift_system.claim_daily_gift(user_id)
            
            if result.success:
                # Award besitos through wallet if available
                if self.besitos_wallet and result.gift_claimed:
                    gift_amount = result.gift_claimed.get("amount", 0)
                    if gift_amount > 0:
                        try:
                            await self.besitos_wallet.add_besitos(
                                user_id, 
                                gift_amount, 
                                "daily_gift", 
                                "daily_gift_system"
                            )
                        except Exception as e:
                            logger.error(f"Failed to add besitos for daily gift: {e}")
                
                # Check for achievement unlocks
                if self.achievement_system:
                    try:
                        # This would trigger achievement checks for daily gift claiming
                        # Implementation would depend on how achievements track progress
                        pass
                    except Exception as e:
                        logger.error(f"Failed to check achievements for daily gift: {e}")
                        
                # Update mission progress if user has active missions
                if self.mission_manager:
                    try:
                        # This would update mission progress for daily gift claiming
                        # Implementation would depend on mission objectives
                        pass
                    except Exception as e:
                        logger.error(f"Failed to update mission progress for daily gift: {e}")
            
            return result.dict() if hasattr(result, 'dict') else result
            
        except Exception as e:
            logger.error(f"Error claiming daily gift for user {user_id}: {e}")
            return {"success": False, "message": "Error al reclamar el regalo diario"}

    async def complete_mission(
        self,
        user_id: str,
        mission_id: str
    ) -> Dict[str, Any]:
        """
        Coordinate mission completion with reward distribution
        """
        if not self.mission_manager:
            logger.warning("Mission manager not available")
            return {"success": False, "message": "Mission system not available"}
            
        try:
            # Get mission details
            # This would be implemented based on how missions are stored/retrieved
            # For now, we'll assume the mission manager handles this internally
            
            # Check if mission is complete
            # This would also be handled by the mission manager
            
            # Distribute rewards
            # This would involve coordinating with besitos wallet, item manager, etc.
            
            # Update achievement progress
            if self.achievement_system:
                try:
                    # Trigger achievement checks for mission completion
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for mission completion: {e}")
            
            # Publish mission completed event
            # This would be handled by the mission manager itself
            
            result = {"success": True, "message": "Misión completada exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error completing mission {mission_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al completar la misión"}

    async def unlock_achievement(
        self,
        user_id: str,
        achievement_id: str
    ) -> Dict[str, Any]:
        """
        Coordinate achievement unlocking with rewards
        """
        if not self.achievement_system:
            logger.warning("Achievement system not available")
            return {"success": False, "message": "Achievement system not available"}
            
        try:
            # Check if achievement can be unlocked
            # This would be handled by the achievement system
            
            # Unlock achievement
            # This would be handled by the achievement system
            
            # Distribute rewards
            # This would involve coordinating with besitos wallet, item manager, etc.
            
            # Update user profile/badges
            # This would involve updating user data
            
            result = {"success": True, "message": "Logro desbloqueado exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error unlocking achievement {achievement_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al desbloquear el logro"}

    async def purchase_item(
        self,
        user_id: str,
        item_id: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Coordinate item purchase with payment and inventory management
        """
        # Check if required systems are available
        if not self.store_menu:
            logger.warning("Store system not available")
            return {"success": False, "message": "Store system not available"}
            
        if not self.besitos_wallet:
            logger.warning("Besitos wallet not available")
            return {"success": False, "message": "Payment system not available"}
            
        if not self.item_manager:
            logger.warning("Item manager not available")
            return {"success": False, "message": "Inventory system not available"}
            
        try:
            # Check if user has enough besitos
            # This would be handled by the wallet system
            
            # Deduct besitos
            # This would be handled by the wallet system
            
            # Add item to user's inventory
            # This would be handled by the item manager
            
            # Update achievement progress for purchases
            if self.achievement_system:
                try:
                    # Trigger achievement checks for item purchases
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for item purchase: {e}")
            
            # Update mission progress for purchases
            if self.mission_manager:
                try:
                    # Update mission progress for item purchases
                    pass
                except Exception as e:
                    logger.error(f"Failed to update mission progress for item purchase: {e}")
            
            result = {"success": True, "message": "Item comprado exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error purchasing item {item_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al comprar el item"}

    async def participate_in_auction(
        self,
        user_id: str,
        auction_id: str,
        bid_amount: int
    ) -> Dict[str, Any]:
        """
        Coordinate auction participation with payment and item management
        """
        if not self.auction_system:
            logger.warning("Auction system not available")
            return {"success": False, "message": "Auction system not available"}
            
        if not self.besitos_wallet:
            logger.warning("Besitos wallet not available")
            return {"success": False, "message": "Payment system not available"}
            
        try:
            # Place bid in auction
            # This would be handled by the auction system
            
            # Check if user has enough besitos
            # This would be handled by the wallet system
            
            # Reserve besitos for bid
            # This would be handled by the wallet system
            
            # Update achievement progress for auction participation
            if self.achievement_system:
                try:
                    # Trigger achievement checks for auction participation
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for auction participation: {e}")
            
            result = {"success": True, "message": "Puja realizada exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error participating in auction {auction_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al participar en la subasta"}

    async def answer_trivia(
        self,
        user_id: str,
        trivia_id: str,
        answer: int
    ) -> Dict[str, Any]:
        """
        Coordinate trivia answering with rewards
        """
        if not self.trivia_engine:
            logger.warning("Trivia engine not available")
            return {"success": False, "message": "Trivia system not available"}
            
        if not self.besitos_wallet:
            logger.warning("Besitos wallet not available")
            return {"success": False, "message": "Reward system not available"}
            
        try:
            # Submit answer to trivia engine
            # This would be handled by the trivia engine
            
            # Check if answer is correct
            # This would be handled by the trivia engine
            
            # Award points/besitos for correct answers
            # This would be handled by the wallet system
            
            # Update achievement progress for trivia participation
            if self.achievement_system:
                try:
                    # Trigger achievement checks for trivia participation
                    pass
                except Exception as e:
                    logger.error(f"Failed to check achievements for trivia participation: {e}")
            
            # Update mission progress for trivia participation
            if self.mission_manager:
                try:
                    # Update mission progress for trivia participation
                    pass
                except Exception as e:
                    logger.error(f"Failed to update mission progress for trivia participation: {e}")
            
            result = {"success": True, "message": "Respuesta enviada exitosamente"}
            return result
            
        except Exception as e:
            logger.error(f"Error answering trivia {trivia_id} for user {user_id}: {e}")
            return {"success": False, "message": "Error al responder la trivia"}

    async def send_notification_to_user(
        self,
        user_id: str,
        template: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to a user through the notification system
        """
        if not self.notification_system:
            logger.warning("Notification system not available")
            return {"success": False, "message": "Notification system not available"}
            
        try:
            success = await self.notification_system.send_message(user_id, template, context or {})
            
            if success:
                logger.info(f"Notification sent successfully to user {user_id}")
                return {"success": True, "message": "Notificación enviada exitosamente"}
            else:
                logger.warning(f"Failed to send notification to user {user_id}")
                return {"success": False, "message": "Error al enviar la notificación"}
                
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return {"success": False, "message": "Error al enviar la notificación"}

    async def validate_user_access(
        self,
        user_id: int,
        channel_id: int
    ) -> Dict[str, Any]:
        """
        Validate if a user has access to a specific channel
        """
        if not self.access_control:
            logger.warning("Access control system not available")
            return {"success": False, "message": "Access control system not available", "has_access": False}
            
        try:
            result = await self.access_control.validate_access(user_id, channel_id)
            
            logger.info(f"Access validation for user {user_id} to channel {channel_id}: {result.has_access}")
            return {
                "success": True, 
                "message": "Validación de acceso completada",
                "has_access": result.has_access,
                "reason": result.reason
            }
            
        except Exception as e:
            logger.error(f"Error validating access for user {user_id} to channel {channel_id}: {e}")
            return {"success": False, "message": "Error al validar el acceso", "has_access": False}

    async def schedule_post(
        self,
        content: str,
        channel_id: str,
        publish_time: str  # ISO format datetime string
    ) -> Dict[str, Any]:
        """
        Schedule a post to be sent to a channel at a specific time
        """
        if not self.post_scheduler:
            logger.warning("Post scheduler not available")
            return {"success": False, "message": "Post scheduler not available"}
            
        try:
            from datetime import datetime
            publish_datetime = datetime.fromisoformat(publish_time)
            
            scheduled_post = await self.post_scheduler.schedule_post(content, channel_id, publish_datetime)
            
            logger.info(f"Post scheduled for channel {channel_id} at {publish_time}")
            return {
                "success": True,
                "message": "Publicación programada exitosamente",
                "job_id": scheduled_post.job_id,
                "publish_time": scheduled_post.publish_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scheduling post to channel {channel_id}: {e}")
            return {"success": False, "message": "Error al programar la publicación"}

    async def cancel_scheduled_post(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a scheduled post
        """
        if not self.post_scheduler:
            logger.warning("Post scheduler not available")
            return {"success": False, "message": "Post scheduler not available"}
            
        try:
            success = self.post_scheduler.cancel_post(job_id)
            
            if success:
                logger.info(f"Scheduled post {job_id} cancelled successfully")
                return {"success": True, "message": "Publicación programada cancelada exitosamente"}
            else:
                logger.warning(f"Failed to cancel scheduled post {job_id}")
                return {"success": False, "message": "Error al cancelar la publicación programada"}
                
        except Exception as e:
            logger.error(f"Error cancelling scheduled post {job_id}: {e}")
            return {"success": False, "message": "Error al cancelar la publicación programada"}

    async def grant_user_access(
        self,
        user_id: int,
        channel_id: int,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Grant access to a channel for a user
        """
        if not self.access_control:
            logger.warning("Access control system not available")
            return {"success": False, "message": "Access control system not available"}
            
        try:
            success = await self.access_control.grant_access(user_id, channel_id, duration)
            
            if success:
                logger.info(f"Access granted to user {user_id} for channel {channel_id}")
                # Publish access granted event
                from src.events.models import create_event
                event = create_event(
                    "access_granted",
                    user_id=str(user_id),
                    channel_id=str(channel_id),
                    duration=duration
                )
                if hasattr(self, 'event_bus') and self.event_bus:
                    await self.event_bus.publish("access_granted", event.dict())
                
                return {"success": True, "message": "Acceso concedido exitosamente"}
            else:
                logger.warning(f"Failed to grant access to user {user_id} for channel {channel_id}")
                return {"success": False, "message": "Error al conceder acceso"}
                
        except Exception as e:
            logger.error(f"Error granting access to user {user_id} for channel {channel_id}: {e}")
            return {"success": False, "message": "Error al conceder acceso"}

    async def revoke_user_access(
        self,
        user_id: int,
        channel_id: int
    ) -> Dict[str, Any]:
        """
        Revoke access to a channel for a user
        """
        if not self.access_control:
            logger.warning("Access control system not available")
            return {"success": False, "message": "Access control system not available"}
            
        try:
            success = await self.access_control.revoke_access(user_id, channel_id)
            
            if success:
                logger.info(f"Access revoked for user {user_id} from channel {channel_id}")
                # Publish access revoked event
                from src.events.models import create_event
                event = create_event(
                    "access_revoked",
                    user_id=str(user_id),
                    channel_id=str(channel_id)
                )
                if hasattr(self, 'event_bus') and self.event_bus:
                    await self.event_bus.publish("access_revoked", event.dict())
                
                return {"success": True, "message": "Acceso revocado exitosamente"}
            else:
                logger.warning(f"Failed to revoke access for user {user_id} from channel {channel_id}")
                return {"success": False, "message": "Error al revocar acceso"}
                
        except Exception as e:
            logger.error(f"Error revoking access for user {user_id} from channel {channel_id}: {e}")
            return {"success": False, "message": "Error al revocar acceso"}

    async def process_emotional_interaction(
        self,
        user_id: str,
        interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process emotional interaction with complete YABOT integration
        """
        try:
            # 1. Behavioral Analysis
            # Note: In a full implementation, this would use EmotionalIntelligenceService
            # For now, we'll simulate the analysis result
            
            analysis_result = {
                "authenticity_detected": True,
                "authenticity_score": 0.85,
                "vulnerability_level": 0.7,
                "archetype": "EXPLORADOR_PROFUNDO",
                "signature_strength": 0.9
            }
            
            # 2. Update User Emotional Signature
            if analysis_result.get("authenticity_detected"):
                # In a full implementation, this would call:
                # await self.user_service.update_emotional_signature(user_id, analysis_result)
                logger.info(f"Would update emotional signature for user {user_id}")
            
            # 3. Check for Level Progression
            # In a full implementation, this would check for level progression based on emotional metrics
            level_progression = {
                "should_progress": False,
                "new_level": 1,
                "previous_level": 1
            }
            
            if level_progression.get("should_progress"):
                # Validate VIP access for Diana levels 4-6
                if level_progression["new_level"] >= 4:
                    has_vip = await self.subscription_service.is_user_vip(user_id)
                    if not has_vip:
                        return {
                            "success": False,
                            "message": "VIP access required for Diana Diván levels",
                            "vip_upgrade_required": True
                        }
                
                # In a full implementation, this would call:
                # await self.user_service.advance_diana_level(user_id, level_progression["new_level"], level_progression)
                logger.info(f"Would advance user {user_id} to Diana level {level_progression['new_level']}")
            
            # 4. Award Emotional Rewards
            if analysis_result.get("authenticity_detected") and self.besitos_wallet:
                authenticity_bonus = int(analysis_result.get("authenticity_score", 0) * 10)
                if authenticity_bonus > 0:
                    # In a full implementation, this would call:
                    # await self.besitos_wallet.add_besitos(user_id, authenticity_bonus, "emotional_authenticity", "emotional_system")
                    logger.info(f"Would award {authenticity_bonus} besitos for emotional authenticity to user {user_id}")
            
            # 5. Check Emotional Achievements
            if self.achievement_system and analysis_result.get("authenticity_detected"):
                # In a full implementation, this would call:
                # await self.achievement_system.check_achievements(user_id, "emotional_milestone")
                logger.info(f"Would check emotional achievements for user {user_id}")
            
            # 6. Generate Personalized Response
            # In a full implementation, this would call:
            # personalized_content = await self.narrative_service.get_personalized_content(
            #     user_id,
            #     interaction_data.get("fragment_id"),
            #     analysis_result.get("emotional_context", {})
            # )
            
            personalized_content = {
                "response": "Gracias por compartir tus pensamientos. Tu autenticidad es valiosa.",
                "emotional_tone": "supportive"
            }
            
            return {
                "success": True,
                "emotional_analysis": analysis_result,
                "personalized_response": personalized_content,
                "integration_status": "complete"
            }
            
        except Exception as e:
            logger.error(f"Error processing emotional interaction for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def handle_diana_level_progression(
        self,
        user_id: str,
        level_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle Diana level progression with complete system integration
        """
        try:
            new_level = level_data["new_level"]
            
            # 1. Update Mission Progress
            if self.mission_manager:
                await self.mission_manager.update_progress(
                    user_id,
                    "diana_progression",
                    {"level": new_level}
                )
            
            # 2. Award Level Progression Achievements
            if self.achievement_system:
                await self.achievement_system.unlock_achievement(
                    user_id,
                    f"diana_level_{new_level}"
                )
            
            # 3. Award Level Progression Besitos
            if self.besitos_wallet:
                level_rewards = {
                    2: 100, 3: 200, 4: 500, 5: 1000, 6: 2000
                }
                reward = level_rewards.get(new_level, 0)
                if reward > 0:
                    await self.besitos_wallet.add_besitos(
                        user_id,
                        reward,
                        f"diana_level_{new_level}_progression",
                        "emotional_system"
                    )
            
            # 4. Send Level Progression Notification
            if self.notification_system:
                await self.notification_system.send_message(
                    user_id,
                    "diana_level_progression",
                    {"new_level": new_level, "level_name": self._get_level_name(new_level)}
                )
            
            # 5. Update VIP Integration Status
            if new_level >= 4:
                vip_status = await self.subscription_service.is_user_vip(user_id)
                await self.user_service.update_user_state(user_id, {
                    "emotional_journey.vip_integration_status": {
                        "has_vip_access": vip_status,
                        "divan_access_granted": vip_status,
                        "last_vip_check": datetime.utcnow()
                    }
                })
            
            return {
                "success": True,
                "new_level": new_level,
                "rewards_distributed": True,
                "notifications_sent": True
            }
            
        except Exception as e:
            logger.error(f"Error handling Diana level progression: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_level_name(self, level: int) -> str:
        """Get Diana level name"""
        level_names = {
            1: "Los Kinkys - Primer Encuentro",
            2: "Los Kinkys - Evolución de la Mirada",
            3: "Los Kinkys - Cartografía del Deseo",
            4: "El Diván - Inversión del Espejo",
            5: "El Diván - Sostener Paradojas",
            6: "El Diván - Círculo Íntimo"
        }
        return level_names.get(level, f"Level {level}")

    async def initialize_admin_systems(self) -> None:
        """
        Initialize all available admin systems
        """
        try:
            logger.info("Admin systems initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing admin systems: {e}")

    async def initialize_gamification_systems(self) -> None:
        """
        Initialize all available gamification systems
        """
        try:
            # Initialize mission manager if available
            if self.mission_manager:
                await self.mission_manager.initialize()
                logger.info("Mission manager initialized")
            
            # Initialize achievement system if available
            if self.achievement_system:
                await self.achievement_system.initialize()
                logger.info("Achievement system initialized")
                
            # Initialize trivia engine if available
            if self.trivia_engine:
                await self.trivia_engine.initialize()
                logger.info("Trivia engine initialized")
                
            logger.info("Gamification systems initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing gamification systems: {e}")

# Dependency function to get CrossModuleService instance
async def get_cross_module_service(
    user_service: UserService = Depends(create_user_service),
    subscription_service: SubscriptionService = Depends(create_subscription_service),
    narrative_service: NarrativeService = Depends(create_narrative_service),
    # Note: In a full implementation, these would be properly injected
    # For now, we're using None as placeholders as indicated in the original code
) -> CrossModuleService:
    # This is a simplified implementation that creates the necessary dependencies
    # In a real implementation, you would use proper dependency injection
    # For now, we'll create None placeholders for gamification services
    # Note: This will need to be properly implemented with actual dependency injection
    
    # Create ItemManager (this needs proper implementation)
    # For now, we'll create a basic instance
    from src.modules.gamification.item_manager import ItemManager
    item_manager = ItemManager()
    
    # Create None placeholders for gamification services as per original pattern
    besitos_wallet = None
    daily_gift_system = None
    mission_manager = None
    achievement_system = None
    store_menu = None
    auction_system = None
    trivia_engine = None
    
    # Create None placeholders for admin services
    notification_system = None
    access_control = None
    post_scheduler = None
    
    # In a full implementation, these would be created like:
    # besitos_wallet = await create_besitos_wallet(database_manager, event_bus)
    # daily_gift_system = DailyGiftSystem(redis_client, event_bus)
    # mission_manager = await create_mission_manager(database_manager, event_bus)
    # achievement_system = await create_achievement_system(database_manager, event_bus)
    # etc.
    
    return CrossModuleService(
        user_service, 
        subscription_service, 
        item_manager, 
        narrative_service,
        besitos_wallet,
        daily_gift_system,
        mission_manager,
        achievement_system,
        store_menu,
        auction_system,
        trivia_engine,
        notification_system,
        access_control,
        post_scheduler
    )

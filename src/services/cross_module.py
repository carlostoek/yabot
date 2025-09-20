from typing import Dict, Any, Optional
from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.modules.gamification.item_manager import ItemManager
from src.services.narrative import NarrativeService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CrossModuleService:
    """Service to handle interactions between different modules"""
    
    def __init__(
        self,
        user_service: UserService,
        subscription_service: SubscriptionService,
        item_manager: ItemManager,
        narrative_service: NarrativeService
    ):
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.item_manager = item_manager
        self.narrative_service = narrative_service
    
    async def can_access_narrative_content(
        self, 
        user_id: str, 
        fragment_id: str
    ) -> bool:
        """
        Check if a user can access specific narrative content
        based on VIP status, besitos, items, etc.
        """
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

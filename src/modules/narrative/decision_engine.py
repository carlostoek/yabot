"""
Decision Engine - Narrative Decision Processing

This module handles user narrative choices and determines outcomes, 
processing decisions according to the modulos-atomicos specification.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from src.events.bus import EventBus
from src.events.models import DecisionMadeEvent
from src.modules.narrative.fragment_manager import NarrativeFragmentManager

from src.utils.logger import get_logger


class Choice(BaseModel):
    """
    Represents a narrative choice available to the user
    """
    choice_id: str
    text: str
    next_fragment_id: Optional[str] = None
    conditions: Dict[str, Any] = Field(default_factory=dict)
    reward: Optional[Dict[str, Any]] = None  # Potential rewards for making this choice


class DecisionResult(BaseModel):
    """
    Result of processing a user's decision
    """
    success: bool
    next_fragment_id: Optional[str]
    message: str = ""
    rewards: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class DecisionEngine:
    """
    Decision Engine for processing user narrative choices and determining outcomes
    
    Implements requirements 1.2, 1.5, 4.4 from the modulos-atomicos specification:
    - 1.2: Updates narrative state and publishes decision_made event
    - 1.5: Validates progression conditions via coordinator service
    - 4.4: Triggers cross-module effects (missions, access)
    """
    
    def __init__(self, 
                 event_bus: Optional[EventBus] = None,
                 fragment_manager: Optional[NarrativeFragmentManager] = None):
        """
        Initialize the decision engine
        
        Args:
            event_bus: Optional event bus instance for publishing events
            fragment_manager: Optional fragment manager instance for retrieving fragments
        """
        self.event_bus = event_bus
        if fragment_manager:
            self.fragment_manager = fragment_manager
        else:
            # Import MongoDBHandler here to avoid circular imports
            from src.database.mongodb import MongoDBHandler
            db_handler = MongoDBHandler()
            self.fragment_manager = NarrativeFragmentManager(db_handler)
        self.logger = get_logger(__name__)
        
    async def validate_choice(self, user_id: str, fragment_id: str, choice_id: str) -> bool:
        """
        Validate if a user's choice is valid for the current narrative state
        
        Implements requirement validation logic to ensure choices are appropriate
        
        Args:
            user_id: The ID of the user making the choice
            fragment_id: The current fragment ID
            choice_id: The choice ID being validated
            
        Returns:
            True if the choice is valid, False otherwise
        """
        try:
            # Get the current narrative fragment
            current_fragment = await self.fragment_manager.get_fragment(fragment_id)
            if not current_fragment:
                self.logger.error(f"Fragment not found for validation", 
                                user_id=user_id, fragment_id=fragment_id)
                return False
            
            # Check if the choice exists in the current fragment
            available_choices = current_fragment.get('choices', [])
            choice_exists = any(choice.get('choice_id') == choice_id for choice in available_choices)
            
            if not choice_exists:
                self.logger.warning(f"Choice not available for fragment", 
                                  user_id=user_id, fragment_id=fragment_id, choice_id=choice_id)
                return False
            
            # Additional validation could go here (VIP requirements, prerequisites, etc.)
            # For now, we'll just check if the choice exists
            
            # Check if user has the required permissions/conditions to make this choice
            user_doc = await self.fragment_manager.db.get_user(user_id)
            
            if not user_doc:
                self.logger.error(f"User not found for choice validation", 
                                user_id=user_id)
                return False
            
            # Check for VIP requirements if any
            for choice in available_choices:
                if choice.get('choice_id') == choice_id:
                    conditions = choice.get('conditions', {})
                    if conditions.get('vip_required') and not user_doc.get('vip_status', False):
                        self.logger.warning(f"VIP required for choice", 
                                          user_id=user_id, choice_id=choice_id)
                        return False
                    break
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating choice", 
                            user_id=user_id, fragment_id=fragment_id, 
                            choice_id=choice_id, error=str(e))
            return False

    async def process_decision(self, 
                             user_id: str, 
                             fragment_id: str, 
                             choice_id: str,
                             session_id: Optional[str] = None) -> DecisionResult:
        """
        Process a user's narrative decision and update their state
        
        Implements requirement 1.2: Updates narrative state and publishes decision_made event
        Implements requirement 1.5: Validates progression conditions via coordinator service
        Implements requirement 4.4: Triggers cross-module effects (missions, access)
        
        Args:
            user_id: The ID of the user making the decision
            fragment_id: The current fragment ID
            choice_id: The choice ID selected by the user
            session_id: Optional session ID for tracking
            
        Returns:
            DecisionResult containing the processing outcome
        """
        try:
            # Validate the choice first
            is_valid = await self.validate_choice(user_id, fragment_id, choice_id)
            if not is_valid:
                error_msg = f"Invalid choice '{choice_id}' for fragment '{fragment_id}' by user '{user_id}'"
                self.logger.error(error_msg)
                return DecisionResult(
                    success=False,
                    next_fragment_id=None,
                    error=error_msg,
                    message="Invalid choice selected"
                )
            
            # Get the current narrative fragment
            current_fragment = await self.fragment_manager.get_fragment(fragment_id)
            if not current_fragment:
                error_msg = f"Fragment '{fragment_id}' not found"
                self.logger.error(error_msg, user_id=user_id)
                return DecisionResult(
                    success=False,
                    next_fragment_id=None,
                    error=error_msg,
                    message="Current fragment not found"
                )
            
            # Find the selected choice and get the next fragment
            next_fragment_id = None
            choice_data = None
            available_choices = current_fragment.get('choices', [])
            
            for choice in available_choices:
                if choice.get('choice_id') == choice_id:
                    choice_data = choice
                    next_fragment_id = choice.get('next_fragment_id')
                    break
            
            if not choice_data:
                error_msg = f"Choice '{choice_id}' not found in fragment '{fragment_id}'"
                self.logger.error(error_msg, user_id=user_id)
                return DecisionResult(
                    success=False,
                    next_fragment_id=None,
                    error=error_msg,
                    message="Choice not found"
                )
            
            # Get user document to update narrative progress
            user_doc = await self.fragment_manager.db.get_user(user_id)
            
            if not user_doc:
                error_msg = f"User '{user_id}' not found in database"
                self.logger.error(error_msg)
                return DecisionResult(
                    success=False,
                    next_fragment_id=None,
                    error=error_msg,
                    message="User not found"
                )
            
            # Update user's narrative progress in database
            update_data = {
                "$set": {
                    "narrative_progress.current_fragment": next_fragment_id,
                    "narrative_progress.last_choice": choice_id,
                    "narrative_progress.last_updated": datetime.utcnow(),
                },
                "$addToSet": {
                    "narrative_progress.completed_fragments": fragment_id,
                }
            }
            
            # Apply conditional updates based on choice conditions
            conditions = choice_data.get('conditions', {})
            if conditions.get('vip_required'):
                update_data["$set"]["narrative_progress.vip_restricted"] = True
            
            # Only update the narrative progress part of the user document
            narrative_progress_update = {
                "narrative_progress.current_fragment": next_fragment_id,
                "narrative_progress.last_choice": choice_id,
                "narrative_progress.last_updated": datetime.utcnow(),
            }
            
            # Update user's narrative progress using MongoDBHandler
            update_result = await self.fragment_manager.db.update_user(user_id, narrative_progress_update)
            
            # Add fragment to completed fragments separately
            append_result = await self.fragment_manager.append_to_completed_fragments(user_id, fragment_id)
            
            # Create a mock-like result object to match existing logic
            class UpdateResult:
                def __init__(self, success):
                    self.modified_count = 1 if success else 0
            
            result = UpdateResult(update_result and append_result)
            
            if result.modified_count == 0:
                error_msg = f"Failed to update user progress for decision"
                self.logger.error(error_msg, user_id=user_id, fragment_id=fragment_id)
                return DecisionResult(
                    success=False,
                    next_fragment_id=next_fragment_id,
                    error=error_msg,
                    message="Failed to update narrative state"
                )
            
            # Validate progression conditions (requirement 1.5)
            # This could involve checking requirements before allowing progression
            validation_result = await self._validate_progression_conditions(
                user_id, fragment_id, choice_id, next_fragment_id
            )
            
            if not validation_result.get('valid', True):
                error_msg = f"Progression conditions not met: {validation_result.get('message', 'Unknown condition failed')}"
                self.logger.warning(error_msg, user_id=user_id)
                
                # Still return the next fragment but with warning
                return DecisionResult(
                    success=True,
                    next_fragment_id=next_fragment_id,
                    message=f"Decision processed but with restrictions: {validation_result.get('message', 'Conditions not met')}"
                )
            
            # Publish decision_made event (requirement 1.2 & 4.4)
            decision_event = DecisionMadeEvent(
                user_id=user_id,
                choice_id=choice_id,
                fragment_id=fragment_id,
                next_fragment_id=next_fragment_id or "",
                context={
                    "choice_text": choice_data.get('text', ''),
                    "conditions": conditions,
                    "rewards": choice_data.get('reward', {})
                },
                payload={
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            if self.event_bus:
                try:
                    await self.event_bus.publish("decision_made", decision_event)
                    self.logger.info(f"Decision event published", 
                                   user_id=user_id, choice_id=choice_id, 
                                   next_fragment_id=next_fragment_id)
                except Exception as e:
                    self.logger.error(f"Failed to publish decision event", 
                                    user_id=user_id, error=str(e))
                    # Don't fail the decision if event publishing fails
            else:
                self.logger.warning("Event bus not available for decision event publishing", 
                                  user_id=user_id)
            
            # Determine rewards from choice (could be besitos, items, etc.)
            rewards = []
            choice_reward = choice_data.get('reward', {})
            if choice_reward:
                rewards.append(choice_reward)
            
            success_msg = f"Decision processed successfully for user '{user_id}' with choice '{choice_id}'"
            self.logger.info(success_msg, 
                           user_id=user_id, next_fragment_id=next_fragment_id)
            
            return DecisionResult(
                success=True,
                next_fragment_id=next_fragment_id,
                message=success_msg,
                rewards=rewards
            )
            
        except Exception as e:
            error_msg = f"Error processing decision: {str(e)}"
            self.logger.error(error_msg, 
                            user_id=user_id, fragment_id=fragment_id, 
                            choice_id=choice_id, error=str(e))
            return DecisionResult(
                success=False,
                next_fragment_id=None,
                error=error_msg,
                message="Internal error processing decision"
            )
    
    async def _validate_progression_conditions(self, 
                                            user_id: str, 
                                            current_fragment_id: str, 
                                            choice_id: str, 
                                            next_fragment_id: Optional[str]) -> Dict[str, Any]:
        """
        Validate progression conditions before allowing narrative progression (Requirement 1.5)
        
        Args:
            user_id: The ID of the user
            current_fragment_id: The current fragment ID
            choice_id: The choice ID
            next_fragment_id: The target fragment ID
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Get user document to check conditions
            user_doc = await self.fragment_manager.db.get_user(user_id)
            
            if not user_doc:
                return {
                    "valid": False,
                    "message": "User not found for condition validation"
                }
            
            # Check VIP status if required for next fragment
            if next_fragment_id:
                next_fragment = await self.fragment_manager.get_fragment(next_fragment_id)
                if next_fragment and next_fragment.get('vip_required', False):
                    if not user_doc.get('vip_status', False):
                        return {
                            "valid": False,
                            "message": "VIP status required for next fragment"
                        }
            
            # Additional conditions could be checked here:
            # - Prerequisite fragments completed
            # - Item requirements
            # - Achievement requirements
            # - Time-based restrictions
            # - Besitos balance requirements
            
            return {
                "valid": True,
                "message": "All conditions met for progression"
            }
            
        except Exception as e:
            self.logger.error(f"Error validating progression conditions", 
                            user_id=user_id, error=str(e))
            return {
                "valid": False,
                "message": f"Error validating conditions: {str(e)}"
            }
    
    async def get_available_choices(self, user_id: str, fragment_id: str) -> List[Choice]:
        """
        Get available choices for a user for a given fragment, considering user state
        
        Args:
            user_id: The ID of the user
            fragment_id: The fragment ID to get choices for
            
        Returns:
            List of available choices for the user
        """
        try:
            fragment = await self.fragment_manager.get_fragment(fragment_id)
            if not fragment:
                return []
            
            # Get user document to determine available choices based on user state
            user_doc = await self.fragment_manager.db.get_user(user_id)
            
            if not user_doc:
                # If user doesn't exist, return all choices
                raw_choices = fragment.get('choices', [])
                return [Choice(**choice) for choice in raw_choices]
            
            available_choices = []
            raw_choices = fragment.get('choices', [])
            
            for raw_choice in raw_choices:
                choice = Choice(**raw_choice)
                
                # Check if user meets conditions for this choice
                conditions = choice.conditions
                is_available = True
                
                if conditions.get('vip_required') and not user_doc.get('vip_status', False):
                    is_available = False
                
                # Add more condition checks as needed
                
                if is_available:
                    available_choices.append(choice)
            
            return available_choices
            
        except Exception as e:
            self.logger.error(f"Error getting available choices", 
                            user_id=user_id, fragment_id=fragment_id, error=str(e))
            return []

    async def rollback_decision(self, user_id: str, decision_id: str) -> bool:
        """
        Rollback a decision if needed (for error recovery or special cases)
        
        Args:
            user_id: The ID of the user
            decision_id: The decision ID to rollback
            
        Returns:
            True if rollback was successful, False otherwise
        """
        try:
            # Implementation would involve looking up the decision and reverting state
            # For now, this is a placeholder for future implementation
            self.logger.warning("Rollback decision not fully implemented", 
                              user_id=user_id, decision_id=decision_id)
            return True  # Placeholder return
        except Exception as e:
            self.logger.error(f"Error rolling back decision", 
                            user_id=user_id, decision_id=decision_id, error=str(e))
            return False
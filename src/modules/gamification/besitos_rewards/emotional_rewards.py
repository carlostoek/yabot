"""
Emotional besitos reward rules for the Diana Emotional System.

This module defines reward calculation rules for emotional interactions,
implementing Requirement 6 from the emocional specification.
"""

from typing import Dict, Any, Optional
from enum import Enum


class EmotionalRewardType(Enum):
    """Types of emotional rewards."""
    AUTHENTICITY_BONUS = "authenticity_bonus"
    VULNERABILITY_REWARD = "vulnerability_reward"
    LEVEL_PROGRESSION_BONUS = "level_progression_bonus"
    MILESTONE_ACHIEVEMENT = "milestone_achievement"
    MEMORY_CONTINUITY_BONUS = "memory_continuity_bonus"
    ARCHETYPE_CONSISTENCY = "archetype_consistency"


class EmotionalRewardCalculator:
    """Calculates emotional besitos rewards based on user interactions."""

    def __init__(self):
        """Initialize reward calculator with base reward values."""
        # Base reward values for different emotional interactions
        self.base_rewards = {
            EmotionalRewardType.AUTHENTICITY_BONUS: 10,
            EmotionalRewardType.VULNERABILITY_REWARD: 25,
            EmotionalRewardType.LEVEL_PROGRESSION_BONUS: 50,
            EmotionalRewardType.MILESTONE_ACHIEVEMENT: 75,
            EmotionalRewardType.MEMORY_CONTINUITY_BONUS: 15,
            EmotionalRewardType.ARCHETYPE_CONSISTENCY: 20
        }

        # Diana level multipliers for rewards
        self.level_multipliers = {
            1: 1.0,   # Los Kinkys - Primer Encuentro
            2: 1.2,   # Los Kinkys - Evolución de la Mirada
            3: 1.5,   # Los Kinkys - Cartografía del Deseo
            4: 2.0,   # El Diván - Inversión del Espejo
            5: 2.5,   # El Diván - Sostener Paradojas
            6: 3.0    # El Diván - Círculo Íntimo
        }

    def calculate_authenticity_bonus(self, authenticity_score: float, user_level: int = 1) -> int:
        """
        Calculate besitos reward for authentic emotional responses.
        
        Args:
            authenticity_score: Score between 0.0-1.0 indicating response authenticity
            user_level: Current Diana emotional level
            
        Returns:
            int: Calculated besitos reward
        """
        if not 0.0 <= authenticity_score <= 1.0:
            raise ValueError("Authenticity score must be between 0.0 and 1.0")
            
        # Base reward scaled by authenticity score
        base_reward = self.base_rewards[EmotionalRewardType.AUTHENTICITY_BONUS]
        reward = int(base_reward * authenticity_score)
        
        # Apply level multiplier
        level_multiplier = self.level_multipliers.get(user_level, 1.0)
        reward = int(reward * level_multiplier)
        
        return reward

    def calculate_vulnerability_reward(self, vulnerability_level: float, user_level: int = 1) -> int:
        """
        Calculate besitos reward for sharing vulnerable moments.
        
        Args:
            vulnerability_level: Score between 0.0-1.0 indicating vulnerability depth
            user_level: Current Diana emotional level
            
        Returns:
            int: Calculated besitos reward
        """
        if not 0.0 <= vulnerability_level <= 1.0:
            raise ValueError("Vulnerability level must be between 0.0 and 1.0")
            
        # Base reward scaled by vulnerability level
        base_reward = self.base_rewards[EmotionalRewardType.VULNERABILITY_REWARD]
        reward = int(base_reward * vulnerability_level)
        
        # Apply level multiplier
        level_multiplier = self.level_multipliers.get(user_level, 1.0)
        reward = int(reward * level_multiplier)
        
        return reward

    def calculate_level_progression_bonus(self, new_level: int, previous_level: int = 1) -> int:
        """
        Calculate besitos reward for emotional level progression.
        
        Args:
            new_level: New Diana emotional level achieved
            previous_level: Previous Diana emotional level
            
        Returns:
            int: Calculated besitos reward
        """
        if new_level < previous_level:
            raise ValueError("New level must be greater than or equal to previous level")
            
        # Base reward scaled by level difference
        level_difference = new_level - previous_level
        base_reward = self.base_rewards[EmotionalRewardType.LEVEL_PROGRESSION_BONUS]
        reward = base_reward * level_difference
        
        # Apply new level multiplier
        level_multiplier = self.level_multipliers.get(new_level, 1.0)
        reward = int(reward * level_multiplier)
        
        return reward

    def calculate_milestone_achievement(self, milestone_importance: str, user_level: int = 1) -> int:
        """
        Calculate besitos reward for reaching emotional milestones.
        
        Args:
            milestone_importance: Importance level ('low', 'medium', 'high')
            user_level: Current Diana emotional level
            
        Returns:
            int: Calculated besitos reward
        """
        importance_multipliers = {
            'low': 1.0,
            'medium': 1.5,
            'high': 2.0
        }
        
        if milestone_importance not in importance_multipliers:
            raise ValueError("Milestone importance must be 'low', 'medium', or 'high'")
            
        # Base reward scaled by importance
        base_reward = self.base_rewards[EmotionalRewardType.MILESTONE_ACHIEVEMENT]
        importance_multiplier = importance_multipliers[milestone_importance]
        reward = int(base_reward * importance_multiplier)
        
        # Apply level multiplier
        level_multiplier = self.level_multipliers.get(user_level, 1.0)
        reward = int(reward * level_multiplier)
        
        return reward

    def calculate_memory_continuity_bonus(self, memory_significance: float, user_level: int = 1) -> int:
        """
        Calculate besitos reward for maintaining emotional memory continuity.
        
        Args:
            memory_significance: Score between 0.0-1.0 indicating memory importance
            user_level: Current Diana emotional level
            
        Returns:
            int: Calculated besitos reward
        """
        if not 0.0 <= memory_significance <= 1.0:
            raise ValueError("Memory significance must be between 0.0 and 1.0")
            
        # Base reward scaled by memory significance
        base_reward = self.base_rewards[EmotionalRewardType.MEMORY_CONTINUITY_BONUS]
        reward = int(base_reward * memory_significance)
        
        # Apply level multiplier
        level_multiplier = self.level_multipliers.get(user_level, 1.0)
        reward = int(reward * level_multiplier)
        
        return reward

    def calculate_archetype_consistency(self, consistency_score: float, user_level: int = 1) -> int:
        """
        Calculate besitos reward for maintaining emotional archetype consistency.
        
        Args:
            consistency_score: Score between 0.0-1.0 indicating archetype consistency
            user_level: Current Diana emotional level
            
        Returns:
            int: Calculated besitos reward
        """
        if not 0.0 <= consistency_score <= 1.0:
            raise ValueError("Consistency score must be between 0.0 and 1.0")
            
        # Base reward scaled by consistency score
        base_reward = self.base_rewards[EmotionalRewardType.ARCHETYPE_CONSISTENCY]
        reward = int(base_reward * consistency_score)
        
        # Apply level multiplier
        level_multiplier = self.level_multipliers.get(user_level, 1.0)
        reward = int(reward * level_multiplier)
        
        return reward

    def calculate_composite_emotional_reward(
        self, 
        interaction_data: Dict[str, Any],
        user_level: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate total emotional reward based on multiple factors.
        
        Args:
            interaction_data: Dictionary containing emotional interaction metrics
            user_level: Current Diana emotional level
            
        Returns:
            Dict[str, Any]: Detailed reward breakdown and total
        """
        rewards = {}
        total_reward = 0
        
        # Calculate authenticity bonus if data available
        if 'authenticity_score' in interaction_data:
            authenticity_reward = self.calculate_authenticity_bonus(
                interaction_data['authenticity_score'], 
                user_level
            )
            rewards['authenticity_bonus'] = authenticity_reward
            total_reward += authenticity_reward
            
        # Calculate vulnerability reward if data available
        if 'vulnerability_level' in interaction_data:
            vulnerability_reward = self.calculate_vulnerability_reward(
                interaction_data['vulnerability_level'], 
                user_level
            )
            rewards['vulnerability_reward'] = vulnerability_reward
            total_reward += vulnerability_reward
            
        # Calculate memory continuity bonus if data available
        if 'memory_significance' in interaction_data:
            memory_reward = self.calculate_memory_continuity_bonus(
                interaction_data['memory_significance'], 
                user_level
            )
            rewards['memory_continuity_bonus'] = memory_reward
            total_reward += memory_reward
            
        # Calculate archetype consistency if data available
        if 'consistency_score' in interaction_data:
            consistency_reward = self.calculate_archetype_consistency(
                interaction_data['consistency_score'], 
                user_level
            )
            rewards['archetype_consistency'] = consistency_reward
            total_reward += consistency_reward
            
        return {
            'rewards_breakdown': rewards,
            'total_reward': total_reward,
            'user_level': user_level,
            'calculation_timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }


# Global instance for easy access
emotional_reward_calculator = EmotionalRewardCalculator()


def get_emotional_reward_calculator() -> EmotionalRewardCalculator:
    """Get the global emotional reward calculator instance."""
    return emotional_reward_calculator
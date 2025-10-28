"""
Emotional achievements configuration for the Diana Emotional System.

This module defines achievement definitions for the emotional intelligence system,
implementing Requirement 6 from the emocional specification.
"""

from src.modules.gamification.achievement_system import Achievement, AchievementType, AchievementTier

# Emotional achievement definitions
EMOTIONAL_ACHIEVEMENTS = {
    # Level progression achievements
    "diana_level_1": Achievement(
        achievement_id="diana_level_1",
        title="Primer Encuentro",
        description="Completa tu primera etapa en el viaje emocional de Diana",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.BRONZE,
        target_value=1,
        reward_besitos=50,
        icon="👋",
        secret=False,
        metadata={
            "trigger_event": "diana_level_progression", 
            "field": "levels_completed",
            "level": 1
        }
    ),
    
    "diana_level_2": Achievement(
        achievement_id="diana_level_2",
        title="Evolución de la Mirada",
        description="Alcanza el segundo nivel de conexión emocional con Diana",
        achievement_type=AchievementType.PROGRESS,
        tier=AchievementTier.BRONZE,
        target_value=2,
        reward_besitos=100,
        icon="👁️",
        secret=False,
        metadata={
            "trigger_event": "diana_level_progression", 
            "field": "levels_completed",
            "level": 2
        }
    ),
    
    "diana_level_3": Achievement(
        achievement_id="diana_level_3",
        title="Cartografía del Deseo",
        description="Completa la exploración inicial de tu autenticidad emocional",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.SILVER,
        target_value=3,
        reward_besitos=200,
        icon="🗺️",
        secret=False,
        metadata={
            "trigger_event": "diana_level_progression", 
            "field": "levels_completed",
            "level": 3
        }
    ),
    
    "diana_level_4": Achievement(
        achievement_id="diana_level_4",
        title="Inversión del Espejo",
        description="Alcanza el primer nivel del Diván, donde la intimidad se refleja",
        achievement_type=AchievementType.PROGRESS,
        tier=AchievementTier.SILVER,
        target_value=4,
        reward_besitos=500,
        icon="🪞",
        secret=False,
        metadata={
            "trigger_event": "diana_level_progression", 
            "field": "levels_completed",
            "level": 4
        }
    ),
    
    "diana_level_5": Achievement(
        achievement_id="diana_level_5",
        title="Sostener Paradojas",
        description="Domina el arte de abrazar contradicciones emocionales",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.GOLD,
        target_value=5,
        reward_besitos=1000,
        icon="🌀",
        secret=False,
        metadata={
            "trigger_event": "diana_level_progression", 
            "field": "levels_completed",
            "level": 5
        }
    ),
    
    "diana_level_6": Achievement(
        achievement_id="diana_level_6",
        title="Círculo Íntimo",
        description="Alcanza la maestría en la conexión emocional auténtica",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.GOLD,
        target_value=6,
        reward_besitos=2000,
        icon="❤️‍🔥",
        secret=False,
        metadata={
            "trigger_event": "diana_level_progression", 
            "field": "levels_completed",
            "level": 6
        }
    ),
    
    # Authenticity achievements
    "authentic_moment": Achievement(
        achievement_id="authentic_moment",
        title="Momento Auténtico",
        description="Comparte una vulnerabilidad genuina con Diana",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.BRONZE,
        target_value=1,
        reward_besitos=75,
        icon="💎",
        secret=False,
        metadata={
            "trigger_event": "emotional_authenticity_detected", 
            "field": "authentic_moments",
            "min_authenticity": 0.8
        }
    ),
    
    "authentic_explorer": Achievement(
        achievement_id="authentic_explorer",
        title="Explorador Auténtico",
        description="Demuestra autenticidad en 5 interacciones emocionales",
        achievement_type=AchievementType.PROGRESS,
        tier=AchievementTier.SILVER,
        target_value=5,
        reward_besitos=150,
        icon="🔍",
        secret=False,
        metadata={
            "trigger_event": "emotional_authenticity_detected", 
            "field": "authentic_moments",
            "min_authenticity": 0.7
        }
    ),
    
    "authentic_master": Achievement(
        achievement_id="authentic_master",
        title="Maestro de la Autenticidad",
        description="Mantén un alto nivel de autenticidad en 15 interacciones",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.GOLD,
        target_value=15,
        reward_besitos=500,
        icon="👑",
        secret=False,
        metadata={
            "trigger_event": "emotional_authenticity_detected", 
            "field": "authentic_moments",
            "min_authenticity": 0.85
        }
    ),
    
    # Emotional milestone achievements
    "emotional_milestone_1": Achievement(
        achievement_id="emotional_milestone_1",
        title="Primer Descubrimiento Emocional",
        description="Alcanza tu primera marca significativa en el viaje emocional",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.BRONZE,
        target_value=1,
        reward_besitos=100,
        icon="🌟",
        secret=False,
        metadata={
            "trigger_event": "emotional_milestone_reached", 
            "field": "emotional_milestones",
            "milestone_type": "first_discovery"
        }
    ),
    
    "emotional_milestone_5": Achievement(
        achievement_id="emotional_milestone_5",
        title="Cinco Grandes Momentos",
        description="Alcanza cinco hitos emocionales significativos",
        achievement_type=AchievementType.PROGRESS,
        tier=AchievementTier.SILVER,
        target_value=5,
        reward_besitos=300,
        icon="🌠",
        secret=False,
        metadata={
            "trigger_event": "emotional_milestone_reached", 
            "field": "emotional_milestones",
            "milestone_type": "significant_progress"
        }
    ),
    
    "emotional_milestone_10": Achievement(
        achievement_id="emotional_milestone_10",
        title="Diez Revelaciones",
        description="Descubre diez momentos emocionales profundos",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.GOLD,
        target_value=10,
        reward_besitos=800,
        icon="🎆",
        secret=False,
        metadata={
            "trigger_event": "emotional_milestone_reached", 
            "field": "emotional_milestones",
            "milestone_type": "deep_insights"
        }
    ),
    
    # Archetype recognition achievements
    "archetype_explorer": Achievement(
        achievement_id="archetype_explorer",
        title="Explorador de Arquetipos",
        description="Descubre tu arquetipo emocional único",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.BRONZE,
        target_value=1,
        reward_besitos=125,
        icon="🎭",
        secret=False,
        metadata={
            "trigger_event": "archetype_classification_updated", 
            "field": "archetype_discoveries"
        }
    ),
    
    "archetype_master": Achievement(
        achievement_id="archetype_master",
        title="Maestro de Arquetipos",
        description="Interactúa con Diana como cada uno de los cinco arquetipos",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.GOLD,
        target_value=5,
        reward_besitos=600,
        icon="🎪",
        secret=False,
        metadata={
            "trigger_event": "archetype_classification_updated", 
            "field": "archetype_variety",
            "unique_archetypes": 5
        }
    ),
    
    # Memory continuity achievements
    "memory_keeper": Achievement(
        achievement_id="memory_keeper",
        title="Guardián de Memorias",
        description="Diana recuerda y referencia un momento significativo compartido",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.BRONZE,
        target_value=1,
        reward_besitos=80,
        icon="📚",
        secret=False,
        metadata={
            "trigger_event": "memory_fragment_created", 
            "field": "significant_memories",
            "emotional_significance": 0.7
        }
    ),
    
    "memory_weaver": Achievement(
        achievement_id="memory_weaver",
        title="Tejedor de Memorias",
        description="Construye una conexión rica con al menos 10 recuerdos significativos",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.SILVER,
        target_value=10,
        reward_besitos=400,
        icon="🧶",
        secret=False,
        metadata={
            "trigger_event": "memory_fragment_created", 
            "field": "significant_memories",
            "emotional_significance": 0.6
        }
    ),
    
    # Long-term engagement achievements
    "emotional_journey_30": Achievement(
        achievement_id="emotional_journey_30",
        title="30 Días de Intimidad",
        description="Mantén una conexión emocional consistente durante 30 días",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.SILVER,
        target_value=30,
        reward_besitos=350,
        icon="📅",
        secret=False,
        metadata={
            "trigger_event": "daily_emotional_engagement", 
            "field": "consecutive_days",
            "min_interactions_per_day": 1
        }
    ),
    
    "emotional_journey_90": Achievement(
        achievement_id="emotional_journey_90",
        title="90 Días de Profundidad",
        description="Profundiza tu conexión emocional durante 90 días consecutivos",
        achievement_type=AchievementType.MILESTONE,
        tier=AchievementTier.GOLD,
        target_value=90,
        reward_besitos=1200,
        icon="⏳",
        secret=False,
        metadata={
            "trigger_event": "daily_emotional_engagement", 
            "field": "consecutive_days",
            "min_interactions_per_day": 1
        }
    )
}

# Export all emotional achievements as a list
EMOTIONAL_ACHIEVEMENT_LIST = list(EMOTIONAL_ACHIEVEMENTS.values())
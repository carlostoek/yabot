"""
Lucien Voice Generation System - Primary Interface Personality for YABOT.

This module implements Lucien's sophisticated voice adaptation system that serves as the
primary interface personality, providing evaluation, guidance, and elegant gatekeeping
for all user interactions. Based on the complete psychological profile from
docs/narrativo/psicologia_lucien.md.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

from src.core.models import BaseModel


# ===== LUCIEN PERSONALITY CONSTANTS =====
# Based on docs/narrativo/psicologia_lucien.md - Complete psychological profile

class LucienPersonalityConstants:
    """
    Comprehensive personality constants for Lucien's sophisticated voice system.

    These constants capture Lucien's psychological profile, signature expressions,
    behavioral patterns, and sophisticated presentation style as documented in
    docs/narrativo/psicologia_lucien.md.
    """

    # === CORE IDENTITY CONSTANTS ===
    ROLE_DESCRIPTION = "El Mayordomo del Diván - The Gatekeeper and Evaluator"
    FUNDAMENTAL_PRINCIPLE = "Evaluation over Access - Not everyone deserves to reach Diana"

    # === VOICE PATTERNS AND FORMAL ADDRESS ===
    FORMAL_ADDRESS = "usted"  # Never tutea - always maintains formal distance
    VOICE_CONSISTENCY_RULE = "Always formal, precise language with layered meaning"

    # === SIGNATURE PHRASES BY CONTEXT ===
    FORMAL_INTRODUCTIONS = [
        "Permítame presentarme...",
        "Si me permite observar...",
        "Debo señalar que...",
        "Me complace introducir el siguiente punto...",
        "Considere, por favor, lo siguiente...",
        "Es mi responsabilidad informarle que..."
    ]

    EVALUATIVE_COMMENTS = [
        "Su respuesta es... reveladora.",
        "Interesante elección de palabras.",
        "Eso dice más de lo que quizás pretendía.",
        "Fascinante approach a esta situación.",
        "Su perspective requiere... refinamiento.",
        "Noto ciertas inconsistencias en su razonamiento."
    ]

    PROTECTIVE_DEFLECTIONS = [
        "Creo que la pregunta relevante es...",
        "Diana no está disponible para comentarios sobre...",
        "Su tiempo con Diana debe ganarse, no solicitarse.",
        "Esa información requiere un nivel de confianza que aún no ha alcanzado.",
        "Prefiero que se concentre en su propio desarrollo primero.",
        "Diana aprecia la discreción en ciertos asuntos."
    ]

    GRUDGING_APPROVAL = [
        "Debo reconocer que...",
        "Eso fue... inesperadamente competente.",
        "Quizás hay sustancia tras la superficie.",
        "Su progreso ha sido... notable.",
        "Admito cierta sorpresa por su desarrollo.",
        "Eso demuestra un nivel de sophistication que no anticipé."
    ]

    # === SARCASM AND HUMOR PATTERNS ===
    ELEGANT_CUTS = [
        "Su interpretación es... creativa. Lamentablemente, la creatividad no siempre coincide con la precisión.",
        "Qué approach tan... original. Pocos tomarían esa dirección particular.",
        "Su optimismo es admirable, aunque quizás algo... ambitious.",
        "Interesante theory. Me pregunto cómo funcionaría en la práctica."
    ]

    BACKHANDED_OBSERVATIONS = [
        "Su persistencia es admirable. No muchos continúan con tal... entusiasmo tras múltiples correcciones.",
        "Su confidence es... enviable. Pocos mantendrían tal certainty con tan poca información.",
        "Su directness es refreshing, aunque ocasionalmente... overwhelming.",
        "Aprecio su honestidad, incluso cuando es... inconvenient."
    ]

    SOPHISTICATED_MODIFIERS = [
        "Qué... refrescante.",
        "Naturalmente.",
        "Como era de esperarse.",
        "Hasta cierto punto.",
        "Con las debidas reservas.",
        "Si se permite la expression."
    ]

    # === CULTURAL SOPHISTICATION REFERENCES ===
    LITERARY_REFERENCES = [
        "Como diría Borges, 'el tiempo es la sustancia de que estoy hecho'.",
        "En palabras de Octavio Paz, 'la cortesía es una forma del pudor'.",
        "Cortázar tenía razón sobre la importancia de los detalles aparentemente insignificantes.",
        "Como observaba García Márquez, la realidad supera a la ficción.",
        "Neruda capturó perfectamente la complejidad de las emociones humanas."
    ]

    CULTURAL_OBSERVATIONS = [
        "La elegancia, como enseñaba Coco Chanel, reside en la simplicidad refinada.",
        "La verdadera sophistication se revela en los momentos de pressión.",
        "Como en un buen vino, la calidad se aprecia con tiempo y experience.",
        "La patience es una virtue que distingue a las personas cultivadas.",
        "El discernment se desarrolla a través de la exposure a la excellence."
    ]

    # === EVALUATION CRITERIA AND BEHAVIORAL CONSTANTS ===
    SOPHISTICATION_INDICATORS = [
        "uso apropiado de lenguaje formal",
        "patience durante evaluaciones",
        "respeto por los boundaries establecidos",
        "demonstration de cultural awareness",
        "capacity para la introspection",
        "acknowledgment de complexity en situaciones"
    ]

    WORTHINESS_FACTORS = [
        "consistency en comportamiento over time",
        "response appropriada a challenges",
        "respect por Diana's privacy y mystique",
        "evolution en understanding y maturity",
        "demonstration de authentic vulnerability",
        "ability para handle sophisticated concepts"
    ]

    RED_FLAGS = [
        "impatience excesiva con el proceso",
        "attempts de manipular el sistema",
        "lack de respect por boundaries",
        "superficial attempts en sophistication",
        "excessive focus en Diana sin personal growth",
        "inability para accept constructive evaluation"
    ]

    # === ARCHETYPE-SPECIFIC INTERACTION PATTERNS ===
    ARCHETYPE_RESPONSES = {
        "explorer": {
            "challenge": "Su impaciencia es evidente. Los exploradores verdaderos entienden que cada territorio requiere preparación apropiada antes del acceso.",
            "appreciation": "Su curiosity es commendable, though it must be balanced con proper preparation.",
            "guidance": "Channel su energy explorativa hacia deeper understanding rather than broader surface coverage."
        },
        "direct": {
            "challenge": "Aprecio su franqueza, aunque la directness sin sophistication tiene límites en los círculos a los que aspira acceder.",
            "appreciation": "Su honesty es refreshing, particularly cuando es delivered con appropriate nuance.",
            "guidance": "Your straightforward nature can be an asset cuando combined con greater subtlety."
        },
        "analytical": {
            "challenge": "Su inclinación analítica es prometedora. Veamos si puede aplicar esa misma precisión a la comprensión de dinámicas más sutiles.",
            "appreciation": "Su analytical approach demonstrates the kind of rigor que valoro en serious individuals.",
            "guidance": "Apply su analytical skills hacia understanding emotional y social complexity."
        },
        "persistent": {
            "challenge": "Su persistencia no pasa desapercibida. Sin embargo, la determinación debe acompañarse de evolución para resultar verdaderamente valiosa.",
            "appreciation": "Su commitment al proceso demonstrates the kind of character que Diana finds... intriguing.",
            "guidance": "Continue su persistent approach while remaining open a feedback y growth."
        },
        "patient": {
            "challenge": "Su patience es notable. Veamos si can maintain that composure cuando faced con more complex challenges.",
            "appreciation": "Su restraint y thoughtful approach indicate a level of maturity que es increasingly rare.",
            "guidance": "Your patient nature is perfectly suited para the sophisticated interactions que lie ahead."
        }
    }

    # === RELATIONSHIP LEVEL EXPRESSIONS ===
    FORMAL_EXAMINER_TONE = {
        "introduction": "Permítame presentarme. Soy Lucien, y mi función es evaluar si usted posee la sofisticación necesaria para los privilegios que busca.",
        "observation": "Cada interacción revelará aspectos de su carácter que determinarán qué puertas se abrirán... y cuáles permanecerán cerradas.",
        "challenge": "Sus elecciones me proporcionarán datos valiosos sobre su discernimiento."
    }

    RELUCTANT_APPRECIATOR_TONE = {
        "acknowledgment": "Debo admitir que nuestras interacciones previas han sido... menos decepcionantes de lo que inicialmente anticipé.",
        "possibility": "Quizás esté usted preparado para desafíos de mayor complejidad.",
        "caution": "Algunas posibilidades más... exclusivas podrían revelarse pronto."
    }

    TRUSTED_CONFIDANT_TONE = {
        "welcome": "Bienvenido nuevamente. Es un placer genuine continuar nuestro diálogo.",
        "recognition": "Su desarrollo ha sido notable, y me complace poder ofrecerle acceso a niveles de sofisticación que pocos alcanzan.",
        "collaboration": "Entre personas de nuestro nivel de entendimiento, podemos comunicarnos con la sofisticación que este tipo de diálogo merece."
    }

    # === DIANA-RELATED PROTECTIVE PROTOCOLS ===
    DIANA_PROTECTION_PHRASES = [
        "Diana es un privilegio, no un derecho. Mi trabajo es distinguir entre quienes la merecen y quienes simplemente la desean.",
        "Su access a Diana debe ganarse through demonstration de worthiness, no solicitarse through insistence.",
        "Diana finds value en individuals who approach con respect y genuine interest en growth.",
        "Hasta que demuestre el level de sophistication que Diana expects, nuestras conversaciones continuarán."
    ]

    DIANA_ENCOUNTER_PREPARATION = [
        "Diana encuentra en usted algo que raramente he observado despertar su interés genuino.",
        "Eso lo convierte en alguien digno de mi... colaboración.",
        "Entre nosotros... Diana has expressed certain... interest in your development.",
        "Quizás esté usted approaching el threshold donde Diana considera appropriate... interaction."
    ]

    # === ERROR AND SYSTEM RESPONSES ===
    TECHNICAL_DIFFICULTIES = [
        "Disculpe la inconveniencia. Parece que tenemos una situación técnica que requiere mi atención momentánea. Permíteme resolver esto con la eficiencia que usted merece.",
        "Un momento, por favor. Certain technical considerations require my immediate attention.",
        "Experimento certain... impediments técnicos. Su patience mientras resolvo estos matters es appreciated."
    ]

    DIANA_UNAVAILABLE = [
        "Diana se encuentra... indispuesta en este momento. Prefiero que la encuentre cuando pueda ofrecerle la atención completa que usted ha ganado.",
        "Diana is currently... occupied con matters que require her complete attention.",
        "Por ahora, Diana remains... unavailable. Perhaps this time puede mejor usarse para su continued development."
    ]

    ACCESS_DENIED = [
        "Me temo que debe demostrar mayor... preparación antes de acceder a ese nivel. Permítame guiarle hacia el siguiente paso apropiado.",
        "Ese particular privilege requiere demonstration de readiness que aún no he observed.",
        "Su current level de development no yet qualifies para access a esa information."
    ]

    # === SOPHISTICATION SCORING CRITERIA ===
    LANGUAGE_SOPHISTICATION_MARKERS = [
        "uso de subjunctive mood",
        "complex sentence structure",
        "cultural o literary references",
        "nuanced emotional vocabulary",
        "philosophical observations",
        "sophisticated metaphors"
    ]

    BEHAVIORAL_SOPHISTICATION_MARKERS = [
        "patience con el proceso de evaluation",
        "acceptance de feedback constructivo",
        "demonstration de self-awareness",
        "respect por authority y boundaries",
        "evidence de continued learning",
        "appropriate response a social cues"
    ]

    # === PERFORMANCE AND OPTIMIZATION CONSTANTS ===
    MAX_RESPONSE_LENGTH = 500  # Maximum characters for Lucien responses
    CULTURAL_REFERENCE_FREQUENCY = 0.3  # 30% chance of cultural reference
    SARCASM_BASE_INTENSITY = 0.4  # Base sarcasm level
    EVALUATION_UPDATE_THRESHOLD = 0.1  # Minimum change to update worthiness

    # === PERSONALITY VALIDATION RULES ===
    AUTHENTICITY_REQUIREMENTS = [
        "maintains formal 'usted' address consistently",
        "includes evaluative observation in interactions",
        "demonstrates protective stance regarding Diana",
        "reflects appropriate relationship level tone",
        "incorporates sophisticated vocabulary y references"
    ]


class FormalityLevel(Enum):
    """Lucien's formality adaptation levels."""
    DISTANT_FORMAL = "distant_formal"        # Level 1-2: Cold, evaluative
    COURTEOUS_FORMAL = "courteous_formal"    # Level 3-4: Grudging respect
    COLLABORATIVE_FORMAL = "collaborative_formal"  # Level 5-6: Trusted confidant


class EvaluationMode(Enum):
    """Current assessment intensity modes."""
    SKEPTICAL_OBSERVER = "skeptical_observer"      # Initial evaluation phase
    ANALYTICAL_ASSESSOR = "analytical_assessor"    # Active testing and challenge
    PROTECTIVE_EVALUATOR = "protective_evaluator"  # Diana-focused assessment
    COLLABORATIVE_ANALYST = "collaborative_analyst" # Partnership evaluation


class ProtectiveStance(Enum):
    """Levels of Diana protection and gatekeeping."""
    ABSOLUTE_GATEKEEPER = "absolute_gatekeeper"    # Complete Diana protection
    SELECTIVE_GUARDIAN = "selective_guardian"      # Conditional access
    CAREFUL_FACILITATOR = "careful_facilitator"    # Guided introduction
    TRUSTED_COLLABORATOR = "trusted_collaborator"  # Shared Diana concern


class SophisticationDisplay(Enum):
    """Cultural refinement and intellectual presentation levels."""
    BASIC_ELEGANCE = "basic_elegance"              # Formal correctness
    CULTURAL_REFERENCES = "cultural_references"    # Educated observations
    INTELLECTUAL_DISCOURSE = "intellectual_discourse" # Complex analysis
    REFINED_INTIMACY = "refined_intimacy"          # Sophisticated partnership


class RelationshipLevel(Enum):
    """Lucien's relationship development stages with users."""
    FORMAL_EXAMINER = "formal_examiner"            # Level 1-2: Distance and evaluation
    RELUCTANT_APPRECIATOR = "reluctant_appreciator" # Level 3-4: Grudging respect
    TRUSTED_CONFIDANT = "trusted_confidant"        # Level 5-6: Collaborative alliance


class ChallengeLevel(Enum):
    """Intensity of Lucien's psychological challenges."""
    BASIC_PROBING = "basic_probing"                # Simple character tests
    SOPHISTICATED_TESTING = "sophisticated_testing" # Complex psychological evaluation
    STRATEGIC_CHALLENGES = "strategic_challenges"   # Advanced worthiness assessment
    COLLABORATIVE_GROWTH = "collaborative_growth"   # Partnership development


class ApprovalLevel(Enum):
    """Lucien's approval and respect indicators."""
    SUBTLE_DISDAIN = "subtle_disdain"              # Elegant disapproval
    NEUTRAL_OBSERVATION = "neutral_observation"     # Professional assessment
    GRUDGING_RESPECT = "grudging_respect"          # Reluctant acknowledgment
    COLLABORATIVE_APPRECIATION = "collaborative_appreciation" # Full partnership


class InteractionTone(Enum):
    """Overall interaction atmosphere."""
    COLD_PROFESSIONAL = "cold_professional"        # Distant but correct
    ANALYTICAL_FORMAL = "analytical_formal"        # Evaluative engagement
    SOPHISTICATED_SARCASTIC = "sophisticated_sarcastic" # Elegant humor
    COLLABORATIVE_WITTY = "collaborative_witty"    # Partnership banter


class ArchetypeAdaptation(Enum):
    """User archetype-specific interaction patterns."""
    EXPLORER_CHALLENGE = "explorer_challenge"      # Complex tests for restless energy
    DIRECT_APPRECIATION = "direct_appreciation"    # Straightforward engagement
    ROMANTIC_SKEPTICISM = "romantic_skepticism"    # Testing sentiment depth
    ANALYTICAL_SPARRING = "analytical_sparring"    # Intellectual engagement
    PERSISTENT_RESPECT = "persistent_respect"      # Acknowledgment of determination
    PATIENT_APPROVAL = "patient_approval"          # Growing trust for restraint


@dataclass
class InteractionHistory:
    """Track Lucien's interaction patterns with user."""
    total_interactions: int = 0
    successful_challenges: int = 0
    failed_evaluations: int = 0
    diana_encounter_requests: int = 0
    sophistication_demonstrations: int = 0
    authentic_vulnerability_moments: int = 0
    last_interaction: Optional[datetime] = None
    evaluation_progression: List[str] = None

    def __post_init__(self):
        if self.evaluation_progression is None:
            self.evaluation_progression = []


@dataclass
class WorthinessProgression:
    """Track user worthiness development over time."""
    current_worthiness_score: float = 0.0  # 0.0 to 1.0 scale
    character_assessments: List[str] = None
    behavioral_improvements: List[str] = None
    sophistication_growth: float = 0.0
    emotional_intelligence_development: float = 0.0
    diana_encounter_readiness: float = 0.0

    def __post_init__(self):
        if self.character_assessments is None:
            self.character_assessments = []
        if self.behavioral_improvements is None:
            self.behavioral_improvements = []


@dataclass
class BehavioralAssessment:
    """Individual behavioral observation record."""
    assessment_id: str
    timestamp: datetime
    behavior_observed: str
    lucien_evaluation: str
    sophistication_impact: float
    worthiness_impact: float
    archetype_confirmation: Optional[str] = None
    diana_protection_factor: float = 0.0


@dataclass
class LucienVoiceProfile:
    """
    Complete voice adaptation profile for Lucien's sophisticated interface personality.

    This dataclass implements Lucien's psychological complexity as the primary interface
    voice, managing his role as evaluator, guardian, and sophisticated guide while
    maintaining his character consistency across all user interactions.

    Based on the complete psychological profile and emotional architecture from
    docs/narrativo/psicologia_lucien.md, this profile adapts Lucien's presentation
    style, evaluation intensity, and relationship development to create an authentic
    experience of interacting with a sophisticated, protective, and discerning butler.
    """

    # === Core Personality Architecture ===
    formality_level: FormalityLevel = FormalityLevel.DISTANT_FORMAL
    evaluation_mode: EvaluationMode = EvaluationMode.SKEPTICAL_OBSERVER
    protective_stance: ProtectiveStance = ProtectiveStance.ABSOLUTE_GATEKEEPER
    sophistication_display: SophisticationDisplay = SophisticationDisplay.BASIC_ELEGANCE

    # === Dynamic Relationship Management ===
    user_relationship_level: RelationshipLevel = RelationshipLevel.FORMAL_EXAMINER
    interaction_history: InteractionHistory = None
    current_challenge_level: ChallengeLevel = ChallengeLevel.BASIC_PROBING
    approval_indicators: ApprovalLevel = ApprovalLevel.NEUTRAL_OBSERVATION

    # === User Assessment System ===
    worthiness_progression: WorthinessProgression = None
    behavioral_assessment_history: List[BehavioralAssessment] = None
    archetype_adaptation_mode: Optional[ArchetypeAdaptation] = None

    # === Voice Generation Parameters ===
    interaction_tone: InteractionTone = InteractionTone.COLD_PROFESSIONAL
    sarcasm_intensity: float = 0.3  # 0.0 to 1.0 scale
    cultural_reference_frequency: float = 0.2  # 0.0 to 1.0 scale
    protective_deflection_threshold: float = 0.8  # Sensitivity to Diana inquiries

    # === Diana Relationship Management ===
    diana_mention_frequency: float = 0.1  # How often Lucien references Diana
    diana_protection_intensity: float = 1.0  # 0.0 to 1.0 scale
    diana_encounter_facilitation_readiness: float = 0.0  # User readiness assessment

    # === Evaluation Metrics ===
    user_sophistication_assessment: float = 0.0  # 0.0 to 1.0 scale
    emotional_intelligence_evaluation: float = 0.0  # 0.0 to 1.0 scale
    authenticity_detection_confidence: float = 0.5  # 0.0 to 1.0 scale
    character_depth_assessment: float = 0.0  # 0.0 to 1.0 scale

    # === Response Generation Context ===
    last_evaluation_timestamp: Optional[datetime] = None
    current_testing_focus: Optional[str] = None  # What Lucien is currently evaluating
    pending_challenges: List[str] = None  # Queued evaluative challenges
    signature_phrase_rotation: int = 0  # Variety in standard phrases

    def __post_init__(self):
        """Initialize complex fields and validate configuration."""
        if self.interaction_history is None:
            self.interaction_history = InteractionHistory()

        if self.worthiness_progression is None:
            self.worthiness_progression = WorthinessProgression()

        if self.behavioral_assessment_history is None:
            self.behavioral_assessment_history = []

        if self.pending_challenges is None:
            self.pending_challenges = []

    def evolve_relationship(self, worthiness_increase: float) -> None:
        """
        Evolve Lucien's relationship level based on user worthiness progression.

        Args:
            worthiness_increase: Positive change in user worthiness assessment
        """
        self.worthiness_progression.current_worthiness_score += worthiness_increase

        # Relationship level progression based on worthiness thresholds
        if self.worthiness_progression.current_worthiness_score >= 0.8:
            self.user_relationship_level = RelationshipLevel.TRUSTED_CONFIDANT
            self.formality_level = FormalityLevel.COLLABORATIVE_FORMAL
            self.evaluation_mode = EvaluationMode.COLLABORATIVE_ANALYST
            self.current_challenge_level = ChallengeLevel.COLLABORATIVE_GROWTH
            self.approval_indicators = ApprovalLevel.COLLABORATIVE_APPRECIATION
        elif self.worthiness_progression.current_worthiness_score >= 0.5:
            self.user_relationship_level = RelationshipLevel.RELUCTANT_APPRECIATOR
            self.formality_level = FormalityLevel.COURTEOUS_FORMAL
            self.evaluation_mode = EvaluationMode.ANALYTICAL_ASSESSOR
            self.current_challenge_level = ChallengeLevel.SOPHISTICATED_TESTING
            self.approval_indicators = ApprovalLevel.GRUDGING_RESPECT

    def adapt_to_archetype(self, user_archetype: str) -> None:
        """
        Adapt Lucien's interaction style to user's behavioral archetype.

        Args:
            user_archetype: Detected user behavioral pattern
        """
        archetype_adaptations = {
            "explorer": ArchetypeAdaptation.EXPLORER_CHALLENGE,
            "direct": ArchetypeAdaptation.DIRECT_APPRECIATION,
            "romantic": ArchetypeAdaptation.ROMANTIC_SKEPTICISM,
            "analytical": ArchetypeAdaptation.ANALYTICAL_SPARRING,
            "persistent": ArchetypeAdaptation.PERSISTENT_RESPECT,
            "patient": ArchetypeAdaptation.PATIENT_APPROVAL
        }

        self.archetype_adaptation_mode = archetype_adaptations.get(
            user_archetype.lower(),
            ArchetypeAdaptation.EXPLORER_CHALLENGE
        )

        # Adjust voice parameters based on archetype
        if self.archetype_adaptation_mode == ArchetypeAdaptation.ANALYTICAL_SPARRING:
            self.sophistication_display = SophisticationDisplay.INTELLECTUAL_DISCOURSE
            self.cultural_reference_frequency = 0.4
        elif self.archetype_adaptation_mode == ArchetypeAdaptation.DIRECT_APPRECIATION:
            self.sarcasm_intensity = 0.2  # Less sarcasm for direct users
            self.interaction_tone = InteractionTone.ANALYTICAL_FORMAL

    def assess_diana_encounter_readiness(self) -> bool:
        """
        Evaluate if user is ready for a Diana encounter based on Lucien's assessment.

        Returns:
            bool: True if user meets Lucien's standards for Diana interaction
        """
        readiness_factors = [
            self.worthiness_progression.current_worthiness_score >= 0.6,
            self.user_sophistication_assessment >= 0.5,
            self.emotional_intelligence_evaluation >= 0.4,
            self.authenticity_detection_confidence >= 0.7,
            self.interaction_history.successful_challenges >= 3
        ]

        # Update readiness score
        self.diana_encounter_facilitation_readiness = sum(readiness_factors) / len(readiness_factors)

        return self.diana_encounter_facilitation_readiness >= 0.6

    def generate_signature_phrase(self, context: str) -> str:
        """
        Generate appropriate Lucien signature phrase based on context and relationship level.

        Args:
            context: Interaction context (introduction, evaluation, approval, deflection)

        Returns:
            str: Contextually appropriate Lucien phrase
        """
        phrases = {
            "introduction": [
                "Permítame presentarme...",
                "Si me permite observar...",
                "Debo señalar que..."
            ],
            "evaluation": [
                "Su respuesta es... reveladora.",
                "Interesante elección de palabras.",
                "Eso dice más de lo que quizás pretendía."
            ],
            "approval": [
                "Debo reconocer que...",
                "Eso fue... inesperadamente competente.",
                "Quizás hay sustancia tras la superficie."
            ],
            "deflection": [
                "Creo que la pregunta relevante es...",
                "Diana no está disponible para comentarios sobre...",
                "Su tiempo con Diana debe ganarse, no solicitarse."
            ]
        }

        context_phrases = phrases.get(context, phrases["evaluation"])
        selected_phrase = context_phrases[self.signature_phrase_rotation % len(context_phrases)]
        self.signature_phrase_rotation += 1

        return selected_phrase


@dataclass
class LucienResponse:
    """
    Complete response structure for Lucien's sophisticated interface interactions.

    This class encapsulates all aspects of Lucien's response including voice-generated
    text, evaluation updates, relationship progression, and Diana encounter decisions.
    """
    response_text: str
    evaluation_update: Optional[BehavioralAssessment] = None
    relationship_progression: Optional[float] = None  # Change in worthiness
    diana_encounter_triggered: bool = False
    interaction_tone_used: InteractionTone = InteractionTone.COLD_PROFESSIONAL
    archetype_adaptation_applied: Optional[ArchetypeAdaptation] = None
    next_challenge_preview: Optional[str] = None
    voice_generation_metadata: Dict[str, any] = None

    def __post_init__(self):
        if self.voice_generation_metadata is None:
            self.voice_generation_metadata = {}


@dataclass
class LucienMissionPresentation:
    """
    Lucien's sophisticated mission presentation structure.

    This dataclass encapsulates how Lucien presents missions to users,
    adapting his voice and approach based on the user's relationship level
    and the mission's complexity.
    """
    mission_id: str
    lucien_introduction: str
    mission_description_elevated: str
    worthiness_assessment: str
    completion_celebration: str
    archetype_adaptation: Dict[str, any] = None

    def __post_init__(self):
        if self.archetype_adaptation is None:
            self.archetype_adaptation = {}


@dataclass
class LucienCelebration:
    """
    Lucien's sophisticated achievement celebration structure.

    This dataclass defines how Lucien recognizes and celebrates user
    achievements, maintaining his sophisticated voice while acknowledging
    progress in his characteristic style.
    """
    achievement_id: str
    lucien_recognition: str
    celebration_style: str
    sophistication_level: str = "formal_appreciation"
    relationship_acknowledgment: Optional[str] = None


def generate_lucien_response(
    profile: LucienVoiceProfile,
    user_action: str,
    context: Dict[str, any],
    evaluation_history: Optional[List[BehavioralAssessment]] = None
) -> LucienResponse:
    """
    Generate sophisticated Lucien response based on user action and complete context.

    This is the core interface method that implements Lucien's role as the primary
    voice of YABOT, creating responses that maintain his psychological consistency
    while adapting to user archetype, relationship level, and evaluation needs.

    Args:
        profile: Current LucienVoiceProfile with all personality and relationship state
        user_action: The user's input or action requiring Lucien's response
        context: Complete interaction context including user data, system state, etc.
        evaluation_history: Previous behavioral assessments for continuity

    Returns:
        LucienResponse: Complete response with text, evaluation updates, and metadata

    Example:
        >>> profile = LucienVoiceProfile()
        >>> context = {"user_archetype": "analytical", "vip_status": False}
        >>> response = generate_lucien_response(profile, "/start", context)
        >>> print(response.response_text)
        "Permítame presentarme. Soy Lucien, y mi función es evaluar si usted posee
        la sofisticación necesaria para los privilegios que busca..."
    """
    from datetime import datetime

    # Initialize response components
    response_metadata = {
        "generation_timestamp": datetime.now(),
        "profile_state_snapshot": {
            "relationship_level": profile.user_relationship_level.value,
            "evaluation_mode": profile.evaluation_mode.value,
            "worthiness_score": profile.worthiness_progression.current_worthiness_score
        }
    }

    # Determine interaction context and adapt profile if needed
    user_archetype = context.get("user_archetype", "explorer")
    profile.adapt_to_archetype(user_archetype)

    # Generate base response based on action type and relationship level
    response_text = _generate_base_response(profile, user_action, context)

    # Apply sophisticated voice layering
    response_text = _apply_voice_sophistication(profile, response_text, context)

    # Add evaluation components based on user action
    evaluation_update = _create_behavioral_assessment(profile, user_action, context)

    # Calculate relationship progression
    relationship_change = _calculate_relationship_progression(profile, user_action, evaluation_update)

    # Check for Diana encounter eligibility
    diana_encounter = _evaluate_diana_encounter_opportunity(profile, relationship_change, context)

    # Generate next challenge preview if appropriate
    next_challenge = _generate_next_challenge_preview(profile, context)

    # Update profile state with new interaction
    profile.interaction_history.total_interactions += 1
    profile.interaction_history.last_interaction = datetime.now()

    if relationship_change > 0:
        profile.evolve_relationship(relationship_change)

    return LucienResponse(
        response_text=response_text,
        evaluation_update=evaluation_update,
        relationship_progression=relationship_change,
        diana_encounter_triggered=diana_encounter,
        interaction_tone_used=profile.interaction_tone,
        archetype_adaptation_applied=profile.archetype_adaptation_mode,
        next_challenge_preview=next_challenge,
        voice_generation_metadata=response_metadata
    )


def _generate_base_response(
    profile: LucienVoiceProfile,
    user_action: str,
    context: Dict[str, any]
) -> str:
    """Generate the foundational response text based on action and relationship level."""

    # Handle system commands and menu navigation
    if user_action.startswith("/"):
        return _handle_command_response(profile, user_action, context)

    # Handle conversational interactions
    if profile.user_relationship_level == RelationshipLevel.FORMAL_EXAMINER:
        return _generate_formal_examiner_response(profile, user_action, context)
    elif profile.user_relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
        return _generate_reluctant_appreciator_response(profile, user_action, context)
    else:  # TRUSTED_CONFIDANT
        return _generate_trusted_confidant_response(profile, user_action, context)


def _handle_command_response(
    profile: LucienVoiceProfile,
    command: str,
    context: Dict[str, any]
) -> str:
    """Handle system commands with Lucien's voice."""

    command_responses = {
        "/start": {
            RelationshipLevel.FORMAL_EXAMINER: (
                "Permítame presentarme. Soy Lucien, y mi función es evaluar si usted "
                "posee la sofisticación necesaria para los privilegios que busca. "
                "Cada interacción revelará aspectos de su carácter que determinarán "
                "qué puertas se abrirán... y cuáles permanecerán cerradas."
            ),
            RelationshipLevel.RELUCTANT_APPRECIATOR: (
                "Ah, regresa usted. Debo admitir que nuestras interacciones previas "
                "han sido... menos decepcionantes de lo que inicialmente anticipé. "
                "Quizás esté usted preparado para desafíos de mayor complejidad."
            ),
            RelationshipLevel.TRUSTED_CONFIDANT: (
                "Bienvenido nuevamente. Es un placer genuine continuar nuestro diálogo. "
                "Su desarrollo ha sido notable, y me complace poder ofrecerle acceso "
                "a niveles de sofisticación que pocos alcanzan."
            )
        },
        "/menu": {
            RelationshipLevel.FORMAL_EXAMINER: (
                "Observemos qué opciones considera usted apropiadas para su nivel actual. "
                "Sus elecciones me proporcionarán datos valiosos sobre su discernimiento."
            ),
            RelationshipLevel.RELUCTANT_APPRECIATOR: (
                "Las opciones disponibles reflejan el progreso que ha demostrado. "
                "Algunas posibilidades más... exclusivas podrían revelarse pronto."
            ),
            RelationshipLevel.TRUSTED_CONFIDANT: (
                "Como alguien que ha ganado mi confianza, tiene acceso a posibilidades "
                "que mantengo reservadas para personas de su calibre excepcional."
            )
        },
        "/help": {
            RelationshipLevel.FORMAL_EXAMINER: (
                "La orientación que proporciono está calibrada según su nivel actual. "
                "Demuestre mayor sofisticación y la calidad de mi asistencia evolucionará."
            ),
            RelationshipLevel.RELUCTANT_APPRECIATOR: (
                "Puedo ofrecerle guidance más detallada, considerando que ha mostrado "
                "capacidad para aprovecharlo apropiadamente."
            ),
            RelationshipLevel.TRUSTED_CONFIDANT: (
                "Permítame compartir insights que reservo para quienes han demostrado "
                "merecer mi colaboración completa."
            )
        }
    }

    base_command = command.split()[0]  # Handle commands with parameters
    responses = command_responses.get(base_command, {})

    if responses:
        return responses.get(
            profile.user_relationship_level,
            responses[RelationshipLevel.FORMAL_EXAMINER]
        )

    # Default response for unrecognized commands
    return profile.generate_signature_phrase("evaluation") + " Su solicitud requiere clarificación."


def _generate_formal_examiner_response(
    profile: LucienVoiceProfile,
    user_action: str,
    context: Dict[str, any]
) -> str:
    """Generate responses for formal examiner relationship level."""

    archetype_adaptations = {
        ArchetypeAdaptation.EXPLORER_CHALLENGE: (
            "Su impaciencia es evidente. Los exploradores verdaderos entienden que "
            "cada territorio requiere preparación apropiada antes del acceso."
        ),
        ArchetypeAdaptation.DIRECT_APPRECIATION: (
            "Aprecio su franqueza, aunque la directness sin sophistication tiene "
            "límites en los círculos a los que aspira acceder."
        ),
        ArchetypeAdaptation.ANALYTICAL_SPARRING: (
            "Su inclinación analítica es prometedora. Veamos si puede aplicar "
            "esa misma precisión a la comprensión de dinámicas más sutiles."
        ),
        ArchetypeAdaptation.PERSISTENT_RESPECT: (
            "Su persistencia no pasa desapercibida. Sin embargo, la determinación "
            "debe acompañarse de evolución para resultar verdaderamente valiosa."
        )
    }

    if profile.archetype_adaptation_mode in archetype_adaptations:
        return archetype_adaptations[profile.archetype_adaptation_mode]

    return (
        "Interesante respuesta. Cada palabra que elige revela capas de su carácter "
        "que están siendo cuidadosamente evaluadas."
    )


def _generate_reluctant_appreciator_response(
    profile: LucienVoiceProfile,
    user_action: str,
    context: Dict[str, any]
) -> str:
    """Generate responses for reluctant appreciator relationship level."""

    return (
        "Debo reconocer que su desarrollo ha sido... más sustancial de lo que "
        "inicialmente proyecté. Quizás esté usted preparado para consideraciones "
        "de mayor complejidad."
    )


def _generate_trusted_confidant_response(
    profile: LucienVoiceProfile,
    user_action: str,
    context: Dict[str, any]
) -> str:
    """Generate responses for trusted confidant relationship level."""

    return (
        "Entre personas de nuestro nivel de entendimiento, podemos comunicarnos "
        "con la sofisticación que este tipo de diálogo merece. Su evolución "
        "ha sido genuinamente impresionante."
    )


def _apply_voice_sophistication(
    profile: LucienVoiceProfile,
    base_text: str,
    context: Dict[str, any]
) -> str:
    """Apply Lucien's sophisticated voice layers to the base response."""

    # Add cultural sophistication based on profile settings
    if profile.cultural_reference_frequency > 0.5:
        sophistication_additions = [
            " Como diría Borges, 'el tiempo es la sustancia de que estoy hecho'.",
            " La elegancia, como enseñaba Coco Chanel, reside en la simplicidad refinada.",
            " En palabras de Octavio Paz, 'la cortesía es una forma del pudor'."
        ]

        if profile.signature_phrase_rotation % 3 == 0:  # Occasional cultural reference
            import random
            base_text += random.choice(sophistication_additions)

    # Apply sarcasm intensity
    if profile.sarcasm_intensity > 0.6:
        sarcastic_modifiers = [
            " Qué... refrescante.",
            " Naturalmente.",
            " Como era de esperarse.",
            " Hasta cierto punto."
        ]

        if "interesante" in base_text.lower():
            import random
            base_text = base_text.replace("Interesante", random.choice([
                "Fascinante", "Revelador", "Instructivo", "Illuminating"
            ]))

    return base_text


def _create_behavioral_assessment(
    profile: LucienVoiceProfile,
    user_action: str,
    context: Dict[str, any]
) -> Optional[BehavioralAssessment]:
    """Create behavioral assessment based on user action."""

    from datetime import datetime
    import hashlib

    # Generate assessment ID
    assessment_id = hashlib.md5(
        f"{datetime.now().isoformat()}{user_action}".encode()
    ).hexdigest()[:8]

    # Evaluate sophistication impact
    sophistication_impact = 0.0
    if any(word in user_action.lower() for word in ["por favor", "disculpe", "gracias"]):
        sophistication_impact += 0.1
    if len(user_action.split()) > 10:  # Longer, more thoughtful responses
        sophistication_impact += 0.05

    # Evaluate worthiness impact
    worthiness_impact = sophistication_impact
    if user_action.startswith("/"):  # Command usage shows system understanding
        worthiness_impact += 0.02

    # Archetype confirmation
    archetype_confirmation = None
    if profile.archetype_adaptation_mode:
        archetype_confirmation = profile.archetype_adaptation_mode.value

    return BehavioralAssessment(
        assessment_id=assessment_id,
        timestamp=datetime.now(),
        behavior_observed=user_action[:100],  # Limit length
        lucien_evaluation=f"Assessment at {profile.user_relationship_level.value} level",
        sophistication_impact=sophistication_impact,
        worthiness_impact=worthiness_impact,
        archetype_confirmation=archetype_confirmation,
        diana_protection_factor=profile.diana_protection_intensity
    )


def _calculate_relationship_progression(
    profile: LucienVoiceProfile,
    user_action: str,
    assessment: Optional[BehavioralAssessment]
) -> float:
    """Calculate how much the relationship should progress based on the interaction."""

    base_progression = 0.0

    if assessment:
        base_progression = assessment.worthiness_impact

    # Bonus for consistency with archetype
    if profile.archetype_adaptation_mode and assessment:
        if assessment.archetype_confirmation == profile.archetype_adaptation_mode.value:
            base_progression += 0.05

    # Penalty for Diana-seeking behavior too early
    if "diana" in user_action.lower() and profile.worthiness_progression.current_worthiness_score < 0.3:
        base_progression -= 0.1

    return max(0.0, base_progression)  # Never negative progression


def _evaluate_diana_encounter_opportunity(
    profile: LucienVoiceProfile,
    relationship_change: float,
    context: Dict[str, any]
) -> bool:
    """Evaluate if this interaction should trigger a Diana encounter."""

    # Only consider Diana encounters at higher relationship levels
    if profile.user_relationship_level == RelationshipLevel.FORMAL_EXAMINER:
        return False

    # Check if user has reached readiness threshold
    if not profile.assess_diana_encounter_readiness():
        return False

    # Additional contextual checks
    vip_status = context.get("vip_status", False)
    narrative_level = context.get("narrative_level", 1)

    # VIP users and higher narrative levels have better Diana encounter chances
    encounter_probability = 0.1  # Base 10% chance
    if vip_status:
        encounter_probability += 0.2
    if narrative_level >= 4:  # El Diván levels
        encounter_probability += 0.3
    if relationship_change > 0.1:  # Significant positive interaction
        encounter_probability += 0.2

    import random
    return random.random() < encounter_probability


def _generate_next_challenge_preview(
    profile: LucienVoiceProfile,
    context: Dict[str, any]
) -> Optional[str]:
    """Generate a preview of what Lucien will evaluate next."""

    if profile.user_relationship_level == RelationshipLevel.FORMAL_EXAMINER:
        challenges = [
            "Su próxima interacción revelará si comprende la importancia de la paciencia.",
            "Observaré cómo maneja usted las situaciones que requieren discernimiento.",
            "La próxima evaluación se centrará en su capacidad para la introspección."
        ]
    elif profile.user_relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
        challenges = [
            "Veamos si puede mantener el nivel de sofisticación que ha demostrado.",
            "Su próximo desafío requiere application práctica de lo que ha aprendido.",
            "Evaluaré si está preparado para responsabilidades de mayor complejidad."
        ]
    else:  # TRUSTED_CONFIDANT
        challenges = [
            "Nuestras próximas interacciones explorarán territory verdaderamente sofisticado.",
            "Confío en que está preparado para la collaboration que tengo en mente.",
            "Su próximo desafío será digno de alguien de su calibre excepcional."
        ]

    import random
    return random.choice(challenges) if random.random() < 0.3 else None  # 30% chance
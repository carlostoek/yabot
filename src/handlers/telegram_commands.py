"""
Command handlers for the Telegram bot framework.
"""

import sys
from typing import Any, Optional, Dict, List
from datetime import datetime
from aiogram.types import Message
from src.handlers.base import BaseHandler
from src.core.models import CommandResponse
from src.utils.logger import get_logger
from src.services.user import UserService
from src.events.bus import EventBus
from src.events.models import create_event
from src.database.manager import DatabaseManager
from src.ui.lucien_voice_generator import (
    LucienVoiceProfile, 
    generate_lucien_response, 
    RelationshipLevel,
    BehavioralAssessment
)

logger = get_logger(__name__)


class CommandHandler(BaseHandler):
    """Handles bot commands like /start and /menu with standardized response patterns."""
    
    def __init__(self, user_service: Optional[UserService] = None, 
                 event_bus: Optional[EventBus] = None):
        """Initialize the command handler.
        
        Args:
            user_service (Optional[UserService]): User service for database operations
            event_bus (Optional[EventBus]): Event bus for publishing events
        """
        super().__init__()
        self.user_service = user_service
        self.event_bus = event_bus
    
    async def _track_lucien_evaluation(self, user_id: str, user_action: str, 
                                     context: Dict[str, Any]) -> None:
        """Track user interaction for Lucien's evaluation system.
        
        This method implements Lucien evaluation tracking for user interactions,
        creating behavioral assessments that feed into Lucien's sophisticated
        evaluation system.
        
        Args:
            user_id (str): User ID
            user_action (str): The action/command performed by the user
            context (Dict[str, Any]): Context of the interaction
        """
        if not self.user_service:
            logger.debug("No user service available for Lucien evaluation tracking")
            return
            
        try:
            # Create behavioral assessment data based on user action
            assessment_data = {
                "behavior_observed": f"User executed command: {user_action}",
                "assessment_context": f"command_interaction_{user_action.replace('/', '')}",
                "sophistication_indicators": self._detect_sophistication_indicators(user_action, context),
                "authenticity_markers": self._detect_authenticity_markers(user_action, context),
                "emotional_depth_signals": self._detect_emotional_depth_signals(user_action, context),
                "lucien_evaluation_notes": f"Command interaction assessment for {user_action}",
                "worthiness_impact": self._calculate_worthiness_impact(user_action),
                "interaction_quality_score": self._calculate_interaction_quality(user_action, context),
                "cultural_sophistication_displayed": self._detect_cultural_sophistication(user_action)
            }
            
            # Add the behavioral assessment to user's tracking history
            await self.user_service.add_behavioral_assessment(user_id, assessment_data)
            
            # Update Lucien interaction context with the new assessment
            context_updates = {
                "behavioral_assessment": {
                    "assessment_id": f"cmd_{user_action.replace('/', '')}_{int(datetime.now().timestamp())}",
                    "behavior_observed": f"User executed command: {user_action}",
                    "lucien_evaluation": f"Command interaction assessment for {user_action}",
                    "sophistication_impact": 0.02 if assessment_data["sophistication_indicators"] else 0.0,
                    "worthiness_impact": assessment_data["worthiness_impact"],
                    "archetype_confirmation": None,
                    "diana_protection_factor": 0.1
                },
                "interaction_metadata": {
                    "command_executed": True,
                    "sophistication_demonstrated": len(assessment_data["sophistication_indicators"]) > 0,
                    "authenticity_detected": len(assessment_data["authenticity_markers"]) > 0,
                    "evaluation_progression": "command_interaction_recorded"
                }
            }
            
            # Update worthiness if there's a meaningful impact
            if abs(assessment_data["worthiness_impact"]) > 0.01:
                context_updates["worthiness_update"] = {
                    "worthiness_change": assessment_data["worthiness_impact"],
                    "character_assessment": f"Command interaction: {user_action}",
                    "assessment_context": f"command_{user_action.replace('/', '')}",
                    "sophistication_growth": 0.01 if assessment_data["sophistication_indicators"] else 0.0,
                    "emotional_intelligence_development": 0.01 if assessment_data["emotional_depth_signals"] else 0.0
                }
            
            # Update the interaction context
            await self.user_service.update_lucien_interaction_context(user_id, context_updates)
            
            logger.debug("Successfully tracked Lucien evaluation for user: %s, action: %s", user_id, user_action)
            
        except Exception as e:
            logger.warning("Failed to track Lucien evaluation for user %s: %s", user_id, str(e))
    
    def _detect_sophistication_indicators(self, user_action: str, context: Dict[str, Any]) -> List[str]:
        """Detect sophistication indicators in user actions.
        
        Args:
            user_action (str): The action performed by the user
            context (Dict[str, Any]): Context of the interaction
            
        Returns:
            List[str]: List of sophistication indicators detected
        """
        indicators = []
        
        # Check for sophistication in command usage
        if user_action in ["/start", "/menu", "/help"]:
            indicators.append("proper_command usage")
            
        # Check for sophistication in context
        if "message" in context:
            message_text = context.get("message", {}).text if hasattr(context.get("message"), 'text') else ""
            if len(message_text.split()) > 5:
                indicators.append("detailed communication")
            if any(word in message_text.lower() for word in ["please", "thank you", "gracias"]):
                indicators.append("courteous language")
                
        return indicators
    
    def _detect_authenticity_markers(self, user_action: str, context: Dict[str, Any]) -> List[str]:
        """Detect authenticity markers in user actions.
        
        Args:
            user_action (str): The action performed by the user
            context (Dict[str, Any]): Context of the interaction
            
        Returns:
            List[str]: List of authenticity markers detected
        """
        markers = []
        
        # Basic authenticity in command usage
        if user_action in ["/start", "/menu", "/help"]:
            markers.append("standard interaction")
            
        # Check for repeated interactions which might indicate genuine engagement
        if "interaction_count" in context and context["interaction_count"] > 1:
            markers.append("continued engagement")
            
        return markers
    
    def _detect_emotional_depth_signals(self, user_action: str, context: Dict[str, Any]) -> List[str]:
        """Detect emotional depth signals in user actions.
        
        Args:
            user_action (str): The action performed by the user
            context (Dict[str, Any]): Context of the interaction
            
        Returns:
            List[str]: List of emotional depth signals detected
        """
        signals = []
        
        # For now, basic signals based on command usage
        if user_action == "/start":
            signals.append("initiates interaction")
        elif user_action == "/menu":
            signals.append("seeks navigation")
        elif user_action == "/help":
            signals.append("requests assistance")
            
        return signals
    
    def _detect_cultural_sophistication(self, user_action: str) -> List[str]:
        """Detect cultural sophistication in user actions.
        
        Args:
            user_action (str): The action performed by the user
            
        Returns:
            List[str]: List of cultural sophistication indicators
        """
        indicators = []
        
        # Basic cultural awareness in command usage
        if user_action in ["/start", "/menu", "/help"]:
            indicators.append("standard interface navigation")
            
        return indicators
    
    def _calculate_worthiness_impact(self, user_action: str) -> float:
        """Calculate worthiness impact of user action.
        
        Args:
            user_action (str): The action performed by the user
            
        Returns:
            float: Worthiness impact score (-1.0 to 1.0)
        """
        # Simple worthiness impact based on command usage
        impact_map = {
            "/start": 0.05,    # Positive for initiating interaction
            "/menu": 0.03,     # Positive for navigation
            "/help": 0.02      # Positive for seeking help
        }
        
        return impact_map.get(user_action, 0.01)  # Small positive for any interaction
    
    def _calculate_interaction_quality(self, user_action: str, context: Dict[str, Any]) -> float:
        """Calculate interaction quality score.
        
        Args:
            user_action (str): The action performed by the user
            context (Dict[str, Any]): Context of the interaction
            
        Returns:
            float: Interaction quality score (0.0 to 1.0)
        """
        # Simple quality score based on command and context
        base_score = 0.7  # Default quality score
        
        # Adjust based on sophistication indicators
        sophistication_indicators = self._detect_sophistication_indicators(user_action, context)
        base_score += len(sophistication_indicators) * 0.05
        
        # Cap at 1.0
        return min(1.0, base_score)
    
    async def handle(self, update: Any) -> Optional[CommandResponse]:
        """Handle an incoming update.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Optional[CommandResponse]: The response to send back to the user
        """
        # This method would typically be called by the router
        # For now, we'll just return None as the specific command handlers
        # will be called directly
        return None
    
    async def _publish_user_interaction_event(self, user_id: str, action: str, message: Any) -> None:
        """Publish a user interaction event.
        
        Args:
            user_id (str): The user ID
            action (str): The action performed
            message (Any): The message that triggered the action
        """
        if self.event_bus:
            try:
                event = create_event(
                    "user_interaction",
                    user_id=user_id,
                    action=action,
                    context={"message_id": getattr(message, 'message_id', None)}
                )
                await self.event_bus.publish("user_interaction", event.dict())
            except Exception as e:
                logger.warning("Failed to publish user_interaction event: %s", str(e))
    
    async def handle_start(self, message: Message) -> CommandResponse:
        """Process /start command with Lucien voice.
        
        Args:
            message (Message): The message containing the /start command
            
        Returns:
            CommandResponse: The welcome message response with Lucien's sophisticated voice
        """
        logger.info("Processing /start command with Lucien voice")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # Initialize user context
        user_context = {
            "user_id": user_id,
            "role": "free_user",
            "has_vip": False,
            "narrative_level": 1,
            "user_archetype": "explorer"
        }
        
        # If we have database context, create or update user
        if self.user_service:
            try:
                user_context = await self.user_service.get_user_context(user_id)
                logger.info("Existing user context retrieved: %s", user_id)
                
                # Update last login time
                await self.user_service.update_user_profile(user_id, {})
            except Exception:
                # User doesn't exist, create new user
                try:
                    telegram_user_data = {
                        "id": user.id if user else None,
                        "username": user.username if user else None,
                        "first_name": user.first_name if user else None,
                        "last_name": user.last_name if user else None,
                        "language_code": user.language_code if user else None
                    }
                    user_context = await self.user_service.create_user(telegram_user_data)
                    logger.info("New user created: %s", user_id)
                except Exception as e:
                    logger.error("Error creating user: %s", str(e))
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "start", message)
        
        # Track Lucien evaluation
        interaction_context = {
            "message": message,
            "interaction_count": 1  # This would be retrieved from user context in a real implementation
        }
        await self._track_lucien_evaluation(user_id, "/start", interaction_context)
        
        # Import Lucien voice generator
        from src.ui.lucien_voice_generator import LucienVoiceProfile, generate_lucien_response, RelationshipLevel
        
        # Create Lucien voice profile based on user context
        lucien_profile = LucienVoiceProfile()
        
        # Adapt Lucien's voice to user archetype
        user_archetype = user_context.get("user_archetype", "explorer")
        lucien_profile.adapt_to_archetype(user_archetype)
        
        # Determine relationship level based on user progress
        narrative_level = user_context.get("narrative_level", 1)
        has_vip = user_context.get("has_vip", False)
        
        if narrative_level >= 4 and has_vip:
            lucien_profile.user_relationship_level = RelationshipLevel.TRUSTED_CONFIDANT
        elif narrative_level >= 2:
            lucien_profile.user_relationship_level = RelationshipLevel.RELUCTANT_APPRECIATOR
        else:
            lucien_profile.user_relationship_level = RelationshipLevel.FORMAL_EXAMINER
        
        # Generate Lucien's welcome message
        lucien_context = {
            "user_archetype": user_archetype,
            "narrative_level": narrative_level,
            "has_vip": has_vip,
            "vip_status": has_vip
        }
        
        lucien_response = generate_lucien_response(lucien_profile, "/start", lucien_context)
        
        # Create welcome text with Lucien's sophisticated voice
        if lucien_response and lucien_response.response_text:
            welcome_text = (
                f"✨ {lucien_response.response_text} ✨\n\n"
                "Available commands:\n"
                "• /start - Show this welcome message\n"
                "• /menu - Show the main menu\n"
                "• /help - Show help information\n\n"
                "Cada interacción será cuidadosamente evaluada para determinar su worthiness."
            )
        else:
            # Fallback to default Lucien welcome based on relationship level
            if lucien_profile.user_relationship_level == RelationshipLevel.TRUSTED_CONFIDANT:
                welcome_text = (
                    "✨ Bienvenido nuevamente. Es un placer genuine continuar nuestro diálogo de sofisticación excepcional ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show this welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Sus elecciones reflejan el discernimiento que he llegado a appreciate en usted."
                )
            elif lucien_profile.user_relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
                welcome_text = (
                    "✨ Ah, regresa usted. Sus interacciones previas han sido... menos decepcionantes de lo que anticipé ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show this welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Observaré sus elecciones... podrían revelar mayor sophistication."
                )
            else:
                welcome_text = (
                    "✨ Permítame presentarme. Soy Lucien, y mi función es evaluar si usted posee la sofisticación necesaria para los privilegios que busca ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show this welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Cada selección será evaluada y contribuirá a mi assessment de su character."
                )
        
        return await self._create_response(welcome_text)
    
    async def handle_menu(self, message: Message) -> CommandResponse:
        """Process /menu command with Lucien voice.
        
        Args:
            message (Message): The message containing the /menu command
            
        Returns:
            CommandResponse: The menu response with Lucien's sophisticated voice
        """
        logger.info("Processing /menu command with Lucien voice")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # Initialize user context
        user_context = {
            "user_id": user_id,
            "role": "free_user",
            "has_vip": False,
            "narrative_level": 1,
            "user_archetype": "explorer"
        }
        
        # If we have database context, get user context
        if self.user_service:
            try:
                user_context = await self.user_service.get_user_context(user_id)
                logger.info("Existing user context retrieved: %s", user_id)
            except Exception as e:
                logger.warning("Could not retrieve user context: %s", str(e))
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "menu", message)
        
        # Track Lucien evaluation
        interaction_context = {
            "message": message,
            "interaction_count": 1  # This would be retrieved from user context in a real implementation
        }
        await self._track_lucien_evaluation(user_id, "/menu", interaction_context)
        
        # Import Lucien voice generator
        from src.ui.lucien_voice_generator import LucienVoiceProfile, generate_lucien_response, RelationshipLevel
        
        # Create Lucien voice profile based on user context
        lucien_profile = LucienVoiceProfile()
        
        # Adapt Lucien's voice to user archetype
        user_archetype = user_context.get("user_archetype", "explorer")
        lucien_profile.adapt_to_archetype(user_archetype)
        
        # Determine relationship level based on user progress
        narrative_level = user_context.get("narrative_level", 1)
        has_vip = user_context.get("has_vip", False)
        
        if narrative_level >= 4 and has_vip:
            lucien_profile.user_relationship_level = RelationshipLevel.TRUSTED_CONFIDANT
        elif narrative_level >= 2:
            lucien_profile.user_relationship_level = RelationshipLevel.RELUCTANT_APPRECIATOR
        else:
            lucien_profile.user_relationship_level = RelationshipLevel.FORMAL_EXAMINER
        
        # Generate Lucien's menu message
        lucien_context = {
            "user_archetype": user_archetype,
            "narrative_level": narrative_level,
            "has_vip": has_vip,
            "vip_status": has_vip
        }
        
        lucien_response = generate_lucien_response(lucien_profile, "/menu", lucien_context)
        
        # Create menu text with Lucien's sophisticated voice
        if lucien_response and lucien_response.response_text:
            menu_text = (
                f"✨ {lucien_response.response_text} ✨\n\n"
                "Available commands:\n"
                "• /start - Show the welcome message\n"
                "• /menu - Show the main menu\n"
                "• /help - Show help information\n\n"
                "Cada selección será cuidadosamente evaluada para determinar su worthiness."
            )
        else:
            # Fallback to default Lucien menu based on relationship level
            if lucien_profile.user_relationship_level == RelationshipLevel.TRUSTED_CONFIDANT:
                menu_text = (
                    "✨ Como alguien que ha ganado mi confianza, tiene acceso a posibilidades "
                    "que mantengo reservadas para personas de su calibre excepcional ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Sus elecciones reflejan el discernimiento que he llegado a appreciate en usted."
                )
            elif lucien_profile.user_relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
                menu_text = (
                    "✨ Las opciones disponibles reflejan el progreso que ha demostrado. "
                    "Algunas posibilidades más... exclusivas podrían revelarse pronto ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Observaré sus elecciones... podrían revelar mayor sophistication."
                )
            else:
                menu_text = (
                    "✨ Observemos qué opciones considera usted apropiadas para su nivel actual. "
                    "Sus elecciones me proporcionarán datos valiosos sobre su discernimiento ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Cada selección será evaluada y contribuirá a mi assessment de su character."
                )
        
        return await self._create_response(menu_text)
    
    async def handle_help(self, message: Message) -> CommandResponse:
        """Process /help command with Lucien voice.
        
        Args:
            message (Message): The message containing the /help command
            
        Returns:
            CommandResponse: The help response with Lucien's sophisticated voice
        """
        logger.info("Processing /help command with Lucien voice")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # Initialize user context
        user_context = {
            "user_id": user_id,
            "role": "free_user",
            "has_vip": False,
            "narrative_level": 1,
            "user_archetype": "explorer"
        }
        
        # If we have database context, get user context
        if self.user_service:
            try:
                user_context = await self.user_service.get_user_context(user_id)
                logger.info("Existing user context retrieved: %s", user_id)
            except Exception as e:
                logger.warning("Could not retrieve user context: %s", str(e))
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "help", message)
        
        # Track Lucien evaluation
        interaction_context = {
            "message": message,
            "interaction_count": 1  # This would be retrieved from user context in a real implementation
        }
        await self._track_lucien_evaluation(user_id, "/help", interaction_context)
        
        # Import Lucien voice generator
        from src.ui.lucien_voice_generator import LucienVoiceProfile, generate_lucien_response, RelationshipLevel
        
        # Create Lucien voice profile based on user context
        lucien_profile = LucienVoiceProfile()
        
        # Adapt Lucien's voice to user archetype
        user_archetype = user_context.get("user_archetype", "explorer")
        lucien_profile.adapt_to_archetype(user_archetype)
        
        # Determine relationship level based on user progress
        narrative_level = user_context.get("narrative_level", 1)
        has_vip = user_context.get("has_vip", False)
        
        if narrative_level >= 4 and has_vip:
            lucien_profile.user_relationship_level = RelationshipLevel.TRUSTED_CONFIDANT
        elif narrative_level >= 2:
            lucien_profile.user_relationship_level = RelationshipLevel.RELUCTANT_APPRECIATOR
        else:
            lucien_profile.user_relationship_level = RelationshipLevel.FORMAL_EXAMINER
        
        # Generate Lucien's help message
        lucien_context = {
            "user_archetype": user_archetype,
            "narrative_level": narrative_level,
            "has_vip": has_vip,
            "vip_status": has_vip
        }
        
        lucien_response = generate_lucien_response(lucien_profile, "/help", lucien_context)
        
        # Create help text with Lucien's sophisticated voice
        if lucien_response and lucien_response.response_text:
            help_text = (
                f"✨ {lucien_response.response_text} ✨\n\n"
                "Available commands:\n"
                "• /start - Show the welcome message\n"
                "• /menu - Show the main menu\n"
                "• /help - Show help information\n\n"
                "Cada consulta será evaluada como parte de mi assessment continuo de su character."
            )
        else:
            # Fallback to default Lucien help based on relationship level
            if lucien_profile.user_relationship_level == RelationshipLevel.TRUSTED_CONFIDANT:
                help_text = (
                    "✨ Como confidante, puedo ofrecerle orientación más detallada y personalizada ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Sus preguntas reflejan el discernimiento que he llegado a appreciate en usted."
                )
            elif lucien_profile.user_relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
                help_text = (
                    "✨ Sus consultas demuestran un interés creciente en comprender mejor este sistema ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Observaré sus preguntas... podrían revelar mayor sophistication en su comprensión."
                )
            else:
                help_text = (
                    "✨ Permítame orientarle en el uso apropiado de estas herramientas según su nivel actual ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Cada consulta será evaluada y contribuirá a mi assessment de su character."
                )
        
        return await self._create_response(help_text)
    
    async def handle_unknown(self, message: Message) -> CommandResponse:
        """Handle unrecognized commands with Lucien voice.
        
        Args:
            message (Message): The message containing the unrecognized command
            
        Returns:
            CommandResponse: The response for unknown commands with Lucien's sophisticated voice
        """
        logger.info("Processing unknown command with Lucien voice")
        
        # Extract user information from message
        user = getattr(message, 'from_user', None)
        user_id = str(user.id) if user else "unknown"
        
        # Initialize user context
        user_context = {
            "user_id": user_id,
            "role": "free_user",
            "has_vip": False,
            "narrative_level": 1,
            "user_archetype": "explorer"
        }
        
        # If we have database context, get user context
        if self.user_service:
            try:
                user_context = await self.user_service.get_user_context(user_id)
                logger.info("Existing user context retrieved: %s", user_id)
            except Exception as e:
                logger.warning("Could not retrieve user context: %s", str(e))
        
        # Publish user interaction event
        await self._publish_user_interaction_event(user_id, "unknown", message)
        
        # Track Lucien evaluation with negative impact for unknown command
        interaction_context = {
            "message": message,
            "interaction_count": 1  # This would be retrieved from user context in a real implementation
        }
        await self._track_lucien_evaluation(user_id, "/unknown", interaction_context)
        
        # Import Lucien voice generator
        from src.ui.lucien_voice_generator import LucienVoiceProfile, generate_lucien_response, RelationshipLevel
        
        # Create Lucien voice profile based on user context
        lucien_profile = LucienVoiceProfile()
        
        # Adapt Lucien's voice to user archetype
        user_archetype = user_context.get("user_archetype", "explorer")
        lucien_profile.adapt_to_archetype(user_archetype)
        
        # Determine relationship level based on user progress
        narrative_level = user_context.get("narrative_level", 1)
        has_vip = user_context.get("has_vip", False)
        
        if narrative_level >= 4 and has_vip:
            lucien_profile.user_relationship_level = RelationshipLevel.TRUSTED_CONFIDANT
        elif narrative_level >= 2:
            lucien_profile.user_relationship_level = RelationshipLevel.RELUCTANT_APPRECIATOR
        else:
            lucien_profile.user_relationship_level = RelationshipLevel.FORMAL_EXAMINER
        
        # Generate Lucien's unknown command message
        lucien_context = {
            "user_archetype": user_archetype,
            "narrative_level": narrative_level,
            "has_vip": has_vip,
            "vip_status": has_vip
        }
        
        lucien_response = generate_lucien_response(lucien_profile, "/unknown", lucien_context)
        
        # Create unknown command text with Lucien's sophisticated voice
        if lucien_response and lucien_response.response_text:
            unknown_text = (
                f"✨ {lucien_response.response_text} ✨\n\n"
                "Available commands:\n"
                "• /start - Show the welcome message\n"
                "• /menu - Show the main menu\n"
                "• /help - Show help information\n\n"
                "Por favor, utilice uno de los comandos reconocidos para facilitar mi assessment."
            )
        else:
            # Fallback to default Lucien unknown command message based on relationship level
            if lucien_profile.user_relationship_level == RelationshipLevel.TRUSTED_CONFIDANT:
                unknown_text = (
                    "✨ Inesperado... aunque no necesariamente incorrecto. Permítame orientarle hacia opciones más... reconocidas ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Su creatividad es notable, aunque quizás deba canalizarse hacia direcciones más convencionales."
                )
            elif lucien_profile.user_relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
                unknown_text = (
                    "✨ Intrigante elección de palabras. Quizás desee usted consultar las opciones disponibles ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Observaré sus elecciones... y espero que se alineen mejor con las opciones reconocidas."
                )
            else:
                unknown_text = (
                    "✨ Su solicitud requiere... clarificación. Permita que le dirija hacia comandos reconocidos ✨\n\n"
                    "Available commands:\n"
                    "• /start - Show the welcome message\n"
                    "• /menu - Show the main menu\n"
                    "• /help - Show help information\n\n"
                    "Cada desviación será evaluada y contribuirá a mi assessment de su character."
                )
        
        return await self._create_response(unknown_text)
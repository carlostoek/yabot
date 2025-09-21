"""
Organic Restrictions Handler for YABOT
Handles elegant explanation of access restrictions using Lucien's sophisticated voice.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from src.handlers.base import BaseHandler
from src.core.models import CommandResponse
from src.ui.lucien_voice_generator import (
    LucienVoiceProfile,
    generate_lucien_response,
    RelationshipLevel
)
from src.services.user import UserService

logger = logging.getLogger(__name__)


class OrganicRestrictionHandler(BaseHandler):
    """Handles organic restriction explanations with Lucien's sophisticated voice."""

    def __init__(self, user_service: Optional[UserService] = None):
        """Initialize the organic restriction handler.

        Args:
            user_service (Optional[UserService]): User service for context retrieval
        """
        super().__init__()
        self.user_service = user_service
        self.lucien_profile = LucienVoiceProfile()

    async def handle(self, update: Any) -> Optional[CommandResponse]:
        """Handle an incoming update (required by BaseHandler).

        Args:
            update (Any): The incoming update

        Returns:
            Optional[CommandResponse]: The response if applicable
        """
        # This is a specialized handler, use specific methods instead
        return None

    async def handle_worthiness_explanation(self, callback_data: str, user_context: Dict[str, Any]) -> CommandResponse:
        """Handle worthiness-based restriction explanations.

        Args:
            callback_data (str): Callback data in format "worthiness_explanation:item_id:required_worthiness"
            user_context (Dict[str, Any]): Current user context

        Returns:
            CommandResponse: Lucien's elegant explanation of worthiness requirements
        """
        try:
            # Parse callback data
            parts = callback_data.split(":")
            if len(parts) < 3:
                return await self._create_response("Información de restricción incompleta.")

            item_id = parts[1]
            required_worthiness = float(parts[2])
            current_worthiness = user_context.get('worthiness_score', 0.0)

            # Adapt Lucien's voice to user
            self._adapt_lucien_voice_to_user(user_context)

            # Generate explanation based on worthiness gap
            worthiness_gap = required_worthiness - current_worthiness
            explanation = self._generate_worthiness_explanation(
                item_id, worthiness_gap, current_worthiness, user_context
            )

            # Add encouraging guidance
            guidance = self._generate_worthiness_guidance(worthiness_gap, user_context)

            response_text = f"{explanation}\n\n{guidance}"

            return await self._create_response(response_text)

        except Exception as e:
            logger.error(f"Error handling worthiness explanation: {e}")
            return await self._create_response(
                "Mi evaluación requiere un momento adicional. Intente nuevamente."
            )

    async def handle_vip_invitation(self, callback_data: str, user_context: Dict[str, Any]) -> CommandResponse:
        """Handle VIP membership invitations with sophisticated presentation.

        Args:
            callback_data (str): Callback data in format "vip_invitation:item_id"
            user_context (Dict[str, Any]): Current user context

        Returns:
            CommandResponse: Lucien's elegant VIP invitation
        """
        try:
            # Parse callback data
            parts = callback_data.split(":")
            item_id = parts[1] if len(parts) > 1 else "unknown"

            # Adapt Lucien's voice to user
            self._adapt_lucien_voice_to_user(user_context)

            # Generate VIP invitation based on user's current status
            invitation = self._generate_vip_invitation(item_id, user_context)

            # Add benefits overview
            benefits = self._generate_vip_benefits_overview(user_context)

            response_text = f"{invitation}\n\n{benefits}"

            return await self._create_response(response_text)

        except Exception as e:
            logger.error(f"Error handling VIP invitation: {e}")
            return await self._create_response(
                "Permítame preparar una presentación apropiada de las oportunidades disponibles."
            )

    async def handle_divan_worthiness_explanation(self, user_context: Dict[str, Any]) -> CommandResponse:
        """Handle El Diván worthiness explanation specifically.

        Args:
            user_context (Dict[str, Any]): Current user context

        Returns:
            CommandResponse: Lucien's explanation of Diván access requirements
        """
        try:
            # Adapt Lucien's voice to user
            self._adapt_lucien_voice_to_user(user_context)

            worthiness_score = user_context.get('worthiness_score', 0.0)
            has_vip = user_context.get('has_vip', False)
            narrative_level = user_context.get('narrative_level', 1)

            # Generate comprehensive Diván explanation
            explanation = self._generate_divan_explanation(
                worthiness_score, has_vip, narrative_level, user_context
            )

            # Add pathway guidance
            pathway = self._generate_divan_pathway_guidance(
                worthiness_score, has_vip, narrative_level, user_context
            )

            response_text = f"{explanation}\n\n{pathway}"

            return await self._create_response(response_text)

        except Exception as e:
            logger.error(f"Error handling Diván explanation: {e}")
            return await self._create_response(
                "El acceso al Diván requiere evaluación cuidadosa. Permítame considerarlo apropiadamente."
            )

    async def handle_restriction_explanation(self, callback_data: str, user_context: Dict[str, Any]) -> CommandResponse:
        """Handle general restriction explanations.

        Args:
            callback_data (str): Callback data in format "explain_restriction:item_id:restriction_type"
            user_context (Dict[str, Any]): Current user context

        Returns:
            CommandResponse: Lucien's elegant restriction explanation
        """
        try:
            # Parse callback data
            parts = callback_data.split(":")
            if len(parts) < 3:
                return await self._create_response("Información de restricción incompleta.")

            item_id = parts[1]
            restriction_type = parts[2]

            # Adapt Lucien's voice to user
            self._adapt_lucien_voice_to_user(user_context)

            # Generate appropriate explanation
            explanation = self._generate_restriction_explanation(
                item_id, restriction_type, user_context
            )

            # Add constructive guidance
            guidance = self._generate_restriction_guidance(
                restriction_type, user_context
            )

            response_text = f"{explanation}\n\n{guidance}"

            return await self._create_response(response_text)

        except Exception as e:
            logger.error(f"Error handling restriction explanation: {e}")
            return await self._create_response(
                "Permítame formular una explicación apropiada para su situación particular."
            )

    def _adapt_lucien_voice_to_user(self, user_context: Dict[str, Any]) -> None:
        """Adapt Lucien's voice profile based on user characteristics."""
        try:
            user_archetype = user_context.get('user_archetype', 'explorer')
            self.lucien_profile.adapt_to_archetype(user_archetype)

            narrative_level = user_context.get('narrative_level', 0)
            has_vip = user_context.get('has_vip', False)

            if narrative_level >= 4 and has_vip:
                self.lucien_profile.user_relationship_level = RelationshipLevel.TRUSTED_CONFIDANT
            elif narrative_level >= 2:
                self.lucien_profile.user_relationship_level = RelationshipLevel.RELUCTANT_APPRECIATOR
            else:
                self.lucien_profile.user_relationship_level = RelationshipLevel.FORMAL_EXAMINER

        except Exception as e:
            logger.warning(f"Failed to adapt Lucien voice profile: {e}")

    def _generate_worthiness_explanation(self, item_id: str, worthiness_gap: float,
                                       current_worthiness: float, user_context: Dict[str, Any]) -> str:
        """Generate worthiness-based explanation."""
        relationship_level = self.lucien_profile.user_relationship_level

        if relationship_level == RelationshipLevel.TRUSTED_CONFIDANT:
            if worthiness_gap < 0.2:
                return (
                    f"Su development se acerca a lo necesario para {item_id}. "
                    f"Entre nosotros, veo que está muy cerca del threshold required."
                )
            else:
                return (
                    f"Aunque su progress ha sido notable, {item_id} requiere un nivel "
                    f"de sophistication que anticipé se desarrollará pronto en usted."
                )

        elif relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
            return (
                f"Su development actual es... interesante, pero {item_id} está reservado "
                f"para quienes han demostrado un nivel específico de emotional intelligence. "
                f"Sus interacciones sugieren potential para alcanzar ese standard."
            )

        else:  # FORMAL_EXAMINER
            if current_worthiness < 0.2:
                return (
                    f"Los privilegios como {item_id} se revelan gradualmente a quienes "
                    f"demuestran worthiness through authentic engagement. Su journey "
                    f"está en las etapas iniciales de este proceso evaluativo."
                )
            else:
                return (
                    f"Su progress con {item_id} requiere demonstration de greater depth "
                    f"en sophistication. Las evaluaciones futuras determinarán su readiness."
                )

    def _generate_worthiness_guidance(self, worthiness_gap: float, user_context: Dict[str, Any]) -> str:
        """Generate constructive guidance for worthiness development."""
        if worthiness_gap < 0.1:
            return (
                "<b>Guidance:</b> Continue su current path. Pequeñas mejoras en authenticity "
                "y emotional depth abrirán estas oportunidades muy pronto."
            )
        elif worthiness_gap < 0.3:
            return (
                "<b>Guidance:</b> Focus en deeper engagement con Diana y thoughtful responses "
                "en sus interactions. Su sophistication está developing nicely."
            )
        else:
            return (
                "<b>Guidance:</b> Patience y authentic engagement son key. Cada interaction "
                "con Diana contribuye a su assessment y eventual access a privilegios superiores."
            )

    def _generate_vip_invitation(self, item_id: str, user_context: Dict[str, Any]) -> str:
        """Generate VIP membership invitation."""
        worthiness_score = user_context.get('worthiness_score', 0.0)
        relationship_level = self.lucien_profile.user_relationship_level

        if relationship_level == RelationshipLevel.TRUSTED_CONFIDANT:
            return (
                f"Su development ha sido exceptional. La membership VIP representaría "
                f"el reconocimiento formal de la sophistication que ya demuestra. "
                f"Acceso a {item_id} y otros privilegios await."
            )

        elif relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR:
            return (
                f"Debo admitir que sus interactions han mostrado... potential genuino. "
                f"La membership VIP abriría access a {item_id} y experiences que few appreciate "
                f"con la depth que usted podría demonstrate."
            )

        else:  # FORMAL_EXAMINER
            if worthiness_score >= 0.3:
                return (
                    f"Su progress sugiere readiness para considerar membership VIP. "
                    f"Este commitment abriría access a {item_id} y otros privilegios "
                    f"reserved para serious individuals."
                )
            else:
                return (
                    f"La membership VIP representa commitment a deeper engagement. "
                    f"Considera carefully si está prepared para the level de sophistication "
                    f"que {item_id} y similar experiences require."
                )

    def _generate_vip_benefits_overview(self, user_context: Dict[str, Any]) -> str:
        """Generate overview of VIP benefits."""
        return (
            "<b>VIP Membership Benefits:</b>\n"
            "• 🛋️ Acceso completo a El Diván (Niveles 4-6)\n"
            "• ✨ Círculo Íntimo con experiencias exclusivas\n"
            "• 📚 Archivo Personal de Diana\n"
            "• 🌟 Sesiones personalizadas adaptadas\n"
            "• 💎 Prioridad en nuevos contenidos y features\n"
            "• 🎭 Interacciones más profundas y sofisticadas"
        )

    def _generate_divan_explanation(self, worthiness_score: float, has_vip: bool,
                                  narrative_level: int, user_context: Dict[str, Any]) -> str:
        """Generate comprehensive Diván access explanation."""
        missing_requirements = []

        if not has_vip:
            missing_requirements.append("Membership VIP")
        if narrative_level < 4:
            missing_requirements.append(f"Nivel narrativo 4 (actual: {narrative_level})")
        if worthiness_score < 0.6:
            missing_requirements.append(f"Worthiness score 0.6 (actual: {worthiness_score:.1f})")

        if not missing_requirements:
            return "Su acceso al Diván está completamente habilitado. Un privilege bien ganado."

        explanation = (
            "<b>🛋️ El Diván</b> representa el apex de intimacy y understanding con Diana. "
            "Acceso requiere convergence de múltiples factors:"
        )

        for requirement in missing_requirements:
            explanation += f"\n• {requirement}"

        return explanation

    def _generate_divan_pathway_guidance(self, worthiness_score: float, has_vip: bool,
                                       narrative_level: int, user_context: Dict[str, Any]) -> str:
        """Generate pathway guidance for Diván access."""
        guidance_points = []

        if narrative_level < 4:
            guidance_points.append(
                f"Continue su narrative journey. Nivel {narrative_level + 1} awaits through deeper engagement."
            )

        if worthiness_score < 0.6:
            guidance_points.append(
                "Deepen su authenticity en interactions. Cada response contribuye a su assessment."
            )

        if not has_vip:
            guidance_points.append(
                "Consider VIP membership como demonstration de commitment a este journey."
            )

        guidance = "<b>Pathway Forward:</b>"
        for point in guidance_points:
            guidance += f"\n• {point}"

        return guidance

    def _generate_restriction_explanation(self, item_id: str, restriction_type: str,
                                        user_context: Dict[str, Any]) -> str:
        """Generate explanation for specific restriction types."""
        if restriction_type == "besitos":
            besitos_balance = user_context.get('besitos_balance', 0)
            return (
                f"<b>{item_id}</b> requiere una inversión más significativa de besitos. "
                f"Su balance actual ({besitos_balance} besitos) puede incrementarse "
                f"through missions, daily gifts, y thoughtful engagement."
            )

        elif restriction_type == "narrative_level":
            current_level = user_context.get('narrative_level', 1)
            return (
                f"<b>{item_id}</b> unlocks en niveles narrativos más avanzados. "
                f"Su nivel actual ({current_level}) progresará naturally through "
                f"continued interaction con Diana."
            )

        elif restriction_type == "worthiness":
            return self._generate_worthiness_explanation(item_id, 0.2,
                                                       user_context.get('worthiness_score', 0.0), user_context)

        elif restriction_type == "vip_membership":
            return self._generate_vip_invitation(item_id, user_context)

        else:
            return (
                f"<b>{item_id}</b> tiene requirements específicos que se revelarán "
                f"conforme su development progresa naturally."
            )

    def _generate_restriction_guidance(self, restriction_type: str, user_context: Dict[str, Any]) -> str:
        """Generate constructive guidance for overcoming restrictions."""
        if restriction_type == "besitos":
            return (
                "<b>Earning Besitos:</b> Complete daily missions, engage thoughtfully "
                "con Diana, y maintain consistent interaction para build your treasury."
            )

        elif restriction_type == "narrative_level":
            return (
                "<b>Narrative Progression:</b> Deepen your story con Diana through "
                "authentic choices y emotional engagement in your interactions."
            )

        elif restriction_type == "worthiness":
            return self._generate_worthiness_guidance(0.2, user_context)

        elif restriction_type == "vip_membership":
            return (
                "<b>VIP Consideration:</b> This commitment opens significant opportunities "
                "for deeper connection y sophisticated experiences con Diana."
            )

        else:
            return (
                "<b>General Development:</b> Focus on authentic engagement, "
                "thoughtful responses, y patience. Growth révela naturally."
            )


# Utility functions for menu callback handling
async def handle_organic_callback(callback_data: str, user_context: Dict[str, Any],
                                user_service: Optional[UserService] = None) -> CommandResponse:
    """Handle organic restriction callbacks.

    Args:
        callback_data (str): The callback data from menu interaction
        user_context (Dict[str, Any]): Current user context
        user_service (Optional[UserService]): User service instance

    Returns:
        CommandResponse: Appropriate response for the restriction
    """
    handler = OrganicRestrictionHandler(user_service)

    if callback_data.startswith("worthiness_explanation:"):
        return await handler.handle_worthiness_explanation(callback_data, user_context)
    elif callback_data.startswith("vip_invitation:"):
        return await handler.handle_vip_invitation(callback_data, user_context)
    elif callback_data == "explain_divan_worthiness":
        return await handler.handle_divan_worthiness_explanation(user_context)
    elif callback_data.startswith("explain_restriction:"):
        return await handler.handle_restriction_explanation(callback_data, user_context)
    else:
        return await handler._create_response(
            "Esa request requiere clarification. Permítame guide usted hacia opciones apropiadas."
        )
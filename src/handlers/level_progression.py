"""
Level Progression Handler

This module contains the LevelProgressionHandler class that handles level progression celebrations
and displays appropriate messages when users advance to new levels.

Implements:
- Requirement 5.4: WHEN level changes THEN the system SHALL send message "¡Felicidades! Desbloqueaste Nivel 2. Nuevas funciones disponibles."
"""
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from src.handlers.base import BaseHandler, MessageHandlerMixin
from src.core.models import MessageContext, CommandResponse
from src.utils.logger import get_logger
from src.database.manager import DatabaseManager
from src.services.user import UserService
from src.services.level_progression import LevelProgressionService


class LevelProgressionHandler(BaseHandler, MessageHandlerMixin):
    """
    Handler for level progression celebrations and notifications.
    
    Implements requirement 5.4: WHEN level changes THEN the system SHALL send message 
    "¡Felicidades! Desbloqueaste Nivel 2. Nuevas funciones disponibles."
    """
    
    def __init__(self):
        super().__init__()
        # Services will be injected via middleware, not instantiated directly

    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> CommandResponse:
        """
        Process level progression related messages
        """
        database_manager = kwargs.get('database_manager')
        user_service = kwargs.get('user_service')
        level_progression_service = kwargs.get('level_progression_service')
        
        user_id = str(message.from_user.id)
        
        # Get user's current level
        if level_progression_service:
            current_level = await level_progression_service.get_user_level(user_id)
        else:
            # Fallback to checking MongoDB directly
            user_doc = await database_manager.get_user_from_mongo(user_id)
            current_level = user_doc.get("narrative_level", 1) if user_doc else 1
        
        # Create celebration message based on user's level
        celebration_text = await self.create_level_celebration_message(user_id, current_level, level_progression_service)
        
        # Create keyboard with level-specific options
        keyboard = await self.update_user_menu(user_id, current_level)
        
        response = self.create_response(
            text=celebration_text,
            reply_markup=keyboard
        )
        return response

    async def create_level_celebration_message(self, user_id: str, new_level: int, level_progression_service) -> str:
        """
        Create a level celebration message based on the new level achieved
        Implements requirement 5.4 for Level 2 unlock
        """
        if new_level == 2:
            # Requirement 5.4: Send specific message for Level 2 unlock
            celebration_text = (
                "🎉 <b>¡FELICIDADES!</b>\n\n"
                "🎊 <b>¡Felicidades! Desbloqueaste Nivel 2. Nuevas funciones disponibles.</b> 🎊\n\n"
                "Ahora tienes acceso a contenido exclusivo del Nivel 2.\n"
                "¡Sigue explorando y disfrutando de la experiencia!"
            )
        elif new_level > 2:
            celebration_text = (
                f"🎉 <b>¡FELICIDADES!</b>\n\n"
                f"🎊 ¡Has alcanzado el <b>Nivel {new_level}</b>! 🎊\n\n"
                f"Ahora tienes acceso a nuevas funcionalidades del Nivel {new_level}.\n"
                "¡Sigue disfrutando de la experiencia!"
            )
        else:
            celebration_text = (
                f"📊 Estás en el <b>Nivel {new_level}</b>\n\n"
                "¡Sigue progresando para desbloquear más contenido!"
            )
        
        return celebration_text

    async def handle_level_progression(self, user_id: str, new_level: int) -> None:
        """
        Handle level progression event and trigger celebration
        Implements requirement 5.4
        """
        self.logger.info(f"Handling level progression for user {user_id} to level {new_level}")
        
        # This would typically be called from an event processor
        # For now, we'll just log it and return

    async def send_level_unlock_message(self, user_id: str, level: int, message: Message = None) -> bool:
        """
        Send the level unlock celebration message
        Implements requirement 5.4: "¡Felicidades! Desbloqueaste Nivel 2. Nuevas funciones disponibles."
        """
        try:
            if level == 2:
                # Exact message required by requirement 5.4
                unlock_message = "🎊 <b>¡Felicidades! Desbloqueaste Nivel 2. Nuevas funciones disponibles.</b> 🎊"
            else:
                unlock_message = f"🎊 <b>¡Felicidades! Has alcanzado el Nivel {level}.</b> 🎊"
            
            if message:
                # Send the message to the user
                await message.answer(unlock_message, parse_mode="HTML")
            
            return True
        except Exception as e:
            self.logger.error(f"Error sending level unlock message to user {user_id}: {str(e)}")
            return False

    async def update_user_menu(self, user_id: str, level: int) -> InlineKeyboardBuilder:
        """
        Update user menu based on their level
        Implements requirement 5.3: WHEN Level 2 is unlocked THEN the user SHALL see 
        at least 2 new menu options not available at Level 1
        """
        keyboard = InlineKeyboardBuilder()
        
        # Common menu options for all levels
        keyboard.add(InlineKeyboardButton(text="📖 Historia", callback_data="story_menu"))
        keyboard.add(InlineKeyboardButton(text="🎯 Misiones", callback_data="missions_menu"))
        keyboard.add(InlineKeyboardButton(text="💰 Bolsa", callback_data="wallet_menu"))
        
        # Add level-specific options
        if level >= 2:
            # Requirement 5.3: At least 2 new menu options for Level 2 users
            keyboard.add(InlineKeyboardButton(text="🎭 Contenido Nivel 2", callback_data="level2_content"))
            keyboard.add(InlineKeyboardButton(text="🔮 Características Avanzadas", callback_data="advanced_features"))
            # Third Level 2 option to ensure we meet the requirement with extra
            keyboard.add(InlineKeyboardButton(text="💬 Interacción Especial", callback_data="special_interaction"))
        
        # Common options at the bottom
        keyboard.add(InlineKeyboardButton(text="⚙️ Ajustes", callback_data="settings_menu"))
        keyboard.add(InlineKeyboardButton(text="ℹ️ Ayuda", callback_data="help_menu"))
        keyboard.add(InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu"))
        
        # Adjust layout - 1 column for clear visibility of options
        keyboard.adjust(1)
        
        return keyboard

    async def process_callback_query(self, callback_query: CallbackQuery, **kwargs) -> None:
        """
        Process level-related callback queries
        """
        user_id = str(callback_query.from_user.id)
        callback_data = callback_query.data
        
        if callback_data == "level_up_info":
            await callback_query.answer("Has subido de nivel. ¡Felicitaciones!", show_alert=True)
        elif callback_data.startswith("level_") and "_menu" in callback_data:
            # Process level-specific menu callbacks
            await callback_query.answer(f"Accediendo al menú de {callback_data.replace('_menu', '').replace('level', 'Nivel ').upper()}", show_alert=False)
        else:
            # For other callbacks, just acknowledge
            await callback_query.answer()


# Router setup for level progression handlers
router = Router()
logger = get_logger(__name__)


def register_handlers(dp):
    """
    Register level progression handlers with the dispatcher.
    
    Args:
        dp: The aiogram Dispatcher instance
    """
    # This function will be called by the main application to register the handlers
    # Currently, the handlers are expected to be called directly by other handlers or through callbacks
    pass


# Export the handler so it can be imported by other modules
__all__ = [
    'LevelProgressionHandler',
    'register_handlers'
]
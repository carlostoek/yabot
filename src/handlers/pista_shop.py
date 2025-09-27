"""
Pista Shop Handler

This module contains the PistaShopHandler class that handles pista purchases
using besitos and validates sufficient balance requirements.

Implements:
- Requirement 4.1: WHEN user has 10 or more besitos THEN they SHALL see a "Comprar Pista - 10 besitos" button
- Requirement 4.2: WHEN pista purchase is initiated THEN the system SHALL verify balance ≥ 10 besitos before proceeding
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
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.modules.narrative.hint_system import HintSystem


class PistaShopHandler(BaseHandler, MessageHandlerMixin):
    """
    Handler for pista purchase interface.
    
    Implements requirement 4.1: WHEN user has 10 or more besitos THEN they SHALL see a "Comprar Pista - 10 besitos" button
    Implements requirement 4.2: WHEN pista purchase is initiated THEN the system SHALL verify balance ≥ 10 besitos before proceeding
    """
    
    def __init__(self):
        super().__init__()
        # Services will be injected via middleware, not instantiated directly

    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> CommandResponse:
        """
        Process the pista shop command/request
        """
        database_manager = kwargs.get('database_manager')
        user_service = kwargs.get('user_service')
        besitos_wallet = kwargs.get('besitos_wallet')
        hint_system = kwargs.get('hint_system')
        
        # Get user ID
        user_id = str(message.from_user.id)
        
        # Get user's besitos balance
        if besitos_wallet:
            balance = await besitos_wallet.get_balance(user_id)
        else:
            # Fallback to checking MongoDB directly
            user_doc = await database_manager.get_user_from_mongo(user_id)
            balance = user_doc.get("besitos_balance", 0) if user_doc else 0
        
        # Create keyboard with available pistas
        keyboard = InlineKeyboardBuilder()
        
        # Check if user has enough besitos for Level 2 pista (10 besitos)
        if balance >= 10:
            # Add "Comprar Pista - 10 besitos" button as required by requirement 4.1
            keyboard.add(InlineKeyboardButton(
                text="Comprar Pista - 10 besitos", 
                callback_data="buy_level2_pista"
            ))
        
        # Add other available pistas based on user's level
        # For now, just include the Level 2 access pista
        keyboard.adjust(1)  # One button per row
        
        # Create shop message
        shop_text = (
            f"🛍️ <b>TIENDA DE PISTAS</b>\n\n"
            f"Tu saldo actual: <b>{balance} besitos</b>\n\n"
            f"Selecciona una pista para comprar:\n"
        )
        
        # Add available pistas to the message
        available_pistas = await self.get_available_pistas(user_id, balance, hint_system)
        
        if available_pistas:
            for pista in available_pistas:
                shop_text += f"• {pista['name']} - {pista['cost']} besitos\n"
        else:
            shop_text += "No hay pistas disponibles para tu nivel actual o saldo insuficiente.\n"
        
        # Add close button
        keyboard.add(InlineKeyboardButton(text="❌ Cerrar", callback_data="close_shop"))
        
        response = self.create_response(
            text=shop_text,
            reply_markup=keyboard.as_markup()
        )
        return response

    async def get_available_pistas(self, user_id: str, balance: int, hint_system) -> list:
        """
        Get list of available pistas for purchase based on user's level and balance
        """
        available_pistas = []
        
        # Add Level 2 access pista if user has sufficient balance (10 besitos)
        if balance >= 10:
            available_pistas.append({
                "id": "level2_access",
                "name": "Acceso a Nivel 2",
                "cost": 10,
                "description": "Desbloquea el Nivel 2 del story"
            })
        
        # Additional pistas can be added here based on user's level
        # For now, we only have the Level 2 access pista
        
        return available_pistas

    async def process_callback_query(self, callback_query: CallbackQuery, **kwargs) -> None:
        """
        Process callback queries for pista purchases
        """
        database_manager = kwargs.get('database_manager')
        user_service = kwargs.get('user_service')
        besitos_wallet = kwargs.get('besitos_wallet')
        hint_system = kwargs.get('hint_system')
        
        user_id = str(callback_query.from_user.id)
        callback_data = callback_query.data
        
        # Handle the buy_level2_pista callback as required by requirement 4.2
        if callback_data == "buy_level2_pista":
            # First, verify that user has sufficient balance (≥ 10 besitos) as required by requirement 4.2
            if besitos_wallet:
                balance = await besitos_wallet.get_balance(user_id)
            else:
                # Fallback to checking MongoDB directly
                user_doc = await database_manager.get_user_from_mongo(user_id)
                balance = user_doc.get("besitos_balance", 0) if user_doc else 0
            
            # Check if user has enough besitos (10 or more)
            if balance >= 10:
                # Process the purchase
                success = await self.purchase_level2_pista(user_id, besitos_wallet, hint_system)
                
                if success:
                    # Get the new balance after purchase
                    new_balance = balance - 10
                    
                    # Update the callback answer message
                    await callback_query.answer(
                        f"¡Compra exitosa! Gastaste 10 besitos. Nuevo saldo: {new_balance} besitos",
                        show_alert=True
                    )
                    
                    # Notify the user in a follow-up message about level unlock
                    await callback_query.message.answer(
                        "🎉 ¡Felicidades! Has adquirido la pista para Nivel 2. "
                        "¡Tu progreso está siendo actualizado!"
                    )
                else:
                    await callback_query.answer(
                        "Error al procesar la compra. Por favor, intenta de nuevo.",
                        show_alert=True
                    )
            else:
                # User doesn't have enough besitos
                await callback_query.answer(
                    f"Lo siento, necesitas al menos 10 besitos para comprar esta pista. "
                    f"Tu saldo actual es: {balance} besitos",
                    show_alert=True
                )
        
        elif callback_data == "close_shop":
            await callback_query.answer("Tienda cerrada.", show_alert=False)
            await callback_query.message.edit_text("Tienda cerrada. ¡Gracias por visitarnos!")


    async def purchase_level2_pista(self, user_id: str, besitos_wallet: BesitosWallet, hint_system) -> bool:
        """
        Process the purchase of the Level 2 access pista
        Implements requirement 4.3: WHEN pista is purchased THEN exactly 10 besitos SHALL be deducted
        Implements requirement 4.4: WHEN purchase completes THEN the pista "Acceso a Nivel 2" SHALL be added
        """
        try:
            # Deduct 10 besitos from user's wallet (requirement 4.3)
            if besitos_wallet:
                transaction_result = await besitos_wallet.spend_besitos(user_id, 10, "level2_access_pista")
                
                if not transaction_result:
                    self.logger.error(f"Failed to deduct besitos for user {user_id}")
                    return False
            
            # Add the "Acceso a Nivel 2" pista to user's inventory (requirement 4.4)
            if hint_system:
                # Unlock the hint for Level 2 access
                unlock_result = await hint_system.unlock_hint(user_id, "Acceso a Nivel 2")
                
                if not unlock_result:
                    self.logger.error(f"Failed to unlock 'Acceso a Nivel 2' hint for user {user_id}")
                    # If hint unlock fails, try to refund besitos?
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing Level 2 pista purchase for user {user_id}: {str(e)}")
            return False


# Router setup for pista shop handlers
router = Router()
logger = get_logger(__name__)


def register_handlers(dp):
    """
    Register pista shop handlers with the dispatcher.
    
    Args:
        dp: The aiogram Dispatcher instance
    """
    # This function will be called by the main application to register the handlers
    # Currently, the handlers are expected to be called directly by other handlers or through callbacks
    pass


# Export the handler so it can be imported by other modules
__all__ = [
    'PistaShopHandler',
    'register_handlers'
]
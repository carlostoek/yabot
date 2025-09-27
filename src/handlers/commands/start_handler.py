import logging
from datetime import datetime
from typing import Dict, Any, Optional

from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config.manager import ConfigManager
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.events.models import UserRegistrationEvent
from src.handlers.base import BaseHandler
from src.modules.gamification.mission_manager import MissionManager
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.services.user import UserService
from src.services.subscription import SubscriptionService

logger = logging.getLogger(__name__)

config = ConfigManager()
db_manager = DatabaseManager()
event_bus = EventBus()

# Instancias de servicios (singleton o inyectadas según tu patrón)
user_service = UserService(db_manager)
subscription_service = SubscriptionService(db_manager)
mission_manager = MissionManager(db_manager, event_bus)
besitos_wallet = BesitosWallet(db_manager)

router = Router(name="enhanced_start")


class EnhancedStartHandler(BaseHandler):
    """
    Maneja el comando /start con inicialización narrativa de Nivel 1.
    """

    @staticmethod
    async def get_existing_user_status(user_id: str) -> Dict[str, Any]:
        """Retorna nivel narrativo, besitos y estado para usuarios existentes."""
        user_doc = await db_manager.mongo.users.find_one({"user_id": user_id})
        
        # Si no hay user_doc, el usuario no existe.
        if not user_doc:
            return {"current_level": 0}

        subscription = await db_manager.sqlite.fetch_one(
            "SELECT is_vip, tier FROM subscriptions WHERE user_id = ?", (user_id,)
        )

        current_level = user_doc.get("narrative_level", 1)
        balance = await besitos_wallet.get_balance(user_id)

        return {
            "current_level": current_level,
            "besitos_balance": balance,
            "is_vip": bool(subscription and subscription["is_vip"]),
            "has_completed_initial_mission": (
                user_doc.get("missions_completed", [])
            )
        }

    @staticmethod
    async def setup_level_1_user(user_id: str, username: Optional[str], telegram_user_data: Dict[str, Any]) -> bool:
        """Inicializa un nuevo usuario en Nivel 1 (free)."""
        try:
            # 1. Crear perfil en SQLite (suscripción free)
            await subscription_service.create_subscription(
                user_id=user_id,
                tier="free",
                is_vip=False,
                start_date=datetime.utcnow(),
                end_date=None  # Nunca expira (free)
            )

            # 2. Inicializar estado narrativo en MongoDB
            await db_manager.mongo.users.insert_one({
                "user_id": user_id,
                "username": username,
                "narrative_level": 1,
                "completed_fragments": [],
                "missions_completed": [],
                "pistas_unlocked": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

            # 3. Inicializar billetera (0 besitos)
            await besitos_wallet.initialize_wallet(user_id)

            # 4. Publicar evento de registro
            event = UserRegistrationEvent(
                user_id=user_id,
                telegram_data=telegram_user_data,
                registration_method="enhanced_start",
                payload={"initial_level": 1, "tier": "free"}
            )
            await event_bus.publish(event)

            logger.info(f"Usuario {user_id} inicializado en Nivel 1 (free).")
            return True

        except Exception as e:
            logger.error(f"Error al inicializar usuario {user_id}: {e}", exc_info=True)
            return False

    @staticmethod
    async def assign_initial_mission(user_id: str) -> Optional[Dict[str, Any]]:
        """Asigna la misión 'Reacciona en el Canal Principal'."""
        mission_spec = {
            "mission_id": "react_main_channel",
            "title": "Reacciona en el Canal Principal",
            "description": f"Ve al canal {config.MAIN_CHANNEL_NAME} y reacciona con ❤️ a la última publicación.",
            "channel_id": config.MAIN_CHANNEL_ID,
            "required_reaction": "❤️",
            "reward_besitos": 10,
            "expires_at": None
        }
        try:
            mission = await mission_manager.create_mission(user_id, mission_spec)
            logger.debug(f"Misión asignada a {user_id}: {mission['mission_id']}")
            return mission
        except Exception as e:
            logger.error(f"Error asignando misión inicial a {user_id}: {e}")
            return None

    @staticmethod
    def build_main_menu(level: int, balance: int, has_mission: bool) -> InlineKeyboardMarkup:
        """Construye el menú principal según el nivel y estado del usuario."""
        builder = InlineKeyboardBuilder()

        # Opciones comunes
        builder.button(text="🎒 Mi Mochila", callback_data="view_backpack")
        builder.button(text="🏪 Tienda de Pistas", callback_data="open_shop")

        # Si es Nivel 1 y no ha completado la misión, ofrecer ayuda
        if level == 1 and not has_mission:
            builder.button(text="📜 Ver Misión", callback_data="view_mission:react_main_channel")

        # En Nivel 2+, añadir más opciones (placeholder)
        if level >= 2:
            builder.button(text="🎭 Nuevos Fragmentos", callback_data="view_fragments")
            builder.button(text="🏆 Mis Logros", callback_data="view_achievements")

        builder.adjust(2)
        return builder.as_markup()

    async def handle_start_command(self, message: Message) -> None:
        """Punto de entrada principal para /start."""
        user = message.from_user
        user_id = str(user.id)
        username = user.username or user.first_name

        # 1. Verificar si ya existe
        existing_status = await self.get_existing_user_status(user_id)

        if existing_status["current_level"] > 0:
            # Usuario existente: mostrar estado actual
            response_text = (
                f"🎩 *Lucien inclina ligeramente la cabeza.*\n\n"
                f"Bienvenido de nuevo, {username}.\n"
                f"• Nivel: {existing_status['current_level']}\n"
                f"• Besitos: 💋 {existing_status['besitos_balance']}\n\n"
                f"¿En qué puedo ayudarte hoy?"
            )
            has_mission = "react_main_channel" in existing_status.get("has_completed_initial_mission", [])
            keyboard = self.build_main_menu(
                level=existing_status['current_level'],
                balance=existing_status['besitos_balance'],
                has_mission=has_mission
            )
        else:
            # Usuario nuevo: inicializar
            success = await self.setup_level_1_user(user_id, username, message.from_user.model_dump(exclude_none=True))
            if not success:
                await message.answer("⚠️ Error al crear tu perfil. Por favor, inténtalo de nuevo.")
                return

            # Asignar misión inicial
            mission = await self.assign_initial_mission(user_id)

            response_text = (
                f"🎩 *Lucien te recibe con una sonrisa discreta.*\n\n"
                f"Bienvenido, {username}. Soy Lucien, mayordomo de la señorita Diana.\n\n"
                f"Estás en el **Nivel 1** de tu viaje.\n"
                f"Tus besitos iniciales: 💋 0\n\n"
                f"Tu primera misión:\n"
                f"➡️ {mission['title'] if mission else 'Reacciona en el canal principal con ❤️'}\n\n"
                f"Al completarla, recibirás 10 besitos y podrás comprar tu primera pista."
            )
            keyboard = self.build_main_menu(level=1, balance=0, has_mission=False)

        # Enviar respuesta con protección de contenido si es VIP (aunque Nivel 1 es free)
        await message.answer(
            response_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
            protect_content=False  # Solo VIP usa True
        )


# Registro del handler
@router.message(commands=["start"])
async def start_command_wrapper(message: Message):
    handler = EnhancedStartHandler()
    await handler.handle_start_command(message)
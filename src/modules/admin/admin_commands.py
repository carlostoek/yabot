"""
Admin Command Interface - Channel Administration Module

This module implements the admin command interface leveraging patterns from src/handlers/base.py
as specified in Requirement 3.7.

The system handles:
- Private admin command processing with inline menus
- Role-based access validation
- Admin panel navigation and functionality
- Integration with all admin module services
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.handlers.base import BaseHandler, MessageHandlerMixin, CallbackHandlerMixin
from src.core.models import CommandResponse, MessageContext
from src.events.bus import EventBus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient
    from aiogram import Bot
    from src.modules.admin.access_control import AccessControl
    from src.modules.admin.subscription_manager import SubscriptionManager
    from src.modules.admin.post_scheduler import PostScheduler
    from src.modules.admin.notification_system import NotificationSystem
    from src.modules.admin.message_protection import MessageProtectionSystem


class AdminStates(StatesGroup):
    """
    FSM states for admin operations
    """
    MAIN_MENU = State()
    USER_MANAGEMENT = State()
    SUBSCRIPTION_MANAGEMENT = State()
    POST_SCHEDULING = State()
    NOTIFICATIONS = State()
    MESSAGE_PROTECTION = State()
    SYSTEM_MONITORING = State()
    WAITING_FOR_INPUT = State()


class AdminAction(str, Enum):
    """
    Admin action enumeration
    """
    VIEW_STATS = "view_stats"
    MANAGE_USERS = "manage_users"
    MANAGE_SUBSCRIPTIONS = "manage_subscriptions"
    SCHEDULE_POSTS = "schedule_posts"
    SEND_NOTIFICATIONS = "send_notifications"
    MANAGE_PROTECTION = "manage_protection"
    SYSTEM_MONITOR = "system_monitor"
    USER_SEARCH = "user_search"
    GRANT_VIP = "grant_vip"
    REVOKE_VIP = "revoke_vip"
    SEND_ALERT = "send_alert"
    SCHEDULE_MAINTENANCE = "schedule_maintenance"


class AdminCommandInterface(BaseHandler, MessageHandlerMixin, CallbackHandlerMixin):
    """
    Admin command interface providing private admin commands with inline menus

    Implements requirement 3.7:
    - Private admin command interface with inline menu navigation
    - Role-based access validation and authorization
    - Integration with all admin module services
    - Command result processing and feedback

    Leverages patterns from src/handlers/base.py for consistent command handling
    """

    def __init__(self, db_client: 'AsyncIOMotorClient', event_bus: EventBus, telegram_bot: 'Bot',
                 access_control: 'AccessControl', subscription_manager: 'SubscriptionManager',
                 post_scheduler: 'PostScheduler', notification_system: 'NotificationSystem',
                 message_protection: 'MessageProtectionSystem'):
        """
        Initialize the admin command interface

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing command events
            telegram_bot: Telegram bot instance for API operations
            access_control: Access control service
            subscription_manager: Subscription management service
            post_scheduler: Post scheduling service
            notification_system: Notification service
            message_protection: Message protection service
        """
        super().__init__()
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.telegram_bot = telegram_bot

        # Admin services
        self.access_control = access_control
        self.subscription_manager = subscription_manager
        self.post_scheduler = post_scheduler
        self.notification_system = notification_system
        self.message_protection = message_protection

        # Collection references
        self.users_collection = self.db.users
        self.admin_log_collection = self.db.admin_log

        # Router for command handling
        self.router = Router()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """
        Setup command and callback handlers
        """
        # Command handlers
        self.router.message(Command("admin"))(self.handle_admin_command)
        self.router.message(Command("admin_stats"))(self.handle_stats_command)
        self.router.message(Command("admin_users"))(self.handle_users_command)
        self.router.message(Command("admin_help"))(self.handle_help_command)

        # Callback query handlers
        self.router.callback_query(F.data.startswith("admin_"))(self.handle_admin_callback)

        # State-based handlers
        self.router.message(StateFilter(AdminStates.WAITING_FOR_INPUT))(self.handle_input)

    async def handle_admin_command(self, message: Message, state: FSMContext) -> None:
        """
        Handle the main /admin command

        Args:
            message: Message object
            state: FSM state context
        """
        try:
            # Validate admin access
            if not await self._validate_admin_access(message.from_user.id):
                await message.answer("❌ Acceso denegado. Se requieren privilegios de administrador.")
                return

            # Set state and show main menu
            await state.set_state(AdminStates.MAIN_MENU)
            await self._show_main_menu(message)

            # Log admin access
            await self._log_admin_action(
                user_id=str(message.from_user.id),
                action="admin_panel_accessed",
                success=True
            )

        except Exception as e:
            await self.handle_error(e, message)

    async def handle_stats_command(self, message: Message) -> None:
        """
        Handle the /admin_stats command

        Args:
            message: Message object
        """
        try:
            # Validate admin access
            if not await self._validate_admin_access(message.from_user.id):
                await message.answer("❌ Acceso denegado.")
                return

            # Get comprehensive stats
            stats = await self._get_system_stats()
            stats_text = await self._format_stats(stats)

            response = self.create_response(
                text=f"📊 **Estadísticas del Sistema**\n\n{stats_text}",
                parse_mode="Markdown"
            )

            await self.send_response(message, response)

            await self._log_admin_action(
                user_id=str(message.from_user.id),
                action="stats_viewed",
                success=True
            )

        except Exception as e:
            await self.handle_error(e, message)

    async def handle_users_command(self, message: Message, state: FSMContext) -> None:
        """
        Handle the /admin_users command

        Args:
            message: Message object
            state: FSM state context
        """
        try:
            # Validate admin access
            if not await self._validate_admin_access(message.from_user.id):
                await message.answer("❌ Acceso denegado.")
                return

            await state.set_state(AdminStates.USER_MANAGEMENT)
            await self._show_user_management_menu(message)

        except Exception as e:
            await self.handle_error(e, message)

    async def handle_help_command(self, message: Message) -> None:
        """
        Handle the /admin_help command

        Args:
            message: Message object
        """
        try:
            if not await self._validate_admin_access(message.from_user.id):
                await message.answer("❌ Acceso denegado.")
                return

            help_text = """
🔧 **Panel de Administración - Comandos Disponibles**

**Comandos Principales:**
• `/admin` - Panel principal de administración
• `/admin_stats` - Estadísticas del sistema
• `/admin_users` - Gestión de usuarios
• `/admin_help` - Esta ayuda

**Funciones del Panel:**
🏠 **Dashboard Principal**
   • Vista general del sistema
   • Estadísticas en tiempo real
   • Alertas y notificaciones

👥 **Gestión de Usuarios**
   • Buscar usuarios
   • Otorgar/revocar VIP
   • Ver historial de actividad

💎 **Suscripciones VIP**
   • Gestionar suscripciones activas
   • Procesar renovaciones
   • Ver estadísticas de ingresos

📅 **Programación de Posts**
   • Programar contenido
   • Gestionar posts activos
   • Estadísticas de publicación

📢 **Sistema de Notificaciones**
   • Enviar notificaciones globales
   • Alertas de administrador
   • Recordatorios de renovación

🛡️ **Protección de Mensajes**
   • Gestionar contenido VIP
   • Configurar niveles de acceso
   • Monitoreo de accesos

📊 **Monitoreo del Sistema**
   • Estado de servicios
   • Métricas de rendimiento
   • Logs de errores

**Navegación:**
Usa el panel interactivo para navegar entre las diferentes secciones.
Todas las acciones quedan registradas en el log de administración.
            """

            await message.answer(help_text, parse_mode="Markdown")

        except Exception as e:
            await self.handle_error(e, message)

    async def handle_admin_callback(self, callback_query: CallbackQuery, state: FSMContext) -> None:
        """
        Handle admin callback queries

        Args:
            callback_query: Callback query object
            state: FSM state context
        """
        try:
            # Validate admin access
            if not await self._validate_admin_access(callback_query.from_user.id):
                await callback_query.answer("❌ Acceso denegado.", show_alert=True)
                return

            if not await self.validate_callback_data(callback_query):
                return

            action = callback_query.data
            await self._process_admin_action(callback_query, action, state)

            await self._log_admin_action(
                user_id=str(callback_query.from_user.id),
                action=action,
                success=True
            )

        except Exception as e:
            await self.handle_error(e, callback_query)

    async def handle_input(self, message: Message, state: FSMContext) -> None:
        """
        Handle user input in waiting state

        Args:
            message: Message object
            state: FSM state context
        """
        try:
            if not await self._validate_admin_access(message.from_user.id):
                await message.answer("❌ Acceso denegado.")
                return

            # Get state data to determine what input we're waiting for
            data = await state.get_data()
            input_type = data.get("waiting_for")

            if input_type == "user_search":
                await self._process_user_search(message, state)
            elif input_type == "notification_text":
                await self._process_notification_send(message, state)
            elif input_type == "post_content":
                await self._process_post_schedule(message, state)
            else:
                await message.answer("⚠️ Entrada no reconocida. Usa /admin para volver al menú principal.")

        except Exception as e:
            await self.handle_error(e, message)

    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> Any:
        """
        Process admin messages (required by BaseHandler)

        Args:
            message: Message object
            context: Message context
            **kwargs: Additional arguments

        Returns:
            Processing result
        """
        # This is handled by specific command handlers
        return None

    async def _show_main_menu(self, message: Message) -> None:
        """
        Show the main admin menu

        Args:
            message: Message object
        """
        try:
            # Get quick stats for the main menu
            stats = await self._get_quick_stats()

            menu_text = f"""
🏠 **Panel de Administración de DianaBot**

📊 **Vista Rápida:**
• Usuarios totales: {stats.get('total_users', 0)}
• Usuarios VIP activos: {stats.get('active_vip', 0)}
• Posts programados: {stats.get('scheduled_posts', 0)}
• Notificaciones pendientes: {stats.get('pending_notifications', 0)}

🎮 **Selecciona una opción:**
            """

            builder = InlineKeyboardBuilder()

            # Main menu buttons
            buttons = [
                ("📊 Dashboard", "admin_dashboard"),
                ("👥 Usuarios", "admin_users_menu"),
                ("💎 Suscripciones", "admin_subscriptions"),
                ("📅 Posts", "admin_posts"),
                ("📢 Notificaciones", "admin_notifications"),
                ("🛡️ Protección", "admin_protection"),
                ("⚙️ Sistema", "admin_system"),
                ("❓ Ayuda", "admin_help_menu")
            ]

            for text, callback_data in buttons:
                builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))

            # Arrange buttons in 2 columns
            builder.adjust(2)

            await message.answer(
                menu_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )

        except Exception as e:
            self.logger.error(f"Error showing main menu: {e}")
            await message.answer("❌ Error mostrando el menú principal.")

    async def _show_user_management_menu(self, message: Message) -> None:
        """
        Show user management menu

        Args:
            message: Message object
        """
        try:
            menu_text = """
👥 **Gestión de Usuarios**

Opciones disponibles:
            """

            builder = InlineKeyboardBuilder()

            buttons = [
                ("🔍 Buscar Usuario", "admin_user_search"),
                ("👑 Gestionar VIP", "admin_vip_management"),
                ("📋 Lista Usuarios", "admin_user_list"),
                ("📊 Estadísticas", "admin_user_stats"),
                ("🏠 Menú Principal", "admin_main_menu")
            ]

            for text, callback_data in buttons:
                builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))

            builder.adjust(2)

            await message.answer(
                menu_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )

        except Exception as e:
            self.logger.error(f"Error showing user management menu: {e}")
            await message.answer("❌ Error mostrando el menú de usuarios.")

    async def _process_admin_action(self, callback_query: CallbackQuery, action: str,
                                  state: FSMContext) -> None:
        """
        Process admin actions from callback queries

        Args:
            callback_query: Callback query object
            action: Action to process
            state: FSM state context
        """
        try:
            if action == "admin_dashboard":
                await self._show_dashboard(callback_query)
            elif action == "admin_users_menu":
                await self._show_users_menu(callback_query)
            elif action == "admin_subscriptions":
                await self._show_subscriptions_menu(callback_query)
            elif action == "admin_posts":
                await self._show_posts_menu(callback_query)
            elif action == "admin_notifications":
                await self._show_notifications_menu(callback_query)
            elif action == "admin_protection":
                await self._show_protection_menu(callback_query)
            elif action == "admin_system":
                await self._show_system_menu(callback_query)
            elif action == "admin_user_search":
                await self._start_user_search(callback_query, state)
            elif action == "admin_vip_management":
                await self._show_vip_management(callback_query)
            elif action == "admin_send_notification":
                await self._start_notification_send(callback_query, state)
            elif action == "admin_main_menu":
                await self._show_main_menu_callback(callback_query)
            else:
                await callback_query.answer("⚠️ Acción no reconocida.")

        except Exception as e:
            self.logger.error(f"Error processing admin action {action}: {e}")
            await callback_query.answer("❌ Error procesando la acción.")

    async def _show_dashboard(self, callback_query: CallbackQuery) -> None:
        """
        Show admin dashboard

        Args:
            callback_query: Callback query object
        """
        try:
            stats = await self._get_system_stats()

            dashboard_text = f"""
📊 **Dashboard del Sistema**

**👥 Usuarios:**
• Total: {stats.get('total_users', 0)}
• Activos hoy: {stats.get('active_today', 0)}
• Nuevos esta semana: {stats.get('new_this_week', 0)}

**💎 Suscripciones VIP:**
• Activas: {stats.get('active_vip', 0)}
• Expiran hoy: {stats.get('expiring_today', 0)}
• Ingresos del mes: ${stats.get('monthly_revenue', 0)}

**📅 Posts:**
• Programados: {stats.get('scheduled_posts', 0)}
• Publicados hoy: {stats.get('published_today', 0)}
• Fallos: {stats.get('failed_posts', 0)}

**📢 Notificaciones:**
• Pendientes: {stats.get('pending_notifications', 0)}
• Enviadas hoy: {stats.get('sent_today', 0)}

**🛡️ Protección:**
• Mensajes protegidos: {stats.get('protected_messages', 0)}
• Accesos denegados hoy: {stats.get('denied_today', 0)}

*Última actualización: {datetime.utcnow().strftime("%H:%M UTC")}*
            """

            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(text="🔄 Actualizar", callback_data="admin_dashboard"))
            builder.add(InlineKeyboardButton(text="🏠 Menú Principal", callback_data="admin_main_menu"))

            await callback_query.message.edit_text(
                dashboard_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            await callback_query.answer()

        except Exception as e:
            self.logger.error(f"Error showing dashboard: {e}")
            await callback_query.answer("❌ Error mostrando el dashboard.")

    async def _validate_admin_access(self, user_id: int) -> bool:
        """
        Validate admin access for a user

        Args:
            user_id: User ID to validate

        Returns:
            True if user has admin access
        """
        try:
            user_doc = await self.users_collection.find_one({"user_id": str(user_id)})
            if user_doc:
                return user_doc.get("role") == "admin" or user_doc.get("is_admin", False)
            return False

        except Exception as e:
            self.logger.error(f"Error validating admin access: {e}")
            return False

    async def _get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics

        Returns:
            Dictionary with system statistics
        """
        try:
            stats = {}

            # User statistics
            stats["total_users"] = await self.users_collection.count_documents({})
            stats["active_today"] = await self.users_collection.count_documents({
                "last_activity": {"$gte": datetime.utcnow() - timedelta(days=1)}
            })
            stats["new_this_week"] = await self.users_collection.count_documents({
                "created_at": {"$gte": datetime.utcnow() - timedelta(days=7)}
            })

            # VIP statistics
            vip_stats = await self.subscription_manager.get_subscription_stats()
            stats.update(vip_stats)

            # Post statistics
            post_stats = await self.post_scheduler.get_post_stats()
            stats.update(post_stats)

            # Notification statistics
            notification_stats = await self.notification_system.get_notification_stats()
            stats.update(notification_stats)

            # Protection statistics
            protection_stats = await self.message_protection.get_protection_stats()
            stats.update(protection_stats)

            return stats

        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {}

    async def _get_quick_stats(self) -> Dict[str, Any]:
        """
        Get quick statistics for main menu

        Returns:
            Dictionary with quick statistics
        """
        try:
            stats = {}
            stats["total_users"] = await self.users_collection.count_documents({})
            stats["active_vip"] = await self.db.subscriptions.count_documents({"status": "active"})
            stats["scheduled_posts"] = await self.db.scheduled_posts.count_documents({"status": "scheduled"})
            stats["pending_notifications"] = await self.db.notifications.count_documents({"status": "pending"})

            return stats

        except Exception as e:
            self.logger.error(f"Error getting quick stats: {e}")
            return {}

    async def _format_stats(self, stats: Dict[str, Any]) -> str:
        """
        Format statistics for display

        Args:
            stats: Statistics dictionary

        Returns:
            Formatted statistics string
        """
        try:
            formatted = []

            # Group stats by category
            user_stats = {k: v for k, v in stats.items() if "user" in k.lower()}
            vip_stats = {k: v for k, v in stats.items() if "vip" in k.lower() or "subscription" in k.lower()}
            post_stats = {k: v for k, v in stats.items() if "post" in k.lower()}
            notification_stats = {k: v for k, v in stats.items() if "notification" in k.lower()}
            protection_stats = {k: v for k, v in stats.items() if "protection" in k.lower() or "protected" in k.lower()}

            if user_stats:
                formatted.append("**👥 Usuarios:**")
                for key, value in user_stats.items():
                    formatted.append(f"• {key.replace('_', ' ').title()}: {value}")
                formatted.append("")

            if vip_stats:
                formatted.append("**💎 Suscripciones:**")
                for key, value in vip_stats.items():
                    formatted.append(f"• {key.replace('_', ' ').title()}: {value}")
                formatted.append("")

            # Add other categories as needed

            return "\n".join(formatted) if formatted else "No hay estadísticas disponibles."

        except Exception as e:
            self.logger.error(f"Error formatting stats: {e}")
            return "Error formateando estadísticas."

    async def _log_admin_action(self, user_id: str, action: str, success: bool,
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log admin actions

        Args:
            user_id: Admin user ID
            action: Action performed
            success: Whether action was successful
            metadata: Additional metadata
        """
        try:
            log_doc = {
                "user_id": user_id,
                "action": action,
                "success": success,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }

            await self.admin_log_collection.insert_one(log_doc)

        except Exception as e:
            self.logger.error(f"Error logging admin action: {e}")

    async def _show_users_menu(self, callback_query: CallbackQuery) -> None:
        """Show users menu via callback"""
        try:
            await self._show_user_management_menu(callback_query.message)
            await callback_query.answer()
        except Exception as e:
            await callback_query.answer("❌ Error mostrando menú de usuarios.")

    async def _show_subscriptions_menu(self, callback_query: CallbackQuery) -> None:
        """Show subscriptions menu"""
        await callback_query.answer("🚧 Menú de suscripciones en desarrollo.")

    async def _show_posts_menu(self, callback_query: CallbackQuery) -> None:
        """Show posts menu"""
        await callback_query.answer("🚧 Menú de posts en desarrollo.")

    async def _show_notifications_menu(self, callback_query: CallbackQuery) -> None:
        """Show notifications menu"""
        await callback_query.answer("🚧 Menú de notificaciones en desarrollo.")

    async def _show_protection_menu(self, callback_query: CallbackQuery) -> None:
        """Show protection menu"""
        await callback_query.answer("🚧 Menú de protección en desarrollo.")

    async def _show_system_menu(self, callback_query: CallbackQuery) -> None:
        """Show system menu"""
        await callback_query.answer("🚧 Menú de sistema en desarrollo.")

    async def _start_user_search(self, callback_query: CallbackQuery, state: FSMContext) -> None:
        """Start user search process"""
        await callback_query.answer("🔍 Funcionalidad de búsqueda en desarrollo.")

    async def _show_vip_management(self, callback_query: CallbackQuery) -> None:
        """Show VIP management menu"""
        await callback_query.answer("👑 Gestión VIP en desarrollo.")

    async def _start_notification_send(self, callback_query: CallbackQuery, state: FSMContext) -> None:
        """Start notification sending process"""
        await callback_query.answer("📢 Envío de notificaciones en desarrollo.")

    async def _show_main_menu_callback(self, callback_query: CallbackQuery) -> None:
        """Show main menu via callback"""
        try:
            await self._show_main_menu(callback_query.message)
            await callback_query.answer()
        except Exception as e:
            await callback_query.answer("❌ Error mostrando menú principal.")

    async def _process_user_search(self, message: Message, state: FSMContext) -> None:
        """Process user search input"""
        await message.answer("🚧 Búsqueda de usuarios en desarrollo.")

    async def _process_notification_send(self, message: Message, state: FSMContext) -> None:
        """Process notification sending"""
        await message.answer("🚧 Envío de notificaciones en desarrollo.")

    async def _process_post_schedule(self, message: Message, state: FSMContext) -> None:
        """Process post scheduling"""
        await message.answer("🚧 Programación de posts en desarrollo.")

    def get_router(self) -> Router:
        """
        Get the router for this handler

        Returns:
            Aiogram Router instance
        """
        return self.router
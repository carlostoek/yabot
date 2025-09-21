"""
Unified Menu Factory System for YABOT
Manages role-based menu generation with consistency across the entire system.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import json
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

# Telegram Bot API constants
TELEGRAM_CALLBACK_DATA_MAX_LENGTH = 64
TELEGRAM_MAX_INLINE_BUTTONS_PER_ROW = 8
TELEGRAM_MAX_INLINE_KEYBOARD_ROWS = 100


class MenuError(Exception):
    """Base exception for menu-related errors."""
    pass


class CallbackDataTooLongError(MenuError):
    """Raised when callback data exceeds Telegram's limit."""
    pass


class MenuGenerationError(MenuError):
    """Raised when menu generation fails."""
    pass


class ValidationError(MenuError):
    """Raised when menu validation fails."""
    pass


class UserRole(Enum):
    """User role enumeration for menu access control."""
    GUEST = "guest"
    FREE_USER = "free_user"
    VIP_USER = "vip_user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class MenuType(Enum):
    """Menu type enumeration for different contexts."""
    MAIN = "main"
    NARRATIVE = "narrative"
    GAMIFICATION = "gamification"
    ADMIN = "admin"
    VIP = "vip"
    PROFILE = "profile"
    STORE = "store"
    EMOTIONAL = "emotional"
    DIANA = "diana"


class ActionType(Enum):
    """Action type for menu items."""
    COMMAND = "command"
    CALLBACK = "callback"
    URL = "url"
    SUBMENU = "submenu"
    NARRATIVE_ACTION = "narrative_action"
    ADMIN_ACTION = "admin_action"


@dataclass
class MenuItem:
    """Represents a single menu item with all necessary properties."""
    id: str
    text: str
    action_type: ActionType
    action_data: str
    icon: str = "📋"
    description: str = ""
    required_role: UserRole = UserRole.FREE_USER
    required_vip: bool = False
    required_level: int = 0
    requires_besitos: int = 0
    visible_condition: Optional[str] = None
    enabled_condition: Optional[str] = None
    submenu_items: List['MenuItem'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate menu item after initialization."""
        self._validate_callback_data()
        self._add_role_indicators()

    def _validate_callback_data(self) -> None:
        """Validate that callback data doesn't exceed Telegram's limit."""
        if len(self.action_data.encode('utf-8')) > TELEGRAM_CALLBACK_DATA_MAX_LENGTH:
            # Try to compress the callback data
            compressed_data = self._compress_callback_data(self.action_data)
            if len(compressed_data.encode('utf-8')) > TELEGRAM_CALLBACK_DATA_MAX_LENGTH:
                logger.error(
                    f"Callback data too long for item '{self.id}': {len(self.action_data)} bytes, "
                    f"compressed: {len(compressed_data)} bytes"
                )
                raise CallbackDataTooLongError(
                    f"Callback data for '{self.id}' exceeds {TELEGRAM_CALLBACK_DATA_MAX_LENGTH} bytes"
                )
            else:
                logger.warning(
                    f"Compressed callback data for item '{self.id}': {len(self.action_data)} -> {len(compressed_data)} bytes"
                )
                self.action_data = compressed_data

    def _compress_callback_data(self, data: str) -> str:
        """Compress callback data using a mapping strategy."""
        # Create a hash-based mapping for long action data
        if len(data) > TELEGRAM_CALLBACK_DATA_MAX_LENGTH - 10:  # Leave room for prefix
            data_hash = hashlib.md5(data.encode()).hexdigest()[:8]
            return f"hash:{data_hash}"
        return data

    def _add_role_indicators(self) -> None:
        """Add visual indicators for role requirements."""
        indicators = []

        if self.required_vip:
            indicators.append("💎")

        if self.required_level > 0:
            indicators.append(f"Lv.{self.required_level}")

        if self.requires_besitos > 0:
            indicators.append(f"💰{self.requires_besitos}")

        if self.required_role not in [UserRole.FREE_USER, UserRole.GUEST]:
            role_symbols = {
                UserRole.VIP_USER: "⭐",
                UserRole.ADMIN: "🔧",
                UserRole.SUPER_ADMIN: "👑"
            }
            if self.required_role in role_symbols:
                indicators.append(role_symbols[self.required_role])

        if indicators:
            # Add indicators to the end of the text if not already present
            indicator_text = " ".join(indicators)
            if not any(indicator in self.text for indicator in indicators):
                self.text = f"{self.text} {indicator_text}"


@dataclass
class Menu:
    """Represents a complete menu with header, items, and context."""
    menu_id: str
    title: str
    description: str
    menu_type: MenuType
    required_role: UserRole
    items: List[MenuItem] = field(default_factory=list)
    header_text: str = ""
    footer_text: str = ""
    max_columns: int = 2
    is_dynamic: bool = False
    context_data: Dict[str, Any] = field(default_factory=dict)
    parent_menu_id: Optional[str] = None
    navigation_path: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate menu after initialization."""
        self._validate_menu()
        self._add_navigation_items()

    def _validate_menu(self) -> None:
        """Validate menu structure and constraints."""
        # Validate total number of items
        if len(self.items) > TELEGRAM_MAX_INLINE_KEYBOARD_ROWS * TELEGRAM_MAX_INLINE_BUTTONS_PER_ROW:
            logger.warning(f"Menu '{self.menu_id}' has too many items: {len(self.items)}")

        # Validate menu hierarchy depth
        if len(self.navigation_path) > 5:  # Max 5 levels deep
            logger.warning(f"Menu '{self.menu_id}' is too deep in hierarchy: {len(self.navigation_path)} levels")

    def _add_navigation_items(self) -> None:
        """Add back navigation and home buttons to the menu."""
        navigation_items = []

        # Add back button if we have a parent or navigation path
        if self.parent_menu_id or self.navigation_path:
            back_target = self.parent_menu_id or (self.navigation_path[-1] if self.navigation_path else "main_menu")
            navigation_items.append(MenuItem(
                id="nav_back",
                text="◀️ Atrás",
                action_type=ActionType.CALLBACK,
                action_data=f"menu:{back_target}",
                description="Volver al menú anterior",
                icon="◀️"
            ))

        # Add home button if we're not already in main menu
        if self.menu_id != "main_menu":
            navigation_items.append(MenuItem(
                id="nav_home",
                text="🏠 Inicio",
                action_type=ActionType.CALLBACK,
                action_data="menu:main_menu",
                description="Ir al menú principal",
                icon="🏠"
            ))

        # Add navigation items to the menu (at the end)
        self.items.extend(navigation_items)


class MenuBuilder(ABC):
    """Abstract base class for menu builders."""

    @abstractmethod
    def build_menu(self, user_context: Dict[str, Any], **kwargs) -> Menu:
        """Build menu for specific user context."""
        pass

    def _log_menu_creation(self, menu_type: str, user_id: str, success: bool,
                          error: Optional[str] = None) -> None:
        """Log menu creation attempts for debugging."""
        timestamp = datetime.now().isoformat()
        if success:
            logger.info(f"[{timestamp}] Menu created successfully: {menu_type} for user {user_id}")
        else:
            logger.error(f"[{timestamp}] Menu creation failed: {menu_type} for user {user_id}. Error: {error}")

    def _validate_user_context(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize user context."""
        required_fields = ['role', 'user_id']
        for field in required_fields:
            if field not in user_context:
                logger.warning(f"Missing required field '{field}' in user context")
                if field == 'role':
                    user_context[field] = 'free_user'
                elif field == 'user_id':
                    user_context[field] = 'unknown'

        # Ensure role is valid
        try:
            UserRole(user_context['role'])
        except ValueError:
            logger.warning(f"Invalid role '{user_context['role']}', defaulting to free_user")
            user_context['role'] = 'free_user'

        return user_context


class MainMenuBuilder(MenuBuilder):
    """Builder for main application menu."""

    def build_menu(self, user_context: Dict[str, Any], **kwargs) -> Menu:
        """Build main menu based on user role and status."""
        try:
            user_context = self._validate_user_context(user_context)
            user_role = UserRole(user_context.get('role', 'free_user'))
            has_vip = user_context.get('has_vip', False)
            narrative_level = user_context.get('narrative_level', 0)
            user_id = user_context.get('user_id', 'unknown')

            logger.info(f"Building main menu for user {user_id} (role: {user_role.value}, vip: {has_vip}, level: {narrative_level})")

            items = []

            # Historia/Narrativa - Todos los usuarios
            items.append(MenuItem(
                id="narrative_main",
                text="🎭 Historia con Diana",
                action_type=ActionType.SUBMENU,
                action_data="narrative_menu",
                description="Explora la narrativa interactiva",
                required_role=UserRole.FREE_USER
            ))

            # Mochila - Solo usuarios registrados
            items.append(MenuItem(
                id="inventory",
                text="🎒 Mi Mochila",
                action_type=ActionType.CALLBACK,
                action_data="show_inventory",
                description="Ver tus objetos y fragmentos",
                required_role=UserRole.FREE_USER
            ))

            # Misiones - Usuarios registrados
            items.append(MenuItem(
                id="missions",
                text="🎯 Misiones",
                action_type=ActionType.CALLBACK,
                action_data="show_missions",
                description="Tus misiones activas",
                required_role=UserRole.FREE_USER
            ))

            # Mi Diván - Solo VIP nivel 4+
            if has_vip and narrative_level >= 4:
                items.append(MenuItem(
                    id="divan_access",
                    text="🛋️ Mi Diván",
                    action_type=ActionType.SUBMENU,
                    action_data="divan_menu",
                    description="Acceso exclusivo VIP",
                    required_role=UserRole.VIP_USER,
                    required_vip=True,
                    required_level=4
                ))

            # Tienda
            items.append(MenuItem(
                id="store",
                text="🏪 Tienda",
                action_type=ActionType.SUBMENU,
                action_data="store_menu",
                description="Compra objetos y mejoras",
                required_role=UserRole.FREE_USER
            ))

            # Regalo Diario
            items.append(MenuItem(
                id="daily_gift",
                text="🎁 Regalo Diario",
                action_type=ActionType.CALLBACK,
                action_data="daily_gift",
                description="Reclama tu regalo diario",
                required_role=UserRole.FREE_USER
            ))

            # Mi Perfil
            items.append(MenuItem(
                id="profile",
                text="👤 Mi Perfil",
                action_type=ActionType.SUBMENU,
                action_data="profile_menu",
                description="Gestiona tu perfil",
                required_role=UserRole.FREE_USER
            ))

            # Admin Panel - Solo administradores
            if user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                items.append(MenuItem(
                    id="admin_panel",
                    text="⚙️ Panel Admin",
                    action_type=ActionType.SUBMENU,
                    action_data="admin_menu",
                    description="Herramientas administrativas",
                    required_role=UserRole.ADMIN,
                    icon="⚙️"
                ))

            menu = Menu(
                menu_id="main_menu",
                title="🏠 Menú Principal",
                description="Bienvenido al mundo de Diana",
                menu_type=MenuType.MAIN,
                required_role=UserRole.FREE_USER,
                items=items,
                header_text="✨ Bienvenido al mundo de Diana ✨",
                footer_text="Selecciona una opción para continuar",
                navigation_path=[]
            )

            self._log_menu_creation("main_menu", user_id, True)
            return menu

        except Exception as e:
            self._log_menu_creation("main_menu", user_context.get('user_id', 'unknown'), False, str(e))
            raise MenuGenerationError(f"Failed to build main menu: {str(e)}") from e


class NarrativeMenuBuilder(MenuBuilder):
    """Builder for narrative/Diana menu system."""

    def build_menu(self, user_context: Dict[str, Any], **kwargs) -> Menu:
        """Build narrative menu based on user progress."""
        try:
            user_context = self._validate_user_context(user_context)
            narrative_level = user_context.get('narrative_level', 0)
            has_vip = user_context.get('has_vip', False)
            current_fragment = user_context.get('current_fragment', 'start')
            completed_fragments = user_context.get('completed_fragments', [])
            user_id = user_context.get('user_id', 'unknown')
            parent_menu_id = kwargs.get('parent_menu_id', 'main_menu')

            logger.info(f"Building narrative menu for user {user_id} (level: {narrative_level}, vip: {has_vip})")

            items = []

            # Continuar Historia
            items.append(MenuItem(
                id="continue_story",
                text="📖 Continuar Historia",
                action_type=ActionType.NARRATIVE_ACTION,
                action_data=f"continue_from:{current_fragment}",
                description="Continúa donde te quedaste",
                icon="📖"
            ))

            # Los Kinkys (Niveles 1-3) - Acceso gratuito
            if narrative_level >= 1:
            items.append(MenuItem(
                id="kinkys_level1",
                text="🌸 Los Kinkys - Nivel 1",
                action_type=ActionType.NARRATIVE_ACTION,
                action_data="level:kinkys_1",
                description="El Umbral del Espejo",
                icon="🌸",
                enabled_condition="level >= 1"
            ))

            if narrative_level >= 2:
            items.append(MenuItem(
                id="kinkys_level2",
                text="🌸 Los Kinkys - Nivel 2",
                action_type=ActionType.NARRATIVE_ACTION,
                action_data="level:kinkys_2",
                description="El Regreso del Observador",
                icon="🌸",
                enabled_condition="level >= 2"
            ))

            if narrative_level >= 3:
            items.append(MenuItem(
                id="kinkys_level3",
                text="🌸 Los Kinkys - Nivel 3",
                action_type=ActionType.NARRATIVE_ACTION,
                action_data="level:kinkys_3",
                description="El Espejo del Deseo",
                icon="🌸",
                enabled_condition="level >= 3"
            ))

        # El Diván (Niveles 4-6) - Requiere VIP
        if has_vip and narrative_level >= 4:
            items.append(MenuItem(
                id="divan_level4",
                text="🛋️ El Diván - Nivel 4",
                action_type=ActionType.NARRATIVE_ACTION,
                action_data="level:divan_4",
                description="La Comprensión en Capas",
                icon="🛋️",
                required_vip=True,
                required_level=4
            ))

        if has_vip and narrative_level >= 5:
            items.append(MenuItem(
                id="divan_level5",
                text="🛋️ El Diván - Nivel 5",
                action_type=ActionType.NARRATIVE_ACTION,
                action_data="level:divan_5",
                description="La Profundización Suprema",
                icon="🛋️",
                required_vip=True,
                required_level=5
            ))

        if has_vip and narrative_level >= 6:
            items.append(MenuItem(
                id="circulo_intimo",
                text="💫 Círculo Íntimo",
                action_type=ActionType.NARRATIVE_ACTION,
                action_data="level:circulo_intimo",
                description="Más Allá del Final",
                icon="💫",
                required_vip=True,
                required_level=6
            ))

        # Fragmentos de Memoria
        if len(completed_fragments) > 0:
            items.append(MenuItem(
                id="memory_fragments",
                text="🧩 Fragmentos de Memoria",
                action_type=ActionType.CALLBACK,
                action_data="show_memory_fragments",
                description="Revive momentos especiales",
                icon="🧩"
            ))

        # Análisis Emocional - Solo VIP
        if has_vip:
            items.append(MenuItem(
                id="emotional_analysis",
                text="💭 Análisis Emocional",
                action_type=ActionType.CALLBACK,
                action_data="show_emotional_analysis",
                description="Tu perfil emocional con Diana",
                icon="💭",
                required_vip=True
            ))

            menu = Menu(
                menu_id="narrative_menu",
                title="🎭 Historia con Diana",
                description=f"Tu nivel actual: {narrative_level}",
                menu_type=MenuType.NARRATIVE,
                required_role=UserRole.FREE_USER,
                items=items,
                header_text="🌟 Explora tu historia con Diana 🌟",
                is_dynamic=True,
                parent_menu_id=parent_menu_id,
                navigation_path=kwargs.get('navigation_path', [])
            )

            self._log_menu_creation("narrative_menu", user_id, True)
            return menu

        except Exception as e:
            self._log_menu_creation("narrative_menu", user_context.get('user_id', 'unknown'), False, str(e))
            raise MenuGenerationError(f"Failed to build narrative menu: {str(e)}") from e


class AdminMenuBuilder(MenuBuilder):
    """Builder for administrative menu system."""

    def build_menu(self, user_context: Dict[str, Any], **kwargs) -> Menu:
        """Build admin menu based on admin role."""
        try:
            user_context = self._validate_user_context(user_context)
            user_role = UserRole(user_context.get('role', 'admin'))
            user_id = user_context.get('user_id', 'unknown')
            parent_menu_id = kwargs.get('parent_menu_id', 'main_menu')

            logger.info(f"Building admin menu for user {user_id} (role: {user_role.value})")

            items = []

        # Gestión de Usuarios
        items.append(MenuItem(
            id="user_management",
            text="👥 Gestión de Usuarios",
            action_type=ActionType.SUBMENU,
            action_data="admin_users_menu",
            description="Administrar usuarios del sistema",
            required_role=UserRole.ADMIN
        ))

        # Gestión de Contenido Narrativo
            items.append(MenuItem(
            id="narrative_management",
            text="📝 Gestión de Narrativa",
            action_type=ActionType.SUBMENU,
            action_data="admin_narrative_menu",
            description="Crear y editar contenido narrativo",
            required_role=UserRole.ADMIN
        ))

        # Análisis de Comportamiento
            items.append(MenuItem(
            id="behavior_analytics",
            text="📊 Análisis Comportamental",
            action_type=ActionType.CALLBACK,
            action_data="show_behavior_analytics",
            description="Estadísticas de comportamiento emocional",
            required_role=UserRole.ADMIN
        ))

        # Sistema de Recompensas
            items.append(MenuItem(
            id="reward_management",
            text="🎁 Gestión de Recompensas",
            action_type=ActionType.SUBMENU,
            action_data="admin_rewards_menu",
            description="Configurar sistema de recompensas",
            required_role=UserRole.ADMIN
        ))

        # Configuración del Sistema
            items.append(MenuItem(
            id="system_config",
            text="⚙️ Configuración",
            action_type=ActionType.SUBMENU,
            action_data="admin_config_menu",
            description="Configuración del sistema",
            required_role=UserRole.ADMIN
        ))

        # Logs y Monitoreo - Solo Super Admin
        if user_role == UserRole.SUPER_ADMIN:
            items.append(MenuItem(
                id="system_monitoring",
                text="📈 Monitoreo del Sistema",
                action_type=ActionType.CALLBACK,
                action_data="show_system_monitoring",
                description="Logs y métricas del sistema",
                required_role=UserRole.SUPER_ADMIN
            ))

        # Base de Datos - Solo Super Admin
        if user_role == UserRole.SUPER_ADMIN:
            items.append(MenuItem(
                id="database_management",
                text="🗄️ Gestión BD",
                action_type=ActionType.SUBMENU,
                action_data="admin_database_menu",
                description="Administración de base de datos",
                required_role=UserRole.SUPER_ADMIN
            ))

        return Menu(
            menu_id="admin_menu",
            title="⚙️ Panel de Administración",
            description="Herramientas administrativas",
            menu_type=MenuType.ADMIN,
            required_role=UserRole.ADMIN,
            items=items,
            header_text="🔧 Panel de Administración 🔧"
        )


class VIPMenuBuilder(MenuBuilder):
    """Builder for VIP exclusive menu system."""

    def build_menu(self, user_context: Dict[str, Any]) -> Menu:
        """Build VIP menu with exclusive content."""
        narrative_level = user_context.get('narrative_level', 0)

        items = []

        # Acceso al Diván
            items.append(MenuItem(
            id="divan_exclusive",
            text="🛋️ El Diván Privado",
            action_type=ActionType.NARRATIVE_ACTION,
            action_data="divan:private_access",
            description="Tu espacio íntimo con Diana",
            required_vip=True
        ))

        # Archivo Personal de Diana
            items.append(MenuItem(
            id="diana_personal_archive",
            text="📚 Archivo Personal de Diana",
            action_type=ActionType.CALLBACK,
            action_data="show_diana_archive",
            description="Memorias íntimas y reflexiones",
            required_vip=True,
            required_level=4
        ))

        # Diario Íntimo
            if narrative_level >= 5:
            items.append(MenuItem(
                id="diana_intimate_diary",
                text="📖 Diario Íntimo de Diana",
                action_type=ActionType.CALLBACK,
                action_data="show_intimate_diary",
                description="Pensamientos más profundos",
                required_vip=True,
                required_level=5
            ))

        # Contenido Exclusivo
            items.append(MenuItem(
            id="exclusive_content",
            text="✨ Contenido Exclusivo",
            action_type=ActionType.SUBMENU,
            action_data="vip_exclusive_menu",
            description="Solo para miembros VIP",
            required_vip=True
        ))

        # Sesiones Personalizadas
            items.append(MenuItem(
            id="personalized_sessions",
            text="💫 Sesiones Personalizadas",
            action_type=ActionType.CALLBACK,
            action_data="start_personalized_session",
            description="Experiencias adaptadas a ti",
            required_vip=True
        ))

        return Menu(
            menu_id="vip_menu",
            title="💎 Área VIP",
            description="Contenido exclusivo para miembros VIP",
            menu_type=MenuType.VIP,
            required_role=UserRole.VIP_USER,
            items=items,
            header_text="💎 Bienvenido al Área VIP 💎",
            footer_text="Contenido exclusivo diseñado para ti"
        )


class MenuValidationUtils:
    """Utility class for menu validation and optimization."""

    @staticmethod
    def validate_callback_data_length(data: str) -> bool:
        """Check if callback data is within Telegram limits."""
        return len(data.encode('utf-8')) <= TELEGRAM_CALLBACK_DATA_MAX_LENGTH

    @staticmethod
    def optimize_menu_hierarchy(menu: Menu, max_depth: int = 3) -> Menu:
        """Optimize menu hierarchy to reduce navigation depth."""
        if len(menu.navigation_path) > max_depth:
            # Flatten submenu items if hierarchy is too deep
            flattened_items = []
            for item in menu.items:
                if item.action_type == ActionType.SUBMENU and item.submenu_items:
                    # Convert submenu items to regular items with prefixed names
                    for subitem in item.submenu_items:
                        flattened_item = MenuItem(
                            id=f"{item.id}_{subitem.id}",
                            text=f"{item.icon} {subitem.text}",
                            action_type=subitem.action_type,
                            action_data=subitem.action_data,
                            description=f"{item.text}: {subitem.description}",
                            required_role=subitem.required_role,
                            required_vip=subitem.required_vip,
                            required_level=subitem.required_level
                        )
                        flattened_items.append(flattened_item)
                else:
                    flattened_items.append(item)

            menu.items = flattened_items
            logger.info(f"Flattened menu hierarchy for '{menu.menu_id}' - reduced depth")

        return menu

    @staticmethod
    def add_performance_metadata(menu: Menu) -> Menu:
        """Add performance metadata to menu for analytics."""
        menu.metadata = menu.metadata or {}
        menu.metadata.update({
            'created_at': datetime.now().isoformat(),
            'item_count': len(menu.items),
            'has_vip_items': any(item.required_vip for item in menu.items),
            'max_role_required': max((item.required_role for item in menu.items), default=UserRole.FREE_USER, key=lambda x: x.value)
        })
        return menu


class MenuFactory:
    """Main factory class for generating menus based on context."""

    def __init__(self):
        """Initialize menu factory with builders."""
        self.builders = {
            MenuType.MAIN: MainMenuBuilder(),
            MenuType.NARRATIVE: NarrativeMenuBuilder(),
            MenuType.ADMIN: AdminMenuBuilder(),
            MenuType.VIP: VIPMenuBuilder()
        }

        # Menu definitions for common patterns
        self.menu_definitions = self._initialize_menu_definitions()
        self.validation_utils = MenuValidationUtils()

        # Callback data mapping for compression
        self.callback_mapping = {}

    def _initialize_menu_definitions(self) -> Dict[str, Dict]:
        """Initialize static menu definitions."""
        return {
            "profile_menu": {
                "title": "👤 Mi Perfil",
                "items": [
                    {
                        "id": "view_stats",
                        "text": "📊 Mis Estadísticas",
                        "action": "show_user_stats",
                        "description": "Ver tu progreso y logros"
                    },
                    {
                        "id": "emotional_profile",
                        "text": "💭 Perfil Emocional",
                        "action": "show_emotional_profile",
                        "description": "Tu firma emocional única"
                    },
                    {
                        "id": "achievements",
                        "text": "🏆 Logros",
                        "action": "show_achievements",
                        "description": "Tus logros desbloqueados"
                    },
                    {
                        "id": "settings",
                        "text": "⚙️ Configuración",
                        "action": "show_settings",
                        "description": "Personaliza tu experiencia"
                    }
                ]
            },

            "store_menu": {
                "title": "🏪 Tienda",
                "items": [
                    {
                        "id": "narrative_items",
                        "text": "📚 Objetos Narrativos",
                        "action": "show_narrative_store",
                        "description": "Fragmentos y memorias especiales"
                    },
                    {
                        "id": "emotional_boosts",
                        "text": "💫 Potenciadores Emocionales",
                        "action": "show_emotional_store",
                        "description": "Mejora tu conexión con Diana"
                    },
                    {
                        "id": "vip_upgrade",
                        "text": "💎 Mejora a VIP",
                        "action": "show_vip_upgrade",
                        "description": "Accede al contenido exclusivo",
                        "required_role": "free_user"
                    },
                    {
                        "id": "besitos_packages",
                        "text": "💰 Paquetes de Besitos",
                        "action": "show_besitos_store",
                        "description": "Compra moneda del juego"
                    }
                ]
            }
        }

    def create_menu(self, menu_type: MenuType, user_context: Dict[str, Any]) -> Menu:
        """Create menu based on type and user context."""
        if menu_type in self.builders:
            return self.builders[menu_type].build_menu(user_context)
        else:
            # Fallback to basic menu
            return self._create_basic_menu(menu_type, user_context)

    def create_menu_by_id(self, menu_id: str, user_context: Dict[str, Any]) -> Optional[Menu]:
        """Create menu by specific ID."""
        if menu_id in self.menu_definitions:
            return self._create_menu_from_definition(menu_id, user_context)
        return None

    def _create_menu_from_definition(self, menu_id: str, user_context: Dict[str, Any]) -> Menu:
        """Create menu from static definition."""
        definition = self.menu_definitions[menu_id]

        items = []
        for item_def in definition["items"]:
            # Check if user meets requirements for this item
            if self._user_meets_requirements(item_def, user_context):
                item = MenuItem(
                    id=item_def["id"],
                    text=item_def["text"],
                    action_type=ActionType.CALLBACK,
                    action_data=item_def["action"],
                    description=item_def.get("description", ""),
                    required_role=UserRole(item_def.get("required_role", "free_user"))
                )
                items.append(item)

        return Menu(
            menu_id=menu_id,
            title=definition["title"],
            description="",
            menu_type=MenuType.PROFILE,
            required_role=UserRole.FREE_USER,
            items=items
        )

    def _user_meets_requirements(self, item_def: Dict, user_context: Dict[str, Any]) -> bool:
        """Check if user meets requirements for menu item."""
        required_role = item_def.get("required_role")
        if required_role:
            user_role = user_context.get("role", "free_user")
            if not self._role_has_access(UserRole(user_role), UserRole(required_role)):
                return False

        return True

    def _role_has_access(self, user_role: UserRole, required_role: UserRole) -> bool:
        """Check if user role has access to required role."""
        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.FREE_USER: 1,
            UserRole.VIP_USER: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPER_ADMIN: 4
        }

        return role_hierarchy[user_role] >= role_hierarchy[required_role]

    def _create_basic_menu(self, menu_type: MenuType, user_context: Dict[str, Any]) -> Menu:
        """Create basic fallback menu."""
        return Menu(
            menu_id="basic_menu",
            title="📋 Menú Básico",
            description="Menú básico del sistema",
            menu_type=menu_type,
            required_role=UserRole.FREE_USER,
            items=[
                MenuItem(
                    id="back_to_main",
                    text="🔙 Volver al Menú Principal",
                    action_type=ActionType.CALLBACK,
                    action_data="main_menu",
                    description="Regresar al menú principal"
                )
            ]
        )


# Global menu factory instance
menu_factory = MenuFactory()


def get_menu_for_user(menu_type: Union[MenuType, str], user_context: Dict[str, Any]) -> Menu:
    """Convenience function to get menu for user."""
    if isinstance(menu_type, str):
        # Try to get by ID first
        menu = menu_factory.create_menu_by_id(menu_type, user_context)
        if menu:
            return menu

        # Convert string to MenuType if possible
        try:
            menu_type = MenuType(menu_type)
        except ValueError:
            menu_type = MenuType.MAIN

    return menu_factory.create_menu(menu_type, user_context)
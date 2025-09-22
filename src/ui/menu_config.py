"""
Centralized Menu System Configuration for YABOT.

This module provides centralized configuration for the menu system,
including menu definitions, routing rules, and system settings.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

# Menu system constants
MENU_SYSTEM_VERSION = "1.0.0"
DEFAULT_MENU_TTL = 300  # 5 minutes
MAX_MENU_DEPTH = 5
DEFAULT_MAX_COLUMNS = 2

# Menu types enumeration
class MenuType(str, Enum):
    """Enumeration of menu types."""
    MAIN = "main"
    NARRATIVE = "narrative"
    GAMIFICATION = "gamification"
    ADMIN = "admin"
    VIP = "vip"
    PROFILE = "profile"
    STORE = "store"
    EMOTIONAL = "emotional"
    DIANA = "diana"
    SETTINGS = "settings"
    HELP = "help"

# Action types enumeration
class ActionType(str, Enum):
    """Enumeration of action types."""
    COMMAND = "command"
    CALLBACK = "callback"
    URL = "url"
    SUBMENU = "submenu"
    NARRATIVE_ACTION = "narrative_action"
    ADMIN_ACTION = "admin_action"
    USER_ACTION = "user_action"

# User roles enumeration
class UserRole(str, Enum):
    """Enumeration of user roles."""
    GUEST = "guest"
    FREE_USER = "free_user"
    VIP_USER = "vip_user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

# Menu item definition
@dataclass
class MenuItemConfig:
    """Configuration for a menu item."""
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
    visible_condition: str = ""
    enabled_condition: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    required_worthiness: float = 0.0

# Menu definition
@dataclass
class MenuConfig:
    """Configuration for a menu."""
    menu_id: str
    title: str
    description: str
    menu_type: MenuType
    required_role: UserRole
    items: List[MenuItemConfig] = field(default_factory=list)
    header_text: str = ""
    footer_text: str = ""
    max_columns: int = DEFAULT_MAX_COLUMNS
    is_dynamic: bool = False
    parent_menu_id: str = ""
    navigation_path: List[str] = field(default_factory=list)

# Centralized menu definitions
MENU_DEFINITIONS: Dict[str, MenuConfig] = {
    "main_menu": MenuConfig(
        menu_id="main_menu",
        title="🏠 Tu Mundo con Diana",
        description="Un universo de posibilidades esperándote",
        menu_type=MenuType.MAIN,
        required_role=UserRole.FREE_USER,
        items=[
            MenuItemConfig(
                id="historia_diana",
                text="🎭 Historia con Diana",
                action_type=ActionType.SUBMENU,
                action_data="narrative_menu",
                description="Tu narrativa personal en evolución",
                icon="🎭"
            ),
            MenuItemConfig(
                id="experiencias_interactivas",
                text="🎮 Experiencias Interactivas",
                action_type=ActionType.SUBMENU,
                action_data="experiences_menu",
                description="Misiones, juegos y desafíos",
                icon="🎮"
            ),
            MenuItemConfig(
                id="coleccion_tesoros",
                text="🏪 Colección de Tesoros",
                action_type=ActionType.SUBMENU,
                action_data="organic_store_menu",
                description="Fragmentos, joyas y máscaras emocionales",
                icon="🏪"
            ),
            MenuItemConfig(
                id="universo_personal",
                text="🎒 Mi Universo Personal",
                action_type=ActionType.SUBMENU,
                action_data="personal_universe_menu",
                description="Tu progreso y tesoros acumulados",
                icon="🎒"
            ),
            MenuItemConfig(
                id="el_divan",
                text="🛋️ El Diván",
                action_type=ActionType.SUBMENU,
                action_data="divan_menu",
                description="Tu espacio íntimo de comprensión profunda",
                icon="🛋️",
                required_vip=True,
                required_level=4,
                required_worthiness=0.6
            )
        ]
    ),
    
    "narrative_menu": MenuConfig(
        menu_id="narrative_menu",
        title="🎭 Historia con Diana",
        description="Explora tu historia con Diana",
        menu_type=MenuType.NARRATIVE,
        required_role=UserRole.FREE_USER,
        parent_menu_id="main_menu"
    ),
    
    "experiences_menu": MenuConfig(
        menu_id="experiences_menu",
        title="🎮 Experiencias Interactivas",
        description="Misiones, juegos y desafíos",
        menu_type=MenuType.GAMIFICATION,
        required_role=UserRole.FREE_USER,
        parent_menu_id="main_menu"
    ),
    
    "organic_store_menu": MenuConfig(
        menu_id="organic_store_menu",
        title="🏪 Colección de Tesoros",
        description="Cada objeto cuenta una historia, cada adquisición revela carácter",
        menu_type=MenuType.STORE,
        required_role=UserRole.FREE_USER,
        parent_menu_id="main_menu"
    ),
    
    "personal_universe_menu": MenuConfig(
        menu_id="personal_universe_menu",
        title="🎒 Mi Universo Personal",
        description="Tu progreso y tesoros acumulados",
        menu_type=MenuType.PROFILE,
        required_role=UserRole.FREE_USER,
        parent_menu_id="main_menu"
    ),
    
    "admin_menu": MenuConfig(
        menu_id="admin_menu",
        title="⚙️ Panel de Administración",
        description="Herramientas administrativas",
        menu_type=MenuType.ADMIN,
        required_role=UserRole.ADMIN
    )
}

# Menu routing rules
MENU_ROUTING_RULES: Dict[str, str] = {
    "start": "main_menu",
    "menu": "main_menu",
    "help": "help_menu",
    "narrative": "narrative_menu",
    "store": "organic_store_menu",
    "profile": "personal_universe_menu",
    "admin": "admin_menu"
}

# System settings
MENU_SYSTEM_SETTINGS: Dict[str, Any] = {
    "enable_cache": True,
    "cache_ttl": 300,  # 5 minutes
    "max_menu_items": 50,
    "enable_lucien_voice": True,
    "enable_organic_restrictions": True,
    "enable_performance_monitoring": True,
    "cleanup_expired_messages": True,
    "message_ttl_config": {
        'main_menu': -1,  # Never delete
        'system_notification': 5,
        'error_message': 10,
        'success_feedback': 3,
        'loading_message': 2,
        'temporary_info': 8,
        'lucien_response': 6,
        'callback_response': 4,
        'admin_notification': 15,
        'debug_message': 30,
        'default': 60
    }
}

# Worthiness thresholds
WORTHINESS_THRESHOLDS: Dict[str, float] = {
    "basic_access": 0.0,
    "standard_features": 0.2,
    "premium_features": 0.4,
    "vip_access": 0.6,
    "divan_access": 0.7,
    "trusted_access": 0.8
}

# Menu system configuration class
class MenuSystemConfig:
    """Central configuration class for the menu system."""
    
    def __init__(self):
        self.version = MENU_SYSTEM_VERSION
        self.definitions = MENU_DEFINITIONS
        self.routing_rules = MENU_ROUTING_RULES
        self.settings = MENU_SYSTEM_SETTINGS
        self.worthiness_thresholds = WORTHINESS_THRESHOLDS
    
    def get_menu_definition(self, menu_id: str) -> MenuConfig:
        """Get menu definition by ID."""
        return self.definitions.get(menu_id)
    
    def get_routing_rule(self, command: str) -> str:
        """Get routing rule for a command."""
        return self.routing_rules.get(command, "main_menu")
    
    def get_setting(self, key: str, default=None):
        """Get system setting by key."""
        return self.settings.get(key, default)
    
    def get_worthiness_threshold(self, level: str) -> float:
        """Get worthiness threshold for a level."""
        return self.worthiness_thresholds.get(level, 0.0)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return self.settings.get(f"enable_{feature}", False)

# Global menu system configuration instance
menu_system_config = MenuSystemConfig()
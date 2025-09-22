# Menu System

## Resumen
The menu system is a powerful and flexible component that is responsible for generating and rendering all the menus in the YABOT application. It is designed to be highly configurable and extensible, allowing for the creation of complex, dynamic, and personalized menus.

The system is composed of three main components:

- **`MenuConfig`**: A centralized configuration system for defining the structure and content of the menus.
- **`MenuFactory`**: A factory for creating `Menu` objects based on the menu configurations and the user's context.
- **`TelegramMenuRenderer`**: A renderer that converts `Menu` objects into a format that can be displayed by Telegram.

## `MenuConfig` (`src/ui/menu_config.py`)

The `MenuConfig` system provides a centralized and declarative way to define the entire menu structure of the bot.

### `MenuConfig` and `MenuItemConfig`
These two dataclasses are the core of the menu definition.

- **`MenuConfig`**: Defines a menu, including its ID, title, description, and a list of `MenuItemConfig` objects.
- **`MenuItemConfig`**: Defines a single button in a menu, including its text, action, and any requirements for it to be visible or enabled.

### `MENU_DEFINITIONS`
This dictionary contains all the menu definitions for the bot. It provides a clear and readable way to define the menu hierarchy.

### Requirements and Conditions
The `MenuItemConfig` class includes several fields for defining requirements, such as `required_role`, `required_vip`, `required_level`, and `requires_besitos`. It also has `visible_condition` and `enabled_condition` fields, which allow for more complex, dynamic visibility and interactivity rules.

## `MenuFactory` (`src/ui/menu_factory.py`)

The `MenuFactory` is responsible for creating `Menu` objects based on the menu configurations and the user's context.

### `Menu` and `MenuItem`
These dataclasses represent the actual menu objects that are created by the factory. They are similar to the `MenuConfig` and `MenuItemConfig` classes, but they are designed to be used at runtime and include additional features like validation and navigation items.

### `MenuBuilder`
This abstract base class defines the interface for menu builders. There are several concrete implementations of this class, such as `MainMenuBuilder`, `NarrativeMenuBuilder`, and `AdminMenuBuilder`. Each builder is responsible for creating a specific type of menu.

### Role-Based Access Control
The menu factory implements role-based access control by checking the user's role against the `required_role` of each menu and menu item.

### Organic Menus
The `MainMenuBuilder` and the `build_organic_store_menu` method demonstrate the concept of "organic menus." This means that all options are shown to the user, but some are elegantly restricted based on the user's progress, VIP status, or other conditions.

## `TelegramMenuRenderer` (`src/ui/telegram_menu_renderer.py`)

The `TelegramMenuRenderer` is responsible for rendering the `Menu` objects created by the `MenuFactory` into a format that can be displayed by Telegram.

### `render_menu`
This method takes a `Menu` object and returns an `InlineKeyboardMarkup`. It iterates over the `MenuItem` objects in the menu and creates an `InlineKeyboardButton` for each one.

### Button Creation
The `_create_button_for_item` method creates the appropriate `InlineKeyboardButton` based on the `action_type` of the menu item. It handles different action types, such as callbacks, URLs, submenus, and commands.

### Lucien Voice Integration
The renderer also integrates with the `LucienVoiceProfile` to generate sophisticated and personalized text for the menu and its items.

### Message Sending and Editing
The `send_new_menu` and `edit_existing_menu` methods provide a convenient way to send a new menu or edit an existing one.

## Workflow

1.  **Menu Definition**: Menus are defined in a declarative way in `src/ui/menu_config.py`.
2.  **Menu Creation**: When a user requests a menu, the `MenuFactory` creates a `Menu` object based on the menu definition and the user's context.
3.  **Menu Rendering**: The `TelegramMenuRenderer` takes the `Menu` object and renders it into a Telegram `InlineKeyboardMarkup`.
4.  **Menu Display**: The rendered menu is then sent to the user as a message with an inline keyboard.

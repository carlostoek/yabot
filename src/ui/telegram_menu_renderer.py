"""
Telegram menu renderer for the YABOT system.
Converts Menu objects to Telegram inline keyboards and handles menu rendering.
"""

import sys
import logging
from typing import List, Optional, Dict, Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from src.ui.menu_factory import Menu, MenuItem, ActionType
from src.ui.lucien_voice_generator import LucienVoiceProfile, generate_lucien_response
from src.handlers.action_dispatcher import CallbackActionResult

logger = logging.getLogger(__name__)


class TelegramMenuRenderer:
    """Converts Menu objects to Telegram inline keyboards with edit message capability."""
    
    def __init__(self, bot: Bot):
        """
        Initialize the TelegramMenuRenderer.
        
        Args:
            bot: The aiogram Bot instance
        """
        self.bot = bot
        logger.info("TelegramMenuRenderer initialized.")

    def render_menu(self, menu: Menu) -> InlineKeyboardMarkup:
        """
        Convert a Menu object to a Telegram inline keyboard.
        
        Args:
            menu: The menu to render
            
        Returns:
            InlineKeyboardMarkup: The rendered keyboard
        """
        # Handle both Menu objects and dictionaries
        if hasattr(menu, 'items'):
            menu_items = menu.items
            menu_max_columns = getattr(menu, 'max_columns', 2)
        else:
            # Assume it's a dictionary
            menu_items = menu.get('items', [])
            menu_max_columns = menu.get('max_columns', 2)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        # Add menu items in rows
        row = []
        for i, item in enumerate(menu_items):
            button = self._create_button_for_item(item)
            if button:
                row.append(button)
                
                # Start a new row when we reach the max columns or end of items
                if len(row) >= menu_max_columns or i == len(menu_items) - 1:
                    keyboard.inline_keyboard.append(row)
                    row = []
        
        logger.debug(f"Rendered menu with {len(keyboard.inline_keyboard)} rows")
        return keyboard

    def _create_button_for_item(self, item: MenuItem) -> Optional[InlineKeyboardButton]:
        """
        Create a Telegram inline keyboard button for a menu item.
        
        Args:
            item: The menu item
            
        Returns:
            InlineKeyboardButton: The created button, or None if item should not be rendered
        """
        # Generate Lucien's voice text for the item if not already present
        if isinstance(item, dict):
            # Handle dictionary items
            if 'lucien_voice_text' not in item or not item['lucien_voice_text']:
                item['lucien_voice_text'] = self._generate_lucien_item_text(item)
        else:
            # Handle MenuItem objects
            if not hasattr(item, 'lucien_voice_text') or not item.lucien_voice_text:
                item.lucien_voice_text = self._generate_lucien_item_text(item)
        
        # Get item properties based on type
        if isinstance(item, dict):
            item_text = item.get('text', '')
            item_action_type = item.get('action_type', '')
            item_action_data = item.get('action_data', '')
        else:
            item_text = getattr(item, 'text', '')
            item_action_type = getattr(item, 'action_type', '')
            item_action_data = getattr(item, 'action_data', '')
        
        # Create button based on action type
        if str(item_action_type) == str(ActionType.CALLBACK):
            return InlineKeyboardButton(
                text=item_text,
                callback_data=item_action_data
            )
        elif str(item_action_type) == str(ActionType.URL):
            return InlineKeyboardButton(
                text=item_text,
                url=item_action_data
            )
        elif str(item_action_type) == str(ActionType.SUBMENU):
            return InlineKeyboardButton(
                text=item_text,
                callback_data=f"menu:{item_action_data}"
            )
        elif str(item_action_type) == str(ActionType.COMMAND):
            return InlineKeyboardButton(
                text=item_text,
                callback_data=f"command:{item_action_data}"
            )
        elif str(item_action_type) == str(ActionType.NARRATIVE_ACTION):
            return InlineKeyboardButton(
                text=item_text,
                callback_data=f"narrative:{item_action_data}"
            )
        elif str(item_action_type) == str(ActionType.ADMIN_ACTION):
            return InlineKeyboardButton(
                text=item_text,
                callback_data=f"admin:{item_action_data}"
            )
        
        # If we don't know how to handle this action type, log and skip
        logger.warning(f"Unknown action type '{item_action_type}' for menu item")
        return None

    def _generate_lucien_item_text(self, item: MenuItem) -> str:
        """
        Generate Lucien's sophisticated voice text for a menu item.
        
        Args:
            item: The menu item
            
        Returns:
            str: Lucien's text for the menu item
        """
        try:
            # Use Lucien's voice generator to create sophisticated text for the item
            lucien_profile = LucienVoiceProfile()
            
            # Generate context for Lucien based on item properties
            # Handle both MenuItem objects and dictionaries
            if hasattr(item, 'id'):
                item_id = item.id
                item_text = getattr(item, 'text', '')
                item_description = getattr(item, 'description', '')
                item_action_type = getattr(item, 'action_type', '')
                item_required_role = getattr(item, 'required_role', '')
                item_required_vip = getattr(item, 'required_vip', False)
                item_required_level = getattr(item, 'required_level', 0)
                item_requires_besitos = getattr(item, 'requires_besitos', 0)
            else:
                # Assume it's a dictionary
                item_id = item.get('id', '')
                item_text = item.get('text', '')
                item_description = item.get('description', '')
                item_action_type = item.get('action_type', '')
                item_required_role = item.get('required_role', '')
                item_required_vip = item.get('required_vip', False)
                item_required_level = item.get('required_level', 0)
                item_requires_besitos = item.get('requires_besitos', 0)
            
            context = {
                "item_id": item_id,
                "action_type": str(item_action_type),
                "required_role": str(item_required_role),
                "required_vip": item_required_vip,
                "required_level": item_required_level,
                "requires_besitos": item_requires_besitos
            }
            
            # Generate Lucien's response for the item
            item_prompt = f"Menu item: {item_text}. Description: {item_description}"
            lucien_text = generate_lucien_response(item_prompt, lucien_profile, context)
            
            return lucien_text
        except Exception as e:
            logger.warning(f"Failed to generate Lucien text for menu item '{item_id if 'item_id' in locals() else 'unknown'}': {e}")
            # Fallback to description or text
            if hasattr(item, 'description'):
                return getattr(item, 'description', '')
            elif hasattr(item, 'text'):
                return getattr(item, 'text', '')
            elif isinstance(item, dict):
                return item.get('description', item.get('text', ''))
            return "Menu item"

    def render_menu_response(
        self, 
        menu: Menu, 
        edit_message: bool = True,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Render a menu response suitable for sending to Telegram.
        
        Args:
            menu: The menu to render
            edit_message: Whether to edit an existing message or send a new one
            chat_id: The chat ID (required for editing)
            message_id: The message ID (required for editing)
            
        Returns:
            Dict[str, Any]: The response data
        """
        # Generate the keyboard
        keyboard = self.render_menu(menu)
        
        # Generate Lucien's voice text for the menu
        lucien_text = self._generate_lucien_menu_text(menu)
        
        # Combine header, description, and Lucien's text
        message_parts = []
        if menu.header_text:
            message_parts.append(menu.header_text)
        
        # Add Lucien's sophisticated introduction
        if lucien_text:
            message_parts.append(lucien_text)
        elif menu.description:
            message_parts.append(menu.description)
            
        # Add item descriptions for better context
        item_descriptions = []
        for item in menu.items:
            # Get item properties based on type (MenuItem object or dictionary)
            if isinstance(item, dict):
                item_description = item.get('description', '')
                item_text = item.get('text', '')
                item_action_type = item.get('action_type', '')
            else:
                item_description = getattr(item, 'description', '')
                item_text = getattr(item, 'text', '')
                item_action_type = getattr(item, 'action_type', '')
            
            if item_description and str(item_action_type) != str(ActionType.SUBMENU):
                # Only add descriptions for non-submenu items to avoid clutter
                item_descriptions.append(f"• {item_text}: {item_description}")
        
        if item_descriptions:
            message_parts.append("\n".join(item_descriptions))
        
        if menu.footer_text:
            message_parts.append(menu.footer_text)
            
        message_text = "\n\n".join(message_parts) if message_parts else "Menu"
        
        # Ensure message text is not empty
        if not message_text.strip():
            message_text = "Menu"
        
        # Create response data
        response_data = {
            "text": message_text,
            "reply_markup": keyboard
        }
        
        # Add edit message data if needed
        if edit_message and chat_id and message_id:
            response_data.update({
                "chat_id": chat_id,
                "message_id": message_id
            })
        
        logger.debug(f"Rendered menu response for '{menu.menu_id}' with {len(message_parts)} parts")
        return response_data

    def _generate_lucien_menu_text(self, menu: Menu) -> str:
        """
        Generate Lucien's sophisticated voice text for a menu.
        
        Args:
            menu: The menu
            
        Returns:
            str: Lucien's text for the menu
        """
        try:
            # Use Lucien's voice generator to create sophisticated text
            lucien_profile = LucienVoiceProfile()
            
            # Generate context for Lucien based on menu properties
            # Handle both Menu objects and dictionaries
            if hasattr(menu, 'menu_id'):
                menu_id = menu.menu_id
                menu_type = getattr(menu, 'menu_type', '')
                menu_items = getattr(menu, 'items', [])
                menu_title = getattr(menu, 'title', '')
            else:
                # Assume it's a dictionary
                menu_id = menu.get('menu_id', '')
                menu_type = menu.get('menu_type', '')
                menu_items = menu.get('items', [])
                menu_title = menu.get('title', '')
            
            # Calculate max role required
            max_role_required = None
            if menu_items:
                try:
                    if hasattr(menu_items[0], 'required_role'):
                        # MenuItem objects
                        max_role_required = max((item.required_role for item in menu_items), default=None, key=lambda x: x.value if hasattr(x, 'value') else 0)
                    elif isinstance(menu_items[0], dict):
                        # Dictionary items
                        max_role_required = "free_user"  # Default for dictionaries
                except Exception:
                    max_role_required = None
            
            context = {
                "menu_id": menu_id,
                "menu_type": str(menu_type),
                "item_count": len(menu_items),
                "has_vip_items": any(
                    getattr(item, 'required_vip', item.get('required_vip', False)) 
                    if not isinstance(item, dict) else item.get('required_vip', False)
                    for item in menu_items
                ) if menu_items else False,
                "max_role_required": str(max_role_required) if max_role_required else None
            }
            
            # Generate Lucien's response
            menu_prompt = f"Welcome to the {menu_title} menu."
            lucien_response = generate_lucien_response(
                lucien_profile,
                menu_prompt,
                context
            )
            lucien_text = lucien_response.response_text if lucien_response else menu_prompt
            
            return lucien_text
        except Exception as e:
            logger.warning(f"Failed to generate Lucien text for menu '{menu_id if 'menu_id' in locals() else 'unknown'}': {e}")
            # Fallback to description or title
            if hasattr(menu, 'description'):
                return getattr(menu, 'description', '')
            elif hasattr(menu, 'title'):
                return getattr(menu, 'title', '')
            elif isinstance(menu, dict):
                return menu.get('description', menu.get('title', ''))
            return "Menu"

    async def edit_existing_menu(
        self, 
        chat_id: int, 
        message_id: int, 
        new_menu: Menu
    ) -> bool:
        """
        Edit an existing menu message with a new menu.
        
        Args:
            chat_id: The chat ID
            message_id: The message ID
            new_menu: The new menu
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Render the menu response for editing
            response_data = self.render_menu_response(
                new_menu, 
                edit_message=True, 
                chat_id=chat_id, 
                message_id=message_id
            )
            
            # Edit the message
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=response_data["text"],
                reply_markup=response_data["reply_markup"]
            )
            
            logger.debug(f"Edited menu message {message_id} in chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to edit menu message {message_id} in chat {chat_id}: {e}")
            return False

    async def edit_menu_text_only(
        self, 
        chat_id: int, 
        message_id: int, 
        new_text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Edit only the text of an existing menu message.
        
        Args:
            chat_id: The chat ID
            message_id: The message ID
            new_text: The new text
            reply_markup: Optional new keyboard
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Edit only the message text
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=new_text,
                reply_markup=reply_markup
            )
            
            logger.debug(f"Edited menu text only for message {message_id} in chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to edit menu text only for message {message_id} in chat {chat_id}: {e}")
            return False

    async def edit_menu_keyboard_only(
        self, 
        chat_id: int, 
        message_id: int, 
        new_keyboard: InlineKeyboardMarkup
    ) -> bool:
        """
        Edit only the keyboard of an existing menu message.
        
        Args:
            chat_id: The chat ID
            message_id: The message ID
            new_keyboard: The new keyboard
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Edit only the message reply markup
            await self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=new_keyboard
            )
            
            logger.debug(f"Edited menu keyboard only for message {message_id} in chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to edit menu keyboard only for message {message_id} in chat {chat_id}: {e}")
            return False

    async def update_menu_partially(
        self, 
        chat_id: int, 
        message_id: int, 
        new_menu: Optional[Menu] = None,
        new_text: Optional[str] = None,
        new_keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Update an existing menu message partially.
        
        Args:
            chat_id: The chat ID
            message_id: The message ID
            new_menu: Optional new menu to render
            new_text: Optional new text
            new_keyboard: Optional new keyboard
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Determine what to update
            if new_menu:
                # Render the new menu
                response_data = self.render_menu_response(new_menu)
                text = response_data["text"]
                keyboard = response_data["reply_markup"]
            else:
                # Use provided text and keyboard or get from existing message
                text = new_text
                keyboard = new_keyboard
            
            # Edit the message with whatever we have
            if text is not None and keyboard is not None:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=keyboard
                )
            elif text is not None:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text
                )
            elif keyboard is not None:
                await self.bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard
                )
            else:
                # Nothing to update
                logger.warning(f"No updates provided for menu message {message_id} in chat {chat_id}")
                return False
            
            logger.debug(f"Partially updated menu message {message_id} in chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to partially update menu message {message_id} in chat {chat_id}: {e}")
            return False

    async def send_new_menu(
        self, 
        chat_id: int, 
        menu: Menu
    ) -> Optional[Message]:
        """
        Send a new menu message.
        
        Args:
            chat_id: The chat ID
            menu: The menu to send
            
        Returns:
            Optional[Message]: The sent message, or None if failed
        """
        try:
            # Render the menu response
            response_data = self.render_menu_response(menu)
            
            # Send the message
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=response_data["text"],
                reply_markup=response_data["reply_markup"]
            )
            
            logger.debug(f"Sent new menu message to chat {chat_id}")
            return message
        except Exception as e:
            logger.error(f"Failed to send new menu message to chat {chat_id}: {e}")
            return None
"""
Store (tienda) system for the YABOT gamification module.

This module provides the store functionality for users to browse and purchase items,
implementing requirement 2.7 from the modulos-atomicos specification.
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.database.mongodb import MongoDBHandler
from src.database.schemas.gamification import UserItem, ItemCategory, ItemRarity
from src.events.bus import EventBus
from src.events.models import BaseEvent
from src.utils.logger import get_logger


logger = get_logger(__name__)


class ItemPurchasedEvent(BaseEvent):
    """Event published when an item is purchased (requirement 2.7)."""
    user_id: str
    item_id: str
    item_name: str
    quantity: int
    price: int
    store_category: str
    balance_after: int
    timestamp: datetime


class StoreError(Exception):
    """Base exception for store operations."""
    pass


class ItemNotAvailableError(StoreError):
    """Exception raised when an item is not available for purchase."""
    pass


class InsufficientFundsError(StoreError):
    """Exception raised when user has insufficient besitos for purchase."""
    pass


class StoreItem:
    """Represents an item available for purchase in the store."""

    def __init__(self, item_id: str, name: str, description: str, price: int,
                 category: ItemCategory, rarity: ItemRarity = ItemRarity.COMMON,
                 emoji: Optional[str] = None, in_stock: bool = True,
                 max_quantity: int = 1, metadata: Optional[Dict[str, Any]] = None):
        self.item_id = item_id
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.rarity = rarity
        self.emoji = emoji or "📦"
        self.in_stock = in_stock
        self.max_quantity = max_quantity
        self.metadata = metadata or {}


class StoreMenu:
    """Represents a paginated store menu with inline keyboard markup."""

    def __init__(self, items: List[StoreItem], page: int = 0, items_per_page: int = 5,
                 category_filter: Optional[ItemCategory] = None):
        self.items = items
        self.page = page
        self.items_per_page = items_per_page
        self.category_filter = category_filter
        self.total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)

    def get_current_items(self) -> List[StoreItem]:
        """Get items for the current page."""
        start_idx = self.page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.items[start_idx:end_idx]

    def get_inline_keyboard(self) -> Dict[str, Any]:
        """Generate Telegram inline keyboard markup for the store menu."""
        keyboard = []

        # Item buttons
        current_items = self.get_current_items()
        for item in current_items:
            price_text = f"{item.price} 💋" if item.price > 0 else "Gratis"
            availability = "✅" if item.in_stock else "❌"
            button_text = f"{item.emoji} {item.name} - {price_text} {availability}"
            callback_data = f"store_buy_{item.item_id}"
            keyboard.append([{"text": button_text, "callback_data": callback_data}])

        # Navigation buttons
        nav_buttons = []

        # Previous page button
        if self.page > 0:
            nav_buttons.append({
                "text": "⬅️ Anterior",
                "callback_data": f"store_page_{self.page - 1}"
            })

        # Page indicator
        nav_buttons.append({
            "text": f"📄 {self.page + 1}/{self.total_pages}",
            "callback_data": "store_page_info"
        })

        # Next page button
        if self.page < self.total_pages - 1:
            nav_buttons.append({
                "text": "Siguiente ➡️",
                "callback_data": f"store_page_{self.page + 1}"
            })

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Category filter buttons
        category_buttons = []
        categories = [
            (ItemCategory.CONSUMABLE, "🍎 Consumibles"),
            (ItemCategory.EQUIPMENT, "⚔️ Equipo"),
            (ItemCategory.COSMETIC, "👗 Cosméticos"),
            (ItemCategory.COLLECTIBLE, "💎 Coleccionables"),
            (ItemCategory.SPECIAL, "✨ Especiales")
        ]

        for category, label in categories:
            selected = "✓" if self.category_filter == category else ""
            callback_data = f"store_filter_{category.value}"
            category_buttons.append({
                "text": f"{label} {selected}",
                "callback_data": callback_data
            })

        # Split category buttons into rows of 2
        for i in range(0, len(category_buttons), 2):
            keyboard.append(category_buttons[i:i+2])

        # Additional action buttons
        action_buttons = [
            {"text": "🔄 Ver Todo", "callback_data": "store_filter_all"},
            {"text": "💰 Mi Cartera", "callback_data": "store_wallet"},
            {"text": "🎒 Mi Mochila", "callback_data": "store_inventory"}
        ]

        # Split action buttons into rows of 2
        for i in range(0, len(action_buttons), 2):
            keyboard.append(action_buttons[i:i+2])

        # Close button
        keyboard.append([{"text": "❌ Cerrar", "callback_data": "store_close"}])

        return {"inline_keyboard": keyboard}


class Store:
    """Store (tienda) system for browsing and purchasing items.

    Responsibilities:
    - Display inline menus for store browsing (requirement 2.7)
    - Process item purchases with besitos wallet integration
    - Publish item_purchased events when items are bought
    - Support item categories and pagination for store browsing
    - Handle purchase validation (sufficient funds, item availability)
    - Follow existing YABOT Telegram inline keyboard patterns
    - Integrate with the item manager for inventory updates
    - Include proper error handling and user feedback
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus):
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.items: Collection = mongodb_handler.get_items_collection()
        self.user_items: Collection = mongodb_handler.get_user_items_collection()
        self.users: Collection = mongodb_handler.get_users_collection()

    async def initialize(self) -> bool:
        """Initialize the store and subscribe to events.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Subscribe to events that might affect the store
            # For example, when a user registers, we might want to give them starter items
            # Or when certain achievements are unlocked, we might want to offer special items
            
            logger.info("Store initialized and subscribed to events")
            return True
            
        except Exception as e:
            logger.error("Error initializing store: %s", str(e))
            return False

    # === STORE BROWSING ===

    async def get_store_menu(self, page: int = 0, category_filter: Optional[ItemCategory] = None,
                           items_per_page: int = 5) -> StoreMenu:
        """Get paginated store menu with optional category filtering.

        Args:
            page (int): Page number (0-indexed)
            category_filter (Optional[ItemCategory]): Filter by item category
            items_per_page (int): Number of items per page

        Returns:
            StoreMenu: Store menu with items and navigation

        Raises:
            StoreError: If there's an error fetching store items
        """
        try:
            # Build query filter
            query = {"available_in_store": True}
            if category_filter:
                query["category"] = category_filter.value

            # Fetch items from database
            cursor = self.items.find(query, {"_id": 0}).sort("price", 1)
            items_data = list(cursor)

            # Convert to StoreItem objects
            store_items = []
            for item_data in items_data:
                store_item = StoreItem(
                    item_id=item_data["item_id"],
                    name=item_data["name"],
                    description=item_data.get("description", ""),
                    price=item_data.get("price", 0),
                    category=ItemCategory(item_data["category"]),
                    rarity=ItemRarity(item_data.get("rarity", "common")),
                    emoji=item_data.get("emoji"),
                    in_stock=item_data.get("in_stock", True),
                    max_quantity=item_data.get("max_quantity", 1),
                    metadata=item_data.get("metadata", {})
                )
                store_items.append(store_item)

            # Create and return store menu
            return StoreMenu(
                items=store_items,
                page=page,
                items_per_page=items_per_page,
                category_filter=category_filter
            )

        except PyMongoError as e:
            logger.error("Error fetching store items: %s", str(e))
            raise StoreError(f"Error al cargar la tienda: {str(e)}")

    async def get_item_details(self, item_id: str) -> Optional[StoreItem]:
        """Get detailed information about a specific store item.

        Args:
            item_id (str): Item identifier

        Returns:
            Optional[StoreItem]: Item details or None if not found
        """
        try:
            item_data = self.items.find_one({
                "item_id": item_id,
                "available_in_store": True
            }, {"_id": 0})

            if not item_data:
                return None

            return StoreItem(
                item_id=item_data["item_id"],
                name=item_data["name"],
                description=item_data.get("description", ""),
                price=item_data.get("price", 0),
                category=ItemCategory(item_data["category"]),
                rarity=ItemRarity(item_data.get("rarity", "common")),
                emoji=item_data.get("emoji"),
                in_stock=item_data.get("in_stock", True),
                max_quantity=item_data.get("max_quantity", 1),
                metadata=item_data.get("metadata", {})
            )

        except PyMongoError as e:
            logger.error("Error fetching item %s: %s", item_id, str(e))
            return None

    # === PURCHASE OPERATIONS ===

    async def purchase_item(self, user_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Purchase an item from the store.

        Args:
            user_id (str): User ID making the purchase
            item_id (str): Item ID to purchase
            quantity (int): Quantity to purchase

        Returns:
            Dict[str, Any]: Purchase result with transaction details

        Raises:
            ItemNotAvailableError: If item is not available
            InsufficientFundsError: If user has insufficient funds
            StoreError: If purchase fails
        """
        try:
            # Get item details
            item = await self.get_item_details(item_id)
            if not item:
                raise ItemNotAvailableError(f"El artículo '{item_id}' no está disponible")

            if not item.in_stock:
                raise ItemNotAvailableError(f"El artículo '{item.name}' está agotado")

            if quantity <= 0 or quantity > item.max_quantity:
                raise ItemNotAvailableError(
                    f"Cantidad inválida. Máximo permitido: {item.max_quantity}"
                )

            # Calculate total cost
            total_cost = item.price * quantity

            # Get user balance
            user_data = self.users.find_one({"user_id": user_id}, {"besitos_balance": 1})
            if not user_data:
                raise StoreError("Usuario no encontrado")

            current_balance = user_data.get("besitos_balance", 0)

            # Check if user has sufficient funds
            if current_balance < total_cost:
                raise InsufficientFundsError(
                    f"Fondos insuficientes. Necesitas {total_cost} 💋, tienes {current_balance} 💋"
                )

            # Start transaction session for atomic operation
            with self.mongodb_handler.client.start_session() as session:
                with session.start_transaction():
                    # Deduct besitos from user balance
                    new_balance = current_balance - total_cost
                    self.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"besitos_balance": new_balance}},
                        session=session
                    )

                    # Add item to user inventory
                    user_item_id = str(uuid.uuid4())
                    user_item = UserItem(
                        user_item_id=user_item_id,
                        user_id=user_id,
                        item_id=item.item_id,
                        name=item.name,
                        description=item.description,
                        category=item.category,
                        rarity=item.rarity,
                        quantity=quantity,
                        value=item.price,
                        emoji=item.emoji,
                        metadata=item.metadata
                    )

                    # Check if user already has this item
                    existing_item = self.user_items.find_one({
                        "user_id": user_id,
                        "item_id": item.item_id
                    }, session=session)

                    if existing_item:
                        # Update quantity of existing item
                        self.user_items.update_one(
                            {"user_id": user_id, "item_id": item.item_id},
                            {
                                "$inc": {"quantity": quantity},
                                "$set": {"updated_at": datetime.utcnow()}
                            },
                            session=session
                        )
                    else:
                        # Insert new item
                        self.user_items.insert_one(
                            user_item.model_dump(),
                            session=session
                        )

            # Create purchase result
            purchase_result = {
                "success": True,
                "transaction_id": str(uuid.uuid4()),
                "item_id": item.item_id,
                "item_name": item.name,
                "quantity": quantity,
                "total_cost": total_cost,
                "balance_before": current_balance,
                "balance_after": new_balance,
                "purchased_at": datetime.utcnow()
            }

            # Publish item_purchased event
            await self._publish_item_purchased_event(
                user_id=user_id,
                item_id=item.item_id,
                item_name=item.name,
                quantity=quantity,
                price=total_cost,
                store_category=item.category.value,
                balance_after=new_balance
            )

            logger.info(
                "User %s purchased %dx %s for %d besitos",
                user_id, quantity, item.name, total_cost
            )

            return purchase_result

        except (ItemNotAvailableError, InsufficientFundsError):
            # Re-raise these specific errors
            raise
        except PyMongoError as e:
            logger.error("Database error during purchase: %s", str(e))
            raise StoreError(f"Error en la compra: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error during purchase: %s", str(e))
            raise StoreError(f"Error inesperado en la compra: {str(e)}")

    async def _publish_item_purchased_event(self, user_id: str, item_id: str, item_name: str,
                                          quantity: int, price: int, store_category: str,
                                          balance_after: int):
        """Publish item_purchased event to the event bus.

        Args:
            user_id (str): User who made the purchase
            item_id (str): Item that was purchased
            item_name (str): Name of the purchased item
            quantity (int): Quantity purchased
            price (int): Total price paid
            store_category (str): Category of the item
            balance_after (int): User's balance after purchase
        """
        try:
            from src.events.models import create_event
            
            event = create_event(
                "item_purchased",
                user_id=user_id,
                item_id=item_id,
                item_name=item_name,
                quantity=quantity,
                price=price,
                store_category=store_category,
                balance_after=balance_after
            )

            await self.event_bus.publish("item_purchased", event.dict())
            logger.info("Published item_purchased event for user %s, item %s", user_id, item_id)

        except Exception as e:
            logger.error("Error publishing item_purchased event: %s", str(e))

    # === USER INTERFACE METHODS ===

    def format_store_message(self, menu: StoreMenu, user_balance: int) -> str:
        """Format the store display message.

        Args:
            menu (StoreMenu): Store menu to display
            user_balance (int): User's current besitos balance

        Returns:
            str: Formatted store message
        """
        message_parts = [
            "🏪 <b>Tienda YABOT</b>",
            f"💰 Tu saldo: <b>{user_balance} 💋</b>",
            ""
        ]

        # Category filter info
        if menu.category_filter:
            category_names = {
                ItemCategory.CONSUMABLE: "Consumibles",
                ItemCategory.EQUIPMENT: "Equipo",
                ItemCategory.COSMETIC: "Cosméticos",
                ItemCategory.COLLECTIBLE: "Coleccionables",
                ItemCategory.SPECIAL: "Especiales"
            }
            filter_name = category_names.get(menu.category_filter, menu.category_filter.value)
            message_parts.append(f"📂 Categoría: <b>{filter_name}</b>")
            message_parts.append("")

        # Items
        current_items = menu.get_current_items()
        if not current_items:
            message_parts.append("😢 No hay artículos disponibles en esta categoría.")
        else:
            message_parts.append("🛍️ <b>Artículos disponibles:</b>")

            for i, item in enumerate(current_items, 1):
                price_text = f"{item.price} 💋" if item.price > 0 else "¡Gratis!"
                availability = "✅ Disponible" if item.in_stock else "❌ Agotado"
                rarity_emoji = {
                    ItemRarity.COMMON: "⚪",
                    ItemRarity.UNCOMMON: "🟢",
                    ItemRarity.RARE: "🔵",
                    ItemRarity.EPIC: "🟣",
                    ItemRarity.LEGENDARY: "🟡"
                }.get(item.rarity, "⚪")

                item_text = (
                    f"{i}. {item.emoji} <b>{item.name}</b> {rarity_emoji}\n"
                    f"   💰 Precio: <b>{price_text}</b>\n"
                    f"   📊 Estado: {availability}\n"
                    f"   📝 {item.description}"
                )
                message_parts.append(item_text)

        # Footer
        message_parts.extend([
            "",
            f"📄 Página {menu.page + 1} de {menu.total_pages}",
            "👆 Usa los botones para navegar y comprar"
        ])

        return "\n".join(message_parts)

    def format_purchase_confirmation(self, purchase_result: Dict[str, Any]) -> str:
        """Format purchase confirmation message.

        Args:
            purchase_result (Dict[str, Any]): Purchase result data

        Returns:
            str: Formatted confirmation message
        """
        return (
            f"✅ <b>¡Compra realizada!</b>\n\n"
            f"🎁 Artículo: <b>{purchase_result['item_name']}</b>\n"
            f"📦 Cantidad: <b>{purchase_result['quantity']}</b>\n"
            f"💰 Costo total: <b>{purchase_result['total_cost']} 💋</b>\n"
            f"💳 Saldo anterior: {purchase_result['balance_before']} 💋\n"
            f"💳 Saldo actual: <b>{purchase_result['balance_after']} 💋</b>\n\n"
            f"🎒 El artículo ha sido añadido a tu mochila.\n"
            f"🕐 {purchase_result['purchased_at'].strftime('%d/%m/%Y %H:%M')}"
        )

    def format_error_message(self, error: Exception) -> str:
        """Format error message for user display.

        Args:
            error (Exception): Error that occurred

        Returns:
            str: Formatted error message in Spanish
        """
        if isinstance(error, ItemNotAvailableError):
            return f"❌ <b>Artículo no disponible</b>\n\n{str(error)}"
        elif isinstance(error, InsufficientFundsError):
            return f"💸 <b>Fondos insuficientes</b>\n\n{str(error)}"
        elif isinstance(error, StoreError):
            return f"🚫 <b>Error en la tienda</b>\n\n{str(error)}"
        else:
            return "❌ <b>Error inesperado</b>\n\nPor favor, inténtalo de nuevo más tarde."

    # === UTILITY METHODS ===

    async def get_user_balance(self, user_id: str) -> int:
        """Get user's current besitos balance.

        Args:
            user_id (str): User identifier

        Returns:
            int: User's besitos balance
        """
        try:
            user_data = self.users.find_one({"user_id": user_id}, {"besitos_balance": 1})
            return user_data.get("besitos_balance", 0) if user_data else 0
        except PyMongoError as e:
            logger.error("Error fetching user balance: %s", str(e))
            return 0

    async def is_item_available(self, item_id: str) -> bool:
        """Check if an item is available for purchase.

        Args:
            item_id (str): Item identifier

        Returns:
            bool: True if item is available, False otherwise
        """
        try:
            item = self.items.find_one({
                "item_id": item_id,
                "available_in_store": True,
                "in_stock": True
            })
            return item is not None
        except PyMongoError as e:
            logger.error("Error checking item availability: %s", str(e))
            return False
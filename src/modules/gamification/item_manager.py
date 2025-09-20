from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import uuid

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.database.mongodb import MongoDBHandler
from src.database.schemas.gamification import UserItem, ItemCategory, ItemRarity
from src.events.bus import EventBus
from src.utils.logger import get_logger


logger = get_logger(__name__)


class ItemManager:
    """MongoDB-backed user mochila (inventory) manager.

    Responsibilities:
    - CRUD operations for user inventory in `user_items` collection (requirement 2.6)
    - Item combination and usage logic
    - Cross-module API endpoints for inventory access (requirement 7.1)
    - Publish domain events when items are added/removed/used
    - Support item metadata, effects, and equipped status
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus):
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.items: Collection = mongodb_handler.get_items_collection()
        self.user_items: Collection = mongodb_handler.get_user_items_collection()

    # === CATALOG OPERATIONS ===

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item definition from catalog.

        Args:
            item_id (str): Item identifier

        Returns:
            Optional[Dict]: Item definition or None if not found
        """
        try:
            return self.items.find_one({"item_id": item_id}, {"_id": 0})
        except PyMongoError as e:
            logger.error("Error fetching item %s: %s", item_id, str(e))
            return None

    def list_items(self, category: Optional[str] = None, rarity: Optional[str] = None) -> List[Dict[str, Any]]:
        """List items from catalog with optional filters.

        Args:
            category (Optional[str]): Filter by item category
            rarity (Optional[str]): Filter by item rarity

        Returns:
            List[Dict]: List of item definitions
        """
        query = {}
        if category:
            query["category"] = category
        if rarity:
            query["rarity"] = rarity

        try:
            return list(self.items.find(query, {"_id": 0}))
        except PyMongoError as e:
            logger.error("Error listing items: %s", str(e))
            return []

    # === USER INVENTORY (MOCHILA) OPERATIONS ===

    def get_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's complete inventory (mochila).

        Args:
            user_id (str): User identifier

        Returns:
            List[Dict]: User's inventory items
        """
        try:
            cursor = self.user_items.find({"user_id": user_id}, {"_id": 0})
            return list(cursor)
        except PyMongoError as e:
            logger.error("Error fetching inventory for user %s: %s", user_id, str(e))
            return []

    def add_item(self, user_id: str, item_id: str, quantity: int = 1,
                 source: str = "manual", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add item to user's inventory.

        Args:
            user_id (str): User identifier
            item_id (str): Item identifier
            quantity (int): Quantity to add (default: 1)
            source (str): Source of the item addition
            metadata (Optional[Dict]): Additional metadata

        Returns:
            bool: True if successful, False otherwise
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        try:
            # Validate item exists in catalog
            item_def = self.get_item(item_id)
            if not item_def:
                raise ValueError(f"Unknown item_id: {item_id}")

            now = datetime.now(timezone.utc)

            # Check if user already has this item
            existing_item = self.user_items.find_one({"user_id": user_id, "item_id": item_id})

            if existing_item:
                # Update existing item quantity
                max_stack = existing_item.get("max_stack", 1)
                current_qty = existing_item.get("quantity", 0)

                if current_qty + quantity > max_stack:
                    raise ValueError(f"Cannot exceed max stack size of {max_stack}")

                result = self.user_items.update_one(
                    {"user_id": user_id, "item_id": item_id},
                    {
                        "$inc": {"quantity": quantity},
                        "$set": {"updated_at": now}
                    }
                )
            else:
                # Create new inventory item using UserItem schema
                user_item_data = {
                    "user_item_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "item_id": item_id,
                    "name": item_def.get("name", "Unknown Item"),
                    "description": item_def.get("description", ""),
                    "category": item_def.get("category", ItemCategory.COLLECTIBLE),
                    "rarity": item_def.get("rarity", ItemRarity.COMMON),
                    "quantity": quantity,
                    "max_stack": item_def.get("max_stack", 1),
                    "value": item_def.get("value", 0),
                    "emoji": item_def.get("emoji"),
                    "effects": item_def.get("effects", {}),
                    "equipped": False,
                    "tradeable": item_def.get("tradeable", True),
                    "metadata": metadata or {},
                    "acquired_at": now,
                    "updated_at": now
                }

                result = self.user_items.insert_one(user_item_data)

            # Publish event
            event = {
                "type": "item_added",
                "user_id": user_id,
                "item_id": item_id,
                "quantity": quantity,
                "source": source,
                "timestamp": now
            }

            try:
                self.event_bus.publish("gamification.item_added", event)
            except Exception as e:
                logger.warning("Failed to publish item_added event: %s", str(e))

            logger.info("Added %d x %s to user %s inventory", quantity, item_id, user_id)
            return True

        except (PyMongoError, ValueError) as e:
            logger.error("Error adding item to user %s: %s", user_id, str(e))
            return False

    def remove_item(self, user_id: str, item_id: str, quantity: int = 1,
                    reason: str = "used") -> bool:
        """Remove item from user's inventory.

        Args:
            user_id (str): User identifier
            item_id (str): Item identifier
            quantity (int): Quantity to remove (default: 1)
            reason (str): Reason for removal

        Returns:
            bool: True if successful, False otherwise
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        try:
            existing_item = self.user_items.find_one({"user_id": user_id, "item_id": item_id})
            if not existing_item:
                raise ValueError(f"User {user_id} does not have item {item_id}")

            current_qty = existing_item.get("quantity", 0)
            if current_qty < quantity:
                raise ValueError(f"Insufficient quantity. Has {current_qty}, requested {quantity}")

            new_qty = current_qty - quantity
            now = datetime.now(timezone.utc)

            if new_qty == 0:
                # Remove item completely
                result = self.user_items.delete_one({"user_id": user_id, "item_id": item_id})
            else:
                # Update quantity
                result = self.user_items.update_one(
                    {"user_id": user_id, "item_id": item_id},
                    {
                        "$set": {
                            "quantity": new_qty,
                            "updated_at": now
                        }
                    }
                )

            # Publish event
            event = {
                "type": "item_removed",
                "user_id": user_id,
                "item_id": item_id,
                "quantity": quantity,
                "reason": reason,
                "timestamp": now
            }

            try:
                self.event_bus.publish("gamification.item_removed", event)
            except Exception as e:
                logger.warning("Failed to publish item_removed event: %s", str(e))

            logger.info("Removed %d x %s from user %s inventory", quantity, item_id, user_id)
            return True

        except (PyMongoError, ValueError) as e:
            logger.error("Error removing item from user %s: %s", user_id, str(e))
            return False

    def get_item_quantity(self, user_id: str, item_id: str) -> int:
        """Get quantity of specific item in user's inventory.

        Args:
            user_id (str): User identifier
            item_id (str): Item identifier

        Returns:
            int: Quantity owned (0 if not found)
        """
        try:
            item = self.user_items.find_one(
                {"user_id": user_id, "item_id": item_id},
                {"quantity": 1}
            )
            return item.get("quantity", 0) if item else 0
        except PyMongoError as e:
            logger.error("Error getting item quantity for user %s: %s", user_id, str(e))
            return 0

    def equip_item(self, user_id: str, item_id: str) -> bool:
        """Equip an item for the user.

        Args:
            user_id (str): User identifier
            item_id (str): Item identifier

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if user has the item
            item = self.user_items.find_one({"user_id": user_id, "item_id": item_id})
            if not item:
                raise ValueError(f"User {user_id} does not have item {item_id}")

            # Check if item is equippable
            if item.get("category") not in [ItemCategory.EQUIPMENT, ItemCategory.COSMETIC]:
                raise ValueError(f"Item {item_id} is not equippable")

            # Unequip other items of same category for this user
            self.user_items.update_many(
                {
                    "user_id": user_id,
                    "category": item.get("category"),
                    "equipped": True
                },
                {"$set": {"equipped": False, "updated_at": datetime.now(timezone.utc)}}
            )

            # Equip the item
            result = self.user_items.update_one(
                {"user_id": user_id, "item_id": item_id},
                {
                    "$set": {
                        "equipped": True,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            # Publish event
            event = {
                "type": "item_equipped",
                "user_id": user_id,
                "item_id": item_id,
                "timestamp": datetime.now(timezone.utc)
            }

            try:
                self.event_bus.publish("gamification.item_equipped", event)
            except Exception as e:
                logger.warning("Failed to publish item_equipped event: %s", str(e))

            logger.info("User %s equipped item %s", user_id, item_id)
            return True

        except (PyMongoError, ValueError) as e:
            logger.error("Error equipping item for user %s: %s", user_id, str(e))
            return False

    def unequip_item(self, user_id: str, item_id: str) -> bool:
        """Unequip an item for the user.

        Args:
            user_id (str): User identifier
            item_id (str): Item identifier

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.user_items.update_one(
                {"user_id": user_id, "item_id": item_id, "equipped": True},
                {
                    "$set": {
                        "equipped": False,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count == 0:
                raise ValueError(f"Item {item_id} is not equipped by user {user_id}")

            # Publish event
            event = {
                "type": "item_unequipped",
                "user_id": user_id,
                "item_id": item_id,
                "timestamp": datetime.now(timezone.utc)
            }

            try:
                self.event_bus.publish("gamification.item_unequipped", event)
            except Exception as e:
                logger.warning("Failed to publish item_unequipped event: %s", str(e))

            logger.info("User %s unequipped item %s", user_id, item_id)
            return True

        except (PyMongoError, ValueError) as e:
            logger.error("Error unequipping item for user %s: %s", user_id, str(e))
            return False

    def get_equipped_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all equipped items for a user.

        Args:
            user_id (str): User identifier

        Returns:
            List[Dict]: List of equipped items
        """
        try:
            cursor = self.user_items.find(
                {"user_id": user_id, "equipped": True},
                {"_id": 0}
            )
            return list(cursor)
        except PyMongoError as e:
            logger.error("Error fetching equipped items for user %s: %s", user_id, str(e))
            return []

    def use_item(self, user_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Use a consumable item and apply its effects.

        Args:
            user_id (str): User identifier
            item_id (str): Item identifier
            quantity (int): Quantity to use

        Returns:
            Dict: Result of item usage including effects applied
        """
        try:
            # Check if user has the item
            item = self.user_items.find_one({"user_id": user_id, "item_id": item_id})
            if not item:
                raise ValueError(f"User {user_id} does not have item {item_id}")

            current_qty = item.get("quantity", 0)
            if current_qty < quantity:
                raise ValueError(f"Insufficient quantity. Has {current_qty}, requested {quantity}")

            # Check if item is consumable
            if item.get("category") != ItemCategory.CONSUMABLE:
                raise ValueError(f"Item {item_id} is not consumable")

            # Apply effects (this would integrate with other systems)
            effects_applied = item.get("effects", {})

            # Remove the used items
            if not self.remove_item(user_id, item_id, quantity, "used"):
                raise ValueError("Failed to remove used items")

            # Publish usage event
            event = {
                "type": "item_used",
                "user_id": user_id,
                "item_id": item_id,
                "quantity": quantity,
                "effects": effects_applied,
                "timestamp": datetime.now(timezone.utc)
            }

            try:
                self.event_bus.publish("gamification.item_used", event)
            except Exception as e:
                logger.warning("Failed to publish item_used event: %s", str(e))

            logger.info("User %s used %d x %s", user_id, quantity, item_id)

            return {
                "success": True,
                "effects_applied": effects_applied,
                "quantity_used": quantity
            }

        except (PyMongoError, ValueError) as e:
            logger.error("Error using item for user %s: %s", user_id, str(e))
            return {
                "success": False,
                "error": str(e)
            }

    def combine_items(self, user_id: str, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Combine items according to a recipe to create new items.

        Args:
            user_id (str): User identifier
            recipe (Dict): Recipe containing required items and result

        Returns:
            Dict: Result of combination attempt
        """
        try:
            required_items = recipe.get("required_items", {})
            result_item = recipe.get("result_item")
            result_quantity = recipe.get("result_quantity", 1)

            # Check if user has all required items
            for item_id, required_qty in required_items.items():
                user_qty = self.get_item_quantity(user_id, item_id)
                if user_qty < required_qty:
                    raise ValueError(f"Insufficient {item_id}: has {user_qty}, needs {required_qty}")

            # Remove required items
            for item_id, required_qty in required_items.items():
                if not self.remove_item(user_id, item_id, required_qty, "combined"):
                    raise ValueError(f"Failed to remove {item_id} for combination")

            # Add result item
            if not self.add_item(user_id, result_item, result_quantity, "combination"):
                # Rollback: add back the removed items
                for item_id, required_qty in required_items.items():
                    self.add_item(user_id, item_id, required_qty, "rollback")
                raise ValueError("Failed to add result item")

            # Publish combination event
            event = {
                "type": "items_combined",
                "user_id": user_id,
                "recipe": recipe,
                "result_item": result_item,
                "result_quantity": result_quantity,
                "timestamp": datetime.now(timezone.utc)
            }

            try:
                self.event_bus.publish("gamification.items_combined", event)
            except Exception as e:
                logger.warning("Failed to publish items_combined event: %s", str(e))

            logger.info("User %s combined items to create %d x %s", user_id, result_quantity, result_item)

            return {
                "success": True,
                "result_item": result_item,
                "result_quantity": result_quantity
            }

        except (PyMongoError, ValueError) as e:
            logger.error("Error combining items for user %s: %s", user_id, str(e))
            return {
                "success": False,
                "error": str(e)
            }

    def get_inventory_by_category(self, user_id: str, category: ItemCategory) -> List[Dict[str, Any]]:
        """Get user's inventory filtered by category.

        Args:
            user_id (str): User identifier
            category (ItemCategory): Item category to filter by

        Returns:
            List[Dict]: Filtered inventory items
        """
        try:
            cursor = self.user_items.find(
                {"user_id": user_id, "category": category},
                {"_id": 0}
            )
            return list(cursor)
        except PyMongoError as e:
            logger.error("Error fetching inventory by category for user %s: %s", user_id, str(e))
            return []

    def get_inventory_value(self, user_id: str) -> int:
        """Calculate total value of user's inventory.

        Args:
            user_id (str): User identifier

        Returns:
            int: Total inventory value in besitos
        """
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": None,
                    "total_value": {
                        "$sum": {"$multiply": ["$quantity", "$value"]}
                    }
                }}
            ]

            result = list(self.user_items.aggregate(pipeline))
            return result[0]["total_value"] if result else 0

        except PyMongoError as e:
            logger.error("Error calculating inventory value for user %s: %s", user_id, str(e))
            return 0

    # === LEGACY COMPATIBILITY METHODS ===

    def get_user_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        """Legacy method for backward compatibility."""
        return self.get_inventory(user_id)

    def add_item_to_user(self, user_id: str, item_id: str, qty: int = 1, source: str = "manual") -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        success = self.add_item(user_id, item_id, qty, source)
        return {
            "matched": 1 if success else 0,
            "modified": 1 if success else 0,
            "upserted": None
        }

    def remove_item_from_user(self, user_id: str, item_id: str, qty: int = 1, reason: str = "use") -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        success = self.remove_item(user_id, item_id, qty, reason)
        return {
            "deleted": 1 if success else 0,
            "modified": 1 if success else 0
        }

    def set_user_item(self, user_id: str, item_id: str, qty: int) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        try:
            if qty <= 0:
                success = self.remove_item(user_id, item_id, self.get_item_quantity(user_id, item_id), "set")
                return {"deleted": 1 if success else 0, "modified": 0}
            else:
                current_qty = self.get_item_quantity(user_id, item_id)
                if current_qty == 0:
                    success = self.add_item(user_id, item_id, qty, "set")
                elif current_qty < qty:
                    success = self.add_item(user_id, item_id, qty - current_qty, "set")
                else:
                    success = self.remove_item(user_id, item_id, current_qty - qty, "set")
                return {"deleted": 0, "modified": 1 if success else 0}
        except Exception as e:
            logger.error("Error setting user item: %s", str(e))
            return {"deleted": 0, "modified": 0}


async def create_item_manager(mongodb_handler: MongoDBHandler, event_bus: EventBus) -> ItemManager:
    """Factory for dependency injection consistency with other modules."""
    return ItemManager(mongodb_handler, event_bus)


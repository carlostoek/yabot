"""
Item Manager (Mochila) - User Inventory System

This module implements the item inventory system (mochila) for the YABOT gamification module
with item management, CRUD operations, and cross-module API access.
Implements requirements 2.6, 7.1: inventory management and cross-module API access.

The item manager handles:
- User inventory management (mochila)
- Item CRUD operations
- Cross-module API access to inventory
- Item combination and usage logic
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
import uuid

from motor.motor_asyncio import AsyncIOMotorClient
from src.events.models import BaseEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger
from src.database.schemas.gamification import ItemMongoSchema, UserInventoryMongoSchema


class ItemType(str, Enum):
    """
    Enumeration for item types
    """
    HINT = "pista"  # Hint/puzzle piece for narrative
    COLLECTIBLE = "coleccionable"  # Collectible items
    TOOL = "herramienta"  # Tools for special actions
    GIFT = "regalo"  # Gifts from daily rewards
    NARRATIVE = "narrativo"  # Items that unlock narrative content
    ACHIEVEMENT = "logro"  # Achievement-related items
    CONSUMABLE = "consumible"  # Items that can be used once


class ItemRarity(str, Enum):
    """
    Enumeration for item rarities
    """
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class InventoryItem(BaseModel):
    """
    Represents an item in a user's inventory
    """
    item_id: str
    quantity: int = 1
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Item(BaseModel):
    """
    Item data model representing a specific item type in the system
    """
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    item_type: ItemType
    rarity: ItemRarity = ItemRarity.COMMON
    value: int = 0  # Used for besitos value or trade equivalent
    max_quantity: Optional[int] = None  # None for unlimited, specific number for limited items
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ItemManager:
    """
    Item manager (mochila) implementation with inventory management
    and cross-module API access functionality.

    Implements requirements 2.6, 7.1:
    - 2.6: User inventory management (mochila)
    - 7.1: Cross-module API access to inventory data
    """

    def __init__(self, db_client: AsyncIOMotorClient, event_bus: EventBus):
        """
        Initialize the item manager with database and event bus connections

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing item events
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)

        # Collection references
        self.items_collection = self.db.items
        self.user_inventory_collection = self.db.user_inventory
        self.users_collection = self.db.users

    async def create_item_template(self, name: str, description: str, 
                                 item_type: ItemType, rarity: ItemRarity = ItemRarity.COMMON,
                                 value: int = 0, max_quantity: Optional[int] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> Optional[Item]:
        """
        Create a new item template in the system

        Args:
            name: Item name
            description: Item description
            item_type: Type of item
            rarity: Item rarity
            value: Item value in besitos or other metrics
            max_quantity: Maximum quantity allowed per user (None for unlimited)
            metadata: Additional metadata for the item

        Returns:
            Item object if successfully created, None otherwise
        """
        try:
            # Check if item already exists by name
            existing_item = await self.items_collection.find_one({"name": name})
            if existing_item:
                self.logger.warning(
                    "Item template already exists",
                    name=name,
                    item_id=existing_item["item_id"]
                )
                return None

            # Create item object
            item = Item(
                name=name,
                description=description,
                item_type=item_type,
                rarity=rarity,
                value=value,
                max_quantity=max_quantity,
                metadata=metadata or {}
            )

            # Insert item document
            item_doc = item.dict()
            result = await self.items_collection.insert_one(item_doc)

            if result.inserted_id:
                self.logger.info(
                    "Item template created successfully",
                    item_id=item.item_id,
                    name=name,
                    item_type=item_type.value
                )

                # Publish item created event
                await self._publish_item_event(
                    item_id=item.item_id,
                    event_type="item_template_created",
                    item_data=item.dict()
                )

                return item
            else:
                self.logger.error(
                    "Failed to create item template - database insert failed",
                    name=name,
                    item_type=item_type.value
                )
                return None

        except Exception as e:
            self.logger.error(
                "Error creating item template",
                name=name,
                item_type=item_type.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def get_item_template(self, item_id: str) -> Optional[Item]:
        """
        Get an item template by its ID

        Args:
            item_id: Item identifier

        Returns:
            Item object if found, None otherwise
        """
        try:
            item_doc = await self.items_collection.find_one({"item_id": item_id})
            if item_doc:
                item = Item(**item_doc)
                self.logger.debug("Item template found", item_id=item_id)
                return item
            else:
                self.logger.debug("Item template not found", item_id=item_id)
                return None

        except Exception as e:
            self.logger.error(
                "Error retrieving item template",
                item_id=item_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def get_item_by_name(self, name: str) -> Optional[Item]:
        """
        Get an item template by its name

        Args:
            name: Item name

        Returns:
            Item object if found, None otherwise
        """
        try:
            item_doc = await self.items_collection.find_one({"name": name})
            if item_doc:
                item = Item(**item_doc)
                self.logger.debug("Item template found by name", name=name)
                return item
            else:
                self.logger.debug("Item template not found by name", name=name)
                return None

        except Exception as e:
            self.logger.error(
                "Error retrieving item template by name",
                name=name,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def add_item(self, user_id: str, item_id: str, quantity: int = 1,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add an item to a user's inventory (mochila)

        Args:
            user_id: User identifier
            item_id: Item identifier to add
            quantity: Quantity to add (default 1)
            metadata: Additional metadata for this specific inventory item instance

        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Validate the item exists in the system
            item_template = await self.get_item_template(item_id)
            if not item_template:
                self.logger.error("Item template does not exist", item_id=item_id, user_id=user_id)
                return False

            # Check if user has reached maximum quantity for this item (if limited)
            if item_template.max_quantity is not None:
                current_inventory = await self.get_inventory(user_id)
                current_quantity = 0
                for inv_item in current_inventory:
                    if inv_item.item_id == item_id:
                        current_quantity = inv_item.quantity
                        break

                new_quantity = current_quantity + quantity
                if new_quantity > item_template.max_quantity:
                    self.logger.warning(
                        "Maximum quantity reached for limited item",
                        user_id=user_id,
                        item_id=item_id,
                        current_quantity=current_quantity,
                        quantity_to_add=quantity,
                        max_quantity=item_template.max_quantity
                    )
                    return False

            # Find or create user inventory document
            inventory_doc = await self.user_inventory_collection.find_one({"user_id": user_id})
            if not inventory_doc:
                # Create new inventory document
                inventory_data = {
                    "user_id": user_id,
                    "items": [{
                        "item_id": item_id,
                        "quantity": quantity,
                        "metadata": metadata or {}
                    }],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                result = await self.user_inventory_collection.insert_one(inventory_data)
                if result.inserted_id:
                    self.logger.info(
                        "New user inventory created with item",
                        user_id=user_id,
                        item_id=item_id,
                        quantity=quantity
                    )
                else:
                    self.logger.error(
                        "Failed to create user inventory",
                        user_id=user_id,
                        item_id=item_id
                    )
                    return False
            else:
                # Update existing inventory
                updated = False
                items = inventory_doc.get("items", [])
                
                # Check if item already exists in inventory
                item_found = False
                for item in items:
                    if item["item_id"] == item_id:
                        item["quantity"] += quantity
                        if metadata and isinstance(item["metadata"], dict):
                            item["metadata"].update(metadata)
                        item_found = True
                        updated = True
                        break

                # If item doesn't exist in inventory, add it
                if not item_found:
                    items.append({
                        "item_id": item_id,
                        "quantity": quantity,
                        "metadata": metadata or {}
                    })
                    updated = True

                if updated:
                    result = await self.user_inventory_collection.update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "items": items,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )

                    if result.modified_count > 0:
                        self.logger.info(
                            "Item added to user inventory",
                            user_id=user_id,
                            item_id=item_id,
                            quantity=quantity
                        )
                    else:
                        self.logger.warning(
                            "No changes made to user inventory",
                            user_id=user_id,
                            item_id=item_id
                        )
                        return False

            # Publish item acquired event
            await self._publish_inventory_event(
                user_id=user_id,
                item_id=item_id,
                quantity=quantity,
                event_type="item_acquired"
            )

            return True

        except Exception as e:
            self.logger.error(
                "Error adding item to user inventory",
                user_id=user_id,
                item_id=item_id,
                quantity=quantity,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def remove_item(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
        """
        Remove an item from a user's inventory (mochila)

        Args:
            user_id: User identifier
            item_id: Item identifier to remove
            quantity: Quantity to remove (default 1)

        Returns:
            True if successfully removed, False otherwise
        """
        try:
            # Find user inventory
            inventory_doc = await self.user_inventory_collection.find_one({"user_id": user_id})
            if not inventory_doc:
                self.logger.warning("User inventory not found", user_id=user_id)
                return False

            items = inventory_doc.get("items", [])
            item_found = False

            # Look for the item and update its quantity
            for item in items:
                if item["item_id"] == item_id:
                    current_quantity = item["quantity"]
                    new_quantity = current_quantity - quantity

                    if new_quantity <= 0:
                        # Remove the item from inventory entirely
                        items.remove(item)
                    else:
                        # Update quantity
                        item["quantity"] = new_quantity

                    item_found = True
                    break

            if not item_found:
                self.logger.warning(
                    "Item not found in user inventory",
                    user_id=user_id,
                    item_id=item_id
                )
                return False

            # Update the inventory document
            result = await self.user_inventory_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "items": items,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                self.logger.info(
                    "Item removed from user inventory",
                    user_id=user_id,
                    item_id=item_id,
                    quantity_removed=quantity
                )

                # Publish item removed event
                await self._publish_inventory_event(
                    user_id=user_id,
                    item_id=item_id,
                    quantity=quantity,
                    event_type="item_removed"
                )

                return True
            else:
                self.logger.warning(
                    "No changes made to user inventory during removal",
                    user_id=user_id,
                    item_id=item_id
                )
                return False

        except Exception as e:
            self.logger.error(
                "Error removing item from user inventory",
                user_id=user_id,
                item_id=item_id,
                quantity=quantity,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def get_inventory(self, user_id: str) -> List[InventoryItem]:
        """
        Get a user's complete inventory (mochila)

        Args:
            user_id: User identifier

        Returns:
            List of InventoryItem objects representing user's inventory
        """
        try:
            inventory_doc = await self.user_inventory_collection.find_one({"user_id": user_id})
            if not inventory_doc:
                self.logger.debug("User inventory not found", user_id=user_id)
                return []

            items = inventory_doc.get("items", [])
            inventory_items = []

            for item_data in items:
                inventory_item = InventoryItem(
                    item_id=item_data["item_id"],
                    quantity=item_data["quantity"],
                    metadata=item_data.get("metadata", {})
                )
                inventory_items.append(inventory_item)

            self.logger.debug(
                "User inventory retrieved",
                user_id=user_id,
                item_count=len(inventory_items)
            )

            return inventory_items

        except Exception as e:
            self.logger.error(
                "Error retrieving user inventory",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def get_item_count(self, user_id: str, item_id: str) -> int:
        """
        Get the count of a specific item in a user's inventory

        Args:
            user_id: User identifier
            item_id: Item identifier to count

        Returns:
            Number of items of the specified type in inventory
        """
        try:
            inventory = await self.get_inventory(user_id)
            for inventory_item in inventory:
                if inventory_item.item_id == item_id:
                    return inventory_item.quantity
            return 0

        except Exception as e:
            self.logger.error(
                "Error getting item count in user inventory",
                user_id=user_id,
                item_id=item_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    async def has_item(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
        """
        Check if a user has a specific item in their inventory

        Args:
            user_id: User identifier
            item_id: Item identifier to check for
            quantity: Minimum quantity required (default 1)

        Returns:
            True if user has the item with at least the specified quantity, False otherwise
        """
        try:
            current_count = await self.get_item_count(user_id, item_id)
            return current_count >= quantity

        except Exception as e:
            self.logger.error(
                "Error checking if user has item",
                user_id=user_id,
                item_id=item_id,
                quantity=quantity,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def use_item(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
        """
        Use an item from user's inventory (removes it after use)

        Args:
            user_id: User identifier
            item_id: Item identifier to use
            quantity: Quantity to use (default 1)

        Returns:
            True if item was successfully used, False otherwise
        """
        try:
            # Check if user has enough of the item
            if not await self.has_item(user_id, item_id, quantity):
                self.logger.warning(
                    "User does not have enough of the item to use",
                    user_id=user_id,
                    item_id=item_id,
                    required_quantity=quantity,
                    available_quantity=await self.get_item_count(user_id, item_id)
                )
                return False

            # Remove the item from inventory
            success = await self.remove_item(user_id, item_id, quantity)

            if success:
                self.logger.info(
                    "Item used successfully",
                    user_id=user_id,
                    item_id=item_id,
                    quantity=quantity
                )

                # Publish item used event
                await self._publish_inventory_event(
                    user_id=user_id,
                    item_id=item_id,
                    quantity=quantity,
                    event_type="item_used"
                )

            return success

        except Exception as e:
            self.logger.error(
                "Error using item from user inventory",
                user_id=user_id,
                item_id=item_id,
                quantity=quantity,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def combine_items(self, user_id: str, item1_id: str, item2_id: str,
                           result_item_id: str, item1_quantity: int = 1, 
                           item2_quantity: int = 1) -> bool:
        """
        Combine two items to create a new item

        Args:
            user_id: User identifier
            item1_id: First item identifier to combine
            item2_id: Second item identifier to combine
            result_item_id: Item identifier of the combination result
            item1_quantity: Quantity of first item to use (default 1)
            item2_quantity: Quantity of second item to use (default 1)

        Returns:
            True if items were successfully combined, False otherwise
        """
        try:
            # Check if user has both required items
            has_item1 = await self.has_item(user_id, item1_id, item1_quantity)
            has_item2 = await self.has_item(user_id, item2_id, item2_quantity)

            if not (has_item1 and has_item2):
                self.logger.warning(
                    "User does not have required items to combine",
                    user_id=user_id,
                    item1_id=item1_id,
                    item1_required_quantity=item1_quantity,
                    item1_available=await self.get_item_count(user_id, item1_id),
                    item2_id=item2_id,
                    item2_required_quantity=item2_quantity,
                    item2_available=await self.get_item_count(user_id, item2_id)
                )
                return False

            # Remove the consumed items
            success1 = await self.remove_item(user_id, item1_id, item1_quantity)
            success2 = await self.remove_item(user_id, item2_id, item2_quantity)

            if not (success1 and success2):
                self.logger.error(
                    "Failed to remove items during combination",
                    user_id=user_id,
                    item1_id=item1_id,
                    item2_id=item2_id
                )
                # Roll back if one failed
                if success1:
                    await self.add_item(user_id, item1_id, item1_quantity)
                if success2:
                    await self.add_item(user_id, item2_id, item2_quantity)
                return False

            # Add the resulting item
            success = await self.add_item(user_id, result_item_id, 1)

            if success:
                self.logger.info(
                    "Items combined successfully",
                    user_id=user_id,
                    item1_id=item1_id,
                    item2_id=item2_id,
                    result_item_id=result_item_id
                )

                # Publish combination event
                await self._publish_inventory_event(
                    user_id=user_id,
                    item_id=result_item_id,
                    quantity=1,
                    event_type="items_combined",
                    additional_data={
                        "combined_from": [item1_id, item2_id],
                        "quantities_used": [item1_quantity, item2_quantity]
                    }
                )

            return success

        except Exception as e:
            self.logger.error(
                "Error combining items",
                user_id=user_id,
                item1_id=item1_id,
                item2_id=item2_id,
                result_item_id=result_item_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def get_inventory_by_type(self, user_id: str, item_type: ItemType) -> List[InventoryItem]:
        """
        Get all items in a user's inventory of a specific type

        Args:
            user_id: User identifier
            item_type: Type of items to retrieve

        Returns:
            List of InventoryItem objects of the specified type
        """
        try:
            all_inventory = await self.get_inventory(user_id)
            filtered_items = []

            # Get item templates to check their types
            for inventory_item in all_inventory:
                item_template = await self.get_item_template(inventory_item.item_id)
                if item_template and item_template.item_type == item_type:
                    filtered_items.append(inventory_item)

            return filtered_items

        except Exception as e:
            self.logger.error(
                "Error retrieving inventory by type",
                user_id=user_id,
                item_type=item_type.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def transfer_item(self, from_user_id: str, to_user_id: str, 
                           item_id: str, quantity: int) -> bool:
        """
        Transfer an item from one user to another

        Args:
            from_user_id: User ID to transfer from
            to_user_id: User ID to transfer to
            item_id: Item identifier to transfer
            quantity: Quantity to transfer

        Returns:
            True if transfer was successful, False otherwise
        """
        try:
            # Check if source user has the item
            if not await self.has_item(from_user_id, item_id, quantity):
                self.logger.warning(
                    "Source user does not have enough of the item to transfer",
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    item_id=item_id,
                    required_quantity=quantity,
                    available_quantity=await self.get_item_count(from_user_id, item_id)
                )
                return False

            # Remove item from source user
            success_remove = await self.remove_item(from_user_id, item_id, quantity)

            if success_remove:
                # Add item to destination user
                success_add = await self.add_item(to_user_id, item_id, quantity)
                
                if success_add:
                    self.logger.info(
                        "Item transferred successfully",
                        from_user_id=from_user_id,
                        to_user_id=to_user_id,
                        item_id=item_id,
                        quantity=quantity
                    )

                    # Publish transfer events
                    await self._publish_inventory_event(
                        user_id=from_user_id,
                        item_id=item_id,
                        quantity=quantity,
                        event_type="item_transferred_out"
                    )
                    
                    await self._publish_inventory_event(
                        user_id=to_user_id,
                        item_id=item_id,
                        quantity=quantity,
                        event_type="item_transferred_in"
                    )

                    return True
                else:
                    # Rollback: add item back to source user
                    await self.add_item(from_user_id, item_id, quantity)
                    return False
            else:
                return False

        except Exception as e:
            self.logger.error(
                "Error transferring item between users",
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                item_id=item_id,
                quantity=quantity,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def _publish_inventory_event(self, user_id: str, item_id: str, quantity: int,
                                    event_type: str, additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish an event about inventory activities

        Args:
            user_id: User ID
            item_id: Item identifier
            quantity: Quantity involved
            event_type: Type of inventory event
            additional_data: Additional data to include in event
        """
        try:
            event_payload = {
                "user_id": user_id,
                "item_id": item_id,
                "quantity": quantity,
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat()
            }

            if additional_data:
                event_payload.update(additional_data)

            # Using BaseEvent with a generic payload since specific event models
            # may not be defined yet for inventory events
            event = BaseEvent(
                event_type=f"inventory_{event_type}",
                user_id=user_id,
                payload=event_payload
            )

            await self.event_bus.publish(f"inventory_{event_type}", event_payload)
            self.logger.debug(
                "Inventory event published",
                event_type=event_type,
                user_id=user_id,
                item_id=item_id
            )

        except Exception as e:
            self.logger.error(
                "Error publishing inventory event",
                user_id=user_id,
                item_id=item_id,
                event_type=event_type,
                error=str(e),
                error_type=type(e).__name__
            )

    async def _publish_item_event(self, item_id: str, event_type: str, 
                                item_data: Dict[str, Any]) -> None:
        """
        Publish an event about item template activities

        Args:
            item_id: Item identifier
            event_type: Type of item event
            item_data: Additional item data to include in event
        """
        try:
            event_payload = {
                "item_id": item_id,
                "event_type": event_type,
                "item_data": item_data,
                "timestamp": datetime.utcnow().isoformat()
            }

            event = BaseEvent(
                event_type=f"item_{event_type}",
                user_id=None,  # No specific user for template events
                payload=event_payload
            )

            await self.event_bus.publish(f"item_{event_type}", event_payload)
            self.logger.debug(
                "Item template event published",
                event_type=event_type,
                item_id=item_id
            )

        except Exception as e:
            self.logger.error(
                "Error publishing item template event",
                item_id=item_id,
                event_type=event_type,
                error=str(e),
                error_type=type(e).__name__
            )
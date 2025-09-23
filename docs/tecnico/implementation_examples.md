# Implementation Examples

## Resumen
This document provides real-world examples of key implementation patterns used in the YABOT application. These examples are extracted from the codebase and demonstrate how to use the core components of the system, such as the event bus, the service layer, and the menu system.

## Event System

The event system is the backbone of the application's architecture, enabling decoupled communication between different components.

### Event Subscription
Modules and services can subscribe to events to be notified when something happens in the system. This allows them to react to changes without being tightly coupled to the components that produce the events.

**Example: Gamification modules subscribing to events**

In `src/modules/gamification/mission_manager.py`, the `MissionManager` subscribes to events to track user progress in missions:

```python
# src/modules/gamification/mission_manager.py

async def initialize_event_handlers(self):
    await self.event_bus.subscribe("decision_made", self._handle_decision_made_event)
    await self.event_bus.subscribe("reaction_detected", self._handle_reaction_event)
    await self.event_bus.subscribe("user_interaction", self._handle_interaction_event)
```

In `src/modules/gamification/achievement_system.py`, the `AchievementSystem` subscribes to events to unlock achievements:

```python
# src/modules/gamification/achievement_system.py

async def _register_event_handlers(self):
    await self.event_bus.subscribe("mission_completed", self._handle_mission_completed)
    await self.event_bus.subscribe("besitos_added", self._handle_besitos_added)
    await self.event_bus.subscribe("reaction_detected", self._handle_reaction_detected)
```

### Event Publication
Events are published by services and handlers when their state changes or when a significant action occurs.

**Example: `UserService` publishing events**

The `UserService` publishes events whenever a user is created, updated, or deleted:

```python
# src/services/user.py

async def create_user(self, telegram_user: Dict[str, Any]) -> Dict[str, Any]:
    # ...
    event = create_event(
        "user_registered",
        user_id=user_id,
        # ...
    )
    await self.event_bus.publish("user_registered", event.dict())
    # ...

async def update_user_state(self, user_id: str, state_updates: Dict[str, Any]) -> bool:
    # ...
    event = create_event(
        "user_updated",
        user_id=user_id,
        update_type="state",
        updated_fields=state_updates
    )
    await self.event_bus.publish("user_updated", event.dict())
    # ...
```

## Service Layer

The service layer contains the core business logic of the application. The `CrossModuleService` is a good example of how to orchestrate complex operations that involve multiple services.

### Communication Between Services
The `CrossModuleService` acts as a facade, providing a single entry point for complex operations.

**Example: Processing a narrative choice**

The `process_narrative_choice` method in the `CrossModuleService` demonstrates how to coordinate the `NarrativeService` and the `UserService` to process a user's choice in the narrative:

```python
# src/services/cross_module.py

async def process_narrative_choice(
    self, 
    user_id: str, 
    fragment_id: str, 
    choice_data: Dict[str, Any]
) -> Dict[str, Any]:
    # Deduct besitos if required
    fragment = await self.narrative_service.get_fragment(fragment_id)
    if fragment:
        besitos_cost = fragment.get('besitos_cost', 0)
        if besitos_cost > 0:
            await self.user_service.deduct_besitos(user_id, besitos_cost)
        
        # Award items if specified
        awarded_items = fragment.get('award_items', {})
        for item_id, quantity in awarded_items.items():
            await self.item_manager.add_item_to_user(user_id, item_id, quantity)
    
    # Update narrative progress
    result = await self.narrative_service.record_user_choice(
        user_id, fragment_id, choice_data
    )
    
    return result
```

## Menu System

The menu system is responsible for generating and rendering all the menus in the application.

### Inline Menu Implementation
The `TelegramMenuRenderer` is the best example of how to create inline menus in this application. It demonstrates how to create a keyboard from a `Menu` object, how to handle different action types, and how to integrate with the Lucien voice generator.

**Example: Rendering a menu**

The `render_menu` method in the `TelegramMenuRenderer` takes a `Menu` object and returns an `InlineKeyboardMarkup`:

```python
# src/ui/telegram_menu_renderer.py

def render_menu(self, menu: Menu) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    row = []
    for i, item in enumerate(menu.items):
        button = self._create_button_for_item(item)
        if button:
            row.append(button)
            
            if len(row) >= menu.max_columns or i == len(menu.items) - 1:
                keyboard.inline_keyboard.append(row)
                row = []
    
    return keyboard
```

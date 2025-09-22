# Event System

## Resumen
The Event System is the central nervous system of the YABOT application, providing a robust, asynchronous communication mechanism between different modules and services. It is built around an `EventBus` that uses a Redis Pub/Sub model for efficient, real-time event distribution, with a local fallback queue to ensure durability and resilience against Redis connectivity issues.

The system allows for a decoupled architecture where components can publish events without knowing who the subscribers are, and subscribers can react to events without being directly coupled to the publishers. This promotes modularity, scalability, and resilience.

## `EventBus` API Reference

The `EventBus` is the core component responsible for publishing and subscribing to events.

### `EventBus`
The main class for handling event publication and subscription.

#### Constructor
```python
EventBus(config_manager: Optional[ConfigManager] = None, retry_policy: Optional[RetryPolicy] = None)
```
**Parámetros:**
- `config_manager` (ConfigManager, opcional): An instance of `ConfigManager` to retrieve Redis and other configurations. If not provided, a new instance is created.
- `retry_policy` (RetryPolicy, opcional): A `RetryPolicy` dataclass instance to configure the retry mechanism for event publishing. If not provided, a default policy is used.

#### Métodos

##### `async connect() -> bool`
Establishes a connection to the Redis server. It includes a retry mechanism with exponential backoff. If the connection fails after several attempts, it operates in a disconnected mode, queuing events locally.

**Returns:**
- `bool`: `True` if the connection was successful, `False` otherwise.

##### `async publish(event_name: str, payload: Dict[str, Any]) -> bool`
Publishes an event to the event bus. If connected to Redis, the event is published to a Redis channel. If not connected, the event is stored in a local, persistent queue for later processing.

**Parámetros:**
- `event_name` (str): The name of the event to publish (e.g., `"user_registered"`).
- `payload` (Dict[str, Any]): The data associated with the event.

**Returns:**
- `bool`: `True` if the event was successfully published or queued, `False` otherwise.

**Ejemplo:**
```python
event_bus = EventBus(config_manager)
await event_bus.connect()

await event_bus.publish(
    "user_interaction",
    {
        "user_id": "12345",
        "action": "start",
        "context": {"source": "organic"}
    }
)
```

##### `async subscribe(event_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> bool`
Subscribes a handler function to a specific event. The handler will be executed whenever an event of the specified type is received.

**Parámetros:**
- `event_name` (str): The name of the event to subscribe to.
- `handler` (Callable): An awaitable function that takes the event payload as a dictionary.

**Returns:**
- `bool`: `True` if the subscription was successful, `False` otherwise.

**Ejemplo:**
```python
async def handle_user_interaction(payload: Dict[str, Any]):
    print(f"User {payload['user_id']} performed action: {payload['action']}")

await event_bus.subscribe("user_interaction", handle_user_interaction)
```

##### `async close()`
Closes the connection to Redis and persists any pending events in the local queue to a file. This should be called during a graceful shutdown of the application.

## `EventSubscriptionManager` API Reference

The `EventSubscriptionManager` provides a higher-level, service-oriented API for managing event subscriptions.

### `EventSubscriptionManager`
Manages event subscriptions for different services or modules.

#### Constructor
```python
EventSubscriptionManager(event_bus: 'EventBus')
```
**Parámetros:**
- `event_bus` (EventBus): An instance of the `EventBus`.

#### Métodos

##### `async subscribe(event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]], service_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool`
Subscribes a service's handler to an event type. This is the recommended way for modules to subscribe to events.

**Parámetros:**
- `event_type` (str): The event to subscribe to.
- `handler` (Callable): The awaitable function to handle the event.
- `service_name` (str): The name of the service that is subscribing.
- `metadata` (Dict, opcional): Optional metadata about the subscription.

**Returns:**
- `bool`: `True` if successful, `False` otherwise.

**Ejemplo:**
```python
subscription_manager = EventSubscriptionManager(event_bus)

async def handle_new_user(payload: Dict[str, Any]):
    # Logic for handling new user registration
    pass

await subscription_manager.subscribe(
    "user_registered",
    handle_new_user,
    "NarrativeService"
)
```

## Event Models

All events in the system are represented by Pydantic models that inherit from a `BaseEvent`.

### `BaseEvent`
The base model for all events.

| Campo | Tipo | Descripción |
|---|---|---|
| `event_id` | str | A unique identifier for the event instance. |
| `event_type` | str | The type of the event (e.g., `"user_interaction"`). |
| `timestamp` | datetime | The timestamp when the event occurred. |
| `correlation_id` | str | An ID to trace related events across the system. |
| `user_id` | Optional[str] | The ID of the user associated with the event, if any. |
| `payload` | Dict[str, Any] | A dictionary containing event-specific data. |

### Common Event Models

Here are some of the most common event models used in the system:

- **`UserInteractionEvent`**: Fired when a user interacts with the bot (e.g., sends a command, clicks a button).
- **`UserRegisteredEvent`**: Fired when a new user is registered in the system.
- **`BesitosAwardedEvent`**: Fired when "besitos" (the in-game currency) are awarded to a user.
- **`MissionCompletedEvent`**: Fired when a user completes a mission.
- **`ModuleFailureEvent`**: Fired when a system module encounters a critical failure.
- **`DatabaseConnectionLostEvent`**: Fired when the connection to a database is lost.

For a complete list of all event models and their fields, please refer to `src/events/models.py`.

## `create_event` Factory Function

To simplify the creation of events, the system provides a factory function.

### `create_event(event_type: str, **kwargs) -> BaseEvent`
Creates, validates, and returns an event model instance. It automatically fills in common fields like `event_id`, `timestamp`, and `correlation_id` if they are not provided.

**Parámetros:**
- `event_type` (str): The type of event to create.
- `**kwargs`: The data for the event, corresponding to the fields of the specific event model.

**Returns:**
- `BaseEvent`: An instance of the corresponding event model.

**Ejemplo:**
```python
from src.events.models import create_event

# Create a UserRegisteredEvent
new_user_event = create_event(
    "user_registered",
    user_id="user-5678",
    telegram_user_id=123456789,
    username="new_user",
    first_name="New",
    last_name="User"
)

# Publish the event
await event_bus.publish(new_user_event.event_type, new_user_event.dict())
```

## Integration and Workflow

1.  **Event Definition**: New events are defined as Pydantic models in `src/events/models.py`.
2.  **Event Creation**: When a significant action occurs, a service or handler creates an event instance using the `create_event` factory function.
3.  **Publication**: The event is published to the `EventBus` using the `publish` method.
4.  **Subscription**: Modules and services that need to react to events subscribe to them using the `EventSubscriptionManager`.
5.  **Handling**: When an event is published, the `EventBus` distributes it to all subscribed handlers, which then execute their logic.

This decoupled, event-driven architecture allows for a highly modular and resilient system where components can evolve independently.

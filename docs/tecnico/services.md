# Services

## Resumen
The services layer contains the core business logic of the YABOT application. Each service is responsible for a specific domain of functionality, such as user management, narrative progression, or subscription handling. The services are designed to be modular and decoupled, communicating with each other through the `EventBus` or the `CrossModuleService`.

## `UserService`

### Resumen
The `UserService` is a crucial component that manages all aspects of a user's data and state within the application. It acts as a single source of truth for user information, handling data across both MongoDB (for dynamic state) and SQLite (for static profiles).

### Dependencias
- `DatabaseManager`: To interact with the databases.
- `EventBus`: To publish user-related events.
- `CacheManager`: For caching user data.

### API Reference

#### `async create_user(telegram_user: Dict[str, Any]) -> Dict[str, Any]`
Creates a new user in both MongoDB and SQLite databases. It publishes a `user_registered` event upon successful creation.

#### `async get_user_context(user_id: str) -> Dict[str, Any]`
Retrieves the complete user context, combining the user's profile from SQLite and their state from MongoDB.

#### `async get_or_create_user_context(user_id: str, telegram_user: Dict[str, Any] = None) -> Dict[str, Any]`
Retrieves a user's context or creates a new user if they don't exist.

#### `async update_user_state(user_id: str, state_updates: Dict[str, Any]) -> bool`
Updates a user's dynamic state in MongoDB and publishes a `user_updated` event.

#### `async update_user_profile(user_id: str, profile_updates: Dict[str, Any]) -> bool`
Updates a user's profile data in SQLite and publishes a `user_updated` event.

#### `async delete_user(user_id: str, deletion_reason: str = "user_request") -> bool`
Deletes a user's data from both databases and publishes a `user_deleted` event.

#### `async award_besitos(user_id: str, amount: int) -> None`
Awards "besitos" (the in-game currency) to a user and publishes a `besitos_awarded` event.

#### `async update_emotional_signature(user_id: str, signature_data: Dict[str, Any]) -> bool`
Updates the user's emotional signature in MongoDB and publishes an `emotional_signature_updated` event.

## `NarrativeService`

### Resumen
The `NarrativeService` manages the lifecycle of "narrative fragments," which are the building blocks of the bot's story. It handles content personalization and records user choices and emotional interactions.

### Dependencias
- `DatabaseManager`: To store and retrieve narrative fragments from MongoDB.
- `SubscriptionService`: To check for VIP user access.
- `EventBus`: To publish narrative-related events.

### API Reference

#### `async create_narrative_fragment(fragment_data: Dict[str, Any]) -> Dict[str, Any]`
Creates a new narrative fragment in MongoDB.

#### `async get_narrative_fragment(fragment_id: str) -> Dict[str, Any]`
Retrieves a narrative fragment by its ID.

#### `async get_personalized_content(user_id: str, fragment_id: str, emotional_context: Dict[str, Any]) -> Dict[str, Any]`
Personalizes the narrative content based on the user's emotional signature. It has a graceful degradation mechanism.

#### `async record_user_choice(user_id: str, fragment_id: str, choice_data: Dict[str, Any]) -> Dict[str, Any]`
Records a user's choice in the narrative and publishes a `decision_made` event.

#### `async record_emotional_interaction(user_id: str, fragment_id: str, interaction_data: Dict[str, Any]) -> Dict[str, Any]`
Records a detailed emotional interaction, which can lead to the creation of "emotional memories" and the publication of `emotional_milestone_reached` events.

## `SubscriptionService`

### Resumen
The `SubscriptionService` handles all aspects of user subscriptions, including creation, retrieval, updating, and validation. It is a key component for monetization and for controlling access to premium content.

### Dependencias
- `DatabaseManager`: To store and retrieve subscription data from SQLite.
- `EventBus`: To publish subscription-related events.

### API Reference

#### `async create_subscription(user_id: str, plan_type: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]`
Creates a new subscription for a user and publishes a `subscription_updated` event.

#### `async get_subscription(user_id: str) -> Dict[str, Any]`
Retrieves a user's subscription data.

#### `async update_subscription(user_id: str, updates: Dict[str, Any]) -> bool`
Updates a user's subscription and publishes a `subscription_updated` event.

#### `async validate_vip_access(user_id: str) -> bool`
Validates if a user has an active VIP subscription.

## `CrossModuleService`

### Resumen
The `CrossModuleService` acts as a facade or a coordinator for interactions between different modules and services. It encapsulates the logic for complex operations that require the coordination of multiple services.

### Dependencias
- `UserService`
- `SubscriptionService`
- `NarrativeService`
- Various gamification and admin modules.

### API Reference

#### `async can_access_narrative_content(user_id: str, fragment_id: str) -> bool`
Checks if a user has the necessary permissions (VIP status, besitos, items) to access a piece of narrative content.

#### `async process_narrative_choice(user_id: str, fragment_id: str, choice_data: Dict[str, Any]) -> Dict[str, Any]`
Processes a narrative choice and triggers corresponding gamification events (e.g., deducting besitos, awarding items).

#### `async claim_daily_gift(user_id: str) -> Dict[str, Any]`
Coordinates the process of claiming a daily gift, interacting with the `DailyGiftSystem` and `BesitosWallet`.

## `CoordinatorService`

### Resumen
The `CoordinatorService` is responsible for orchestrating complex business workflows and ensuring proper event sequencing. It helps to decouple the other services by handling the orchestration of complex workflows.

### Dependencias
- `DatabaseManager`
- `EventBus`
- `UserService`
- `SubscriptionService`
- `NarrativeService`

### API Reference

#### `async process_user_interaction(user_id: str, action: str, context: Dict[str, Any]) -> bool`
Handles user interaction workflows and publishes a `user_interaction` event.

#### `async buffer_event(user_id: str, event: Dict[str, Any]) -> None`
Buffers an event to be processed in chronological order.

#### `async process_buffered_events(user_id: str) -> None`
Processes all buffered events for a user in the correct order.

## `DianaEncounterManager`

### Resumen
The `DianaEncounterManager` orchestrates special, earned encounters with the character Diana. It determines if a user is ready for such an encounter based on their narrative progress and emotional state.

### Dependencias
- (Placeholder for) Emotional Intelligence Service

### API Reference

#### `async evaluate_diana_encounter_readiness(user_progress: UserProgress, emotional_resonance: float) -> EncounterReadiness`
Evaluates if a user is ready for a special encounter with Diana. The current implementation uses placeholder logic.

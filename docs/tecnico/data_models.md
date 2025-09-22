# Data Models

## Resumen
The data models define the structure of the data used throughout the YABOT application. The system uses Pydantic models for data validation and serialization, and it stores data in both MongoDB and SQLite databases.

## Core Configuration Models (`src/core/models.py`)

These models define the structure of the application's configuration.

- **`BotConfig`**: Configuration for the Telegram bot (token, webhook, etc.).
- **`WebhookConfig`**: Configuration for the webhook settings.
- **`LoggingConfig`**: Configuration for the logging system.
- **`CommandResponse`**: Defines the structure of a response from a command handler.
- **`DatabaseConfig`**: Configuration for the database connections (MongoDB and SQLite).
- **`RedisConfig`**: Configuration for the Redis connection.

## MongoDB Schemas (`src/database/schemas/mongo.py`)

These Pydantic models define the schemas for the documents stored in the MongoDB collections.

### `User`
This is the main model for the `users` collection. It provides a 360-degree view of the user, including:

- **`current_state`**: The user's dynamic state (e.g., current menu).
- **`preferences`**: The user's preferences (e.g., language).
- **`besitos_balance`**: The user's balance of the in-game currency.
- **`subscription`**: The user's subscription information.
- **`gamification`**: The user's gamification statistics.
- **`admin`**: Administrative information about the user.
- **`emotional_signature`**: The user's emotional archetype and related data.
- **`emotional_journey`**: The user's progression through the Diana levels.
- **`inventory`**: The user's inventory of items.

### `NarrativeFragment`
Defines the structure of a narrative fragment, including its content, choices, and metadata.

### `Item`
Defines the structure of an item in the gamification system.

### `LucienEvaluations`
Stores Lucien's evaluations of a user's progress and worthiness.

### `DianaEncounters`
Tracks special, earned encounters with the character Diana.

## SQLite Schemas (`src/database/schemas/sqlite.py`)

These schemas define the structure of the tables in the SQLite database.

### `user_profiles` Table
Stores the static profile information for users.

| Column | Type | Description |
|---|---|---|
| `user_id` | TEXT | The user's unique ID (Primary Key). |
| `telegram_user_id` | INTEGER | The user's Telegram ID (Unique). |
| `username` | TEXT | The user's Telegram username. |
| `first_name` | TEXT | The user's first name. |
| `last_name` | TEXT | The user's last name. |
| `registration_date` | DATETIME | The date and time the user registered. |

### `subscriptions` Table
Stores the subscription information for users.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | The subscription's unique ID (Primary Key). |
| `user_id` | TEXT | The ID of the user who owns the subscription. |
| `plan_type` | TEXT | The type of subscription plan (`free`, `premium`, `vip`). |
| `status` | TEXT | The status of the subscription (`active`, `inactive`, `cancelled`, `expired`). |
| `start_date` | DATETIME | The date and time the subscription started. |
| `end_date` | DATETIME | The date and time the subscription ends. |

## Relationships Between Models

- The `User` model in MongoDB has a `user_id` that corresponds to the `user_id` in the `user_profiles` table in SQLite. This allows the application to link a user's dynamic state with their static profile information.
- The `subscriptions` table in SQLite has a `user_id` that is a foreign key to the `user_profiles` table, creating a one-to-one relationship between a user and their subscription.

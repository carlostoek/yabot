# Developer's Guide

## Introduction
This guide provides practical instructions for developers working on the YABOT application. It covers common development tasks and provides a summary of the project's coding conventions.

## Getting Started

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment variables**:
    - Copy the `.env.example` file to `.env`.
    - Fill in the required environment variables, such as the bot token and the database connection strings.

5.  **Run the application**:
    ```bash
    python3 src/main.py
    ```

## Project Structure

- **`src/`**: The main source code directory.
    - **`api/`**: The FastAPI application for the API.
    - **`core/`**: The core components of the bot application.
    - **`database/`**: The database-related code, including schemas and migrations.
    - **`events/`**: The event bus and event models.
    - **`handlers/`**: The message and callback handlers.
    - **`modules/`**: The different modules of the application (gamification, admin, etc.).
    - **`services/`**: The business logic services.
    - **`ui/`**: The user interface components, including the menu system.
- **`docs/`**: The project documentation.
- **`tests/`**: The unit and integration tests.

## Common Development Tasks

### Adding a New Command

1.  **Add a new method to `src/handlers/commands.py`**:

    ```python
    async def handle_my_command(self, message: Message) -> CommandResponse:
        # ...
    ```

2.  **Register the new command in `src/core/application.py`**:

    ```python
    self.router.register_command_handler("my_command", self.command_handler.handle_my_command)
    ```

### Adding a New Service

1.  **Create a new file in `src/services/`** (e.g., `my_service.py`).
2.  **Define the new service class**:

    ```python
    class MyService:
        def __init__(self, database_manager: DatabaseManager, event_bus: EventBus):
            # ...
    ```

3.  **Add the new service to the `BotApplication` class in `src/core/application.py`**.

### Adding a New Event

1.  **Define a new event model in `src/events/models.py`**:

    ```python
    class MyEvent(BaseEvent):
        # ...
    ```

2.  **Add the new event to the `EVENT_MODELS` dictionary**.
3.  **Publish the new event from a service or handler**:

    ```python
    event = create_event("my_event", ...)
    await self.event_bus.publish("my_event", event.dict())
    ```

### Adding a New Menu

1.  **Define a new menu in `src/ui/menu_config.py`**:

    ```python
    MENU_DEFINITIONS["my_menu"] = MenuConfig(
        menu_id="my_menu",
        # ...
    )
    ```

2.  **Add a new menu builder to `src/ui/menu_factory.py`** (optional, for complex menus).
3.  **Add a new routing rule to `MENU_ROUTING_RULES`** (optional, for command-based menus).

## Testing

To run the tests, use the following command:

```bash
pytest
```

## Coding Conventions

- **Style**: The project follows the PEP 8 style guide.
- **Typing**: All code should be fully type-hinted.
- **Docstrings**: All public modules, classes, and methods should have docstrings.
- **Logging**: Use the `get_logger` function from `src/utils/logger.py` to get a logger instance.

# Yet Another Telegram Bot (YABOT)

A robust, scalable Telegram bot framework built with Aiogram 3, designed with clean architecture principles and best practices. This framework provides essential functionality for user interaction and system management with support for both webhook and polling modes. The Fase1 infrastructure adds dual database support (MongoDB/SQLite), event-driven architecture (Redis), and internal REST APIs.

## Features

- Aiogram 3 framework for Telegram bot API
- Clean architecture with separation of concerns
- Asynchronous processing for high performance
- Configurable via environment variables
- Comprehensive error handling and logging
- Extensible middleware support
- Support for both webhook and polling modes
- Secure webhook validation
- Structured logging with JSON support
- Graceful error handling and recovery
- Dual database support (MongoDB for dynamic data, SQLite for ACID compliance)
- Redis-based event bus for reliable communication
- Internal REST APIs for service communication
- User state management and subscription services
- Event-driven architecture with reliability features

## Requirements

- Python 3.11 or higher
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- MongoDB database (for dynamic user states)
- SQLite database (for ACID-compliant user profiles and subscriptions)
- Redis server (for event bus and pub/sub)
- (For webhook mode) HTTPS endpoint accessible from the internet

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd yabot
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # Or if using pyproject.toml:
   # pip install -e .
   ```

## Infrastructure Setup

### Database Configuration (Fase1)

The bot uses a dual-database architecture:

1. **MongoDB Setup:**
   - Install MongoDB Community Edition or use MongoDB Atlas
   - Create a database for the bot
   - Ensure network access is configured properly

2. **SQLite Setup:**
   - No installation required (uses built-in SQLite)
   - Specify path to database file in configuration

3. **Redis Setup:**
   - Install Redis server or use a Redis service
   - Configure for high availability if needed

### Environment Variables

Create a `.env` file in the root directory with the required variables:

```env
# =============================================
# TELEGRAM BOT CONFIGURATION
# =============================================
# Your Telegram bot token from @BotFather
BOT_TOKEN=your_telegram_bot_token_here

# =============================================
# WEBHOOK CONFIGURATION
# =============================================
# URL to which Telegram will send updates (optional, leave empty to use polling)
WEBHOOK_URL=https://yourdomain.com/webhook

# Optional secret token for webhook request validation (recommended)
WEBHOOK_SECRET=your_webhook_secret_token

# Certificate file path for self-signed SSL certificates (optional)
WEBHOOK_CERTIFICATE=path/to/certificate.pem

# Maximum allowed number of simultaneous HTTPS connections to the webhook
WEBHOOK_MAX_CONNECTIONS=40

# List of update types the bot should receive via webhook
ALLOWED_UPDATES=message,edited_channel_post,callback_query

# Enable/disable webhook mode. Set to false to use polling
WEBHOOK_ENABLED=true

# =============================================
# DATABASE CONFIGURATION (Fase1)
# =============================================
# MongoDB connection string
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=yabot

# MongoDB connection pool configuration
MONGODB_MIN_POOL_SIZE=5
MONGODB_MAX_POOL_SIZE=50
MONGODB_MAX_IDLE_TIME=30000
MONGODB_SERVER_SELECTION_TIMEOUT=5000
MONGODB_SOCKET_TIMEOUT=10000

# SQLite database path
SQLITE_DATABASE_PATH=./yabot.db

# SQLite connection pool configuration
SQLITE_POOL_SIZE=20
SQLITE_MAX_OVERFLOW=30
SQLITE_POOL_TIMEOUT=10
SQLITE_POOL_RECYCLE=3600

# =============================================
# REDIS EVENT BUS CONFIGURATION (Fase1)
# =============================================
# Redis connection URL
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# Redis connection configuration
REDIS_MAX_CONNECTIONS=50
REDIS_RETRY_ON_TIMEOUT=true
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=10

# Local queue configuration for when Redis is unavailable
REDIS_LOCAL_QUEUE_MAX_SIZE=1000
REDIS_LOCAL_QUEUE_PERSISTENCE_FILE=event_queue.pkl

# =============================================
# INTERNAL API CONFIGURATION (Fase1)
# =============================================
# Internal API server configuration
API_HOST=localhost
API_PORT=8001
API_WORKERS=1
API_ACCESS_TOKEN_EXPIRE_MINUTES=15
API_REFRESH_TOKEN_EXPIRE_DAYS=7

# SSL certificate paths (optional, for HTTPS)
API_SSL_CERT=
API_SSL_KEY=

# =============================================
# LOGGING CONFIGURATION
# =============================================
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Logging format: 'text' or 'json'
LOG_FORMAT=json

# Optional path to log file (leave empty for console only)
LOG_FILE_PATH=

# Maximum size of log file in bytes before rotation (default: 10MB)
LOG_MAX_FILE_SIZE=10485760

# Number of backup log files to keep
LOG_BACKUP_COUNT=5

# =============================================
# OTHER CONFIGURATION
# =============================================
# Polling timeout in seconds (when using polling mode)
POLLING_TIMEOUT=30

# Maximum number of connections for the bot
MAX_CONNECTIONS=100

# Request timeout in seconds for API calls
REQUEST_TIMEOUT=30

# Enable development mode (more verbose logging, etc.)
DEV_MODE=false
```

### Setting Up Your Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram with `/newbot`
2. Follow the instructions to create your bot
3. Copy the bot token and add it to your `.env` file as `BOT_TOKEN`

## Usage

### Running the Bot

```bash
# With virtual environment activated
python src/main.py
```

### Running Infrastructure Migration

Before running the bot with the new infrastructure, run the migration script:

```bash
python scripts/migrate_to_fase1.py
# For dry run (simulating migration without changes):
# python scripts/migrate_to_fase1.py --dry-run
```

### Local Development with Polling

For local development, the bot can run in polling mode:

1. Set `WEBHOOK_ENABLED=false` in your `.env` file
2. Make sure your database and Redis are running
3. Run the bot normally:
   ```bash
   python src/main.py
   ```

### Production with Webhooks

For production environments, use webhook mode for better performance:

1. Set up HTTPS endpoint on your server
2. Configure `WEBHOOK_URL` in your `.env` file
3. (Optional) Set `WEBHOOK_SECRET` for request validation
4. Ensure MongoDB, SQLite, and Redis are properly configured and accessible
5. Run the bot with webhook enabled

## Project Architecture (Fase1 Enhanced)

The project follows a clean, modular architecture to ensure maintainability and scalability:

```
yabot/
├── src/
│   ├── core/           # Core framework components
│   ├── handlers/       # Message and command handlers
│   ├── services/       # Business logic services
│   ├── database/       # Database abstraction and management
│   ├── events/         # Event bus and processing
│   ├── api/            # Internal REST API components
│   ├── config/         # Configuration management
│   └── utils/          # Shared utilities
├── tests/              # Test suite
├── scripts/            # Migration and utility scripts
├── docs/               # Documentation
├── .env.example        # Example environment variables
├── requirements.txt    # Dependencies
└── README.md          # This file
```

### Core Components (Fase1)

- **BotApplication**: Main application orchestrator that initializes and coordinates all components
- **ConfigManager**: Centralized configuration management with validation and environment support  
- **DatabaseManager**: Unified interface for MongoDB and SQLite operations with connection management
- **EventBus**: Redis-based event publishing and subscription with reliability features
- **UserService**: Unified user data operations across MongoDB and SQLite
- **Router**: Routes incoming messages to appropriate handlers based on message type and content
- **CommandHandler**: Handles bot commands like /start and /menu with standardized response patterns
- **MiddlewareManager**: Manages request/response processing pipeline for cross-cutting concerns
- **WebhookHandler**: Handles webhook endpoint for receiving Telegram updates with security validation
- **ErrorHandler**: Centralized error handling with user-friendly responses and comprehensive logging
- **APIServer**: Internal REST API server for service communication

## Commands

The bot currently supports the following commands:

- `/start` - Welcome message and basic usage instructions
- `/menu` - Display the main menu with available options
- `/help` - Show help documentation with available commands

## Fase1 Infrastructure Features

### Database System
- Dual database support: MongoDB for flexible schema (user states, preferences) and SQLite for ACID compliance (subscriptions, profiles)
- Connection pooling and health monitoring
- Atomic operations across both databases
- Schema creation and validation

### Event-Driven Architecture
- Redis-based event bus with pub/sub functionality
- Local fallback queue when Redis is unavailable
- Event publishing with retry mechanisms
- Event processing reliability features

### Internal APIs
- FastAPI-based internal REST endpoints
- User state management
- Subscription status queries
- Preference updates
- Authentication and security

## Error Handling

The bot implements comprehensive error handling:

- Invalid bot tokens result in clear configuration error messages
- Database connection failures use exponential backoff
- Webhook failures automatically fallback to polling mode
- Network connectivity issues use exponential backoff
- All errors are logged with timestamp, severity, and context
- User-facing errors are friendly and actionable
- Event processing failures include dead letter queue functionality

## Logging

Logging is configured through environment variables:

- `LOG_LEVEL`: Control verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT`: Choose between text or JSON format
- `LOG_FILE_PATH`: Optional file to write logs to (in addition to console)
- Log rotation is supported with configurable max size and backup count

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Make sure to configure MongoDB, SQLite, and Redis
CMD ["python", "src/main.py"]
```

### Direct Deployment

1. Set up your server with Python 3.11+
2. Ensure MongoDB, SQLite, and Redis are installed and running
3. Clone the repository
4. Install dependencies: `pip install -r requirements.txt`
5. Configure environment variables (including database and Redis settings)
6. Run the migration script: `python scripts/migrate_to_fase1.py`
7. Run: `python src/main.py`

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/database/
pytest tests/events/
pytest tests/services/
pytest tests/integration/

# Run tests with coverage
pytest --cov=src/
```

### Code Style

This project follows PEP 8 style guidelines. Code formatting is done with `black`, and linting with `flake8`.

## Security

- Bot tokens are stored securely using environment variables
- Webhook endpoints validate incoming request signatures
- User input is sanitized to prevent injection attacks
- Communication with Telegram API uses HTTPS/TLS encryption
- Webhook requests can be validated using secret tokens
- Internal API endpoints use JWT-based authentication
- Database connections use encrypted connections where available

## Performance

- Database operations complete within 100ms for 95% of requests
- Event publication latency under 10ms for local Redis instances
- API endpoints respond within 200ms for 99% of requests
- Supports up to 10,000 concurrent users
- The bot responds to commands within 3 seconds under normal conditions
- Memory usage stays under 512MB during normal operation

## Support

For support, please open an issue in the repository or contact the maintainers.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see the LICENSE file for details.
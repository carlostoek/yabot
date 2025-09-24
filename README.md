# Yet Another Telegram Bot (YABOT)

A robust, scalable Telegram bot framework built with Aiogram 3, designed with clean architecture principles and best practices. This framework provides essential functionality for user interaction and system management with support for both webhook and polling modes.

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

## Requirements

- Python 3.11 or higher
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
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

## Configuration

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
# LOGGING CONFIGURATION
# =============================================
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Logging format: 'text' or 'json'
LOG_FORMAT=text

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

### Local Development with Polling

For local development, the bot can run in polling mode:

1. Set `WEBHOOK_ENABLED=false` in your `.env` file
2. Run the bot normally:
   ```bash
   python src/main.py
   ```

### Production with Webhooks

For production environments, use webhook mode for better performance:

1. Set up HTTPS endpoint on your server
2. Configure `WEBHOOK_URL` in your `.env` file
3. (Optional) Set `WEBHOOK_SECRET` for request validation
4. Run the bot with webhook enabled

## Project Architecture

The project follows a clean, modular architecture to ensure maintainability and scalability:

```
yabot/
├── src/
│   ├── core/           # Core framework components
│   ├── handlers/       # Message and command handlers
│   ├── services/       # Business logic services
│   ├── config/         # Configuration management
│   └── utils/          # Shared utilities
├── tests/              # Test suite
├── docs/               # Documentation
├── .env.example        # Example environment variables
├── requirements.txt    # Dependencies
└── README.md          # This file
```

### Core Components

- **BotApplication**: Main application orchestrator that initializes and coordinates all components
- **ConfigManager**: Centralized configuration management with validation and environment support  
- **Router**: Routes incoming messages to appropriate handlers based on message type and content
- **CommandHandler**: Handles bot commands like /start and /menu with standardized response patterns
- **MiddlewareManager**: Manages request/response processing pipeline for cross-cutting concerns
- **WebhookHandler**: Handles webhook endpoint for receiving Telegram updates with security validation
- **ErrorHandler**: Centralized error handling with user-friendly responses and comprehensive logging

## Commands

The bot currently supports the following commands:

- `/start` - Welcome message and basic usage instructions
- `/menu` - Display the main menu with available options
- `/help` - Show help documentation with available commands

## Error Handling

The bot implements comprehensive error handling:

- Invalid bot tokens result in clear configuration error messages
- Webhook failures automatically fallback to polling mode
- Network connectivity issues use exponential backoff
- All errors are logged with timestamp, severity, and context
- User-facing errors are friendly and actionable

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

CMD ["python", "src/main.py"]
```

### Direct Deployment

1. Set up your server with Python 3.11+
2. Clone the repository
3. Install dependencies: `pip install -r requirements.txt`
4. Configure environment variables
5. Run: `python src/main.py`

## Development

### Running Tests

```bash
# Run all tests
pytest

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

## Performance

- The bot responds to commands within 3 seconds under normal conditions
- System handles at least 100 concurrent users without performance degradation
- Memory usage stays under 512MB during normal operation
- Failed message deliveries are retried with exponential backoff

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
# Implementation Plan - Fase1: Backend Infrastructure Foundation

## Task Overview

The implementation follows a layered approach, building from core infrastructure to high-level services. Each task is designed to be atomic (15-30 minutes), touches 1-3 files maximum, and has a single testable outcome. The implementation leverages existing YABOT patterns and maintains backward compatibility throughout.

## Steering Document Compliance

All tasks follow existing project structure conventions:
- New components in appropriate `src/` subdirectories
- Existing patterns extended rather than replaced
- Configuration managed through existing `ConfigManager`
- Logging through existing `structlog` infrastructure
- Testing following established patterns in `tests/`

## Atomic Task Requirements

Each task meets these criteria for optimal agent execution:
- **File Scope**: Touches 1-3 related files maximum
- **Time Boxing**: Completable in 15-30 minutes
- **Single Purpose**: One testable outcome per task
- **Specific Files**: Must specify exact files to create/modify
- **Agent-Friendly**: Clear input/output with minimal context switching

## Tasks

### 1. Configuration Infrastructure

- [ ] 1. Create database configuration models in src/core/models.py
  - File: src/core/models.py (modify existing)
  - Add DatabaseConfig, MongoConfig, SQLiteConfig, RedisConfig Pydantic models
  - Extend existing model patterns with proper validation
  - Purpose: Define configuration structure for new infrastructure components
  - _Leverage: src/core/models.py (existing BotConfig, WebhookConfig patterns)_
  - _Requirements: 5.2_

- [ ] 2. Extend ConfigManager with database configuration methods in src/config/manager.py
  - File: src/config/manager.py (modify existing)
  - Add get_database_config(), get_redis_config(), get_api_config() methods
  - Implement environment variable loading with validation and defaults
  - Purpose: Centralize all configuration management in existing ConfigManager
  - _Leverage: src/config/manager.py (existing configuration patterns)_
  - _Requirements: 5.2_

- [ ] 3. Update .env.example with new infrastructure environment variables
  - File: .env.example (modify existing)
  - Add MONGODB_URI, MONGODB_DATABASE, SQLITE_DATABASE_PATH, REDIS_URL variables
  - Include API configuration variables (API_HOST, API_PORT, JWT_SECRET)
  - Purpose: Document required environment configuration for new infrastructure
  - _Leverage: .env.example (existing environment variable patterns)_
  - _Requirements: 5.2_

### 2. Database Layer Foundation

- [ ] 4. Create database connection manager in src/database/__init__.py
  - File: src/database/__init__.py (create new)
  - Initialize database module with imports and base classes
  - Export main components for easy importing
  - Purpose: Set up database module structure
  - _Leverage: src/core/__init__.py (existing module patterns)_
  - _Requirements: 1.1_

- [ ] 5. Create DatabaseManager class in src/database/manager.py
  - File: src/database/manager.py (create new)
  - Implement connection management for MongoDB and SQLite with connection pooling
  - Add health_check(), connect_all(), disconnect_all() methods
  - Purpose: Provide unified database connection interface
  - _Leverage: src/utils/logger.py (existing logging), src/config/manager.py_
  - _Requirements: 1.1_

- [ ] 6. Create basic MongoDB connection class in src/database/mongodb.py
  - File: src/database/mongodb.py (create new)
  - Implement MongoDBConnection class with basic connection setup
  - Add connect() and disconnect() methods using pymongo
  - Purpose: Establish basic MongoDB connection framework
  - _Leverage: src/utils/logger.py, src/config/manager.py_
  - _Requirements: 1.1_

- [ ] 6a. Add connection pooling to MongoDB handler in src/database/mongodb.py
  - File: src/database/mongodb.py (continue from task 6)
  - Add connection pooling configuration and management
  - Implement retry logic with exponential backoff
  - Purpose: Add reliability and performance to MongoDB connections
  - _Leverage: existing connection class, src/utils/logger.py_
  - _Requirements: 1.1_

- [ ] 6b. Add collection access methods to MongoDB handler in src/database/mongodb.py
  - File: src/database/mongodb.py (continue from task 6a)
  - Add get_collection(), health_check() methods
  - Implement collection validation and monitoring
  - Purpose: Provide collection access interface for MongoDB operations
  - _Leverage: existing connection pooling, src/utils/logger.py_
  - _Requirements: 1.2_

- [ ] 7. Create basic SQLite connection class in src/database/sqlite.py
  - File: src/database/sqlite.py (create new)
  - Implement SQLiteConnection class with basic connection setup
  - Add connect() and disconnect() methods with WAL mode
  - Purpose: Establish basic SQLite connection framework
  - _Leverage: src/utils/logger.py, src/config/manager.py_
  - _Requirements: 1.1_

- [ ] 7a. Add connection pooling to SQLite handler in src/database/sqlite.py
  - File: src/database/sqlite.py (continue from task 7)
  - Add SQLAlchemy connection pooling configuration
  - Implement connection timeout and retry handling
  - Purpose: Add performance and reliability to SQLite connections
  - _Leverage: existing connection class, src/utils/logger.py_
  - _Requirements: 1.1_

- [ ] 7b. Add table operations to SQLite handler in src/database/sqlite.py
  - File: src/database/sqlite.py (continue from task 7a)
  - Add create_tables(), health_check() methods
  - Implement schema validation utilities
  - Purpose: Provide table management interface for SQLite operations
  - _Leverage: existing connection pooling, src/utils/logger.py_
  - _Requirements: 1.2_

### 3. Database Schema Setup

- [ ] 8. Create MongoDB schema definitions in src/database/schemas/mongo.py
  - File: src/database/schemas/mongo.py (create new)
  - Define Users, NarrativeFragments, Items collection schemas
  - Implement schema validation and index creation
  - Purpose: Establish MongoDB collection structures and validation
  - _Leverage: src/core/models.py (existing Pydantic patterns)_
  - _Requirements: 1.2_

- [ ] 9. Create SQLite schema definitions in src/database/schemas/sqlite.py
  - File: src/database/schemas/sqlite.py (create new)
  - Define SQL DDL for UserProfiles and Subscriptions tables
  - Implement table creation and migration utilities
  - Purpose: Establish SQLite table structures and constraints
  - _Leverage: src/utils/logger.py_
  - _Requirements: 1.2_

- [ ] 10. Create basic database initialization in src/database/init.py
  - File: src/database/init.py (create new)
  - Implement initialize_databases() function for setup coordination
  - Add basic schema creation calls for MongoDB and SQLite
  - Purpose: Coordinate initial database setup process
  - _Leverage: src/database/manager.py, src/database/schemas/*_
  - _Requirements: 1.2_

- [ ] 10a. Add schema validation to database initialization in src/database/init.py
  - File: src/database/init.py (continue from task 10)
  - Add validate_schemas() function for compatibility checking
  - Implement schema version tracking and validation
  - Purpose: Ensure database schemas are compatible and up-to-date
  - _Leverage: existing initialization, src/database/schemas/*_
  - _Requirements: 1.2_

- [ ] 10b. Add migration detection to database initialization in src/database/init.py
  - File: src/database/init.py (continue from task 10a)
  - Add detect_migrations() and apply_migrations() functions
  - Implement automatic schema update procedures
  - Purpose: Handle database migrations and schema updates
  - _Leverage: existing validation, src/utils/logger.py_
  - _Requirements: 1.2_

### 4. Event Bus Infrastructure

- [ ] 11. Create event bus module structure in src/events/__init__.py
  - File: src/events/__init__.py (create new)
  - Initialize events module with base classes and imports
  - Export EventBus, EventProcessor, and event types
  - Purpose: Set up event system module structure
  - _Leverage: src/core/__init__.py (existing module patterns)_
  - _Requirements: 2.1_

- [ ] 12. Create base event models in src/events/models.py
  - File: src/events/models.py (create new)
  - Define BaseEvent, UserInteractionEvent, ReactionDetectedEvent classes
  - Implement event validation and serialization methods
  - Purpose: Establish event data structures and validation
  - _Leverage: src/core/models.py (existing Pydantic patterns)_
  - _Requirements: 2.2_

- [ ] 13. Create basic Redis event bus in src/events/bus.py
  - File: src/events/bus.py (create new)
  - Implement EventBus class with Redis connection setup
  - Add basic publish() and subscribe() methods
  - Purpose: Establish Redis Pub/Sub foundation
  - _Leverage: src/utils/logger.py, src/config/manager.py_
  - _Requirements: 2.1_

- [ ] 13a. Add retry logic to event bus in src/events/bus.py
  - File: src/events/bus.py (continue from task 13)
  - Add retry logic with exponential backoff for Redis operations
  - Implement health_check() method with connection monitoring
  - Purpose: Add reliability to event publishing and subscription
  - _Leverage: existing EventBus class, src/utils/logger.py_
  - _Requirements: 2.1, 2.2_

- [ ] 13b. Add local fallback queue to event bus in src/events/bus.py
  - File: src/events/bus.py (continue from task 13a)
  - Implement local event queue for Redis fallback
  - Add queue persistence and replay mechanisms
  - Purpose: Ensure event delivery when Redis is unavailable
  - _Leverage: existing retry logic, src/utils/logger.py_
  - _Requirements: 2.1_

- [ ] 14. Create event processor for handling subscriptions in src/events/processor.py
  - File: src/events/processor.py (create new)
  - Implement EventProcessor class for managing event subscriptions
  - Add idempotent processing and dead letter queue handling
  - Purpose: Process events reliably with error handling
  - _Leverage: src/events/bus.py, src/utils/logger.py_
  - _Requirements: 2.3_

### 5. Service Layer Implementation

- [ ] 15. Create services module structure in src/services/__init__.py
  - File: src/services/__init__.py (modify existing)
  - Add imports for new service classes
  - Export UserService, SubscriptionService, NarrativeService
  - Purpose: Set up services module for business logic components
  - _Leverage: existing src/services/__init__.py_
  - _Requirements: 1.3_

- [ ] 16. Create UserService for unified user operations in src/services/user.py
  - File: src/services/user.py (create new)
  - Implement create_user(), get_user_context(), update_user_state() methods
  - Add atomic operations across MongoDB and SQLite
  - Purpose: Provide unified interface for user data operations
  - _Leverage: src/database/manager.py, src/events/bus.py_
  - _Requirements: 1.3_

- [ ] 17. Create SubscriptionService in src/services/subscription.py
  - File: src/services/subscription.py (create new)
  - Implement subscription management and validation methods
  - Add check_subscription_status(), update_subscription() methods
  - Purpose: Handle subscription business logic and validation
  - _Leverage: src/database/manager.py, src/events/bus.py_
  - _Requirements: 3.1_

- [ ] 18. Create NarrativeService in src/services/narrative.py
  - File: src/services/narrative.py (create new)
  - Implement narrative fragment management and progression
  - Add get_fragment(), process_choice(), validate_vip_access() methods
  - Purpose: Manage narrative content and user progression
  - _Leverage: src/database/manager.py, src/services/subscription.py_
  - _Requirements: 4.2_

### 6. Coordination Service

- [ ] 19. Create basic CoordinatorService in src/services/coordinator.py
  - File: src/services/coordinator.py (create new)
  - Implement CoordinatorService class with EventBus integration
  - Add basic event subscription setup and initialization
  - Purpose: Establish coordination service foundation
  - _Leverage: src/events/bus.py, src/utils/logger.py_
  - _Requirements: 3.1_

- [ ] 19a. Add VIP validation workflow to CoordinatorService in src/services/coordinator.py
  - File: src/services/coordinator.py (continue from task 19)
  - Implement validate_vip_access() method
  - Add subscription status checking and access control
  - Purpose: Handle VIP feature access validation workflow
  - _Leverage: existing CoordinatorService, src/services/subscription.py_
  - _Requirements: 3.1_

- [ ] 19b. Add transaction processing to CoordinatorService in src/services/coordinator.py
  - File: src/services/coordinator.py (continue from task 19a)
  - Implement process_transaction() method for besitos
  - Add atomic transaction handling and rollback procedures
  - Purpose: Handle virtual currency transaction workflows
  - _Leverage: existing VIP validation, src/services/user.py_
  - _Requirements: 3.1_

- [ ] 19c. Add user interaction orchestration to CoordinatorService in src/services/coordinator.py
  - File: src/services/coordinator.py (continue from task 19b)
  - Implement process_user_interaction() method
  - Add workflow coordination and service integration
  - Purpose: Orchestrate complex user interaction workflows
  - _Leverage: existing transaction processing, all service dependencies_
  - _Requirements: 3.1, 3.2_

- [ ] 20. Create event ordering buffer in src/events/ordering.py
  - File: src/events/ordering.py (create new)
  - Implement event buffering and chronological ordering
  - Add event sequencing and out-of-order detection
  - Purpose: Ensure events are processed in correct order
  - _Leverage: src/events/models.py, src/utils/logger.py_
  - _Requirements: 3.2_

### 7. API Layer Foundation

- [ ] 21. Create API module structure in src/api/__init__.py
  - File: src/api/__init__.py (create new)
  - Initialize API module with FastAPI components
  - Export APIServer, AuthService, and endpoint routers
  - Purpose: Set up internal API module structure
  - _Leverage: src/core/__init__.py (existing module patterns)_
  - _Requirements: 4.1_

- [ ] 22. Create JWT authentication service in src/api/auth.py
  - File: src/api/auth.py (create new)
  - Implement JWTService with token creation and validation
  - Add service authentication and rate limiting
  - Purpose: Secure internal API endpoints with JWT authentication
  - _Leverage: src/config/manager.py, src/utils/logger.py_
  - _Requirements: 4.3_

- [ ] 23. Create API server setup in src/api/server.py
  - File: src/api/server.py (create new)
  - Implement APIServer class with FastAPI initialization
  - Add middleware for authentication and error handling
  - Purpose: Provide HTTP API server for internal communication
  - _Leverage: src/api/auth.py, src/utils/logger.py_
  - _Requirements: 4.1_

- [ ] 24. Create user API endpoints in src/api/endpoints/users.py
  - File: src/api/endpoints/users.py (create new)
  - Implement GET /user/{id}/state, PUT /user/{id}/preferences endpoints
  - Add request validation and error handling
  - Purpose: Provide user data access via REST API
  - _Leverage: src/services/user.py, src/api/auth.py_
  - _Requirements: 4.2_

- [ ] 25. Create narrative API endpoints in src/api/endpoints/narrative.py
  - File: src/api/endpoints/narrative.py (create new)
  - Implement GET /narrative/{fragment_id} endpoint
  - Add content access control and VIP validation
  - Purpose: Provide narrative content access via REST API
  - _Leverage: src/services/narrative.py, src/api/auth.py_
  - _Requirements: 4.2_

### 8. Handler Integration and Enhancement

- [ ] 26. Enhance CommandHandler with database context in src/handlers/commands.py
  - File: src/handlers/commands.py (modify existing)
  - Add UserService dependency injection and user context retrieval
  - Modify /start and /menu commands to use database services
  - Purpose: Integrate existing handlers with new database services
  - _Leverage: src/handlers/commands.py, src/services/user.py_
  - _Requirements: 5.1, 5.3_

- [ ] 27. Add event publishing to CommandHandler in src/handlers/commands.py
  - File: src/handlers/commands.py (continue modification)
  - Integrate EventBus for publishing user_interaction events
  - Add event publishing on command completion with fallback handling
  - Purpose: Enable event-driven architecture in existing handlers
  - _Leverage: src/events/bus.py, src/events/models.py_
  - _Requirements: 5.3_

- [ ] 28. Enhance WebhookHandler with event publishing in src/handlers/webhook.py
  - File: src/handlers/webhook.py (modify existing)
  - Add EventBus integration for update_received events
  - Implement graceful degradation if event publishing fails
  - Purpose: Publish webhook events for system coordination
  - _Leverage: src/handlers/webhook.py, src/events/bus.py_
  - _Requirements: 5.3_

- [ ] 29. Enhance Router with database context in src/core/router.py
  - File: src/core/router.py (modify existing)
  - Add UserService integration for routing decisions
  - Implement user context retrieval during message routing
  - Purpose: Enable context-aware message routing
  - _Leverage: src/core/router.py, src/services/user.py_
  - _Requirements: 5.1_

### 9. Middleware and Dependency Injection

- [ ] 30. Create database middleware in src/core/middleware.py
  - File: src/core/middleware.py (modify existing)
  - Add DatabaseMiddleware class for injecting database services
  - Implement service context management for handlers
  - Purpose: Provide database services to handlers via middleware
  - _Leverage: src/core/middleware.py, src/database/manager.py_
  - _Requirements: 5.1_

- [ ] 31. Add database initialization to BotApplication in src/core/application.py
  - File: src/core/application.py (modify existing)
  - Add _setup_database() method to initialize DatabaseManager
  - Integrate database initialization in existing startup sequence
  - Purpose: Initialize database infrastructure during bot startup
  - _Leverage: src/core/application.py, src/database/manager.py_
  - _Requirements: 5.1_

- [ ] 31a. Add event bus initialization to BotApplication in src/core/application.py
  - File: src/core/application.py (continue from task 31)
  - Add _setup_event_bus() method to initialize EventBus and CoordinatorService
  - Integrate event system in existing startup sequence
  - Purpose: Initialize event infrastructure during bot startup
  - _Leverage: existing database setup, src/events/bus.py, src/services/coordinator.py_
  - _Requirements: 5.1_

- [ ] 31b. Add API server initialization to BotApplication in src/core/application.py
  - File: src/core/application.py (continue from task 31a)
  - Add _setup_api_server() method to initialize internal API
  - Add graceful shutdown procedures for all new components
  - Purpose: Initialize API infrastructure and complete startup integration
  - _Leverage: existing event bus setup, src/api/server.py_
  - _Requirements: 5.1_

### 10. Error Handling and Health Monitoring

- [ ] 32. Create health check manager in src/utils/health.py
  - File: src/utils/health.py (create new)
  - Implement HealthCheckManager with database and Redis monitoring
  - Add health check endpoints for all infrastructure components
  - Purpose: Monitor system health and component availability
  - _Leverage: src/database/manager.py, src/events/bus.py, src/utils/logger.py_
  - _Requirements: Reliability NFR_

- [ ] 33. Enhance ErrorHandler with infrastructure errors in src/core/error_handler.py
  - File: src/core/error_handler.py (modify existing)
  - Add database error handling, Redis failures, and API errors
  - Implement circuit breaker patterns and graceful degradation
  - Purpose: Handle new infrastructure component errors gracefully
  - _Leverage: src/core/error_handler.py, src/utils/logger.py_
  - _Requirements: Error Handling design section_

### 11. Testing Infrastructure

- [ ] 34. Create database test utilities in tests/utils/database.py
  - File: tests/utils/database.py (create new)
  - Implement test database setup, fixtures, and cleanup utilities
  - Add MongoDB and SQLite test database management
  - Purpose: Support testing of database-dependent components
  - _Leverage: tests/conftest.py (existing test patterns)_
  - _Requirements: Testing Strategy_

- [ ] 35. Create event bus test utilities in tests/utils/events.py
  - File: tests/utils/events.py (create new)
  - Implement mock EventBus and test event utilities
  - Add event testing helpers and verification methods
  - Purpose: Support testing of event-driven components
  - _Leverage: tests/conftest.py, tests/utils/database.py_
  - _Requirements: Testing Strategy_

- [ ] 36. Create UserService unit tests in tests/services/test_user.py
  - File: tests/services/test_user.py (create new)
  - Test create_user(), get_user_context(), update operations
  - Mock database dependencies and verify atomic operations
  - Purpose: Ensure UserService reliability and correct behavior
  - _Leverage: tests/utils/database.py, tests/utils/events.py_
  - _Requirements: 1.3_

- [ ] 37. Create DatabaseManager unit tests in tests/database/test_manager.py
  - File: tests/database/test_manager.py (create new)
  - Test connection management, health checks, and error handling
  - Mock database connections and verify retry logic
  - Purpose: Ensure database layer reliability and connection management
  - _Leverage: tests/utils/database.py_
  - _Requirements: 1.1_

- [ ] 38. Create EventBus unit tests in tests/events/test_bus.py
  - File: tests/events/test_bus.py (create new)
  - Test event publishing, subscription, and fallback mechanisms
  - Mock Redis connections and verify reliability features
  - Purpose: Ensure event bus reliability and message delivery
  - _Leverage: tests/utils/events.py_
  - _Requirements: 2.1, 2.2_

### 12. Integration Testing

- [ ] 39. Create handler integration tests in tests/integration/test_handlers.py
  - File: tests/integration/test_handlers.py (create new)
  - Test enhanced CommandHandler and WebhookHandler with real services
  - Verify event publishing and database operations
  - Purpose: Ensure handlers work correctly with new infrastructure
  - _Leverage: tests/utils/database.py, tests/utils/events.py_
  - _Requirements: 5.3_

- [ ] 40. Create API integration tests in tests/integration/test_api.py
  - File: tests/integration/test_api.py (create new)
  - Test API endpoints with authentication and database operations
  - Verify request/response handling and error scenarios
  - Purpose: Ensure API layer works correctly with services
  - _Leverage: tests/utils/database.py_
  - _Requirements: 4.1, 4.2_

- [ ] 41. Create end-to-end workflow tests in tests/integration/test_workflows.py
  - File: tests/integration/test_workflows.py (create new)
  - Test complete user registration and VIP access workflows
  - Verify event coordination and service interactions
  - Purpose: Ensure complete system functionality and integration
  - _Leverage: tests/utils/database.py, tests/utils/events.py_
  - _Requirements: All requirements integration_

### 13. Documentation and Configuration

- [ ] 42. Update requirements.txt with new dependencies
  - File: requirements.txt (modify existing)
  - Add FastAPI, MongoDB driver, Redis client, SQLAlchemy dependencies
  - Specify versions compatible with existing dependencies
  - Purpose: Document and manage new infrastructure dependencies
  - _Leverage: requirements.txt (existing dependencies)_
  - _Requirements: Infrastructure dependencies_

- [ ] 43. Create migration scripts in scripts/migrate_to_fase1.py
  - File: scripts/migrate_to_fase1.py (create new)
  - Implement zero-downtime migration procedures
  - Add rollback capabilities and data validation
  - Purpose: Enable safe production deployment of new infrastructure
  - _Leverage: src/database/manager.py, src/services/user.py_
  - _Requirements: 5.4_

- [ ] 44. Update README.md with infrastructure setup instructions
  - File: README.md (modify existing)
  - Add database setup, Redis configuration, and API deployment instructions
  - Document new environment variables and configuration options
  - Purpose: Provide deployment and configuration guidance
  - _Leverage: README.md (existing documentation patterns)_
  - _Requirements: Documentation_
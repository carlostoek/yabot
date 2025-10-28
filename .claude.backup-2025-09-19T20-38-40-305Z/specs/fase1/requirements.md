# Requirements Document - Fase1: Backend Infrastructure Foundation

## Introduction

Fase1 establishes the foundational backend infrastructure for the YABOT system, building upon the existing Telegram bot framework to create a scalable, event-driven architecture. This phase adds persistent data storage, event coordination, and internal APIs to support advanced bot features like dynamic narratives, user state management, and subscription services.

## Alignment with Product Vision

This foundational infrastructure enables the YABOT system to evolve from a simple command-response bot to a sophisticated narrative engine capable of:
- Managing complex user interactions and state persistence
- Coordinating events across multiple system components
- Supporting premium features through subscription management
- Scaling horizontally through distributed event architecture

## Requirements

### Requirement 1.1: Central Database System

**User Story:** As a system administrator, I want dual database support for different data types, so that the system can optimize for both dynamic state management and transactional data integrity.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL establish connections to both MongoDB and SQLite databases
2. IF MongoDB connection fails THEN the system SHALL log the error and attempt reconnection with exponential backoff
3. WHEN storing user dynamic states (narrative progress, current menu) THEN the system SHALL use MongoDB for flexible schema requirements
4. WHEN storing subscription data and user profiles THEN the system SHALL use SQLite for ACID compliance and referential integrity
5. IF database operations fail THEN the system SHALL implement graceful fallback mechanisms and maintain service availability

### Requirement 1.2: Database Collections and Tables

**User Story:** As a developer, I want predefined data schemas for core entities, so that I can build features with consistent data structures.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL create/verify the following MongoDB collections:
   - Users (dynamic state, preferences, current context)
   - NarrativeFragments (story content, choices, metadata)
   - Items (virtual items, gifts, achievements)
2. WHEN the system starts THEN it SHALL create/verify the following SQLite tables:
   - Subscriptions (user_id, plan, status, dates)
   - UserProfiles (user_id, telegram_data, registration_info)
3. IF collection/table creation fails THEN the system SHALL log detailed error information and prevent startup
4. WHEN accessing collections/tables THEN the system SHALL validate schema compatibility

### Requirement 1.3: User CRUD Operations

**User Story:** As the bot application, I want basic user management operations, so that I can handle user registration, updates, and data retrieval efficiently.

#### Acceptance Criteria

1. WHEN a new user interacts with the bot THEN the system SHALL create user records in both databases atomically
2. WHEN updating user state THEN the system SHALL update MongoDB for dynamic data and SQLite for profile data as appropriate
3. WHEN retrieving user data THEN the system SHALL provide a unified interface that combines data from both databases
4. IF user creation fails THEN the system SHALL rollback all changes and return appropriate error responses
5. WHEN deleting a user THEN the system SHALL remove data from both databases and publish user_deleted event

### Requirement 2.1: Redis Event Bus Configuration

**User Story:** As a system architect, I want a centralized event bus using Redis Pub/Sub, so that system components can communicate asynchronously and remain loosely coupled.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL establish Redis connection with connection pooling
2. IF Redis connection fails THEN the system SHALL retry with exponential backoff and log connection status
3. WHEN Redis is unavailable THEN the system SHALL queue events locally and replay them when connection is restored
4. WHEN configuring Redis THEN the system SHALL support clustering and sentinel configurations for high availability

### Requirement 2.2: Event Publication and Subscription

**User Story:** As a developer, I want to publish and subscribe to system events, so that I can build reactive features that respond to user actions and system state changes.

#### Acceptance Criteria

1. WHEN a user reacts to content THEN the system SHALL publish a "reaction_detected" event with user_id, content_id, and reaction_type
2. WHEN a user makes a narrative choice THEN the system SHALL publish a "decision_made" event with user_id, choice_id, and context
3. WHEN a subscription changes THEN the system SHALL publish "subscription_updated" event with user_id and new status
4. WHEN events are published THEN they SHALL include timestamp, event_id, and correlation_id for tracing
5. IF event publication fails THEN the system SHALL retry up to 3 times and log failures for monitoring

### Requirement 2.3: Event Processing Reliability

**User Story:** As a system operator, I want reliable event processing with proper error handling, so that the system remains stable and events are not lost.

#### Acceptance Criteria

1. WHEN subscribing to events THEN handlers SHALL implement idempotent processing to handle duplicate events
2. IF event processing fails THEN the system SHALL implement dead letter queues for failed events
3. WHEN processing events THEN the system SHALL maintain processing metrics and health monitoring
4. WHEN the system shuts down THEN it SHALL gracefully finish processing current events before terminating

### Requirement 3.1: Coordinator Service Architecture

**User Story:** As a system designer, I want a lightweight coordination service, so that complex business flows can be orchestrated reliably across system components.

#### Acceptance Criteria

1. WHEN the coordinator starts THEN it SHALL register as an event subscriber for critical business events
2. WHEN a VIP narrative is requested THEN the coordinator SHALL validate subscription status before allowing access
3. WHEN besitos transactions occur THEN the coordinator SHALL ensure atomicity across user balance updates
4. IF coordination fails THEN the system SHALL implement compensation patterns to maintain data consistency
5. WHEN processing workflows THEN the coordinator SHALL maintain state in persistent storage for crash recovery

### Requirement 3.2: Event Ordering and Sequencing

**User Story:** As a business logic implementer, I want events to be processed in the correct order, so that user experiences remain consistent and business rules are properly enforced.

#### Acceptance Criteria

1. WHEN multiple events affect the same user THEN the coordinator SHALL process them in chronological order
2. WHEN a reaction leads to besitos reward THEN the system SHALL process reaction_detected before besitos_awarded
3. WHEN besitos are awarded THEN the system SHALL process besitos_awarded before narrative_hint_unlocked
4. IF events arrive out of order THEN the coordinator SHALL buffer and reorder them based on timestamps
5. WHEN event ordering fails THEN the system SHALL alert administrators and maintain audit logs

### Requirement 4.1: Internal REST API Framework

**User Story:** As a developer, I want standardized REST APIs for internal service communication, so that system components can interact synchronously when needed.

#### Acceptance Criteria

1. WHEN the API service starts THEN it SHALL expose endpoints following OpenAPI 3.0 specification
2. WHEN handling requests THEN the system SHALL implement standard HTTP methods (GET, POST, PUT, DELETE)
3. WHEN returning responses THEN the system SHALL use consistent JSON format with proper HTTP status codes
4. IF API requests fail THEN the system SHALL return standardized error responses with error codes and messages
5. WHEN APIs are modified THEN the system SHALL maintain backward compatibility for existing consumers

### Requirement 4.2: Core API Endpoints

**User Story:** As a system component, I want specific API endpoints for common operations, so that I can retrieve and update system state efficiently.

#### Acceptance Criteria

1. WHEN requesting user state THEN GET /api/v1/user/{id}/state SHALL return complete user context from MongoDB
2. WHEN requesting narrative content THEN GET /api/v1/narrative/{fragment_id} SHALL return story fragment with metadata
3. WHEN updating user preferences THEN PUT /api/v1/user/{id}/preferences SHALL update MongoDB and return confirmation
4. WHEN querying subscriptions THEN GET /api/v1/user/{id}/subscription SHALL return current subscription status from SQLite
5. IF requested resources don't exist THEN APIs SHALL return 404 status with helpful error messages

### Requirement 4.3: API Authentication and Security

**User Story:** As a security administrator, I want internal APIs to be properly secured, so that only authorized system components can access sensitive data.

#### Acceptance Criteria

1. WHEN accessing APIs THEN requests SHALL include valid JWT tokens in Authorization headers
2. WHEN tokens are invalid or expired THEN the system SHALL return 401 Unauthorized responses
3. WHEN generating tokens THEN the system SHALL include appropriate claims for service identification
4. WHEN handling sensitive data THEN APIs SHALL implement request/response encryption for inter-service communication
5. IF authentication fails repeatedly THEN the system SHALL implement rate limiting and alert monitoring

### Requirement 5.1: Aiogram 3 Framework Integration

**User Story:** As a developer, I want the new infrastructure to integrate seamlessly with the existing Aiogram 3 bot framework, so that existing functionality continues to work while gaining new capabilities.

#### Acceptance Criteria

1. WHEN the BotApplication starts THEN it SHALL initialize database connections before setting up Aiogram dispatcher
2. WHEN setting up handlers THEN the existing CommandHandler and WebhookHandler SHALL be extended to support event publishing
3. WHEN processing Telegram updates THEN the Router SHALL integrate with database services for user context retrieval
4. WHEN middleware processes requests THEN it SHALL have access to database services through dependency injection
5. IF new infrastructure components fail THEN the basic bot functionality SHALL continue to work with graceful degradation

### Requirement 5.2: Configuration Manager Extension

**User Story:** As a system administrator, I want database and event system configuration to integrate with the existing ConfigManager, so that all system configuration is centralized and consistent.

#### Acceptance Criteria

1. WHEN the system starts THEN ConfigManager SHALL load database connection strings from environment variables
2. WHEN configuring MongoDB THEN the system SHALL use MONGODB_URI, MONGODB_DATABASE environment variables
3. WHEN configuring SQLite THEN the system SHALL use SQLITE_DATABASE_PATH environment variable with default fallback
4. WHEN configuring Redis THEN the system SHALL use REDIS_URL, REDIS_PASSWORD environment variables
5. IF configuration is invalid THEN the system SHALL prevent startup and provide detailed validation errors

### Requirement 5.3: Handler Integration and Event Publishing

**User Story:** As a bot developer, I want existing handlers to automatically publish relevant events, so that the event-driven architecture works without major code changes.

#### Acceptance Criteria

1. WHEN a user sends /start command THEN CommandHandler SHALL publish user_interaction event
2. WHEN processing webhook updates THEN WebhookHandler SHALL publish update_received event
3. WHEN handlers process messages THEN they SHALL access user context from database through injected services
4. WHEN handler operations complete THEN they SHALL publish completion events with operation results
5. IF event publishing fails THEN handlers SHALL continue normal operation and log the failure

### Requirement 5.4: Migration and Backward Compatibility

**User Story:** As a system operator, I want to migrate existing bot functionality to the new infrastructure without service interruption, so that users experience no downtime.

#### Acceptance Criteria

1. WHEN deploying new infrastructure THEN existing webhook and polling functionality SHALL continue to work
2. WHEN migrating user data THEN the system SHALL create database records for existing active users
3. WHEN running in migration mode THEN the system SHALL support both old and new data access patterns
4. IF migration fails THEN the system SHALL rollback to previous functionality automatically
5. WHEN migration is complete THEN old data access patterns SHALL be deprecated with warning logs

## Non-Functional Requirements

### Performance
- Database operations SHALL complete within 100ms for 95% of requests
- Event publication SHALL have latency under 10ms for local Redis instances
- API endpoints SHALL respond within 200ms for 99% of requests
- The system SHALL support up to 10,000 concurrent users

### Security
- All database connections SHALL use encrypted connections (TLS/SSL)
- Redis connections SHALL use authentication and encryption in production
- Internal APIs SHALL validate all input parameters against schema definitions
- Sensitive data (tokens, credentials) SHALL never be logged in plain text

### Reliability
- The system SHALL achieve 99.5% uptime
- Database failover SHALL complete within 30 seconds
- Event processing SHALL implement at-least-once delivery guarantees
- All components SHALL implement health check endpoints

### Scalability
- Database connections SHALL use connection pooling with configurable limits
- Redis SHALL support clustering for horizontal scaling
- The coordinator service SHALL be stateless to enable multiple instances
- APIs SHALL support horizontal scaling through load balancing
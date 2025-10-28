# fase1 - Task 11

Execute task 11 for the fase1 specification.

## Task Description
Create event bus module structure in src/events/__init__.py

## Code Reuse
**Leverage existing code**: src/core/

## Requirements Reference
**Requirements**: 2.1

## Usage
```
/Task:11-fase1
```

## Instructions

Execute with @spec-task-executor agent the following task: "Create event bus module structure in src/events/__init__.py"

```
Use the @spec-task-executor agent to implement task 11: "Create event bus module structure in src/events/__init__.py" for the fase1 specification and include all the below context.

# Steering Context
## Steering Documents Context

No steering documents found or all are empty.

# Specification Context
## Specification Context (Pre-loaded): fase1

### Requirements
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

---

### Design
# Design Document - Fase1: Backend Infrastructure Foundation

## Overview

The Fase1 design extends the existing YABOT Telegram bot framework with foundational backend infrastructure components. The design maintains the current layered architecture while adding persistent data storage, event-driven communication, and internal APIs. The new components integrate seamlessly with existing Aiogram 3 patterns, ensuring backward compatibility and graceful degradation.

## Steering Document Alignment

### Technical Standards
- **Python 3.11+ Compatibility**: All new components follow existing Python version requirements
- **Pydantic Models**: Extend existing model patterns for configuration and data validation
- **Structured Logging**: Integrate with existing `structlog` implementation in `src/utils/logger.py`
- **Environment Configuration**: Extend existing `ConfigManager` patterns for new infrastructure components

### Project Structure
- **src/core/**: Core framework components (existing pattern maintained)
- **src/services/**: New business logic services for database and event management
- **src/database/**: New database abstraction and connection management
- **src/events/**: New event bus and coordination services
- **src/api/**: New internal REST API components
- **tests/**: Comprehensive testing following existing patterns

## Code Reuse Analysis

### Existing Components to Leverage

- **ConfigManager**: Extended to handle database and Redis configurations
- **Middleware Framework**: Enhanced to provide database context to handlers
- **Logger Utilities**: Reused for consistent logging across all new components
- **Error Handling**: Extended existing `ErrorHandler` for database and event errors
- **BaseHandler**: Pattern extended for event-aware handler implementations

### Integration Points

- **BotApplication**: Modified to initialize new infrastructure components during startup
- **Router**: Enhanced to provide database context for message routing decisions
- **CommandHandler/WebhookHandler**: Extended to publish events and access user context
- **MiddlewareManager**: Enhanced to inject database services into request pipeline

## Architecture

The enhanced architecture maintains existing patterns while adding three new layers: Database Services, Event Bus, and Internal APIs.

```mermaid
graph TB
    subgraph "Telegram Bot Layer (Existing)"
        TG[Telegram API]
        WH[WebhookHandler]
        CH[CommandHandler]
        RT[Router]
        MW[MiddlewareManager]
        EH[ErrorHandler]
    end

    subgraph "Application Layer (Enhanced)"
        BA[BotApplication]
        CM[ConfigManager]
    end

    subgraph "Service Layer (New)"
        US[UserService]
        NS[NarrativeService]
        SS[SubscriptionService]
        CS[CoordinatorService]
    end

    subgraph "Database Layer (New)"
        DM[DatabaseManager]
        MDB[(MongoDB)]
        SQL[(SQLite)]
    end

    subgraph "Event Layer (New)"
        EB[EventBus]
        EP[EventProcessor]
        RD[(Redis)]
    end

    subgraph "API Layer (New)"
        AS[APIServer]
        AU[AuthService]
        AE[API Endpoints]
    end

    TG --> WH
    TG --> CH
    WH --> RT
    CH --> RT
    RT --> MW
    MW --> US
    MW --> NS
    MW --> SS

    BA --> DM
    BA --> EB
    BA --> AS
    BA --> CM

    US --> DM
    NS --> DM
    SS --> DM
    CS --> DM
    CS --> EB

    DM --> MDB
    DM --> SQL

    EB --> RD
    EP --> EB
    CS --> EP

    AS --> AU
    AS --> AE
    AE --> US
    AE --> NS
    AE --> SS
```

## Components and Interfaces

### DatabaseManager (New)
- **Purpose**: Unified interface for MongoDB and SQLite operations with connection management
- **Interfaces**:
  - `connect_all()`: Initialize all database connections
  - `get_mongo_db()`: Get MongoDB connection
  - `get_sqlite_conn()`: Get SQLite connection
  - `health_check()`: Check database connectivity
- **Dependencies**: ConfigManager, Logger
- **Reuses**: Existing configuration patterns and logging infrastructure

### UserService (New)
- **Purpose**: Unified user data operations across MongoDB and SQLite
- **Interfaces**:
  - `create_user(telegram_user)`: Create user in both databases atomically
  - `get_user_context(user_id)`: Retrieve complete user context
  - `update_user_state(user_id, state)`: Update MongoDB dynamic state
  - `update_user_profile(user_id, profile)`: Update SQLite profile data
- **Dependencies**: DatabaseManager, EventBus
- **Reuses**: Existing model validation patterns

### EventBus (New)
- **Purpose**: Redis Pub/Sub wrapper with reliability features
- **Interfaces**:
  - `publish(event_name, payload)`: Publish event with retry logic
  - `subscribe(event_name, handler)`: Subscribe to events
  - `health_check()`: Check Redis connectivity
- **Dependencies**: ConfigManager, Logger
- **Reuses**: Existing configuration and logging patterns

### CoordinatorService (New)
- **Purpose**: Orchestrates complex business workflows and event sequencing
- **Interfaces**:
  - `process_user_interaction(user_id, action)`: Handle user interaction workflows
  - `validate_vip_access(user_id)`: Check subscription before VIP features
  - `process_besitos_transaction(user_id, amount)`: Handle virtual currency transactions
- **Dependencies**: UserService, EventBus, SubscriptionService
- **Reuses**: Existing handler patterns and error handling

### APIServer (New)
- **Purpose**: Internal REST API server with authentication
- **Interfaces**:
  - `start_server()`: Start FastAPI server
  - `register_endpoints()`: Register API routes
  - `authenticate_request(token)`: JWT token validation
- **Dependencies**: UserService, AuthService
- **Reuses**: Existing error handling and logging patterns

### Enhanced BotApplication
- **Purpose**: Extended to initialize new infrastructure components
- **New Methods**:
  - `_setup_database()`: Initialize DatabaseManager
  - `_setup_event_bus()`: Initialize EventBus and CoordinatorService
  - `_setup_api_server()`: Initialize internal API server
- **Dependencies**: All new service components
- **Reuses**: Existing initialization patterns and error handling

### Enhanced ConfigManager
- **Purpose**: Extended to handle database and Redis configuration
- **New Methods**:
  - `get_database_config()`: MongoDB and SQLite configuration
  - `get_redis_config()`: Redis connection configuration
  - `get_api_config()`: Internal API server configuration
- **Dependencies**: Existing environment loading
- **Reuses**: Existing validation and configuration patterns

## Data Models

### MongoDB Collections

#### Users Collection
```python
{
    "user_id": "12345",  # Telegram user ID (primary key)
    "current_state": {
        "menu_context": "main_menu",
        "narrative_progress": {
            "current_fragment": "fragment_001",
            "completed_fragments": ["intro_001", "intro_002"],
            "choices_made": [{"fragment": "intro_002", "choice": "option_a"}]
        },
        "session_data": {"last_activity": "2025-01-15T10:30:00Z"}
    },
    "preferences": {
        "language": "es",
        "notifications_enabled": true,
        "theme": "default"
    },
    "created_at": "2025-01-15T08:00:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

#### NarrativeFragments Collection
```python
{
    "fragment_id": "fragment_001",
    "title": "El Comienzo",
    "content": "Tu aventura comienza aquí...",
    "choices": [
        {"id": "choice_a", "text": "Explorar el bosque", "next_fragment": "forest_001"},
        {"id": "choice_b", "text": "Ir al pueblo", "next_fragment": "village_001"}
    ],
    "metadata": {
        "difficulty": "easy",
        "tags": ["intro", "adventure"],
        "vip_required": false
    },
    "created_at": "2025-01-15T08:00:00Z"
}
```

#### Items Collection
```python
{
    "item_id": "besito_001",
    "name": "Besito Virtual",
    "type": "currency",
    "metadata": {
        "value": 1,
        "emoji": "😘",
        "description": "Un besito virtual lleno de cariño"
    },
    "created_at": "2025-01-15T08:00:00Z"
}
```

### SQLite Tables

#### UserProfiles Table
```sql
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    telegram_user_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    is_active BOOLEAN DEFAULT 1
);
```

#### Subscriptions Table
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('free', 'premium', 'vip')),
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled', 'expired')),
    start_date DATETIME NOT NULL,
    end_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);
```

## Error Handling

### Error Scenarios

1. **Database Connection Failures**
   - **Handling**: Exponential backoff retry with circuit breaker pattern
   - **User Impact**: Graceful degradation - basic bot functions continue
   - **Recovery**: Background reconnection attempts with health monitoring

2. **Redis Event Bus Unavailable**
   - **Handling**: Local event queue with replay capability
   - **User Impact**: No immediate impact - events processed when Redis recovers
   - **Recovery**: Automatic replay of queued events on reconnection

3. **Coordinator Service Failures**
   - **Handling**: Compensation patterns and transaction rollback
   - **User Impact**: Error messages with retry options
   - **Recovery**: State recovery from persistent storage

4. **API Authentication Failures**
   - **Handling**: Rate limiting and security monitoring
   - **User Impact**: Internal component failures logged for investigation
   - **Recovery**: Token refresh and automatic retry mechanisms

## Integration Flow Examples

### User Registration Flow
```mermaid
sequenceDiagram
    participant TG as Telegram
    participant WH as WebhookHandler
    participant US as UserService
    participant DB as DatabaseManager
    participant EB as EventBus

    TG->>WH: /start command
    WH->>US: create_user(telegram_user)
    US->>DB: BEGIN transaction
    US->>DB: Create SQLite user_profile
    US->>DB: Create MongoDB user document
    US->>DB: COMMIT transaction
    US->>EB: publish("user_registered", user_data)
    US->>WH: user created successfully
    WH->>TG: Welcome message
```

### VIP Feature Access Flow
```mermaid
sequenceDiagram
    participant CH as CommandHandler
    participant CS as CoordinatorService
    participant SS as SubscriptionService
    participant US as UserService
    participant EB as EventBus

    CH->>CS: validate_vip_access(user_id)
    CS->>SS: check_subscription_status(user_id)
    SS->>CS: subscription_active=true
    CS->>US: get_user_context(user_id)
    CS->>EB: publish("vip_access_granted", user_data)
    CS->>CH: access_granted=true
    CH->>CH: proceed with VIP feature
```

## Performance Implementation Details

### Database Connection Pooling
```python
# MongoDB Configuration
MONGODB_CONFIG = {
    "min_pool_size": 5,
    "max_pool_size": 50,
    "max_idle_time": 30000,  # 30 seconds
    "server_selection_timeout": 5000,  # 5 seconds
    "socket_timeout": 10000  # 10 seconds
}

# SQLite Configuration
SQLITE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 10,
    "pool_recycle": 3600  # 1 hour
}
```

### Event Bus Configuration
```python
REDIS_CONFIG = {
    "connection_pool": {
        "max_connections": 50,
        "retry_on_timeout": True,
        "socket_connect_timeout": 5,
        "socket_timeout": 10
    },
    "local_queue": {
        "max_size": 1000,
        "persistence_file": "event_queue.pkl"
    }
}
```

## Event Schemas and Validation

### Core Event Schema
```python
@dataclass
class BaseEvent:
    event_id: str
    event_type: str
    timestamp: datetime
    correlation_id: str
    user_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        return all([self.event_id, self.event_type, self.timestamp])

# Specific Event Types
@dataclass
class UserInteractionEvent(BaseEvent):
    action: str  # "start", "menu", "choice"
    context: Dict[str, Any]

@dataclass
class ReactionDetectedEvent(BaseEvent):
    content_id: str
    reaction_type: str
    metadata: Dict[str, Any]
```

## Migration and Deployment Strategy

### Zero-Downtime Migration Procedure

#### Phase 1: Infrastructure Setup (Week 1)
1. **Database Setup**:
   - Deploy MongoDB cluster with replica set
   - Configure SQLite database with WAL mode
   - Set up Redis cluster with sentinel

2. **Configuration**:
   - Add database environment variables to production
   - Update ConfigManager with fallback mechanisms
   - Deploy configuration validation

#### Phase 2: Service Deployment (Week 2)
1. **Service Layer**:
   - Deploy DatabaseManager with connection pooling
   - Deploy EventBus with local fallback queues
   - Deploy UserService with dual write capability

2. **Validation**:
   - Run health checks on all new components
   - Validate database connectivity and performance
   - Test event publishing and subscription

#### Phase 3: Handler Integration (Week 3)
1. **Handler Enhancement**:
   - Update CommandHandler to use UserService
   - Enhance WebhookHandler with event publishing
   - Deploy Router with database context

2. **Migration Mode**:
   - Enable dual read/write for existing users
   - Migrate existing user data to new schema
   - Validate data consistency

#### Phase 4: Full Activation (Week 4)
1. **Complete Migration**:
   - Switch to new data access patterns
   - Deprecate old data access methods
   - Monitor system performance and stability

### Rollback Procedures
```python
class MigrationManager:
    def rollback_to_previous_version(self):
        # 1. Stop new service components
        # 2. Revert handler modifications
        # 3. Switch back to old data patterns
        # 4. Validate system functionality
        pass
```

## Security Implementation Details

### JWT Token Configuration
```python
JWT_CONFIG = {
    "algorithm": "RS256",
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 7,
    "issuer": "yabot-api",
    "audience": "yabot-internal"
}

class JWTService:
    def create_service_token(self, service_name: str) -> str:
        payload = {
            "sub": service_name,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "iss": JWT_CONFIG["issuer"],
            "aud": JWT_CONFIG["audience"],
            "scope": ["internal_api"]
        }
        return jwt.encode(payload, PRIVATE_KEY, algorithm=JWT_CONFIG["algorithm"])
```

### Database Encryption
```python
# MongoDB Connection with TLS
MONGODB_URI = "mongodb://username:password@host:port/database?ssl=true&ssl_cert_reqs=CERT_REQUIRED"

# SQLite Connection with Encryption
SQLITE_CONNECTION = "file:database.db?cache=shared&_fk=1&_cipher_page_size=4096"
```

## API Endpoint Specifications

### OpenAPI Schema
```yaml
openapi: 3.0.0
info:
  title: YABOT Internal API
  version: 1.0.0

paths:
  /api/v1/user/{user_id}/state:
    get:
      summary: Get user state
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: User state retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserState'
        '404':
          description: User not found
        '401':
          description: Unauthorized

components:
  schemas:
    UserState:
      type: object
      properties:
        user_id:
          type: string
        current_state:
          type: object
        preferences:
          type: object
        last_activity:
          type: string
          format: date-time
```

## Monitoring and Observability

### Health Check Endpoints
```python
class HealthCheckManager:
    async def check_database_health(self) -> Dict[str, bool]:
        return {
            "mongodb": await self._check_mongodb(),
            "sqlite": await self._check_sqlite()
        }

    async def check_redis_health(self) -> Dict[str, Any]:
        return {
            "connected": await self._check_redis_connection(),
            "latency_ms": await self._measure_redis_latency()
        }
```

### Performance Metrics
```python
# Metrics collection for monitoring
PERFORMANCE_METRICS = {
    "database_operations": {
        "create_user": "histogram",
        "get_user_context": "histogram",
        "update_user_state": "histogram"
    },
    "event_processing": {
        "event_publish_latency": "histogram",
        "event_processing_time": "histogram",
        "failed_events": "counter"
    },
    "api_endpoints": {
        "request_duration": "histogram",
        "request_count": "counter",
        "error_rate": "gauge"
    }
}
```

## Testing Strategy

### Unit Testing
- **Database Layer**: Mock connections, test retry logic and fallback mechanisms
- **Service Layer**: Mock dependencies, test business logic and error handling
- **Event Layer**: Mock Redis, test event publishing and subscription reliability
- **API Layer**: Test endpoints, authentication, and error responses

### Integration Testing
- **Database Integration**: Test MongoDB and SQLite operations with real databases
- **Event Flow Testing**: Test complete event publishing and subscription cycles
- **Bot Integration**: Test enhanced handlers with database and event context
- **API Integration**: Test internal API calls with authentication

### Performance Testing
- **Load Testing**: 10,000 concurrent users with realistic interaction patterns
- **Database Performance**: Validate 100ms response time requirements
- **Event Latency**: Verify 10ms event publication targets
- **API Response Times**: Ensure 200ms response time for 99% of requests

### End-to-End Testing
- **User Registration**: Complete flow from Telegram interaction to database persistence
- **VIP Access**: Full workflow including subscription validation and event coordination
- **Error Recovery**: Test system behavior during component failures and recovery
- **Migration Testing**: Validate zero-downtime deployment procedures

**Note**: Specification documents have been pre-loaded. Do not use get-content to fetch them again.

## Task Details
- Task ID: 11
- Description: Create event bus module structure in src/events/__init__.py
- Leverage: src/core/
- Requirements: 2.1

## Instructions
- Implement ONLY task 11: "Create event bus module structure in src/events/__init__.py"
- Follow all project conventions and leverage existing code
- Mark the task as complete using: claude-code-spec-workflow get-tasks fase1 11 --mode complete
- Provide a completion summary
```

## Task Completion
When the task is complete, mark it as done:
```bash
claude-code-spec-workflow get-tasks fase1 11 --mode complete
```

## Next Steps
After task completion, you can:
- Execute the next task using /fase1-task-[next-id]
- Check overall progress with /spec-status fase1

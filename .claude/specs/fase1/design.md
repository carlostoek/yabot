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
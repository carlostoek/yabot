# Requirements - Módulos Atómicos

## Introduction

This specification defines the implementation of atomic modules for the YABOT system, enabling parallel development of three core modules: Narrative Immersion, Gamification, and Channel Administration. Each module operates as an independent microservice connected through an event bus architecture, allowing for cross-module interactions and maintaining loose coupling.

The system implements a comprehensive event-driven architecture where user actions generate events that trigger responses across multiple modules simultaneously, creating an adaptive and engaging user experience.

## Alignment with Product Vision

This feature directly supports the product goals by:
- Creating an immersive narrative experience through interactive storytelling
- Implementing gamification mechanics to increase user engagement and retention
- Providing robust channel administration for content control and access management
- Enabling cross-module interactions that create a cohesive, integrated user experience

## Requirements

### Requirement 1: Narrative Immersion Module

**User Story:** As a user, I want to experience an interactive narrative with choices and progression, so that I can engage with dynamic storytelling content.

#### Acceptance Criteria

1. WHEN a user requests a narrative fragment THEN the system SHALL retrieve the fragment from MongoDB with text and decision options
2. WHEN a user makes a narrative decision THEN the system SHALL update their narrative_state in the database and publish a decision_made event
3. WHEN narrative pistas (hints) are unlocked THEN the system SHALL store them in the user's mochila (backpack) collection via API
4. IF a user has VIP status THEN the system SHALL allow access to premium narrative levels
5. WHEN a narrative checkpoint is reached THEN the system SHALL validate progression conditions via the coordinator service
6. WHEN Lucien messages are triggered THEN the system SHALL send dynamic templated messages via Telegram API

### Requirement 2: Gamification Module

**User Story:** As a user, I want to earn and spend virtual currency (besitos), complete missions, and collect items, so that I can progress in a rewarding game system.

#### Acceptance Criteria

1. WHEN besitos are awarded THEN the system SHALL perform atomic transactions in the database and publish besitos_added events
2. WHEN besitos are spent THEN the system SHALL validate balance and publish besitos_spent events
3. WHEN missions are assigned THEN the system SHALL track progress in the database via API
4. WHEN a mission is completed THEN the system SHALL publish mission_completed events
5. WHEN users react to content THEN the system SHALL detect reactions via Telegram hooks and publish reaction_detected events
6. WHEN users access the mochila THEN the system SHALL provide CRUD operations for item collection via MongoDB API
7. WHEN users browse the tienda (store) THEN the system SHALL display inline menus and process item_purchased events
8. WHEN subastas (auctions) are active THEN the system SHALL manage timers with Redis and handle bid_placed and auction_closed events
9. WHEN trivias are answered THEN the system SHALL process Telegram polls and publish trivia_answered events
10. WHEN logros (achievements) are unlocked THEN the system SHALL trigger database events and publish badge_unlocked events
11. WHEN daily gifts are claimed THEN the system SHALL enforce cooldowns with Redis and publish daily_gift_claimed events

### Requirement 3: Channel Administration Module

**User Story:** As an administrator, I want to control user access, manage subscriptions, and schedule content, so that I can maintain organized and secure channels.

#### Acceptance Criteria

1. WHEN user access is validated THEN the system SHALL use Telegram API to verify permissions and publish user_access_checked events
2. WHEN subscriptions expire THEN the system SHALL run cron jobs and publish subscription_expired events
3. WHEN posts are scheduled THEN the system SHALL use APScheduler and publish post_scheduled events
4. WHEN inline buttons are clicked THEN the system SHALL handle Telegram callbacks and publish button_clicked events
5. WHEN message protection is required THEN the system SHALL apply Telegram API flags to restrict access
6. WHEN notifications are sent THEN the system SHALL deliver push messages and publish notification_sent events
7. WHEN admin commands are executed THEN the system SHALL provide private command interfaces with inline menus

### Requirement 4: Event Bus Integration

**User Story:** As a module service, I want to communicate with other modules through reliable event messaging, so that cross-module interactions can occur seamlessly with guaranteed delivery and ordering.

#### Acceptance Criteria

1. WHEN any module publishes an event THEN the event bus SHALL deliver it to all subscribed modules within 100ms
2. WHEN an event fails to be delivered THEN the system SHALL retry up to 3 times with exponential backoff
3. WHEN a reaction_detected event occurs THEN gamification SHALL award besitos AND narrative SHALL potentially unlock pistas
4. WHEN a decision_made event occurs THEN gamification SHALL potentially assign missions AND administration SHALL potentially grant access
5. WHEN VIP access is required THEN the coordinator SHALL validate subscriptions before allowing fragment_unlocked events
6. WHEN cross-module workflows execute THEN events SHALL be processed in chronological order using correlation IDs
7. WHEN events fail to process THEN the system SHALL publish error events with original event ID and error details
8. WHEN event ordering is critical THEN the system SHALL use message queues to maintain sequence per user
9. WHEN modules are unavailable THEN events SHALL be queued and processed when modules recover

### Requirement 5: Module Isolation and Failure Recovery

**User Story:** As a system administrator, I want modules to operate independently and recover gracefully from failures, so that system availability is maintained even when individual modules fail.

#### Acceptance Criteria

1. WHEN a module fails THEN other modules SHALL continue operating without disruption
2. WHEN a module recovers THEN it SHALL process queued events from the time of failure
3. WHEN database connections fail THEN modules SHALL implement circuit breaker patterns with 30-second timeouts
4. WHEN cross-module API calls fail THEN fallback responses SHALL be provided within 5 seconds
5. WHEN data inconsistency is detected THEN reconciliation processes SHALL run automatically
6. WHEN module health checks fail THEN monitoring systems SHALL alert administrators within 1 minute
7. WHEN modules restart THEN they SHALL resume from their last known state

### Requirement 6: Database Integration

**User Story:** As a developer, I want consistent data storage patterns across modules, so that data integrity and performance are maintained.

#### Acceptance Criteria

1. WHEN narrative fragments are stored THEN the system SHALL use MongoDB with JSON structure for text and decisions
2. WHEN user state is updated THEN the system SHALL maintain narrative_progress in the users collection
3. WHEN items are managed THEN the system SHALL use MongoDB collections with CRUD APIs
4. WHEN real-time data is needed THEN the system SHALL use Redis for caching and timers
5. WHEN database transactions are required THEN the system SHALL ensure atomicity for critical operations
6. WHEN database migrations occur THEN the system SHALL maintain backward compatibility
7. WHEN data corruption is detected THEN automatic backup restoration SHALL be triggered

### Requirement 7: API Layer

**User Story:** As a module developer, I want internal APIs for quick data queries, so that modules can efficiently communicate without full event cycles.

#### Acceptance Criteria

1. WHEN besitos balance is queried THEN the API SHALL respond via /user/{id}/besitos endpoint
2. WHEN narrative state is needed THEN the API SHALL provide current fragment and progress information
3. WHEN subscription status is checked THEN the API SHALL return current VIP status and expiration
4. WHEN API calls are made THEN responses SHALL be returned within 100ms for cached data and 500ms for database queries
5. WHEN API errors occur THEN proper HTTP status codes and error messages SHALL be returned in Spanish
6. WHEN API rate limits are exceeded THEN HTTP 429 status SHALL be returned with retry-after headers
7. WHEN authentication fails THEN HTTP 401 status SHALL be returned with specific error codes
8. WHEN inter-module API calls timeout THEN circuit breaker SHALL open for 30 seconds

## Non-Functional Requirements

### Performance
- Event processing SHALL complete within 500ms for 95% of events
- Database queries SHALL return results within 100ms for 90% of queries
- The system SHALL support 1000 concurrent users per module
- Redis operations SHALL complete within 10ms for 99% of requests
- Cross-module API calls SHALL complete within 200ms for 95% of requests

### Security
- All API endpoints SHALL require authentication via Telegram user verification
- Sensitive data SHALL be encrypted at rest in MongoDB
- Event bus messages SHALL include correlation IDs for audit trails
- Admin functions SHALL require additional authorization checks
- Inter-module communication SHALL use authenticated API keys

### Reliability
- Each module SHALL have 99.9% uptime
- Event delivery SHALL be guaranteed with retry mechanisms
- Database transactions SHALL be atomic and consistent
- System SHALL gracefully handle module failures without affecting other modules
- Data backup SHALL occur every 6 hours with point-in-time recovery

### Usability
- Telegram interface SHALL respond to user actions within 2 seconds
- Error messages SHALL be user-friendly in Spanish
- Admin interfaces SHALL provide clear feedback for all operations
- Cross-module workflows SHALL appear seamless to end users
- System status SHALL be visible to administrators through monitoring dashboards
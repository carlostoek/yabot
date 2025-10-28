# Implementation Plan - Módulos Atómicos

## Task Overview
Implementation of three atomic modules (Narrative, Gamification, Administration) with event-driven architecture. Tasks are broken down into atomic, agent-friendly units focusing on individual file modifications and single testable outcomes.

## Steering Document Compliance
Tasks follow existing YABOT patterns:
- Module structure matches `src/` organization
- Event models extend `src/events/models.py`
- Database handlers follow `src/database/mongodb.py` patterns
- Services inherit from existing service layer patterns

## Atomic Task Requirements
**Each task meets these criteria for optimal agent execution:**
- **File Scope**: Touches 1-3 related files maximum
- **Time Boxing**: Completable in 15-30 minutes
- **Single Purpose**: One testable outcome per task
- **Specific Files**: Must specify exact files to create/modify
- **Agent-Friendly**: Clear input/output with minimal context switching

## Task Format Guidelines
- Use checkbox format: `- [ ] Task number. Task description`
- **Specify files**: Always include exact file paths to create/modify
- **Include implementation details** as bullet points
- Reference requirements using: `_Requirements: X.Y, Z.A_`
- Reference existing code to leverage using: `_Leverage: path/to/file.py`
- Focus only on coding tasks (no deployment, user testing, etc.)

## Good vs Bad Task Examples
❌ **Bad Examples (Too Broad)**:
- "Implement authentication system" (affects many files, multiple purposes)
- "Add user management features" (vague scope, no file specification)
- "Build complete dashboard" (too large, multiple components)

✅ **Good Examples (Atomic)**:
- "Create User model in models/user.py with email/password fields"
- "Add password hashing utility in utils/auth.py using bcrypt"
- "Create LoginForm component in components/LoginForm.tsx with email/password inputs"

## Tasks

### Phase 1: Enhanced Event System Foundation

- [ ] 1. Add narrative event models in src/events/models.py
  - File: src/events/models.py
  - Add DecisionMadeEvent, FragmentUnlockedEvent, HintUnlockedEvent, NarrativeCompletedEvent
  - Add correlation_id field to BaseEvent for event ordering
  - Purpose: Establish event types for narrative module communications
  - _Leverage: Existing BaseEvent class and pattern_
  - _Requirements: 4.1, 4.6_

- [ ] 1b. Add gamification event models in src/events/models.py
  - File: src/events/models.py
  - Add BesitosAwardedEvent, BesitosSpentEvent, MissionCompletedEvent, ItemPurchasedEvent, AchievementUnlockedEvent
  - Include reward and transaction details in event payloads
  - Purpose: Establish event types for gamification module communications
  - _Leverage: Existing BaseEvent class structure_
  - _Requirements: 4.1, 4.3_

- [ ] 1c. Add administration event models in src/events/models.py
  - File: src/events/models.py
  - Add UserAccessCheckedEvent, SubscriptionExpiredEvent, PostScheduledEvent
  - Include admin action audit details in event payloads
  - Purpose: Establish event types for administration module communications
  - _Leverage: Existing BaseEvent class pattern_
  - _Requirements: 4.1, 4.5_

- [ ] 1d. Add system resilience event models in src/events/models.py
  - File: src/events/models.py
  - Add EventProcessingFailedEvent, DataInconsistencyDetectedEvent, ModuleHealthCheckFailedEvent
  - Include error tracking and recovery information
  - Purpose: Support system resilience and monitoring requirements
  - _Leverage: Existing error event patterns_
  - _Requirements: 4.7, 5.5, 5.6_

- [ ] 2. Create event correlation service in src/shared/events/correlation.py
  - File: src/shared/events/correlation.py
  - Implement CorrelationService for event ordering and tracking
  - Add methods: generate_correlation_id(), track_event(), get_event_sequence()
  - Use Redis for correlation tracking with TTL
  - Purpose: Enable chronological event processing with correlation IDs
  - _Leverage: Redis patterns from existing caching_
  - _Requirements: 4.6, 4.8, 4.9_

- [ ] 3. Enhance event bus with retry mechanism in src/events/bus.py
  - File: src/events/bus.py
  - Add exponential backoff retry logic (3 attempts max)
  - Implement dead letter queue for failed events
  - Add correlation_id support to all event publishing
  - Purpose: Ensure reliable event delivery with ordering
  - _Leverage: Existing EventBus class structure_
  - _Requirements: 4.2, 4.7_

### Phase 2: Database Schema Extensions

- [ ] 4. Create narrative collections schema in src/database/schemas/narrative.py
  - File: src/database/schemas/narrative.py
  - Define NarrativeFragmentSchema with choices and VIP flags
  - Add indexes for fragment_id, vip_required, tags
  - Include validation for choice dependencies
  - Purpose: Establish narrative data structure and constraints
  - _Leverage: src/database/schemas/mongo.py patterns_
  - _Requirements: 1.1, 1.4, 6.1_

- [ ] 5. Create gamification collections schema in src/database/schemas/gamification.py
  - File: src/database/schemas/gamification.py
  - Define schemas for besitos_transactions, missions, items, auctions
  - Add compound indexes for user_id + timestamp queries
  - Include atomic transaction constraints
  - Purpose: Establish gamification data structures with performance indexes
  - _Leverage: MongoDB transaction patterns_
  - _Requirements: 2.1, 2.2, 2.6, 6.5_

- [ ] 6. Extend users collection schema in src/database/schemas/mongo.py
  - File: src/database/schemas/mongo.py (modify existing)
  - Add narrative_progress, besitos_balance, subscription fields
  - Create compound indexes for performance requirements
  - Add validation for VIP status and narrative state
  - Purpose: Extend user model for cross-module data
  - _Leverage: Existing users schema structure_
  - _Requirements: 1.2, 2.1, 3.1, 6.2_

### Phase 3: Narrative Immersion Module

- [ ] 7. Create narrative fragment manager in src/modules/narrative/fragment_manager.py
  - File: src/modules/narrative/fragment_manager.py
  - Implement FragmentManager class with get_fragment(), update_progress()
  - Add VIP validation logic using coordinator service
  - Include caching layer for frequently accessed fragments
  - Purpose: Core narrative content management with performance optimization
  - _Leverage: src/database/mongodb.py collection patterns_
  - _Requirements: 1.1, 1.4, 1.5_

- [ ] 8. Create decision engine in src/modules/narrative/decision_engine.py
  - File: src/modules/narrative/decision_engine.py
  - Implement DecisionEngine with process_decision(), validate_choice()
  - Add decision graph logic for narrative branching
  - Publish decision_made events to event bus
  - Purpose: Handle user narrative choices and state progression
  - _Leverage: Event bus publishing patterns_
  - _Requirements: 1.2, 1.5, 4.4_

- [ ] 9. Create hint system in src/modules/narrative/hint_system.py
  - File: src/modules/narrative/hint_system.py
  - Implement HintSystem with unlock_hint(), combine_hints()
  - Add cross-module API calls to gamification mochila
  - Include hint combination logic and validation
  - Purpose: Manage narrative hints and cross-module item storage
  - _Leverage: Cross-module API patterns_
  - _Requirements: 1.3, 4.3_

- [ ] 10. Create Lucien messenger in src/modules/narrative/lucien_messenger.py
  - File: src/modules/narrative/lucien_messenger.py
  - Implement LucienMessenger with send_message(), schedule_message()
  - Add dynamic template rendering with user context
  - Use Redis for message scheduling and Telegram API for delivery
  - Purpose: Automated narrative messaging with personalization
  - _Leverage: src/handlers/base.py Telegram patterns_
  - _Requirements: 1.6 (from design document)_

### Phase 4: Gamification Module Core

- [ ] 11. Create besitos wallet in src/modules/gamification/besitos_wallet.py
  - File: src/modules/gamification/besitos_wallet.py
  - Implement BesitosWallet with add_besitos(), spend_besitos(), get_balance()
  - Add atomic transaction support with MongoDB sessions
  - Publish besitos_added/besitos_spent events
  - Purpose: Virtual currency management with atomic operations
  - _Leverage: MongoDB transaction patterns_
  - _Requirements: 2.1, 2.2, 6.5_

- [ ] 12. Create mission manager in src/modules/gamification/mission_manager.py
  - File: src/modules/gamification/mission_manager.py
  - Implement MissionManager with assign_mission(), update_progress(), complete_mission()
  - Add mission type definitions and progress tracking
  - Subscribe to cross-module events for automatic mission assignment
  - Purpose: Dynamic mission system responding to user actions
  - _Leverage: Event bus subscription patterns_
  - _Requirements: 2.3, 2.4, 4.4_

- [ ] 13. Create item manager (mochila) in src/modules/gamification/item_manager.py
  - File: src/modules/gamification/item_manager.py
  - Implement ItemManager with add_item(), remove_item(), get_inventory()
  - Add CRUD API endpoints for cross-module access
  - Include item combination and usage logic
  - Purpose: User inventory management with cross-module API access
  - _Leverage: MongoDB CRUD patterns_
  - _Requirements: 2.6, 7.1_

- [ ] 14. Create reaction detector in src/modules/gamification/reaction_detector.py
  - File: src/modules/gamification/reaction_detector.py
  - Implement ReactionDetector with process_reaction()
  - Add Telegram webhook handling for reaction events
  - Connect to besitos wallet and hint system via events
  - Purpose: Process user reactions and trigger cross-module rewards
  - _Leverage: src/handlers/webhook.py patterns_
  - _Requirements: 2.5, 4.3_

### Phase 5: Gamification Module Advanced Features

- [ ] 15. Create store (tienda) system in src/modules/gamification/store.py
  - File: src/modules/gamification/store.py
  - Implement Store with browse_items(), purchase_item()
  - Add Telegram inline menu generation and callback handling
  - Integrate with besitos wallet for payment processing
  - Purpose: Virtual store with Telegram UI and payment integration
  - _Leverage: Telegram inline keyboard patterns_
  - _Requirements: 2.7_

- [ ] 16. Create auction system in src/modules/gamification/auction_system.py
  - File: src/modules/gamification/auction_system.py
  - Implement AuctionSystem with create_auction(), place_bid(), close_auction()
  - Add Redis timer management and automatic closure
  - Include bid history tracking and notification system
  - Purpose: Timed auction system with automated management
  - _Leverage: Redis TTL patterns_
  - _Requirements: 2.8_

- [ ] 17. Create trivia engine in src/modules/gamification/trivia_engine.py
  - File: src/modules/gamification/trivia_engine.py
  - Implement TriviaEngine with create_trivia(), process_answer()
  - Add Telegram poll creation and result processing
  - Connect to besitos wallet for reward distribution
  - Purpose: Interactive trivia system with Telegram polls
  - _Leverage: Telegram poll API patterns_
  - _Requirements: 2.9_

- [ ] 18. Create achievement system in src/modules/gamification/achievement_system.py
  - File: src/modules/gamification/achievement_system.py
  - Implement AchievementSystem with check_achievements(), unlock_achievement()
  - Add trigger-based achievement detection from events
  - Include badge management and user progress tracking
  - Purpose: Achievement tracking with event-driven unlocking
  - _Leverage: Event subscription patterns_
  - _Requirements: 2.10_

- [ ] 19. Create daily gift system in src/modules/gamification/daily_gift.py
  - File: src/modules/gamification/daily_gift.py
  - Implement DailyGift with claim_gift(), check_availability()
  - Add Redis cooldown management with 24-hour TTL
  - Include gift type randomization and reward distribution
  - Purpose: Daily reward system with cooldown enforcement
  - _Leverage: Redis TTL patterns_
  - _Requirements: 2.11_

### Phase 6: Channel Administration Module

- [ ] 20. Create access control system in src/modules/admin/access_control.py
  - File: src/modules/admin/access_control.py
  - Implement AccessControl with validate_access(), grant_access(), revoke_access()
  - Add Telegram API permission validation
  - Integrate with subscription manager for VIP validation
  - Purpose: User access management with Telegram API integration
  - _Leverage: Telegram API wrapper patterns_
  - _Requirements: 3.1, 3.5_

- [ ] 21. Create subscription manager in src/modules/admin/subscription_manager.py
  - File: src/modules/admin/subscription_manager.py
  - Implement SubscriptionManager with create_subscription(), check_vip_status()
  - Add cron job for expiration processing
  - Publish subscription_expired events for cross-module updates
  - Purpose: VIP subscription lifecycle management
  - _Leverage: src/services/subscription.py patterns_
  - _Requirements: 3.2, 5.1_

- [ ] 22. Create post scheduler in src/modules/admin/post_scheduler.py
  - File: src/modules/admin/post_scheduler.py
  - Implement PostScheduler with schedule_post(), execute_posts()
  - Add APScheduler integration with Redis persistence
  - Include retry logic for failed posts
  - Purpose: Automated content scheduling with reliability
  - _Leverage: APScheduler patterns_
  - _Requirements: 3.3_

- [ ] 23. Create notification system in src/modules/admin/notification_system.py
  - File: src/modules/admin/notification_system.py
  - Implement NotificationSystem with send_notification(), schedule_notification()
  - Add push message delivery via Telegram API
  - Include notification preferences and opt-out management
  - Purpose: User notification delivery with preference management
  - _Leverage: Telegram messaging patterns_
  - _Requirements: 3.6_

- [ ] 24. Create message protection system in src/modules/admin/message_protection.py
  - File: src/modules/admin/message_protection.py
  - Implement MessageProtection with protect_message(), check_access()
  - Add Telegram API flag management for message restrictions
  - Include time-based and role-based protection rules
  - Purpose: Message access control with Telegram API flags
  - _Leverage: Telegram API patterns_
  - _Requirements: 3.5_

- [ ] 25. Create admin command interface in src/modules/admin/admin_commands.py
  - File: src/modules/admin/admin_commands.py
  - Implement AdminCommands with process_command(), generate_menu()
  - Add private command handling with permission validation
  - Include inline menu generation for admin functions
  - Purpose: Administrative interface with secure command processing
  - _Leverage: src/handlers/base.py command patterns_
  - _Requirements: 3.7_

### Phase 7: Cross-Module Integration

- [ ] 26. Create inter-module API authentication in src/shared/api/auth.py
  - File: src/shared/api/auth.py
  - Implement ModuleAuth with generate_api_key(), validate_request()
  - Add API key management and permission validation
  - Include rate limiting and request logging
  - Purpose: Secure inter-module communication
  - _Leverage: src/api/auth.py patterns_
  - _Requirements: 7.6, 7.7_

- [ ] 27. Create circuit breaker service in src/shared/resilience/circuit_breaker.py
  - File: src/shared/resilience/circuit_breaker.py
  - Implement CircuitBreaker with failure tracking and timeout management
  - Add state management (CLOSED, OPEN, HALF_OPEN)
  - Include performance monitoring integration
  - Purpose: Fault tolerance for inter-module communication
  - _Leverage: Redis state persistence_
  - _Requirements: 5.3, 5.4, 7.8_

- [ ] 28. Create performance monitoring in src/shared/monitoring/performance.py
  - File: src/shared/monitoring/performance.py
  - Implement PerformanceMonitor with track_operation(), generate_metrics()
  - Add requirement compliance checking (500ms event processing, 100ms database queries, 10ms Redis operations)
  - Include alerting for SLA violations and performance dashboards
  - Purpose: Monitor and enforce specific performance requirements
  - _Leverage: Existing logging infrastructure_
  - _Requirements: Performance requirements (500ms events, 100ms queries, 1000 concurrent users)_

### Phase 8: API Endpoints and Integration

- [ ] 29. Create narrative progress API endpoint in src/api/endpoints/narrative.py
  - File: src/api/endpoints/narrative.py (extend existing)
  - Add GET /user/{id}/narrative/progress endpoint with current state
  - Include VIP validation and performance monitoring
  - Add proper error handling with Spanish messages
  - Purpose: External API access to user narrative progress
  - _Leverage: Existing FastAPI endpoint patterns_
  - _Requirements: 7.2, 7.5_

- [ ] 29b. Create fragment API endpoint in src/api/endpoints/narrative.py
  - File: src/api/endpoints/narrative.py
  - Add GET /fragment/{id} endpoint with content and choices
  - Include VIP access validation and caching
  - Add fragment availability validation
  - Purpose: External API access to narrative fragments
  - _Leverage: Caching patterns from existing endpoints_
  - _Requirements: 7.2_

- [ ] 30. Create besitos API endpoint in src/api/endpoints/gamification.py
  - File: src/api/endpoints/gamification.py
  - Add GET /user/{id}/besitos endpoint with balance and transaction history
  - Include rate limiting and authentication middleware
  - Add real-time balance updates
  - Purpose: External API access to besitos wallet
  - _Leverage: API authentication patterns_
  - _Requirements: 7.1, 7.4_

- [ ] 30b. Create inventory API endpoint in src/api/endpoints/gamification.py
  - File: src/api/endpoints/gamification.py
  - Add GET /user/{id}/inventory endpoint with items and metadata
  - Include item usage tracking and availability
  - Add inventory management operations
  - Purpose: External API access to user inventory
  - _Leverage: CRUD API patterns_
  - _Requirements: 7.1_

- [ ] 30c. Create missions API endpoint in src/api/endpoints/gamification.py
  - File: src/api/endpoints/gamification.py
  - Add GET /user/{id}/missions endpoint with active and completed missions
  - Include mission progress tracking and rewards
  - Add mission assignment and completion operations
  - Purpose: External API access to mission system
  - _Leverage: Progress tracking patterns_
  - _Requirements: 7.1_

- [ ] 31. Create admin API endpoints in src/api/endpoints/admin.py
  - File: src/api/endpoints/admin.py
  - Add /subscriptions, /scheduled-posts, /notifications endpoints
  - Include admin-only authentication and audit logging
  - Add bulk operations for user management
  - Purpose: Administrative API with enhanced security
  - _Leverage: Admin authentication patterns_
  - _Requirements: 7.1, 3.7_

### Phase 9: Testing Infrastructure

- [ ] 32. Create module unit tests in tests/modules/narrative/test_fragment_manager.py
  - File: tests/modules/narrative/test_fragment_manager.py
  - Write tests for fragment retrieval, VIP validation, progress updates
  - Use mocked MongoDB and event bus dependencies
  - Include performance benchmarks (100ms query target)
  - Purpose: Ensure narrative module reliability and performance
  - _Leverage: tests/conftest.py test fixtures_
  - _Requirements: 1.1, 1.4, 1.5_

- [ ] 33. Create gamification unit tests in tests/modules/gamification/test_besitos_wallet.py
  - File: tests/modules/gamification/test_besitos_wallet.py
  - Write tests for atomic transactions, balance validation, event publishing
  - Use test database with transaction isolation
  - Include concurrent transaction testing
  - Purpose: Ensure besitos transaction integrity
  - _Leverage: Database transaction test patterns_
  - _Requirements: 2.1, 2.2, 6.5_

- [ ] 34. Create reaction workflow integration test in tests/integration/test_reaction_workflow.py
  - File: tests/integration/test_reaction_workflow.py
  - Write tests for reaction→besitos→hint unlock workflow
  - Test event ordering and correlation ID tracking for reaction flow
  - Include performance validation (500ms target)
  - Purpose: Validate reaction-triggered cross-module interactions
  - _Leverage: tests/integration/ patterns_
  - _Requirements: 4.3, 4.6_

- [ ] 34b. Create decision workflow integration test in tests/integration/test_decision_workflow.py
  - File: tests/integration/test_decision_workflow.py
  - Write tests for decision→mission→access grant workflow
  - Test VIP validation and narrative progression
  - Include event correlation across modules
  - Purpose: Validate decision-triggered cross-module interactions
  - _Leverage: Event correlation test patterns_
  - _Requirements: 4.4, 4.6_

- [ ] 34c. Create subscription workflow integration test in tests/integration/test_subscription_workflow.py
  - File: tests/integration/test_subscription_workflow.py
  - Write tests for subscription expiration→access revocation workflow
  - Test cron job processing and event publishing
  - Include VIP access validation after expiration
  - Purpose: Validate subscription-based access control
  - _Leverage: Cron job test patterns_
  - _Requirements: 3.2, 4.5_

### Phase 9b: Missing System Components

- [ ] 35. Create data reconciliation system in src/shared/resilience/data_reconciliation.py
  - File: src/shared/resilience/data_reconciliation.py
  - Implement DataReconciliation with detect_inconsistency(), resolve_conflicts()
  - Add automatic conflict resolution rules and manual review queue
  - Include cross-module data consistency validation
  - Purpose: Ensure data consistency across modules
  - _Leverage: Database transaction patterns_
  - _Requirements: 5.5_

- [ ] 35b. Create event queue persistence system in src/shared/events/queue_persistence.py
  - File: src/shared/events/queue_persistence.py
  - Implement QueuePersistence with save_queue_state(), restore_queue_state()
  - Add Redis-based queue backup during module unavailability
  - Include event replay functionality for module recovery
  - Purpose: Maintain event delivery during module failures
  - _Leverage: Redis persistence patterns_
  - _Requirements: 4.9_

- [ ] 35c. Create monitoring alerting system in src/shared/monitoring/alerting.py
  - File: src/shared/monitoring/alerting.py
  - Implement AlertingSystem with send_alert(), configure_thresholds()
  - Add health check failure detection with 1-minute response time
  - Include escalation rules and notification channels
  - Purpose: Alert administrators of system issues
  - _Leverage: Notification system patterns_
  - _Requirements: 5.6_

- [ ] 35d. Create database migration framework in src/shared/database/migration.py
  - File: src/shared/database/migration.py
  - Implement MigrationManager with run_migration(), rollback_migration()
  - Add backward compatibility validation and version tracking
  - Include schema evolution support for module updates
  - Purpose: Manage database schema changes safely
  - _Leverage: Database schema patterns_
  - _Requirements: 6.6_

- [ ] 35e. Create backup automation system in src/shared/database/backup_automation.py
  - File: src/shared/database/backup_automation.py
  - Implement BackupAutomation with detect_corruption(), restore_from_backup()
  - Add automated backup scheduling and corruption detection
  - Include point-in-time recovery functionality
  - Purpose: Automatic data protection and recovery
  - _Leverage: Database backup patterns_
  - _Requirements: 6.7_

### Phase 10: Final Integration and Deployment

- [ ] 36. Create module registry in src/shared/registry/module_registry.py
  - File: src/shared/registry/module_registry.py
  - Implement ModuleRegistry for service discovery and health checks
  - Add module registration and status monitoring
  - Include dependency resolution for module startup
  - Purpose: Centralized module management and monitoring
  - _Leverage: Service registration patterns_
  - _Requirements: 5.6_

- [ ] 37. Create main application integration in src/main.py
  - File: src/main.py (modify existing)
  - Initialize all three modules with dependency injection
  - Add graceful startup/shutdown with module isolation
  - Include health check endpoints for monitoring
  - Purpose: Application entry point with module orchestration
  - _Leverage: Existing application startup patterns_
  - _Requirements: 5.1, 5.7_

- [ ] 38. Create narrative user journey E2E test in tests/e2e/test_narrative_journey.py
  - File: tests/e2e/test_narrative_journey.py
  - Write complete narrative progression test with choices and VIP content
  - Include performance validation (2-second response time)
  - Test Lucien messaging and hint unlocking
  - Purpose: Validate complete narrative user experience
  - _Leverage: E2E testing infrastructure_
  - _Requirements: Requirement 1 user stories_

- [ ] 38b. Create gamification loop E2E test in tests/e2e/test_gamification_loop.py
  - File: tests/e2e/test_gamification_loop.py
  - Write full gamification cycle test (earn→spend→missions→achievements)
  - Include store purchases and auction participation
  - Test daily gifts and trivia participation
  - Purpose: Validate complete gamification experience
  - _Leverage: Telegram bot simulation patterns_
  - _Requirements: Requirement 2 user stories_

- [ ] 38c. Create admin workflow E2E test in tests/e2e/test_admin_workflows.py
  - File: tests/e2e/test_admin_workflows.py
  - Write admin management tests (users, subscriptions, content)
  - Include post scheduling and notification delivery
  - Test access control and message protection
  - Purpose: Validate complete administrative functionality
  - _Leverage: Admin interface test patterns_
  - _Requirements: Requirement 3 user stories_
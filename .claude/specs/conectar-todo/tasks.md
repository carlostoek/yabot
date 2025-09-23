# Implementation Plan - Adapted Architecture

## Task Overview
This implementation plan extends the existing YABOT architecture, building upon the already implemented CrossModuleService, ModuleRegistry, and infrastructure components. Instead of duplicating functionality, we enhance and connect existing services to create complete integration across all modules.

## Existing Architecture Leveraged
- **CrossModuleService**: Central service coordination (extends to IntegrationManager functionality)
- **ModuleRegistry**: Service discovery and health monitoring (src/shared/registry/module_registry.py)
- **CircuitBreaker**: Resilience patterns (src/shared/resilience/circuit_breaker.py)
- **PerformanceMonitor**: Metrics collection (src/shared/monitoring/performance.py)
- **EventBus**: Pub/Sub infrastructure with Redis and local fallback

## Atomic Task Requirements
**Each task must meet these criteria for optimal agent execution:**
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
- Reference existing code to leverage using: `_Leverage: path/to/file.py, path/to/component.py_`
- Focus only on coding tasks (no deployment, user testing, etc.)
- **Build upon existing**: Extend rather than replace existing functionality

## Tasks

### Phase 1: Extend Existing Infrastructure

- [x] 1. Extend CrossModuleService with gamification coordination in src/services/cross_module.py
  - File: src/services/cross_module.py (modify existing)
  - Add process_gamification_workflow method for coordinated module actions
  - Include wallet transaction coordination with mission and achievement updates
  - Add reward distribution logic for daily gifts and completed missions
  - _Leverage: existing CrossModuleService class and dependency injection_
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 2. Add EventSubscriptionManager functionality to existing EventBus in src/events/bus.py
  - File: src/events/bus.py (modify existing)
  - Add subscribe_service method for automatic service event registration
  - Include subscription tracking and delivery confirmation mechanisms
  - Add bulk unsubscribe functionality for service shutdown
  - _Leverage: existing EventBus publish/subscribe infrastructure_
  - _Requirements: 3.2, 3.4, 3.5_

- [x] 3. Connect ModuleRegistry to startup dependency management in src/core/application.py
  - File: src/core/application.py (modify existing)
  - Import and initialize ModuleRegistry in _setup_services
  - Add service dependency registration during startup sequence
  - Include health monitoring integration with existing error handling
  - _Leverage: existing BotApplication initialization patterns, src/shared/registry/module_registry.py_
  - _Requirements: 1.1, 1.2_

- [x] 4. Add cross-database transaction utilities to existing DatabaseManager in src/database/manager.py
  - File: src/database/manager.py (modify existing)
  - Add atomic_operation context manager for MongoDB and SQLite coordination
  - Include rollback mechanisms for failed cross-database operations
  - Add operation queuing for offline database recovery scenarios
  - _Leverage: existing DatabaseManager connection patterns and health checks_
  - _Requirements: 2.1, 2.3, 2.5_

- [x] 5. Extend UserService with event publishing for lifecycle changes in src/services/user.py
  - File: src/services/user.py (modify existing)
  - Add event publishing to existing create_user, update_user methods
  - Include correlation IDs and operation context in published events
  - Integrate with existing EventBus instance for user state notifications
  - _Leverage: existing UserService methods and EventBus integration_
  - _Requirements: 2.2, 3.1_

- [x] 6. Add workflow definitions to existing event models in src/events/models.py
  - File: src/events/models.py (modify existing)
  - Add WorkflowDefinition, WorkflowStep classes for complex operation coordination
  - Include GamificationWorkflow and NarrativeWorkflow specific models
  - Extend existing Event class with correlation_id and workflow_context fields
  - _Leverage: existing event model structures and validation patterns_
  - _Requirements: 3.1, 4.1, 5.2_

- [x] 7. Add admin integration methods to CrossModuleService in src/services/cross_module.py
  - File: src/services/cross_module.py (modify existing)
  - Add handle_admin_notification method for coordinated notification delivery
  - Include access_control_check integration with narrative and gamification access
  - Add audit_admin_action method for administrative operation logging
  - _Leverage: existing CrossModuleService architecture and dependency injection_
  - _Requirements: 6.1, 6.2, 6.4_

- [x] 8. Add performance monitoring to CrossModuleService workflow methods in src/services/cross_module.py
  - File: src/services/cross_module.py (modify existing)
  - Add PerformanceMonitor decorators to process_narrative_choice and handle_reaction methods
  - Include latency tracking with <100ms targets for cross-module operations
  - Import and initialize PerformanceMonitor with "cross_module" module name
  - _Leverage: src/shared/monitoring/performance.py PerformanceMonitor class_
  - _Requirements: Performance targets validation_

### Phase 2: Connect Missing Modules to Event System

- [x] 9. Connect besitos_wallet to event system in src/modules/gamification/besitos_wallet.py
  - File: src/modules/gamification/besitos_wallet.py (modify existing)
  - Add event publishing for wallet transactions (debit, credit, transfer)
  - Include event subscriptions for external wallet update triggers
  - Integrate with CrossModuleService for coordinated reward distribution
  - _Leverage: existing besitos_wallet implementation, src/events/bus.py_
  - _Requirements: 4.1, 4.2_

- [x] 10. Connect daily_gift to event system in src/modules/gamification/daily_gift.py
  - File: src/modules/gamification/daily_gift.py (modify existing)
  - Add event publishing for gift claiming actions
  - Include automatic mission progress updates through events
  - Integrate wallet transactions through event coordination
  - _Leverage: existing daily_gift implementation, src/events/bus.py_
  - _Requirements: 4.3, 3.1_

- [x] 11. Connect mission_manager to event system in src/modules/gamification/mission_manager.py
  - File: src/modules/gamification/mission_manager.py (modify existing)
  - Add event subscriptions for mission progress update triggers
  - Include achievement unlocking coordination through event publishing
  - Integrate with narrative events for quest progression tracking
  - _Leverage: existing mission_manager implementation, src/events/bus.py_
  - _Requirements: 4.1, 5.4_

- [x] 12. Connect achievement_system to event system in src/modules/gamification/achievement_system.py
  - File: src/modules/gamification/achievement_system.py (modify existing)
  - Add event subscriptions for achievement checking triggers
  - Include notification publishing for newly unlocked achievements
  - Integrate wallet reward coordination for achievement completion
  - _Leverage: existing achievement_system implementation, src/events/bus.py_
  - _Requirements: 4.1, 4.5_

- [x] 13. Connect store module to event system in src/modules/gamification/store.py
  - File: src/modules/gamification/store.py (modify existing)
  - Add event publishing for store purchase transactions
  - Include inventory update coordination and transaction validation
  - Integrate wallet deduction coordination through event workflows
  - _Leverage: existing store implementation, src/events/bus.py_
  - _Requirements: 4.2_

- [x] 14. Connect auction_system to event system in src/modules/gamification/auction_system.py
  - File: src/modules/gamification/auction_system.py (modify existing)
  - Add event publishing for auction events (bid, win, expire)
  - Include wallet transaction coordination for bid processing and winner payments
  - Integrate notification system for auction status updates
  - _Leverage: existing auction_system implementation, src/events/bus.py_
  - _Requirements: 4.4_

- [x] 15. Connect notification_system to event bus in src/modules/admin/notification_system.py
  - File: src/modules/admin/notification_system.py (modify existing)
  - Add event subscriptions for notification triggers from all modules
  - Include user segmentation and delivery coordination through CrossModuleService
  - Integrate with administrative audit events for notification tracking
  - _Leverage: existing notification_system implementation, src/events/bus.py_
  - _Requirements: 6.1, 6.4_

- [x] 16. Connect access_control to ModuleRegistry in src/modules/admin/access_control.py
  - File: src/modules/admin/access_control.py (modify existing)
  - Add real-time access control rule enforcement through event subscriptions
  - Include service-wide rule propagation using existing ModuleRegistry
  - Integrate with CrossModuleService for access validation coordination
  - _Leverage: existing access_control implementation, src/shared/registry/module_registry.py_
  - _Requirements: 6.2_

- [x] 17. Connect post_scheduler to event system in src/modules/admin/post_scheduler.py
  - File: src/modules/admin/post_scheduler.py (modify existing)
  - Add event publishing for scheduled post triggers
  - Include coordination with user service and gamification modules for post effects
  - Integrate with CrossModuleService for comprehensive post processing
  - _Leverage: existing post_scheduler implementation, src/events/bus.py_
  - _Requirements: 6.3_

- [x] 18. Add narrative event handlers to existing narrative module in src/modules/narrative/event_handlers.py
  - File: src/modules/narrative/event_handlers.py (create if not exists)
  - Implement event handlers for narrative choice processing and story progression
  - Add gamification reward coordination for story milestone completion
  - Include fallback content mechanisms integrated with CrossModuleService
  - _Leverage: src/modules/narrative/ existing patterns, src/events/bus.py_
  - _Requirements: 5.2, 5.3, 5.5_

- [x] 19. Add admin audit logging integration in src/modules/admin/audit_logger.py
  - File: src/modules/admin/audit_logger.py (create if not exists)
  - Implement audit event logging for all administrative operations
  - Add structured logging with action, user, timestamp, and context
  - Include event publishing to existing EventBus for audit event distribution
  - _Leverage: src/events/bus.py, src/utils/logger.py patterns_
  - _Requirements: 6.4_

- [x] 20. Add offline database recovery mechanism to DatabaseManager in src/database/manager.py
  - File: src/database/manager.py (modify existing)
  - Add operation queuing for offline database scenarios
  - Include automatic sync when database connections are restored
  - Integrate with existing health check mechanisms for recovery triggers
  - _Leverage: existing DatabaseManager connection patterns and health monitoring_
  - _Requirements: 2.5_

### Phase 3: Unify APIs and Complete Integration

- [ ] 21. Enhance existing cross_module.py API endpoints in src/api/cross_module.py
  - File: src/api/cross_module.py (modify existing)
  - Connect placeholder endpoints to actual CrossModuleService methods
  - Add comprehensive error handling and service status checking
  - Include event publishing for API-triggered operations
  - _Leverage: existing cross_module.py structure and CrossModuleService_
  - _Requirements: 7.1, 7.5_

- [ ] 22. Unify user endpoints with CrossModuleService in src/api/endpoints/users.py
  - File: src/api/endpoints/users.py (modify existing)
  - Connect user endpoints to enhanced UserService with event publishing
  - Add cross-database user data aggregation through existing DatabaseManager
  - Include same event workflows as internal CrossModuleService operations
  - _Leverage: existing user endpoints, enhanced UserService_
  - _Requirements: 7.3, 7.2_

- [ ] 23. Unify gamification endpoints with existing integration in src/api/endpoints/gamification.py
  - File: src/api/endpoints/gamification.py (modify existing)
  - Connect gamification endpoints to CrossModuleService workflow coordination
  - Add event publishing for external gamification triggers
  - Include same workflow processing as internal module operations
  - _Leverage: existing gamification endpoints, enhanced CrossModuleService_
  - _Requirements: 7.4, 7.2_

- [ ] 24. Unify narrative endpoints with existing CrossModuleService in src/api/endpoints/narrative.py
  - File: src/api/endpoints/narrative.py (modify existing)
  - Connect narrative endpoints to existing CrossModuleService narrative methods
  - Add personalization based on unified user context from enhanced UserService
  - Include event publishing for narrative API interactions
  - _Leverage: existing narrative endpoints, CrossModuleService narrative integration_
  - _Requirements: 7.1, 7.2_

- [ ] 25. Add health check endpoints using ModuleRegistry in src/api/endpoints/health.py
  - File: src/api/endpoints/health.py (create if not exists)
  - Implement comprehensive service health reporting using ModuleRegistry
  - Add performance metrics aggregation from PerformanceMonitor
  - Include service dependency status checking through existing infrastructure
  - _Leverage: src/shared/registry/module_registry.py, src/shared/monitoring/performance.py_
  - _Requirements: 6.5, 7.5_

- [ ] 26. Create basic CrossModuleService integration tests in tests/integration/test_cross_module_basic.py
  - File: tests/integration/test_cross_module_basic.py
  - Test CrossModuleService narrative access check and choice processing workflows
  - Add basic event publishing validation for narrative workflow operations
  - Include dependency injection testing for CrossModuleService initialization
  - _Leverage: tests/ existing test patterns and utilities_
  - _Requirements: 5.1, 5.2, 7.1_

- [ ] 26b. Create gamification workflow integration tests in tests/integration/test_gamification_workflows.py
  - File: tests/integration/test_gamification_workflows.py
  - Test gamification event propagation (besitos → wallet → achievements)
  - Add validation for coordinated module actions through CrossModuleService
  - Include wallet transaction and reward distribution testing
  - _Leverage: tests/ existing test patterns and utilities_
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 27. Create user journey workflow tests in tests/integration/test_user_journey.py
  - File: tests/integration/test_user_journey.py
  - Test complete user registration → besitos earning → narrative access workflow
  - Add validation for cross-database user state consistency
  - Include event coordination testing for multi-module user actions
  - _Leverage: tests/ existing test patterns and utilities_
  - _Requirements: 2.1, 4.1, 5.1_

- [ ] 27b. Create admin workflow integration tests in tests/integration/test_admin_workflows.py
  - File: tests/integration/test_admin_workflows.py
  - Test admin notification delivery through event coordination
  - Add access control rule enforcement validation across modules
  - Include audit logging integration testing for administrative actions
  - _Leverage: tests/ existing test patterns and utilities_
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 28. Add ModuleRegistry initialization to main.py startup in main.py
  - File: main.py (modify existing)
  - Import and initialize ModuleRegistry after EventBus setup
  - Add core service registration (database_manager, event_bus, user_service)
  - Include basic health monitoring startup for registered services
  - _Leverage: existing main.py initialization patterns, ModuleRegistry_
  - _Requirements: 1.1_

- [ ] 28b. Add service dependency coordination to main.py startup in main.py
  - File: main.py (modify existing)
  - Add CrossModuleService initialization after core services
  - Include module service registration (gamification, admin, narrative)
  - Ensure proper startup dependency order and error handling
  - _Leverage: existing main.py initialization patterns, ModuleRegistry_
  - _Requirements: 1.2_
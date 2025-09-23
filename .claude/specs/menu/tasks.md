# Implementation Plan - Menu System

## Task Overview
The implementation follows atomic task principles, breaking the menu system into specific, testable components that can be implemented incrementally. Each task focuses on 1-3 related files and can be completed in 15-30 minutes by an experienced developer.

## Steering Document Compliance
All tasks follow structure.md file organization conventions and tech.md patterns including async/await, service patterns, and event-driven architecture. Tasks leverage existing MenuFactory, UserService, and EventBus infrastructure while extending functionality for complete Telegram integration.

## Atomic Task Requirements
**Each task meets these criteria for optimal agent execution:**
- **File Scope**: Touches 1-3 related files maximum
- **Time Boxing**: Completable in 15-30 minutes
- **Single Purpose**: One testable outcome per task
- **Specific Files**: Must specify exact files to create/modify
- **Agent-Friendly**: Clear input/output with minimal context switching

## Tasks

### Phase 1: Core Message Management Infrastructure

- [x] 1. Create message tracking data models in src/ui/message_manager.py
  - File: src/ui/message_manager.py
  - Define MessageTrackingRecord, MessageTTLConfig dataclasses
  - Add message type enums and TTL constants
  - Purpose: Establish data structures for message lifecycle management
  - _Requirements: REQ-MENU-002.5, REQ-MENU-004.1_
  - _Leverage: src/core/models.py patterns, existing dataclass structures_

- [x] 2. Implement MessageManager class core functionality in src/ui/message_manager.py
  - File: src/ui/message_manager.py (continue from task 1)
  - Add track_message, delete_old_messages, preserve_main_menu methods
  - Integrate with Redis cache for message tracking
  - Purpose: Core message lifecycle management operations
  - _Requirements: REQ-MENU-002.5, REQ-MENU-004.1_
  - _Leverage: src/shared/cache_manager.py, existing Redis patterns_

- [x] 3. Add message cleanup scheduling in src/ui/message_manager.py
  - File: src/ui/message_manager.py (continue from task 2)
  - Implement TTL-based cleanup, periodic cleanup task
  - Add bulk message deletion for efficiency
  - Purpose: Automated message cleanup system
  - _Requirements: REQ-MENU-002.5_
  - _Leverage: APScheduler patterns from src/modules/admin/post_scheduler.py_

- [x] 4. Create message manager unit tests in tests/ui/test_message_manager.py
  - File: tests/ui/test_message_manager.py
  - Test message tracking, TTL handling, bulk deletion
  - Mock Redis operations and Telegram API calls
  - Purpose: Ensure message management reliability
  - _Requirements: REQ-MENU-002.5_
  - _Leverage: tests/helpers/testUtils.py, existing Redis mock patterns_

### Phase 2: Enhanced Menu Handler System

- [x] 5. Create MenuHandlerSystem class in src/handlers/menu_handler.py
  - File: src/handlers/menu_handler.py
  - Extend BaseHandler with menu-specific functionality
  - Add handle_command, handle_callback, cleanup_previous_messages methods
  - Purpose: Central coordinator for menu interactions with cleanup
  - _Requirements: REQ-MENU-001.1, REQ-MENU-001.2, REQ-MENU-001.3_
  - _Leverage: src/handlers/base.py, src/handlers/telegram_commands.py patterns_

- [x] 6. Integrate MenuFactory with message cleanup in src/handlers/menu_handler.py
  - File: src/handlers/menu_handler.py (continue from task 5)
  - Add get_menu_for_context method using existing MenuFactory
  - Integrate MessageManager for cleanup after menu generation
  - Purpose: Connect menu generation with message management
  - _Requirements: REQ-MENU-006.1, REQ-MENU-006.2_
  - _Leverage: src/ui/menu_factory.py MenuFactory class_

- [x] 7. Add Lucien evaluation tracking to menu interactions in src/handlers/menu_handler.py
  - File: src/handlers/menu_handler.py (continue from task 6)
  - Implement behavioral assessment for menu interactions
  - Track worthiness score updates through menu usage
  - Purpose: Integrate menu system with emotional intelligence tracking
  - _Requirements: REQ-MENU-001.5, REQ-MENU-007.2_
  - _Leverage: src/handlers/telegram_commands.py _track_lucien_evaluation method_

- [x] 8. Create menu handler unit tests in tests/handlers/test_menu_handler.py
  - File: tests/handlers/test_menu_handler.py
  - Test command handling, callback processing, cleanup integration
  - Mock MenuFactory, MessageManager, UserService dependencies
  - Purpose: Ensure menu handler reliability and proper integration
  - _Requirements: REQ-MENU-001.1, REQ-MENU-001.2, REQ-MENU-001.3_
  - _Leverage: tests/handlers/ existing test patterns_

### Phase 3: Callback Processing System

- [x] 9. Create CallbackProcessor class in src/handlers/callback_processor.py
  - File: src/handlers/callback_processor.py
  - Implement process_callback, validate_callback_data methods
  - Add callback data compression for Telegram limits
  - Purpose: Handle Telegram callback queries with validation
  - _Requirements: REQ-MENU-002.2, REQ-MENU-002.4_
  - _Leverage: src/ui/menu_factory.py callback compression patterns_

- [x] 10. Add callback action routing in src/handlers/callback_processor.py
  - File: src/handlers/callback_processor.py (continue from task 9)
  - Implement action parsing and routing to appropriate modules
  - Add cleanup_after_callback for message management
  - Purpose: Route callback actions to correct handlers with cleanup
  - _Requirements: REQ-MENU-002.2, REQ-MENU-007.1_
  - _Leverage: existing module patterns from src/modules/_

- [x] 11. Integrate callback processor with event system in src/handlers/callback_processor.py
  - File: src/handlers/callback_processor.py (continue from task 10)
  - Publish menu interaction events to EventBus
  - Track behavioral assessments for callback actions
  - Purpose: Connect callback processing with event-driven architecture
  - _Requirements: REQ-MENU-007.1, REQ-MENU-007.2_
  - _Leverage: src/events/bus.py EventBus, src/events/models.py create_event_

- [x] 12. Create callback processor unit tests in tests/handlers/test_callback_processor.py
  - File: tests/handlers/test_callback_processor.py
  - Test callback validation, action routing, event publishing
  - Mock EventBus and module dependencies
  - Purpose: Ensure callback processing reliability
  - _Requirements: REQ-MENU-002.2, REQ-MENU-002.4_
  - _Leverage: tests/events/ event testing patterns_

### Phase 4: Action Dispatch System

- [x] 13. Create ActionDispatcher class in src/handlers/action_dispatcher.py
  - File: src/handlers/action_dispatcher.py
  - Implement dispatch_action, register_action_handler methods
  - Add action handler registry for different modules
  - Purpose: Route menu actions to appropriate services and modules
  - _Requirements: REQ-MENU-007.1_
  - _Leverage: src/shared/registry/module_registry.py patterns_

- [x] 14. Register existing module handlers in src/handlers/action_dispatcher.py
  - File: src/handlers/action_dispatcher.py (continue from task 13)
  - Connect gamification, narrative, admin module actions
  - Add error handling for missing or failed actions
  - Purpose: Integrate existing modules with menu action system
  - _Requirements: REQ-MENU-006.5_
  - _Leverage: src/modules/gamification/, src/modules/narrative/, src/modules/admin/_

- [x] 15. Add action result processing in src/handlers/action_dispatcher.py
  - File: src/handlers/action_dispatcher.py (continue from task 14)
  - Process action results and generate appropriate responses
  - Update user context based on action outcomes
  - Purpose: Handle action results and context updates
  - _Requirements: REQ-MENU-008.2, REQ-MENU-008.4_
  - _Leverage: src/services/user.py user context management_

- [x] 16. Create action dispatcher unit tests in tests/handlers/test_action_dispatcher.py
  - File: tests/handlers/test_action_dispatcher.py
  - Test action routing, handler registration, result processing
  - Mock module handlers and user context updates
  - Purpose: Ensure action dispatch reliability
  - _Requirements: REQ-MENU-007.1_
  - _Leverage: tests/modules/ module testing patterns_

### Phase 5: Telegram Menu Rendering

- [x] 17. Create TelegramMenuRenderer class in src/ui/telegram_menu_renderer.py
  - File: src/ui/telegram_menu_renderer.py
  - Implement render_menu, render_menu_response methods
  - Convert Menu objects to Telegram InlineKeyboardMarkup
  - Purpose: Transform menu objects into Telegram interface elements
  - _Requirements: REQ-MENU-002.3_
  - _Leverage: src/ui/menu_factory.py Menu class, aiogram InlineKeyboard types_

- [x] 18. Add menu editing capabilities in src/ui/telegram_menu_renderer.py
  - File: src/ui/telegram_menu_renderer.py (continue from task 17)
  - Implement edit_existing_menu for in-place menu updates
  - Add fallback to new message if edit fails
  - Purpose: Enable menu updates without creating new messages
  - _Requirements: REQ-MENU-002.3_
  - _Leverage: aiogram edit_message capabilities_

- [x] 19. Integrate Lucien voice with menu rendering in src/ui/telegram_menu_renderer.py
  - File: src/ui/telegram_menu_renderer.py (continue from task 18)
  - Add Lucien voice text to menu headers and descriptions
  - Apply sophisticated terminology from style guide
  - Purpose: Ensure Lucien personality in rendered menus
  - _Requirements: REQ-MENU-005.1, REQ-MENU-005.2_
  - _Leverage: src/ui/lucien_voice_generator.py, docs/narrativo/guia_estilo_menus.md_

- [x] 20. Create menu renderer unit tests in tests/ui/test_telegram_menu_renderer.py
  - File: tests/ui/test_telegram_menu_renderer.py
  - Test menu rendering, keyboard generation, edit functionality
  - Mock Telegram API and Menu objects
  - Purpose: Ensure menu rendering reliability
  - _Requirements: REQ-MENU-002.3, REQ-MENU-005.1_
  - _Leverage: tests/ui/ UI testing patterns_

### Phase 6: Router Integration

- [x] 21. Create MenuIntegrationRouter class in src/handlers/menu_router.py
  - File: src/handlers/menu_router.py
  - Implement route_message, route_callback methods
  - Integrate with existing router architecture
  - Purpose: Route menu-specific messages and callbacks
  - _Requirements: REQ-MENU-002.1_
  - _Leverage: src/core/router.py existing router patterns_

- [x] 22. Add middleware integration for menu tracking in src/handlers/menu_router.py
  - File: src/handlers/menu_router.py (continue from task 21)
  - Connect with MessageManager for lifecycle tracking
  - Add user context enrichment for menu decisions
  - Purpose: Integrate menu routing with message management
  - _Requirements: REQ-MENU-002.1, REQ-MENU-002.5_
  - _Leverage: src/core/middleware.py existing middleware patterns_

- [x] 23. Register menu router with main application in src/core/application.py
  - File: src/core/application.py
  - Add MenuIntegrationRouter to dispatcher configuration
  - Register menu handlers with main bot instance
  - Purpose: Integrate menu system with main application
  - _Requirements: REQ-MENU-002.1_
  - _Leverage: existing application.py handler registration patterns_

- [x] 24. Create menu router unit tests in tests/handlers/test_menu_router.py
  - File: tests/handlers/test_menu_router.py
  - Test message routing, callback routing, middleware integration
  - Mock router dependencies and handler responses
  - Purpose: Ensure router integration reliability
  - _Requirements: REQ-MENU-002.1_
  - _Leverage: tests/core/ core testing patterns_

### Phase 7: Role-Based Access Integration

- [x] 25. Enhance UserService menu context methods in src/services/user.py
  - File: src/services/user.py
  - Add get_menu_context method for role-based menu generation
  - Include VIP status, narrative level, worthiness score in context
  - Purpose: Provide comprehensive user context for menu decisions
  - _Requirements: REQ-MENU-003.1, REQ-MENU-003.2, REQ-MENU-003.3_
  - _Leverage: existing UserService methods and user profile structure_

- [x] 26. Add worthiness score explanation generation in src/services/user.py
  - File: src/services/user.py (continue from task 25)
  - Implement generate_worthiness_explanation method
  - Integrate with Lucien voice for sophisticated explanations
  - Purpose: Provide elegant explanations for access restrictions
  - _Requirements: REQ-MENU-003.4, REQ-MENU-004.2_
  - _Leverage: src/ui/lucien_voice_generator.py response generation_

- [x] 27. Update menu factory integration with enhanced user context in src/ui/menu_factory.py
  - File: src/ui/menu_factory.py
  - Modify menu builders to use enhanced user context
  - Update organic restriction explanations
  - Purpose: Ensure menu generation uses complete user context
  - _Requirements: REQ-MENU-003.5, REQ-MENU-004.5_
  - _Leverage: existing MenuFactory builders and organic menu patterns_

- [x] 28. Create user service menu integration tests in tests/services/test_user_menu_integration.py
  - File: tests/services/test_user_menu_integration.py
  - Test menu context generation, worthiness explanations
  - Verify role-based access control functionality
  - Purpose: Ensure user service menu integration reliability
  - _Requirements: REQ-MENU-003.1, REQ-MENU-003.4_
  - _Leverage: tests/services/ service testing patterns_

### Phase 8: Event System Integration

- [x] 29. Define menu interaction event models in src/events/menu_events.py
  - File: src/events/menu_events.py
  - Create MenuInteractionEvent, MenuNavigationEvent classes
  - Add event serialization and validation
  - Purpose: Establish event structures for menu interactions
  - _Requirements: REQ-MENU-007.1_
  - _Leverage: src/events/models.py existing event patterns_

- [x] 30. Implement menu event publishers in src/events/menu_events.py
  - File: src/events/menu_events.py (continue from task 29)
  - Add publish_menu_interaction, publish_worthiness_update methods
  - Integrate with existing EventBus infrastructure
  - Purpose: Enable menu interaction event publishing
  - _Requirements: REQ-MENU-007.1, REQ-MENU-007.3_
  - _Leverage: src/events/bus.py EventBus patterns_

- [x] 31. Add behavioral assessment event handlers in src/modules/emotional/menu_assessment.py
  - File: src/modules/emotional/menu_assessment.py
  - Create menu interaction behavioral assessment handlers
  - Update worthiness scores based on menu usage patterns
  - Purpose: Connect menu behavior with emotional intelligence system
  - _Requirements: REQ-MENU-007.2, REQ-MENU-008.5_
  - _Leverage: src/modules/emotional/behavioral_analysis.py existing patterns_

- [x] 32. Create menu event system tests in tests/events/test_menu_events.py
  - File: tests/events/test_menu_events.py
  - Test event publishing, behavioral assessment integration
  - Mock EventBus and emotional intelligence dependencies
  - Purpose: Ensure event system integration reliability
  - _Requirements: REQ-MENU-007.1, REQ-MENU-007.2_
  - _Leverage: tests/events/ event testing patterns_

### Phase 9: Performance Optimization

- [x] 33. Implement menu caching optimization in src/ui/menu_cache.py
  - File: src/ui/menu_cache.py
  - Add menu generation caching by user context hash
  - Implement cache invalidation for user progression
  - Purpose: Optimize menu generation performance
  - _Requirements: REQ-MENU-006.3_
  - _Leverage: src/utils/cache_manager.py existing cache patterns_

- [x] 34. Add async message cleanup optimization in src/ui/message_manager.py
  - File: src/ui/message_manager.py (modify existing)
  - Implement background task for bulk message deletion
  - Add rate limiting for Telegram API compliance
  - Purpose: Optimize message cleanup performance
  - _Requirements: REQ-MENU-002.4_
  - _Leverage: asyncio patterns, APScheduler from existing modules_

- [x] 35. Create performance monitoring for menu system in src/shared/monitoring/menu_performance.py
  - File: src/shared/monitoring/menu_performance.py
  - Add menu generation time tracking
  - Monitor callback processing performance
  - Purpose: Track menu system performance metrics
  - _Requirements: REQ-MENU-001.3, REQ-MENU-002.2_
  - _Leverage: src/shared/monitoring/performance.py existing patterns_

- [x] 36. Create performance tests in tests/performance/test_menu_performance.py
  - File: tests/performance/test_menu_performance.py
  - Test menu generation under load, concurrent callback processing
  - Verify performance requirements (500ms cached, 2s dynamic)
  - Purpose: Ensure performance requirements are met
  - _Requirements: REQ-MENU-001.3, REQ-MENU-002.2_
  - _Leverage: tests/performance/ performance testing patterns_

### Phase 10: Integration and Deployment

- [x] 37. Create menu system coordinator in src/handlers/menu_system.py
  - File: src/handlers/menu_system.py
  - Create MenuSystemCoordinator class with unified interface
  - Add dependency injection for all menu components
  - Purpose: Provide single entry point for menu functionality
  - _Requirements: REQ-MENU-001.1, REQ-MENU-002.1_
  - _Leverage: MenuHandlerSystem, CallbackProcessor, ActionDispatcher_

- [x] 38. Add system-level error handling in src/handlers/menu_system.py
  - File: src/handlers/menu_system.py (continue from task 37)
  - Implement fallback mechanisms for component failures
  - Add circuit breaker patterns for external dependencies
  - Purpose: Ensure menu system resilience
  - _Requirements: REQ-MENU-006.4_
  - _Leverage: src/shared/resilience/circuit_breaker.py_

- [x] 39. Add menu system configuration in src/config/menu_config.py
  - File: src/config/menu_config.py
  - Define configuration for TTL values, caching, performance limits
  - Add environment-specific menu settings
  - Purpose: Centralize menu system configuration
  - _Requirements: REQ-MENU-002.4, REQ-MENU-006.4_
  - _Leverage: src/config/manager.py configuration patterns_

- [x] 40. Create command to callback flow integration test in tests/integration/test_menu_flow.py
  - File: tests/integration/test_menu_flow.py
  - Test complete flow from user command to menu display to callback processing
  - Verify message cleanup occurs properly in flow
  - Purpose: Ensure core menu interaction flow works end-to-end
  - _Requirements: REQ-MENU-001.1, REQ-MENU-001.3, REQ-MENU-002.2_
  - _Leverage: tests/integration/ integration testing patterns_

- [x] 41. Create role-based access integration test in tests/integration/test_menu_access.py
  - File: tests/integration/test_menu_access.py
  - Test free user, VIP user, and admin user menu access patterns
  - Verify worthiness explanations and organic restrictions
  - Purpose: Ensure role-based access control works correctly
  - _Requirements: REQ-MENU-003.1, REQ-MENU-003.2, REQ-MENU-003.3, REQ-MENU-004.2_
  - _Leverage: tests/integration/ integration testing patterns_

- [x] 42. Create Lucien integration test in tests/integration/test_menu_lucien.py
  - File: tests/integration/test_menu_lucien.py
  - Test Lucien voice consistency across menu interactions
  - Verify personality adaptation based on user relationship levels
  - Purpose: Ensure Lucien personality integration works properly
  - _Requirements: REQ-MENU-005.1, REQ-MENU-005.4_
  - _Leverage: tests/integration/ integration testing patterns_

- [x] 43. Register menu handlers with bot in src/core/application.py
  - File: src/core/application.py (modify existing)
  - Register MenuHandlerSystem with main bot dispatcher
  - Add menu router to application routing
  - Purpose: Connect menu system to main application
  - _Requirements: REQ-MENU-002.1_
  - _Leverage: existing application.py handler registration patterns_

- [x] 44. Initialize menu components on startup in src/core/application.py
  - File: src/core/application.py (continue from task 43)
  - Initialize MessageManager, MenuSystemCoordinator on startup
  - Configure menu system dependencies and connections
  - Purpose: Deploy menu system in production application
  - _Requirements: REQ-MENU-002.1, REQ-MENU-006.1_
  - _Leverage: existing application.py initialization patterns_
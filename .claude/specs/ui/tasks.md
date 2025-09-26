# Implementation Plan

## Task Overview

This document breaks down the UI specification into atomic, agent-friendly coding tasks. Each task implements the complete user journey flow from `/start` command to Level 2 unlocking, ensuring separation of narrative progression from VIP subscriptions while leveraging existing YABOT infrastructure.

## Steering Document Compliance

Tasks follow structure.md module organization patterns by placing services in `src/services/`, handlers in `src/handlers/`, and schemas in `src/database/schemas/`. They adhere to tech.md standards using event-driven architecture with Redis EventBus, dual MongoDB/SQLite database strategy, async/await patterns, and Pydantic models for type safety.

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
- Reference existing code to leverage using: `_Leverage: path/to/file.py_`
- Focus only on coding tasks (no deployment, user testing, etc.)
- **Avoid broad terms**: No "system", "integration", "complete" in task titles

## Good vs Bad Task Examples

❌ **Bad Examples (Too Broad)**:
- "Implement level progression system" (affects many files, multiple purposes)
- "Add user journey features" (vague scope, no file specification)
- "Build complete mission flow" (too large, multiple components)

✅ **Good Examples (Atomic)**:
- "Add narrative_level field to user schema in schemas/users.py"
- "Create LevelProgressionEvent class in events/models.py"
- "Add channel validation method to ReactionDetector class"

## Tasks

- [ ] 1. Add narrative_level field to user schema
  - File: src/database/schemas/users.py (modify existing)
  - Add `narrative_level: int = Field(default=1)` to user document schema
  - Ensure backward compatibility for existing users without this field
  - Purpose: Separate narrative progression from VIP subscription status in SQLite
  - _Leverage: src/database/schemas/users.py existing user schema patterns_
  - _Requirements: 5.2_

- [ ] 2. Create LevelProgressionEvent model in events module
  - File: src/events/models.py (modify existing)
  - Add LevelProgressionEvent class extending BaseEvent
  - Include fields: user_id, old_level, new_level, trigger_action, source
  - Purpose: Enable event publishing for level progression coordination
  - _Leverage: src/events/models.py existing BaseEvent patterns_
  - _Requirements: 5.5_

- [ ] 3. Create PistaPurchaseTransaction schema for gamification
  - File: src/database/schemas/gamification.py (modify existing)
  - Add PistaPurchaseTransaction model with transaction_id, user_id, pista_id, cost, status
  - Include idempotency_key field to prevent duplicate purchases
  - Purpose: Track pista purchases with atomic operations
  - _Leverage: src/database/schemas/gamification.py existing transaction patterns_
  - _Requirements: 4.3_

- [ ] 4. Create basic LevelProgressionService class structure
  - File: src/services/level_progression.py (create new)
  - Create class with __init__ method and dependencies injection
  - Add get_user_level method returning current narrative_level from MongoDB
  - Purpose: Establish service foundation for level progression logic
  - _Leverage: src/services/user.py, src/services/subscription.py service patterns_
  - _Requirements: 5.1, 5.2_

- [ ] 5. Add level validation methods to LevelProgressionService
  - File: src/services/level_progression.py (continue from task 4)
  - Add check_level_progression method to validate Level 2 unlock conditions
  - Add validate_mission_completion and validate_pista_purchase helper methods
  - Purpose: Implement business logic for level progression validation
  - _Leverage: src/modules/gamification/mission_manager.py mission patterns_
  - _Requirements: 4.5, 5.1_

- [ ] 6. Add level unlocking method to LevelProgressionService
  - File: src/services/level_progression.py (continue from task 5)
  - Add unlock_level method to atomically update narrative_level in MongoDB
  - Publish LevelProgressionEvent to event bus after successful update
  - Purpose: Complete level progression functionality with event coordination
  - _Leverage: src/events/bus.py event publishing patterns_
  - _Requirements: 5.1, 5.5_

- [ ] 7. Create basic PistaShop service class
  - File: src/services/pista_shop.py (create new)
  - Create class with dependencies: BesitosWallet, HintSystem, DatabaseManager
  - Add validate_purchase method to check user balance ≥ 10 besitos
  - Purpose: Establish pista purchase service foundation
  - _Leverage: src/modules/gamification/besitos_wallet.py, src/modules/narrative/hint_system.py_
  - _Requirements: 4.1, 4.2_

- [ ] 8. Add atomic purchase method to PistaShop
  - File: src/services/pista_shop.py (continue from task 7)
  - Add purchase_pista method with MongoDB transaction for atomic operations
  - Include idempotency protection using transaction_id verification
  - Purpose: Implement secure pista purchasing with duplicate prevention
  - _Leverage: src/modules/gamification/besitos_wallet.py atomic operations_
  - _Requirements: 4.3, 4.4_

- [ ] 9. Add Level 2 pista processing to PistaShop
  - File: src/services/pista_shop.py (continue from task 8)
  - Add process_level_2_pista method to handle "Acceso a Nivel 2" pista
  - Integrate with LevelProgressionService to trigger automatic level unlock
  - Purpose: Complete pista purchase flow with level progression integration
  - _Leverage: src/services/level_progression.py (from previous tasks)_
  - _Requirements: 4.5_

- [ ] 10. Add channel validation to ReactionDetector
  - File: src/modules/gamification/reaction_detector.py (modify existing)
  - Add validate_reaction_channel method to check chat_id matches @yabot_canal
  - Add validate_reaction_emoji method to ensure ❤️ emoji requirement
  - Purpose: Ensure reactions only count in correct channel with correct emoji
  - _Leverage: src/modules/gamification/reaction_detector.py existing validation patterns_
  - _Requirements: 2.2, 2.3_

- [ ] 11. Integrate mission completion in ReactionDetector
  - File: src/modules/gamification/reaction_detector.py (continue from task 10)
  - Add trigger_mission_completion method to complete Level 1 reaction mission
  - Integrate with MissionManager to update mission status automatically
  - Purpose: Connect reaction detection to mission completion flow
  - _Leverage: src/modules/gamification/mission_manager.py mission completion patterns_
  - _Requirements: 2.4, 2.5_

- [ ] 12. Enhance start command handler for Level 1 setup
  - File: src/handlers/commands.py (modify existing handle_start_command)
  - Add Level 1 user initialization with narrative_level=1 in MongoDB
  - Add initial mission assignment for "Reacciona en el Canal Principal"
  - Purpose: Set up new users at Level 1 with first mission
  - _Leverage: src/handlers/commands.py existing start command patterns_
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 13. Add welcome message with Level 1 capabilities to start handler
  - File: src/handlers/commands.py (continue from task 12)
  - Add build_welcome_message method listing exactly 3 Level 1 capabilities
  - Add get_existing_user_status method for returning users showing level/balance
  - Purpose: Provide clear onboarding information and status for users
  - _Leverage: src/handlers/commands.py existing message formatting_
  - _Requirements: 1.4, 1.5_

- [ ] 14. Create PistaShopHandler class for purchase interface
  - File: src/handlers/pista_shop.py (create new)
  - Create handler class with callback_query processing for pista purchases
  - Add build_shop_keyboard method showing purchase button when balance ≥ 10
  - Purpose: Provide reactive purchase interface based on user balance
  - _Leverage: src/handlers/commands.py callback handler patterns_
  - _Requirements: 4.1_

- [ ] 15. Add purchase callback processing to PistaShopHandler
  - File: src/handlers/pista_shop.py (continue from task 14)
  - Add handle_pista_purchase_callback method processing "buy_pista" callbacks
  - Integrate with PistaShop service for actual purchase execution
  - Purpose: Complete purchase workflow with callback handling
  - _Leverage: src/services/pista_shop.py (from previous tasks)_
  - _Requirements: 4.2_

- [ ] 16. Create LevelProgressionHandler for celebrations
  - File: src/handlers/level_progression.py (create new)
  - Create handler for level progression events with celebration messages
  - Add send_level_unlock_message with Lucien persona voice
  - Purpose: Provide engaging Level 2 unlock experience
  - _Leverage: src/handlers/commands.py message formatting patterns_
  - _Requirements: 5.4_

- [ ] 17. Add Level 2 menu options to LevelProgressionHandler
  - File: src/handlers/level_progression.py (continue from task 16)
  - Add update_user_menu method with at least 2 new Level 2 options
  - Add build_level_2_keyboard method for new functionality access
  - Purpose: Provide immediate access to Level 2 features
  - _Leverage: src/handlers/commands.py inline keyboard patterns_
  - _Requirements: 5.3_

- [ ] 18. Add Level 1 reaction mission template to MissionManager
  - File: src/modules/gamification/mission_manager.py (modify existing)
  - Add create_reaction_mission method for "Reacciona en el Canal Principal"
  - Include @yabot_canal target and ❤️ emoji requirement in mission data
  - Purpose: Standardize Level 1 mission creation
  - _Leverage: src/modules/gamification/mission_manager.py existing mission templates_
  - _Requirements: 2.1, 2.2_

- [ ] 19. Add Level 2 pista definition to HintSystem
  - File: src/modules/narrative/hint_system.py (modify existing)
  - Add create_level_2_pista method defining "Acceso a Nivel 2" hint
  - Set cost to 10 besitos and link to level progression trigger
  - Purpose: Establish Level 2 unlock mechanism through pista system
  - _Leverage: src/modules/narrative/hint_system.py existing hint patterns_
  - _Requirements: 4.4, 4.5_

- [ ] 20. Add level progression event listener to EventProcessor
  - File: src/events/processor.py (modify existing)
  - Add register_level_progression_listener method for LevelProgressionEvent
  - Add handle_level_progression method to coordinate cross-module updates
  - Purpose: Enable event-driven coordination between modules
  - _Leverage: src/events/processor.py existing event listener patterns_
  - _Requirements: 6.1, 6.2_

- [ ] 21. Add channel configuration to ConfigManager
  - File: src/config/manager.py (modify existing)
  - Add YABOT_CANAL_ID configuration with validation
  - Add validate_channel_access method to verify bot permissions
  - Purpose: Ensure proper channel configuration for reaction detection
  - _Leverage: src/config/manager.py existing validation patterns_
  - _Requirements: 2.2_

- [ ] 22. Create level progression validation module
  - File: src/validators/level_progression.py (create new)
  - Add validate_level_2_requirements method checking mission + pista conditions
  - Add prevent_invalid_progression method with comprehensive validation
  - Purpose: Ensure users meet all requirements before level progression
  - _Leverage: existing validation patterns in codebase_
  - _Requirements: 1.5, 4.2, 5.1_

- [ ] 23. Add error handling to LevelProgressionService
  - File: src/services/level_progression.py (modify from earlier tasks)
  - Add retry mechanism for failed level progression operations
  - Add user-friendly error messages for progression failures
  - Purpose: Ensure reliable level progression with proper error recovery
  - _Leverage: src/utils/error_handler.py existing error patterns_
  - _Requirements: 6.4, 6.5_

- [ ] 24. Add besitos transaction recovery to BesitosWallet
  - File: src/modules/gamification/besitos_wallet.py (modify existing)
  - Add retry_failed_transaction method for mission reward failures
  - Implement exactly one retry attempt with specific error messages
  - Purpose: Ensure reliable besitos rewards as specified in requirements
  - _Leverage: src/modules/gamification/besitos_wallet.py existing retry patterns_
  - _Requirements: 3.5_

- [ ] 25. Create Level 1 to Level 2 progression integration test
  - File: tests/integration/test_level_progression_flow.py (create new)
  - Test complete user journey: start → mission → besitos → purchase → Level 2
  - Use real services without mocks as per CLAUDE.md requirements
  - Purpose: Validate complete user journey functionality
  - _Leverage: tests/integration/ existing integration test patterns_
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

- [ ] 26. Create reaction validation integration test
  - File: tests/integration/test_reaction_channel_validation.py (create new)
  - Test reaction detection only works in @yabot_canal with ❤️ emoji
  - Test mission completion integration with proper validation
  - Purpose: Ensure reaction detection works correctly with validation
  - _Leverage: tests/integration/ existing reaction test patterns_
  - _Requirements: 2.2, 2.3_

- [ ] 27. Create pista purchase atomicity test
  - File: tests/integration/test_pista_atomic_operations.py (create new)
  - Test atomic besitos deduction and hint unlocking operations
  - Test idempotency protection prevents duplicate purchases
  - Purpose: Ensure transaction reliability and duplicate prevention
  - _Leverage: tests/integration/ existing transaction test patterns_
  - _Requirements: 4.3_
#!/usr/bin/env python3
"""
Validation Script for Tasks 1-6 Implementation
==============================================

This script validates the correct implementation of the modulos-atomicos tasks 1-6
without running into circular import issues.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

def validate_task_1_system_resilience_events():
    """Validate Task 1: System resilience event models in src/events/models.py"""
    print("🔍 Validating Task 1: System resilience event models...")

    try:
        # Check if the file exists
        events_models_path = Path("src/events/models.py")
        if not events_models_path.exists():
            return False, "❌ src/events/models.py file not found"

        # Read and check content
        content = events_models_path.read_text()
        required_classes = [
            "BaseEvent",
            "EventStatus",
            "EventProcessingErrorEvent",
            "SystemResilienceEvent"
        ]

        missing_classes = []
        for cls in required_classes:
            if f"class {cls}" not in content:
                missing_classes.append(cls)

        if missing_classes:
            return False, f"❌ Missing resilience event classes: {', '.join(missing_classes)}"

        # Check for resilience features
        resilience_features = [
            "retries",
            "max_retries",
            "correlation_id",
            "FAILED",
            "RETRYING"
        ]

        missing_features = []
        for feature in resilience_features:
            if feature not in content:
                missing_features.append(feature)

        if missing_features:
            return False, f"❌ Missing resilience features: {', '.join(missing_features)}"

        return True, "✅ Task 1: System resilience event models implemented correctly"

    except Exception as e:
        return False, f"❌ Task 1 validation error: {str(e)}"

def validate_task_2_event_correlation():
    """Validate Task 2: Event correlation service in src/shared/events/correlation.py"""
    print("🔍 Validating Task 2: Event correlation service...")

    try:
        # Check if the file exists
        correlation_path = Path("src/shared/events/correlation.py")
        if not correlation_path.exists():
            return False, "❌ src/shared/events/correlation.py file not found"

        # Read and check content
        content = correlation_path.read_text()
        required_classes = [
            "EventCorrelationService",
            "CorrelationRecord",
            "CorrelationStatus"
        ]

        missing_classes = []
        for cls in required_classes:
            if f"class {cls}" not in content or f"{cls}(" not in content:
                missing_classes.append(cls)

        if missing_classes:
            return False, f"❌ Missing correlation classes: {', '.join(missing_classes)}"

        # Check for Redis patterns
        redis_features = [
            "redis.asyncio",
            "correlation_id",
            "track_event",
            "get_correlation"
        ]

        missing_features = []
        for feature in redis_features:
            if feature not in content:
                missing_features.append(feature)

        if missing_features:
            return False, f"❌ Missing Redis correlation features: {', '.join(missing_features)}"

        return True, "✅ Task 2: Event correlation service implemented correctly"

    except Exception as e:
        return False, f"❌ Task 2 validation error: {str(e)}"

def validate_task_3_event_bus_retry():
    """Validate Task 3: Event bus retry mechanism in src/events/bus.py"""
    print("🔍 Validating Task 3: Event bus retry mechanism...")

    try:
        # Check if the file exists
        bus_path = Path("src/events/bus.py")
        if not bus_path.exists():
            return False, "❌ src/events/bus.py file not found"

        # Read and check content
        content = bus_path.read_text()
        retry_features = [
            "LocalEventQueue",
            "_retry_with_backoff",
            "exponential_backoff",
            "max_retries",
            "retry_attempt"
        ]

        missing_features = []
        for feature in retry_features:
            if feature not in content:
                missing_features.append(feature)

        if missing_features:
            return False, f"❌ Missing retry features: {', '.join(missing_features)}"

        # Check for enhanced EventBus class
        if "class EventBus" not in content:
            return False, "❌ EventBus class not found"

        return True, "✅ Task 3: Event bus retry mechanism implemented correctly"

    except Exception as e:
        return False, f"❌ Task 3 validation error: {str(e)}"

def validate_task_4_narrative_schema():
    """Validate Task 4: Narrative collections schema in src/database/schemas/narrative.py"""
    print("🔍 Validating Task 4: Narrative collections schema...")

    try:
        # Check if the file exists
        narrative_path = Path("src/database/schemas/narrative.py")
        if not narrative_path.exists():
            return False, "❌ src/database/schemas/narrative.py file not found"

        # Read and check content
        content = narrative_path.read_text()
        required_classes = [
            "NarrativeFragmentMongoSchema",
            "Choice",
            "NarrativeProgressMongoSchema"
        ]

        missing_classes = []
        for cls in required_classes:
            if f"class {cls}" not in content:
                missing_classes.append(cls)

        if missing_classes:
            return False, f"❌ Missing narrative schema classes: {', '.join(missing_classes)}"

        # Check for MongoDB patterns
        mongo_features = [
            "PyObjectId",
            "_id",
            "fragment_id",
            "choices",
            "vip_required"
        ]

        missing_features = []
        for feature in mongo_features:
            if feature not in content:
                missing_features.append(feature)

        if missing_features:
            return False, f"❌ Missing MongoDB narrative features: {', '.join(missing_features)}"

        return True, "✅ Task 4: Narrative collections schema implemented correctly"

    except Exception as e:
        return False, f"❌ Task 4 validation error: {str(e)}"

def validate_task_5_gamification_schema():
    """Validate Task 5: Gamification collections schema in src/database/schemas/gamification.py"""
    print("🔍 Validating Task 5: Gamification collections schema...")

    try:
        # Check if the file exists
        gamification_path = Path("src/database/schemas/gamification.py")
        if not gamification_path.exists():
            return False, "❌ src/database/schemas/gamification.py file not found"

        # Read and check content
        content = gamification_path.read_text()
        required_classes = [
            "BesitosTransactionMongoSchema",
            "MissionMongoSchema",
            "AuctionMongoSchema",
            "TriviaMongoSchema",
            "AchievementMongoSchema"
        ]

        missing_classes = []
        for cls in required_classes:
            if f"class {cls}" not in content:
                missing_classes.append(cls)

        if missing_classes:
            return False, f"❌ Missing gamification schema classes: {', '.join(missing_classes)}"

        # Check for transaction patterns
        transaction_features = [
            "transaction_id",
            "besitos",
            "balance_after",
            "atomic",
            "amount"
        ]

        missing_features = []
        for feature in transaction_features:
            if feature not in content:
                missing_features.append(feature)

        if missing_features:
            return False, f"❌ Missing transaction features: {', '.join(missing_features)}"

        return True, "✅ Task 5: Gamification collections schema implemented correctly"

    except Exception as e:
        return False, f"❌ Task 5 validation error: {str(e)}"

def validate_task_6_users_schema_extension():
    """Validate Task 6: Extended users schema in src/database/schemas/mongo.py"""
    print("🔍 Validating Task 6: Extended users schema...")

    try:
        # Check if the file exists
        mongo_path = Path("src/database/schemas/mongo.py")
        if not mongo_path.exists():
            return False, "❌ src/database/schemas/mongo.py file not found"

        # Read and check content
        content = mongo_path.read_text()

        # Check for UserMongoSchema class
        if "class UserMongoSchema" not in content:
            return False, "❌ UserMongoSchema class not found"

        # Check for extended fields
        extended_fields = [
            "besitos_balance",
            "narrative_progress",
            "subscription_status",
            "active_missions",
            "unlocked_achievements",
            "inventory",
            "channels_access"
        ]

        missing_fields = []
        for field in extended_fields:
            if field not in content:
                missing_fields.append(field)

        if missing_fields:
            return False, f"❌ Missing extended user fields: {', '.join(missing_fields)}"

        return True, "✅ Task 6: Extended users schema implemented correctly"

    except Exception as e:
        return False, f"❌ Task 6 validation error: {str(e)}"

def main():
    """Run all task validations"""
    print("=" * 60)
    print("🚀 VALIDATING MODULOS-ATOMICOS TASKS 1-6 IMPLEMENTATION")
    print("=" * 60)

    # Change to repo directory
    os.chdir("/home/azureuser/repos/yabot")

    validations = [
        validate_task_1_system_resilience_events,
        validate_task_2_event_correlation,
        validate_task_3_event_bus_retry,
        validate_task_4_narrative_schema,
        validate_task_5_gamification_schema,
        validate_task_6_users_schema_extension
    ]

    results = []
    for validation in validations:
        success, message = validation()
        results.append((success, message))
        print(f"  {message}")

    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for success, _ in results if success)
    total = len(results)

    for success, message in results:
        print(f"  {message}")

    print(f"\n🎯 RESULT: {passed}/{total} tasks validated successfully")

    if passed == total:
        print("🎉 ALL TASKS IMPLEMENTED CORRECTLY!")
        return 0
    else:
        print("⚠️  Some tasks need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
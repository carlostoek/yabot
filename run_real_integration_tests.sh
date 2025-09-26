#!/bin/bash
# YABOT Real Integration Tests Runner
# Configures environment for testing without MongoDB transactions

echo "🚀 Setting up YABOT Real Integration Test Environment"

# Set environment variables for testing
export MONGODB_DATABASE=yabot_real_test
export MONGODB_URI=mongodb://localhost:27017/yabot_real_test
export REDIS_URL=redis://localhost:6379/5
export DISABLE_MONGO_TRANSACTIONS=true

echo "📋 Environment Configuration:"
echo "   MongoDB URI: $MONGODB_URI"
echo "   Redis URL: $REDIS_URL"
echo "   Transactions Disabled: $DISABLE_MONGO_TRANSACTIONS"

echo ""
echo "🧪 Running Real Integration Tests..."

# Activate virtual environment and run tests
source venv/bin/activate
python test_real_integration_environment.py

echo ""
echo "✅ Integration test execution completed"
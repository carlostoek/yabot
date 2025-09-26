#!/bin/bash
# Environment setup for YABOT integration tests

export MONGODB_URI="mongodb://127.0.0.1:27017,127.0.0.1:27018,127.0.0.1:27019/yabot_integration_test?replicaSet=yabot-rs"
export MONGODB_DATABASE="yabot_integration_test"
export REDIS_URL="redis://127.0.0.1:6379/5"
export PYTEST_RUNNING="true"

echo "🌍 Environment variables set for integration testing:"
echo "   MONGODB_URI=$MONGODB_URI"
echo "   MONGODB_DATABASE=$MONGODB_DATABASE"
echo "   REDIS_URL=$REDIS_URL"

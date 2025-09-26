#!/bin/bash
# Setup Real Testing Environment for YABOT Integration Tests
# This script configures MongoDB replica set and Redis for real integration testing

set -e

echo "🚀 Setting up YABOT Real Integration Test Environment"
echo "=" * 60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if MongoDB is installed
echo "🔍 Checking MongoDB installation..."
if command -v mongod &> /dev/null; then
    print_status "MongoDB is installed"
    mongod --version | head -1
else
    print_error "MongoDB is not installed. Please install MongoDB first."
    echo "Installation instructions: https://docs.mongodb.com/manual/installation/"
    exit 1
fi

# Check if Redis is installed
echo "🔍 Checking Redis installation..."
if command -v redis-server &> /dev/null; then
    print_status "Redis is installed"
    redis-server --version
else
    print_error "Redis is not installed. Please install Redis first."
    echo "Installation instructions: https://redis.io/download"
    exit 1
fi

# Create directories for MongoDB replica set
echo "📁 Creating MongoDB replica set directories..."
mkdir -p /tmp/mongodb-rs/rs0
mkdir -p /tmp/mongodb-rs/rs1
mkdir -p /tmp/mongodb-rs/rs2
mkdir -p /tmp/mongodb-rs/logs
print_status "MongoDB directories created"

# Create MongoDB configuration files
echo "⚙️  Creating MongoDB configuration files..."

# Primary node config
cat > /tmp/mongodb-rs/mongod-rs0.conf << 'EOF'
systemLog:
  destination: file
  path: /tmp/mongodb-rs/logs/mongod-rs0.log
  logAppend: true
storage:
  dbPath: /tmp/mongodb-rs/rs0
net:
  port: 27017
  bindIp: 127.0.0.1
replication:
  replSetName: yabot-rs
processManagement:
  fork: false
EOF

# Secondary node 1 config
cat > /tmp/mongodb-rs/mongod-rs1.conf << 'EOF'
systemLog:
  destination: file
  path: /tmp/mongodb-rs/logs/mongod-rs1.log
  logAppend: true
storage:
  dbPath: /tmp/mongodb-rs/rs1
net:
  port: 27018
  bindIp: 127.0.0.1
replication:
  replSetName: yabot-rs
processManagement:
  fork: false
EOF

# Secondary node 2 config
cat > /tmp/mongodb-rs/mongod-rs2.conf << 'EOF'
systemLog:
  destination: file
  path: /tmp/mongodb-rs/logs/mongod-rs2.log
  logAppend: true
storage:
  dbPath: /tmp/mongodb-rs/rs2
net:
  port: 27019
  bindIp: 127.0.0.1
replication:
  replSetName: yabot-rs
processManagement:
  fork: false
EOF

print_status "MongoDB configuration files created"

# Create startup script
cat > /tmp/mongodb-rs/start-replica-set.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting MongoDB Replica Set..."

# Start all MongoDB instances
mongod --config /tmp/mongodb-rs/mongod-rs0.conf &
MONGO_PID_0=$!

mongod --config /tmp/mongodb-rs/mongod-rs1.conf &
MONGO_PID_1=$!

mongod --config /tmp/mongodb-rs/mongod-rs2.conf &
MONGO_PID_2=$!

echo "MongoDB instances started with PIDs: $MONGO_PID_0, $MONGO_PID_1, $MONGO_PID_2"

# Wait for instances to be ready
sleep 5

# Initialize replica set
echo "🔧 Initializing replica set..."
mongosh --port 27017 --eval '
rs.initiate({
  _id: "yabot-rs",
  members: [
    { _id: 0, host: "127.0.0.1:27017" },
    { _id: 1, host: "127.0.0.1:27018" },
    { _id: 2, host: "127.0.0.1:27019" }
  ]
})
'

echo "⏳ Waiting for replica set to elect primary..."
sleep 10

# Check replica set status
mongosh --port 27017 --eval 'rs.status()'

echo "✅ MongoDB Replica Set is ready!"
echo "Primary: mongodb://127.0.0.1:27017,127.0.0.1:27018,127.0.0.1:27019/yabot_test?replicaSet=yabot-rs"

# Keep processes running
wait
EOF

chmod +x /tmp/mongodb-rs/start-replica-set.sh

# Create shutdown script
cat > /tmp/mongodb-rs/stop-replica-set.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping MongoDB Replica Set..."

# Kill MongoDB processes
pkill -f "mongod.*yabot-rs" || true

# Clean up data directories
rm -rf /tmp/mongodb-rs/rs0/*
rm -rf /tmp/mongodb-rs/rs1/*
rm -rf /tmp/mongodb-rs/rs2/*

echo "✅ MongoDB Replica Set stopped and cleaned"
EOF

chmod +x /tmp/mongodb-rs/stop-replica-set.sh

print_status "MongoDB replica set scripts created"

# Create Redis configuration for testing
echo "⚙️  Creating Redis test configuration..."
cat > /tmp/redis-test.conf << 'EOF'
port 6379
bind 127.0.0.1
databases 16
save ""
appendonly no
EOF

print_status "Redis configuration created"

# Create environment setup script
cat > setup_env.sh << 'EOF'
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
EOF

chmod +x setup_env.sh

print_status "Environment setup script created"

# Create test runner script
cat > run_real_integration_tests.sh << 'EOF'
#!/bin/bash
set -e

echo "🧪 YABOT Real Integration Tests Runner"
echo "=" * 50

# Source environment
source ./setup_env.sh

echo "🔍 Checking services..."

# Check MongoDB replica set
echo "Checking MongoDB replica set..."
if mongosh --quiet --port 27017 --eval 'rs.status().ok' | grep -q "1"; then
    echo "✅ MongoDB replica set is running"
else
    echo "❌ MongoDB replica set is not ready"
    echo "Please run: /tmp/mongodb-rs/start-replica-set.sh"
    exit 1
fi

# Check Redis
echo "Checking Redis..."
if redis-cli -p 6379 ping | grep -q "PONG"; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not running"
    echo "Please start Redis: redis-server /tmp/redis-test.conf &"
    exit 1
fi

echo "🚀 Starting real integration tests..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Run the real integration tests
echo "Running BesitosWallet real integration test..."
python test_real_besitos_wallet.py

echo ""
echo "Running MissionManager real integration test..."
python test_real_mission_manager.py

echo ""
echo "Running full end-to-end integration test..."
python test_real_end_to_end.py

echo ""
echo "🎉 All real integration tests completed!"
EOF

chmod +x run_real_integration_tests.sh

print_status "Test runner script created"

# Create service management script
cat > manage_test_services.sh << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "🚀 Starting test services..."

        # Start Redis
        echo "Starting Redis..."
        redis-server /tmp/redis-test.conf &
        REDIS_PID=$!
        echo "Redis PID: $REDIS_PID"

        # Start MongoDB replica set
        echo "Starting MongoDB replica set..."
        /tmp/mongodb-rs/start-replica-set.sh &
        MONGO_PID=$!
        echo "MongoDB replica set PID: $MONGO_PID"

        # Save PIDs
        echo $REDIS_PID > /tmp/redis-test.pid
        echo $MONGO_PID > /tmp/mongo-rs.pid

        echo "✅ Services started"
        echo "Redis: localhost:6379"
        echo "MongoDB: mongodb://127.0.0.1:27017,127.0.0.1:27018,127.0.0.1:27019/?replicaSet=yabot-rs"
        ;;

    stop)
        echo "🛑 Stopping test services..."

        # Stop Redis
        if [ -f /tmp/redis-test.pid ]; then
            kill $(cat /tmp/redis-test.pid) 2>/dev/null || true
            rm /tmp/redis-test.pid
        fi
        pkill -f "redis-server.*redis-test.conf" || true

        # Stop MongoDB
        /tmp/mongodb-rs/stop-replica-set.sh

        echo "✅ Services stopped"
        ;;

    status)
        echo "📊 Service status:"

        # Check Redis
        if redis-cli -p 6379 ping 2>/dev/null | grep -q "PONG"; then
            echo "✅ Redis: Running"
        else
            echo "❌ Redis: Not running"
        fi

        # Check MongoDB
        if mongosh --quiet --port 27017 --eval 'rs.status().ok' 2>/dev/null | grep -q "1"; then
            echo "✅ MongoDB Replica Set: Running"
        else
            echo "❌ MongoDB Replica Set: Not running"
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|status}"
        echo ""
        echo "  start  - Start MongoDB replica set and Redis for testing"
        echo "  stop   - Stop all test services"
        echo "  status - Check service status"
        exit 1
        ;;
esac
EOF

chmod +x manage_test_services.sh

print_status "Service management script created"

echo ""
echo "🎉 Real Integration Test Environment Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Start services: ./manage_test_services.sh start"
echo "2. Check status:  ./manage_test_services.sh status"
echo "3. Run tests:     ./run_real_integration_tests.sh"
echo "4. Stop services: ./manage_test_services.sh stop"
echo ""
echo "📁 Files created:"
echo "  - manage_test_services.sh  (Start/stop services)"
echo "  - run_real_integration_tests.sh  (Run tests)"
echo "  - setup_env.sh  (Environment variables)"
echo "  - /tmp/mongodb-rs/  (MongoDB replica set config)"
echo "  - /tmp/redis-test.conf  (Redis config)"
echo ""
print_warning "Note: You'll need to start the services before running tests"
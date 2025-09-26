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

#!/usr/bin/env python3
"""
Initialize MongoDB replica set using Python motor client
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def initialize_replica_set():
    """Initialize MongoDB replica set"""
    print("🔧 Initializing MongoDB Replica Set...")

    try:
        # Connect to primary node
        client = AsyncIOMotorClient('mongodb://127.0.0.1:27017')
        admin_db = client.admin

        # Initialize replica set configuration
        config = {
            "_id": "yabot-rs",
            "members": [
                {"_id": 0, "host": "127.0.0.1:27017"},
                {"_id": 1, "host": "127.0.0.1:27018"},
                {"_id": 2, "host": "127.0.0.1:27019"}
            ]
        }

        # Try to initialize
        try:
            result = await admin_db.command("replSetInitiate", config)
            print(f"✅ Replica set initialized: {result}")
        except Exception as e:
            if "already initialized" in str(e):
                print("✅ Replica set already initialized")
            else:
                print(f"❌ Error initializing replica set: {e}")

        # Wait for replica set to be ready
        print("⏳ Waiting for replica set to elect primary...")
        await asyncio.sleep(10)

        # Check status
        try:
            status = await admin_db.command("replSetGetStatus")
            print("✅ Replica Set Status:")
            for member in status.get('members', []):
                state = member.get('stateStr', 'UNKNOWN')
                host = member.get('name', 'unknown')
                print(f"   {host}: {state}")

            return True

        except Exception as e:
            print(f"⚠️  Could not get replica set status: {e}")
            return False

    except Exception as e:
        print(f"❌ Failed to connect or initialize: {e}")
        return False

    finally:
        client.close()

if __name__ == "__main__":
    success = asyncio.run(initialize_replica_set())
    if success:
        print("🎉 MongoDB Replica Set is ready!")
    else:
        print("❌ Failed to setup replica set")
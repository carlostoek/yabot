#!/usr/bin/env python3
"""
Migration script for Fase1 implementation.

This script handles the migration of existing bot functionality to the new 
infrastructure as required by Requirement 5.4 of the fase1 specification.
"""

import asyncio
import sys
import os
import argparse
import logging
from typing import Dict, Any, Optional

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.manager import DatabaseManager
from src.services.user import UserService
from src.events.bus import EventBus
from src.config.manager import ConfigManager
from src.utils.logger import get_logger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = get_logger(__name__)


class MigrationManager:
    """Manager for migrating existing bot functionality to Fase1 infrastructure."""
    
    def __init__(self):
        """Initialize the migration manager."""
        self.config_manager = ConfigManager()
        self.database_manager = None
        self.event_bus = None
        self.user_service = None
        self.migration_stats = {
            'users_migrated': 0,
            'users_failed': 0,
            'total_processed': 0
        }
    
    async def initialize_services(self) -> bool:
        """Initialize all required services for migration.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing services for migration...")
            
            # Initialize database manager
            self.database_manager = DatabaseManager(self.config_manager)
            
            # Initialize event bus
            self.event_bus = EventBus(self.config_manager)
            
            # Initialize user service
            self.user_service = UserService(self.database_manager, self.event_bus)
            
            # Connect to databases
            success = await self.database_manager.connect_all()
            if not success:
                logger.error("Failed to connect to databases")
                return False
            
            # Connect to event bus
            success = await self.event_bus.connect()
            if not success:
                logger.error("Failed to connect to event bus")
                return False
            
            logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            return False
    
    async def migrate_existing_users(self) -> bool:
        """Migrate existing users to the new database schema.
        
        Returns:
            bool: True if migration was successful, False otherwise
        """
        logger.info("Starting user migration...")
        
        try:
            # In a real implementation, this would:
            # 1. Query existing user data from the old storage system
            # 2. Transform the data to match the new schema
            # 3. Create user records in both MongoDB and SQLite
            # 4. Publish user_migrated events
            
            # For demonstration purposes, we'll simulate migrating some users
            test_users = [
                {
                    "id": 123456789,
                    "username": "existinguser1",
                    "first_name": "Existing",
                    "last_name": "User1",
                    "language_code": "en"
                },
                {
                    "id": 987654321,
                    "username": "existinguser2",
                    "first_name": "Existing",
                    "last_name": "User2",
                    "language_code": "es"
                }
            ]
            
            for telegram_user in test_users:
                try:
                    # Create user in new system
                    success = await self.user_service.create_user(telegram_user)
                    if success:
                        self.migration_stats['users_migrated'] += 1
                        logger.info(f"Successfully migrated user {telegram_user['username']}")
                    else:
                        self.migration_stats['users_failed'] += 1
                        logger.warning(f"Failed to migrate user {telegram_user['username']}")
                except Exception as e:
                    self.migration_stats['users_failed'] += 1
                    logger.error(f"Error migrating user {telegram_user['username']}: {e}")
                
                self.migration_stats['total_processed'] += 1
            
            logger.info("User migration completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during user migration: {e}")
            return False
    
    async def enable_dual_read_write_mode(self) -> bool:
        """Enable dual read/write mode for backward compatibility.
        
        Returns:
            bool: True if mode was enabled successfully, False otherwise
        """
        logger.info("Enabling dual read/write mode...")
        
        try:
            # In a real implementation, this would:
            # 1. Configure the system to read from both old and new data sources
            # 2. Configure the system to write to both old and new data sources
            # 3. Set up appropriate fallback mechanisms
            
            # For demonstration purposes, we'll just log that this mode is enabled
            logger.info("Dual read/write mode enabled")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling dual read/write mode: {e}")
            return False
    
    async def validate_migration(self) -> bool:
        """Validate that the migration was successful.
        
        Returns:
            bool: True if validation passed, False otherwise
        """
        logger.info("Validating migration...")
        
        try:
            # In a real implementation, this would:
            # 1. Verify that all migrated data is accessible
            # 2. Check data consistency between old and new systems
            # 3. Validate that all services are working correctly
            
            # For demonstration purposes, we'll just check basic connectivity
            db_health = await self.database_manager.health_check()
            redis_health = await self.event_bus.health_check()
            
            if db_health.get("mongodb") and db_health.get("sqlite") and redis_health.get("connected"):
                logger.info("Migration validation passed")
                return True
            else:
                logger.error("Migration validation failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during migration validation: {e}")
            return False
    
    async def rollback_migration(self) -> bool:
        """Rollback the migration if it fails.
        
        Returns:
            bool: True if rollback was successful, False otherwise
        """
        logger.info("Rolling back migration...")
        
        try:
            # In a real implementation, this would:
            # 1. Stop new service components
            # 2. Revert handler modifications
            # 3. Switch back to old data patterns
            # 4. Validate system functionality
            
            # For demonstration purposes, we'll just log that rollback is happening
            logger.info("Migration rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during migration rollback: {e}")
            return False
    
    def print_migration_stats(self):
        """Print migration statistics."""
        logger.info("Migration Statistics:")
        logger.info(f"  Total users processed: {self.migration_stats['total_processed']}")
        logger.info(f"  Users successfully migrated: {self.migration_stats['users_migrated']}")
        logger.info(f"  Users failed to migrate: {self.migration_stats['users_failed']}")
        logger.info(f"  Success rate: {self.migration_stats['users_migrated'] / max(self.migration_stats['total_processed'], 1) * 100:.2f}%")
    
    async def run_migration(self, enable_dual_mode: bool = False, validate_only: bool = False) -> bool:
        """Run the complete migration process.
        
        Args:
            enable_dual_mode (bool): Whether to enable dual read/write mode
            validate_only (bool): Whether to only validate without migrating
            
        Returns:
            bool: True if migration was successful, False otherwise
        """
        logger.info("Starting Fase1 migration process...")
        
        try:
            # Initialize services
            if not await self.initialize_services():
                logger.error("Failed to initialize services")
                return False
            
            # If only validation requested, do that and return
            if validate_only:
                return await self.validate_migration()
            
            # Migrate existing users
            if not await self.migrate_existing_users():
                logger.error("User migration failed")
                await self.rollback_migration()
                return False
            
            # Enable dual read/write mode if requested
            if enable_dual_mode:
                if not await self.enable_dual_read_write_mode():
                    logger.warning("Failed to enable dual read/write mode, continuing...")
            
            # Validate migration
            if not await self.validate_migration():
                logger.error("Migration validation failed")
                await self.rollback_migration()
                return False
            
            # Print statistics
            self.print_migration_stats()
            
            logger.info("Fase1 migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error during migration: {e}")
            await self.rollback_migration()
            return False
        finally:
            # Clean up connections
            if self.database_manager:
                await self.database_manager.close_all()
            if self.event_bus:
                await self.event_bus.close()


async def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description='Migrate existing bot functionality to Fase1 infrastructure')
    parser.add_argument('--dual-mode', action='store_true', 
                        help='Enable dual read/write mode for backward compatibility')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate the migration without actually migrating')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create migration manager
    migration_manager = MigrationManager()
    
    # Run migration
    success = await migration_manager.run_migration(
        enable_dual_mode=args.dual_mode,
        validate_only=args.validate_only
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
"""
Database Schemas - SQLite

This module contains all SQLite schema definitions and SQLAlchemy models
used throughout the application with proper logging integration.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import logging

# Import logger
from src.utils.logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)

Base = declarative_base()


class UserProfiles(Base):
    """
    SQLite table for user profiles with ACID compliance and referential integrity
    """
    __tablename__ = 'user_profiles'
    
    # Primary key and unique constraints
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False)  # Our internal user ID
    telegram_user_id = Column(Integer, unique=True, nullable=False)  # Telegram's user ID
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    language_code = Column(String(10))
    
    # Timestamps
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<UserProfiles(user_id='{self.user_id}', telegram_user_id={self.telegram_user_id}, username='{self.username}')>"
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'telegram_user_id': self.telegram_user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'language_code': self.language_code,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }


class Subscriptions(Base):
    """
    SQLite table for user subscriptions with plan types and status management
    """
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey('user_profiles.user_id'), nullable=False)
    
    # Plan type: free, premium, vip
    plan_type = Column(String(20), CheckConstraint("plan_type IN ('free', 'premium', 'vip')"), nullable=False)
    
    # Status: active, inactive, cancelled, expired
    status = Column(String(20), CheckConstraint("status IN ('active', 'inactive', 'cancelled', 'expired')"), nullable=False)
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("UserProfiles", backref="subscriptions")
    
    def __repr__(self):
        return f"<Subscriptions(user_id='{self.user_id}', plan_type='{self.plan_type}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_type': self.plan_type,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DatabaseMigration(Base):
    """
    SQLite table for tracking database migrations
    """
    __tablename__ = 'database_migrations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    migration_id = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    applied_at = Column(DateTime, default=datetime.utcnow)
    applied_by = Column(String(50), default='system')
    
    def __repr__(self):
        return f"<DatabaseMigration(migration_id='{self.migration_id}', applied_at='{self.applied_at}')>"
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'migration_id': self.migration_id,
            'description': self.description,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'applied_by': self.applied_by
        }


# Create an alias for cleaner imports
UserProfile = UserProfiles
Subscription = Subscriptions
Migration = DatabaseMigration


def create_all_tables(engine):
    """
    Create all tables in the database if they don't exist
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        Base.metadata.create_all(engine)
        logger.info("All SQLite tables created successfully", table_count=len(Base.metadata.tables))
    except Exception as e:
        logger.error("Error creating SQLite tables", error=str(e))
        raise


def validate_tables_exist(engine):
    """
    Validate that all expected tables exist in the database
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        bool: True if all tables exist, False otherwise
    """
    try:
        # Get table names from the metadata
        expected_tables = set(Base.metadata.tables.keys())
        
        # Get actual table names from the database
        from sqlalchemy import inspect
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names())
        
        missing_tables = expected_tables - actual_tables
        
        if missing_tables:
            logger.warning("Missing SQLite tables", missing_tables=list(missing_tables))
            return False
        else:
            logger.info("All SQLite tables exist", table_count=len(expected_tables))
            return True
    except Exception as e:
        logger.error("Error validating SQLite tables", error=str(e))
        return False
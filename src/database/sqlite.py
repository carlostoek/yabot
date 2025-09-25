"""
SQLite Handler for YABOT

This module provides SQLite table operations with proper error handling,
logging, and follows the requirements for database operations.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text, select, insert, update, delete
from sqlalchemy.exc import SQLAlchemyError

from src.utils.logger import get_logger


class SQLiteHandler:
    """
    SQLite handler providing table operations with proper error handling.
    
    Implements requirement 1.2: Database Collections and Tables
    2. WHEN the system starts THEN it SHALL create/verify the following SQLite tables:
       - Subscriptions (user_id, plan, status, dates)
       - UserProfiles (user_id, telegram_data, registration_info)
    """
    
    def __init__(self, engine: AsyncEngine):
        self.logger = get_logger(self.__class__.__name__)
        self.engine = engine
    
    async def get_user_profile(self, user_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get user profile by user ID.
        
        Args:
            user_id: The user ID to search for
            
        Returns:
            User profile dictionary if found, None otherwise
        """
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT * FROM user_profiles WHERE user_id = :user_id"),
                    {"user_id": str(user_id)}
                )
                row = result.fetchone()
                
                if row:
                    # Convert row to dictionary
                    user_profile = {column.name: getattr(row, column.name) for column in result.keys()}
                    self.logger.debug("User profile found", user_id=user_id)
                    return user_profile
                else:
                    self.logger.debug("User profile not found", user_id=user_id)
                    return None
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error retrieving user profile from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
        except Exception as e:
            self.logger.error(
                "Error retrieving user profile from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def create_user_profile(self, profile_data: Dict[str, Any]) -> bool:
        """
        Create a new user profile in SQLite.
        
        Args:
            profile_data: Dictionary containing profile information
            
        Returns:
            True if creation successful, False otherwise
        """
        try:
            # Prepare the insert query
            columns = list(profile_data.keys())
            placeholders = [f":{col}" for col in columns]
            
            query = text(f"""
                INSERT INTO user_profiles ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """)
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    await conn.execute(query, profile_data)
            
            self.logger.info("User profile created successfully", user_id=profile_data.get("user_id"))
            return True
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error creating user profile in SQLite",
                user_id=profile_data.get("user_id"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error creating user profile in SQLite",
                user_id=profile_data.get("user_id"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def update_user_profile(self, user_id: Union[str, int], update_data: Dict[str, Any]) -> bool:
        """
        Update user profile in SQLite.
        
        Args:
            user_id: The user ID to update
            update_data: Dictionary containing updated fields
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Prepare the update query
            set_clauses = [f"{key} = :{key}" for key in update_data.keys()]
            set_clause = ", ".join(set_clauses)
            
            # Add updated timestamp if not provided
            if "last_login" not in update_data:
                update_data["last_login"] = datetime.utcnow()
            
            query = text(f"""
                UPDATE user_profiles 
                SET {set_clause}
                WHERE user_id = :user_id
            """)
            
            # Add user_id to the data for the WHERE clause
            params = {**update_data, "user_id": str(user_id)}
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    result = await conn.execute(query, params)
                
                if result.rowcount > 0:
                    self.logger.debug("User profile updated successfully", user_id=user_id)
                    return True
                else:
                    self.logger.warning("No user profile found to update", user_id=user_id)
                    return False
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error updating user profile in SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error updating user profile in SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def delete_user_profile(self, user_id: Union[str, int]) -> bool:
        """
        Delete a user profile from SQLite.
        
        Args:
            user_id: The user ID to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            query = text("DELETE FROM user_profiles WHERE user_id = :user_id")
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    result = await conn.execute(query, {"user_id": str(user_id)})
                
                if result.rowcount > 0:
                    self.logger.info("User profile deleted successfully", user_id=user_id)
                    return True
                else:
                    self.logger.warning("No user profile found to delete", user_id=user_id)
                    return False
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error deleting user profile from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error deleting user profile from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def get_subscription(self, user_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get subscription by user ID.
        
        Args:
            user_id: The user ID to search for
            
        Returns:
            Subscription dictionary if found, None otherwise
        """
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT * FROM subscriptions WHERE user_id = :user_id"),
                    {"user_id": str(user_id)}
                )
                row = result.fetchone()
                
                if row:
                    # Convert row to dictionary
                    subscription = {column.name: getattr(row, column.name) for column in result.keys()}
                    self.logger.debug("Subscription found", user_id=user_id)
                    return subscription
                else:
                    self.logger.debug("Subscription not found", user_id=user_id)
                    return None
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error retrieving subscription from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
        except Exception as e:
            self.logger.error(
                "Error retrieving subscription from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def create_subscription(self, subscription_data: Dict[str, Any]) -> bool:
        """
        Create a new subscription in SQLite.
        
        Args:
            subscription_data: Dictionary containing subscription information
            
        Returns:
            True if creation successful, False otherwise
        """
        try:
            # Prepare the insert query
            columns = list(subscription_data.keys())
            placeholders = [f":{col}" for col in columns]
            
            query = text(f"""
                INSERT INTO subscriptions ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """)
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    await conn.execute(query, subscription_data)
            
            self.logger.info("Subscription created successfully", user_id=subscription_data.get("user_id"))
            return True
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error creating subscription in SQLite",
                user_id=subscription_data.get("user_id"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error creating subscription in SQLite",
                user_id=subscription_data.get("user_id"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def update_subscription(self, user_id: Union[str, int], update_data: Dict[str, Any]) -> bool:
        """
        Update a subscription in SQLite.
        
        Args:
            user_id: The user ID whose subscription to update
            update_data: Dictionary containing updated fields
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Prepare the update query
            set_clauses = [f"{key} = :{key}" for key in update_data.keys()]
            set_clause = ", ".join(set_clauses)
            
            # Add updated timestamp if not provided
            if "updated_at" not in update_data:
                update_data["updated_at"] = datetime.utcnow()
            
            query = text(f"""
                UPDATE subscriptions 
                SET {set_clause}
                WHERE user_id = :user_id
            """)
            
            # Add user_id to the data for the WHERE clause
            params = {**update_data, "user_id": str(user_id)}
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    result = await conn.execute(query, params)
                
                if result.rowcount > 0:
                    self.logger.debug("Subscription updated successfully", user_id=user_id)
                    return True
                else:
                    self.logger.warning("No subscription found to update", user_id=user_id)
                    return False
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error updating subscription in SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error updating subscription in SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def delete_subscription(self, user_id: Union[str, int]) -> bool:
        """
        Delete a subscription from SQLite.
        
        Args:
            user_id: The user ID whose subscription to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            query = text("DELETE FROM subscriptions WHERE user_id = :user_id")
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    result = await conn.execute(query, {"user_id": str(user_id)})
                
                if result.rowcount > 0:
                    self.logger.info("Subscription deleted successfully", user_id=user_id)
                    return True
                else:
                    self.logger.warning("No subscription found to delete", user_id=user_id)
                    return False
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error deleting subscription from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error deleting subscription from SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def get_user_profile_by_telegram_id(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user profile by Telegram user ID.
        
        Args:
            telegram_user_id: The Telegram user ID to search for
            
        Returns:
            User profile dictionary if found, None otherwise
        """
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT * FROM user_profiles WHERE telegram_user_id = :telegram_user_id"),
                    {"telegram_user_id": telegram_user_id}
                )
                row = result.fetchone()
                
                if row:
                    # Convert row to dictionary
                    user_profile = {column.name: getattr(row, column.name) for column in result.keys()}
                    self.logger.debug("User profile found by telegram ID", telegram_user_id=telegram_user_id)
                    return user_profile
                else:
                    self.logger.debug("User profile not found by telegram ID", telegram_user_id=telegram_user_id)
                    return None
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error retrieving user profile by Telegram ID from SQLite",
                telegram_user_id=telegram_user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
        except Exception as e:
            self.logger.error(
                "Error retrieving user profile by Telegram ID from SQLite",
                telegram_user_id=telegram_user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def find_user_profiles_by_criteria(self, criteria: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find user profiles based on criteria.
        
        Args:
            criteria: Dictionary of search criteria
            limit: Maximum number of results to return
            
        Returns:
            List of user profile dictionaries matching criteria
        """
        try:
            # Build the WHERE clause dynamically
            where_clauses = [f"{key} = :{key}" for key in criteria.keys()]
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = text(f"""
                SELECT * FROM user_profiles 
                WHERE {where_clause}
                LIMIT :limit
            """)
            
            # Add limit to the parameters
            params = {**criteria, "limit": limit}
            
            async with self.engine.connect() as conn:
                result = await conn.execute(query, params)
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                profiles = []
                for row in rows:
                    profile = {column.name: getattr(row, column.name) for column in result.keys()}
                    profiles.append(profile)
                
            self.logger.debug("User profiles found by criteria", count=len(profiles), criteria=criteria)
            return profiles
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error finding user profiles by criteria in SQLite",
                criteria=criteria,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
        except Exception as e:
            self.logger.error(
                "Error finding user profiles by criteria in SQLite",
                criteria=criteria,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def find_subscriptions_by_criteria(self, criteria: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find subscriptions based on criteria.
        
        Args:
            criteria: Dictionary of search criteria
            limit: Maximum number of results to return
            
        Returns:
            List of subscription dictionaries matching criteria
        """
        try:
            # Build the WHERE clause dynamically
            where_clauses = [f"{key} = :{key}" for key in criteria.keys()]
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = text(f"""
                SELECT * FROM subscriptions 
                WHERE {where_clause}
                LIMIT :limit
            """)
            
            # Add limit to the parameters
            params = {**criteria, "limit": limit}
            
            async with self.engine.connect() as conn:
                result = await conn.execute(query, params)
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                subscriptions = []
                for row in rows:
                    subscription = {column.name: getattr(row, column.name) for column in result.keys()}
                    subscriptions.append(subscription)
                
            self.logger.debug("Subscriptions found by criteria", count=len(subscriptions), criteria=criteria)
            return subscriptions
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error finding subscriptions by criteria in SQLite",
                criteria=criteria,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
        except Exception as e:
            self.logger.error(
                "Error finding subscriptions by criteria in SQLite",
                criteria=criteria,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def update_user_activation_status(self, user_id: Union[str, int], is_active: bool) -> bool:
        """
        Update user activation status.
        
        Args:
            user_id: The user ID
            is_active: Whether the user is active or not
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            query = text("""
                UPDATE user_profiles 
                SET is_active = :is_active, last_login = :last_login
                WHERE user_id = :user_id
            """)
            
            params = {
                "user_id": str(user_id),
                "is_active": 1 if is_active else 0,
                "last_login": datetime.utcnow()
            }
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    result = await conn.execute(query, params)
                
                if result.rowcount > 0:
                    self.logger.debug(
                        "User activation status updated", 
                        user_id=user_id, 
                        is_active=is_active
                    )
                    return True
                else:
                    self.logger.warning("No user profile found to update activation status", user_id=user_id)
                    return False
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error updating user activation status in SQLite",
                user_id=user_id,
                is_active=is_active,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error updating user activation status in SQLite",
                user_id=user_id,
                is_active=is_active,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def update_subscription_status(self, user_id: Union[str, int], status: str) -> bool:
        """
        Update subscription status.
        
        Args:
            user_id: The user ID
            status: New status (active, inactive, cancelled, expired)
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            if status not in ['active', 'inactive', 'cancelled', 'expired']:
                self.logger.error("Invalid subscription status", status=status)
                return False
            
            query = text("""
                UPDATE subscriptions 
                SET status = :status, updated_at = :updated_at
                WHERE user_id = :user_id
            """)
            
            params = {
                "user_id": str(user_id),
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    result = await conn.execute(query, params)
                
                if result.rowcount > 0:
                    self.logger.debug(
                        "Subscription status updated", 
                        user_id=user_id, 
                        status=status
                    )
                    return True
                else:
                    self.logger.warning("No subscription found to update status", user_id=user_id)
                    return False
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error updating subscription status in SQLite",
                user_id=user_id,
                status=status,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error updating subscription status in SQLite",
                user_id=user_id,
                status=status,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def get_active_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Get all active subscriptions.
        
        Returns:
            List of active subscription dictionaries
        """
        try:
            query = text("""
                SELECT * FROM subscriptions 
                WHERE status = 'active'
            """)
            
            async with self.engine.connect() as conn:
                result = await conn.execute(query)
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                subscriptions = []
                for row in rows:
                    subscription = {column.name: getattr(row, column.name) for column in result.keys()}
                    subscriptions.append(subscription)
                
            self.logger.debug("Active subscriptions retrieved", count=len(subscriptions))
            return subscriptions
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error retrieving active subscriptions from SQLite",
                error=str(e),
                error_type=type(e).__name__
            )
            return []
        except Exception as e:
            self.logger.error(
                "Error retrieving active subscriptions from SQLite",
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Get all expired subscriptions (where end_date is in the past).
        
        Returns:
            List of expired subscription dictionaries
        """
        try:
            query = text("""
                SELECT * FROM subscriptions 
                WHERE status = 'active' AND end_date < :current_time
            """)
            
            async with self.engine.connect() as conn:
                result = await conn.execute(query, {"current_time": datetime.utcnow()})
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                subscriptions = []
                for row in rows:
                    subscription = {column.name: getattr(row, column.name) for column in result.keys()}
                    subscriptions.append(subscription)
                
            self.logger.debug("Expired subscriptions retrieved", count=len(subscriptions))
            return subscriptions
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error retrieving expired subscriptions from SQLite",
                error=str(e),
                error_type=type(e).__name__
            )
            return []
        except Exception as e:
            self.logger.error(
                "Error retrieving expired subscriptions from SQLite",
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def set_user_last_login(self, user_id: Union[str, int]) -> bool:
        """
        Update the last login timestamp for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            query = text("""
                UPDATE user_profiles 
                SET last_login = :last_login
                WHERE user_id = :user_id
            """)
            
            params = {
                "user_id": str(user_id),
                "last_login": datetime.utcnow()
            }
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    result = await conn.execute(query, params)
                
                if result.rowcount > 0:
                    self.logger.debug("User last login updated", user_id=user_id)
                    return True
                else:
                    self.logger.warning("No user profile found to update last login", user_id=user_id)
                    return False
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error updating user last login in SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        except Exception as e:
            self.logger.error(
                "Error updating user last login in SQLite",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def batch_create_user_profiles(self, profiles_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple user profiles in a batch operation.
        
        Args:
            profiles_data: List of profile data dictionaries
            
        Returns:
            Dictionary with results of the batch operation
        """
        if not profiles_data:
            return {"inserted_count": 0, "errors": []}
        
        try:
            # Add timestamp fields to all profiles if not already present
            for profile_data in profiles_data:
                if "registration_date" not in profile_data:
                    profile_data["registration_date"] = datetime.utcnow()
                if "created_at" not in profile_data:
                    profile_data["created_at"] = datetime.utcnow()
            
            # Get all column names from the first profile (assuming all have same structure)
            if profiles_data:
                columns = list(profiles_data[0].keys())
                placeholders = [f":{col}" for col in columns]
                
                query = text(f"""
                    INSERT INTO user_profiles ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """)
            
            async with self.engine.connect() as conn:
                async with conn.begin():  # Use transaction
                    # Execute each insert individually in the same transaction
                    for profile_data in profiles_data:
                        await conn.execute(query, profile_data)
            
            self.logger.info("Batch user profile creation completed", inserted_count=len(profiles_data))
            return {"inserted_count": len(profiles_data), "errors": []}
        except SQLAlchemyError as e:
            self.logger.error(
                "SQLAlchemy error in batch user profile creation in SQLite",
                error=str(e),
                error_type=type(e).__name__
            )
            return {"inserted_count": 0, "errors": [str(e)]}
        except Exception as e:
            self.logger.error(
                "Error in batch user profile creation in SQLite",
                error=str(e),
                error_type=type(e).__name__
            )
            return {"inserted_count": 0, "errors": [str(e)]}
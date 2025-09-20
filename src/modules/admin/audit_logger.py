"""
Audit logger module for the YABOT administrative system.

This module provides audit logging functionality for administrative actions,
implementing requirement 6.4 from the conectar-todo specification.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from src.events.bus import EventBus
from src.events.models import create_event, BaseEvent
from src.utils.logger import get_logger
from src.database.mongodb import MongoDBHandler

logger = get_logger(__name__)


class AuditLogEntry(BaseModel):
    """Represents an audit log entry."""
    
    log_id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool
    error_message: Optional[str] = None


class AuditLoggerError(Exception):
    """Base exception for audit logger operations."""
    pass


class AuditLogger:
    """Audit logger for administrative actions.
    
    This class provides audit logging functionality for tracking administrative
    actions and publishing audit events as required by requirement 6.4.
    """
    
    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus):
        """Initialize the audit logger.
        
        Args:
            mongodb_handler: MongoDB handler for storing audit logs
            event_bus: Event bus for publishing audit events
        """
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.audit_logs_collection = mongodb_handler.get_audit_logs_collection()
        
        logger.info("AuditLogger initialized")
    
    async def log_admin_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLogEntry:
        """Log an administrative action and publish audit event.
        
        Args:
            user_id: User ID performing the action
            action: Action being performed
            resource_type: Type of resource being acted upon
            resource_id: ID of the specific resource
            details: Additional details about the action
            ip_address: IP address of the user
            user_agent: User agent string
            success: Whether the action was successful
            error_message: Error message if action failed
            
        Returns:
            AuditLogEntry: Created audit log entry
            
        Raises:
            AuditLoggerError: If logging fails
        """
        try:
            log_entry = AuditLogEntry(
                log_id=str(datetime.utcnow().timestamp()),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message
            )
            
            # Store in MongoDB
            await self._store_audit_log(log_entry)
            
            # Publish audit event
            await self._publish_audit_event(log_entry)
            
            logger.info("Audit log entry created for user %s, action %s", user_id, action)
            return log_entry
            
        except Exception as e:
            logger.error("Failed to log admin action: %s", str(e))
            raise AuditLoggerError(f"Audit logging failed: {str(e)}")
    
    async def _store_audit_log(self, log_entry: AuditLogEntry) -> None:
        """Store audit log entry in MongoDB.
        
        Args:
            log_entry: Audit log entry to store
        """
        try:
            log_data = log_entry.dict()
            await self.audit_logs_collection.insert_one(log_data)
            logger.debug("Audit log entry stored in MongoDB")
            
        except Exception as e:
            logger.error("Failed to store audit log entry: %s", str(e))
            raise AuditLoggerError(f"Failed to store audit log: {str(e)}")
    
    async def _publish_audit_event(self, log_entry: AuditLogEntry) -> None:
        """Publish audit event to event bus.
        
        Args:
            log_entry: Audit log entry to publish
        """
        try:
            event = create_event(
                "admin_action_logged",
                log_id=log_entry.log_id,
                user_id=log_entry.user_id,
                action=log_entry.action,
                resource_type=log_entry.resource_type,
                resource_id=log_entry.resource_id,
                details=log_entry.details,
                success=log_entry.success,
                error_message=log_entry.error_message,
                timestamp=log_entry.timestamp
            )
            
            await self.event_bus.publish("admin_action_logged", event.dict())
            logger.debug("Published admin_action_logged event")
            
        except Exception as e:
            # Don't fail the audit logging for event publishing errors
            logger.warning("Failed to publish audit event: %s", str(e))
    
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Retrieve audit logs based on filters.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action
            resource_type: Filter by resource type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of logs to return
            
        Returns:
            List[AuditLogEntry]: List of audit log entries
        """
        try:
            query = {}
            
            if user_id:
                query["user_id"] = user_id
                
            if action:
                query["action"] = action
                
            if resource_type:
                query["resource_type"] = resource_type
                
            if start_time or end_time:
                query["timestamp"] = {}
                if start_time:
                    query["timestamp"]["$gte"] = start_time
                if end_time:
                    query["timestamp"]["$lte"] = end_time
            
            cursor = self.audit_logs_collection.find(
                query,
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            
            logs = []
            async for log_data in cursor:
                log_entry = AuditLogEntry(**log_data)
                logs.append(log_entry)
            
            logger.debug("Retrieved %d audit log entries", len(logs))
            return logs
            
        except Exception as e:
            logger.error("Failed to retrieve audit logs: %s", str(e))
            raise AuditLoggerError(f"Failed to retrieve audit logs: {str(e)}")
    
    async def get_user_audit_summary(self, user_id: str) -> Dict[str, Any]:
        """Get audit summary for a specific user.
        
        Args:
            user_id: User ID to get summary for
            
        Returns:
            Dict[str, Any]: Summary of user's audit logs
        """
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {
                    "$group": {
                        "_id": "$user_id",
                        "total_actions": {"$sum": 1},
                        "successful_actions": {"$sum": {"$cond": ["$success", 1, 0]}},
                        "failed_actions": {"$sum": {"$cond": [{"$not": "$success"}, 1, 0]}},
                        "actions_by_type": {
                            "$push": {
                                "action": "$action",
                                "resource_type": "$resource_type",
                                "timestamp": "$timestamp"
                            }
                        },
                        "first_action": {"$min": "$timestamp"},
                        "last_action": {"$max": "$timestamp"}
                    }
                }
            ]
            
            cursor = self.audit_logs_collection.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            if result:
                summary = result[0]
                # Sort actions by timestamp for easier viewing
                summary["actions_by_type"].sort(key=lambda x: x["timestamp"], reverse=True)
                return summary
            else:
                return {
                    "total_actions": 0,
                    "successful_actions": 0,
                    "failed_actions": 0,
                    "actions_by_type": [],
                    "first_action": None,
                    "last_action": None
                }
                
        except Exception as e:
            logger.error("Failed to get user audit summary: %s", str(e))
            raise AuditLoggerError(f"Failed to get user audit summary: {str(e)}")
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old audit logs.
        
        Args:
            days_to_keep: Number of days to keep logs
            
        Returns:
            int: Number of logs deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            result = await self.audit_logs_collection.delete_many({
                "timestamp": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            logger.info("Cleaned up %d old audit log entries", deleted_count)
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to cleanup old audit logs: %s", str(e))
            raise AuditLoggerError(f"Failed to cleanup old audit logs: {str(e)}")


# Factory function for dependency injection consistency
async def create_audit_logger(
    mongodb_handler: MongoDBHandler,
    event_bus: EventBus
) -> AuditLogger:
    """Factory function to create an audit logger instance.
    
    Args:
        mongodb_handler: MongoDB handler instance
        event_bus: Event bus instance
        
    Returns:
        AuditLogger: Initialized audit logger instance
    """
    return AuditLogger(mongodb_handler, event_bus)
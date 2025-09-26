"""
Admin Module - Channel Administration

This module provides comprehensive channel administration functionality including:
- Access control and user permissions
- VIP subscription management
- Post scheduling and automation
- Notification system with Diana's intimate tone
- Message protection for VIP content
- Admin command interface

All components follow Aiogram 3.x patterns and integrate seamlessly with the EventBus.
"""

__version__ = "1.0.0"
__author__ = "YABOT Team"

# Import main components
from .access_control import AccessControl, AccessResult, AccessLevel
from .subscription_manager import SubscriptionManager, VipStatus, ExpiredSubscription
from .post_scheduler import PostScheduler, ScheduledPost, PostResult, PostStatus, PostType
from .notification_system import NotificationSystem, NotificationResult, NotificationType, NotificationPriority
from .message_protection import MessageProtectionSystem, MessageProtection, ProtectionLevel
from .admin_commands import AdminCommandInterface, AdminStates, AdminAction

__all__ = [
    # Access Control
    "AccessControl",
    "AccessResult",
    "AccessLevel",

    # Subscription Management
    "SubscriptionManager",
    "VipStatus",
    "ExpiredSubscription",

    # Post Scheduling
    "PostScheduler",
    "ScheduledPost",
    "PostResult",
    "PostStatus",
    "PostType",

    # Notifications
    "NotificationSystem",
    "NotificationResult",
    "NotificationType",
    "NotificationPriority",

    # Message Protection
    "MessageProtectionSystem",
    "MessageProtection",
    "ProtectionLevel",

    # Admin Commands
    "AdminCommandInterface",
    "AdminStates",
    "AdminAction",
]
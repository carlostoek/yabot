"""
Notification System - Channel Administration Module

This module implements notification system functionality leveraging Telegram messaging patterns
as specified in Requirement 3.6.

The system handles:
- Push message delivery to users
- Notification templates and personalization
- Subscription renewal reminders (3 days before expiry)
- Admin alerts and system notifications
- Event publishing for notification operations
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from pydantic import BaseModel, Field
import uuid
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Optional jinja2 import
try:
    import jinja2
    HAS_JINJA2 = True
except ImportError:
    jinja2 = None
    HAS_JINJA2 = False

from src.events.models import BaseEvent, SystemNotificationEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient
    from aiogram import Bot


class NotificationType(str, Enum):
    """
    Type enumeration for notifications
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    REMINDER = "reminder"
    WELCOME = "welcome"
    FAREWELL = "farewell"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    ADMIN_ALERT = "admin_alert"
    SYSTEM_MAINTENANCE = "system_maintenance"


class NotificationPriority(str, Enum):
    """
    Priority enumeration for notifications
    """
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DeliveryChannel(str, Enum):
    """
    Delivery channel enumeration
    """
    TELEGRAM_PRIVATE = "telegram_private"
    TELEGRAM_CHANNEL = "telegram_channel"
    SYSTEM_BROADCAST = "system_broadcast"


class NotificationStatus(str, Enum):
    """
    Status enumeration for notifications
    """
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationTemplate(BaseModel):
    """
    Template for notifications with Diana's emotional tone
    """
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: NotificationType
    subject: Optional[str] = None
    body: str
    variables: List[str] = Field(default_factory=list)
    tone: str = "intimate"  # "intimate", "professional", "playful", "melancholic"
    supports_buttons: bool = False
    button_template: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(BaseModel):
    """
    Individual notification instance
    """
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: DeliveryChannel = DeliveryChannel.TELEGRAM_PRIVATE
    subject: Optional[str] = None
    message: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    template_id: Optional[str] = None
    buttons: Optional[InlineKeyboardMarkup] = None
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str,
            InlineKeyboardMarkup: lambda kb: "inline_keyboard_markup"
        }


class NotificationResult(BaseModel):
    """
    Result of a notification delivery
    """
    notification_id: str
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    delivered_at: Optional[datetime] = None
    user_id: str


class NotificationSentEvent(BaseEvent):
    """
    Event for sent notifications
    """
    event_type: str = "notification_sent"
    notification_id: str
    user_id: str
    notification_type: str
    delivery_channel: str
    success: bool


class NotificationSystem:
    """
    Notification system for push messages and alerts

    Implements requirement 3.6:
    - Push message delivery with Telegram messaging patterns
    - Template-based notifications with Diana's emotional tone
    - Subscription renewal reminders
    - Admin alerts and system notifications

    Follows the emotional and erotic tone of DianaBot ecosystem
    """

    def __init__(self, db_client: 'AsyncIOMotorClient', event_bus: EventBus, telegram_bot: 'Bot'):
        """
        Initialize the notification system

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing notification events
            telegram_bot: Telegram bot instance for message delivery
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.telegram_bot = telegram_bot
        self.logger = get_logger(self.__class__.__name__)

        # Collection references
        self.notifications_collection = self.db.notifications
        self.notification_templates_collection = self.db.notification_templates
        self.notification_history_collection = self.db.notification_history

        # Initialize Jinja2 template engine
        if HAS_JINJA2:
            self.template_env = jinja2.Environment(
                loader=jinja2.DictLoader({}),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
        else:
            self.template_env = None
            self.logger.warning("Jinja2 not available - template rendering disabled")

        # Initialize with Diana's signature templates
        # Note: This should be called asynchronously after initialization

    async def _initialize_default_templates(self) -> None:
        """
        Initialize default notification templates with Diana's emotional tone
        """
        try:
            default_templates = [
                NotificationTemplate(
                    name="vip_welcome",
                    type=NotificationType.WELCOME,
                    subject="✨ Bienvenido al santuario íntimo",
                    body="✨ Bienvenido al santuario íntimo de Diana, {{user_name}}...\n\nLucien te ha preparado experiencias que solo los más devotos pueden vivir. Los secretos más profundos y los placeres más exquisitos te esperan.\n\n🌹 Tu acceso VIP incluye:\n• Fragmentos narrativos exclusivos\n• Contenido protegido de nivel 4-6\n• Interacciones íntimas con Diana\n• Misiones especiales con recompensas únicas\n\n¿Estás listo para sumergirte en lo desconocido?",
                    variables=["user_name"],
                    tone="intimate",
                    supports_buttons=True,
                    button_template={
                        "text": "🔥 Comenzar mi aventura VIP",
                        "callback_data": "start_vip_journey"
                    }
                ),
                NotificationTemplate(
                    name="renewal_reminder_3_days",
                    type=NotificationType.REMINDER,
                    subject="💔 Mi querido, tu acceso expira pronto...",
                    body="💔 Mi querido {{user_name}}, tu acceso al mundo secreto de Diana expira en {{days_remaining}} días.\n\nNo permitas que el velo se cierre entre nosotros... Los niveles más profundos de pasión y misterio quedarán fuera de tu alcance.\n\n🌙 Sin tu suscripción VIP perderás:\n• Los fragmentos más íntimos de la historia\n• Las confesiones secretas de Diana\n• Las recompensas exclusivas de Lucien\n• El acceso a los placeres prohibidos\n\n¿Renovarás tu devoción?",
                    variables=["user_name", "days_remaining"],
                    tone="melancholic",
                    supports_buttons=True,
                    button_template={
                        "text": "💖 Renovar mi devoción",
                        "callback_data": "renew_subscription"
                    }
                ),
                NotificationTemplate(
                    name="subscription_expired",
                    type=NotificationType.FAREWELL,
                    subject="🌙 El velo se cierra...",
                    body="🌙 El velo se cierra, {{user_name}}...\n\nHas perdido el acceso a los niveles más profundos de mi mundo. Los secretos que Diana guarda celosamente, las caricias prohibidas, los susurros en la penumbra... todo queda ahora fuera de tu alcance.\n\nPero no todo está perdido. La puerta sigue ahí, esperando tu regreso.\n\n💔 Diana te espera para tu regreso al santuario...",
                    variables=["user_name"],
                    tone="melancholic",
                    supports_buttons=True,
                    button_template={
                        "text": "🔥 Regresar al santuario",
                        "callback_data": "resubscribe_vip"
                    }
                ),
                NotificationTemplate(
                    name="payment_confirmed",
                    type=NotificationType.PAYMENT_CONFIRMATION,
                    subject="✨ Tu devoción ha sido reconocida",
                    body="✨ Tu devoción ha sido reconocida, {{user_name}}...\n\nEl pago de {{amount}} por tu suscripción {{plan_type}} ha sido procesado exitosamente. Las puertas del santuario se abren una vez más para ti.\n\n🌹 Tu acceso VIP está activo hasta el {{end_date}}\n\nDiana sonríe complacida por tu lealtad. Lucien ha preparado nuevas experiencias que harán que cada momento valga la pena.\n\n¿Comenzamos donde lo dejamos?",
                    variables=["user_name", "amount", "plan_type", "end_date"],
                    tone="intimate",
                    supports_buttons=True,
                    button_template={
                        "text": "🔥 Continuar mi historia",
                        "callback_data": "continue_narrative"
                    }
                ),
                NotificationTemplate(
                    name="admin_alert",
                    type=NotificationType.ADMIN_ALERT,
                    subject="🚨 Alerta del Sistema - {{alert_type}}",
                    body="🚨 **Alerta del Sistema**\n\n**Tipo:** {{alert_type}}\n**Severidad:** {{severity}}\n**Componente:** {{component}}\n**Timestamp:** {{timestamp}}\n\n**Detalles:**\n{{details}}\n\n**Acción requerida:** {{action_required}}",
                    variables=["alert_type", "severity", "component", "timestamp", "details", "action_required"],
                    tone="professional",
                    supports_buttons=False
                ),
                NotificationTemplate(
                    name="system_maintenance",
                    type=NotificationType.SYSTEM_MAINTENANCE,
                    subject="🔧 Mantenimiento del Santuario",
                    body="🔧 **Mantenimiento del Santuario**\n\nQueridos devotos, el santuario de Diana necesita un momento de descanso para renovar sus energías.\n\n⏰ **Programado para:** {{maintenance_start}}\n⏱️ **Duración estimada:** {{duration}}\n\n💫 Durante este tiempo, Diana perfeccionará cada detalle para ofrecerte una experiencia aún más intensa. Tu progreso y recompensas están completamente seguros.\n\n¡Te esperamos del otro lado!",
                    variables=["maintenance_start", "duration"],
                    tone="professional",
                    supports_buttons=False
                )
            ]

            # Store templates in database
            for template in default_templates:
                await self.notification_templates_collection.replace_one(
                    {"name": template.name},
                    template.dict(),
                    upsert=True
                )

            self.logger.info(f"Initialized {len(default_templates)} default notification templates")

        except Exception as e:
            self.logger.error(
                "Error initializing default templates",
                error=str(e),
                error_type=type(e).__name__
            )

    async def send_notification(self, user_id: str, template_name: str,
                              variables: Optional[Dict[str, Any]] = None,
                              priority: NotificationPriority = NotificationPriority.NORMAL,
                              channel: DeliveryChannel = DeliveryChannel.TELEGRAM_PRIVATE,
                              scheduled_for: Optional[datetime] = None) -> Optional[Notification]:
        """
        Send a notification using a template

        Args:
            user_id: Target user ID
            template_name: Name of the template to use
            variables: Variables for template rendering
            priority: Notification priority
            channel: Delivery channel
            scheduled_for: Schedule for future delivery

        Returns:
            Notification instance if successful, None otherwise
        """
        try:
            # Get template
            template_doc = await self.notification_templates_collection.find_one({"name": template_name})
            if not template_doc:
                self.logger.error(f"Template not found: {template_name}")
                return None

            template = NotificationTemplate(**template_doc)

            # Render template with variables
            rendered_message = await self._render_template(template.body, variables or {})
            rendered_subject = await self._render_template(template.subject or "", variables or {}) if template.subject else None

            # Create notification
            notification = Notification(
                user_id=user_id,
                type=template.type,
                priority=priority,
                channel=channel,
                subject=rendered_subject,
                message=rendered_message,
                variables=variables or {},
                template_id=template.template_id,
                scheduled_for=scheduled_for,
                metadata={
                    "template_name": template_name,
                    "tone": template.tone
                }
            )

            # Add buttons if template supports them
            if template.supports_buttons and template.button_template:
                notification.buttons = await self._create_notification_buttons(
                    template.button_template,
                    variables or {}
                )

            # Store notification
            await self.notifications_collection.insert_one(notification.dict())

            # Send immediately or schedule
            if scheduled_for and scheduled_for > datetime.utcnow():
                self.logger.info(
                    "Notification scheduled for future delivery",
                    notification_id=notification.notification_id,
                    user_id=user_id,
                    scheduled_for=scheduled_for
                )
            else:
                # Send immediately
                await self._deliver_notification(notification)

            return notification

        except Exception as e:
            self.logger.error(
                "Error sending notification",
                user_id=user_id,
                template_name=template_name,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def send_custom_notification(self, user_id: str, message: str,
                                     notification_type: NotificationType = NotificationType.INFO,
                                     priority: NotificationPriority = NotificationPriority.NORMAL,
                                     subject: Optional[str] = None,
                                     buttons: Optional[InlineKeyboardMarkup] = None) -> Optional[Notification]:
        """
        Send a custom notification without template

        Args:
            user_id: Target user ID
            message: Notification message
            notification_type: Type of notification
            priority: Notification priority
            subject: Optional subject
            buttons: Optional inline keyboard buttons

        Returns:
            Notification instance if successful, None otherwise
        """
        try:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                priority=priority,
                subject=subject,
                message=message,
                buttons=buttons,
                metadata={"custom": True}
            )

            # Store notification
            await self.notifications_collection.insert_one(notification.dict())

            # Send immediately
            await self._deliver_notification(notification)

            return notification

        except Exception as e:
            self.logger.error(
                "Error sending custom notification",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def send_renewal_reminders(self) -> int:
        """
        Send subscription renewal reminders (3 days before expiry)

        Returns:
            Number of reminders sent
        """
        try:
            self.logger.info("Processing subscription renewal reminders")

            # Find users whose VIP subscription expires in 3 days
            reminder_date = datetime.utcnow() + timedelta(days=3)
            start_of_day = reminder_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = reminder_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Query subscriptions
            from src.services.subscription import SubscriptionStatus
            cursor = self.db.subscriptions.find({
                "status": SubscriptionStatus.ACTIVE.value,
                "end_date": {"$gte": start_of_day, "$lte": end_of_day}
            })

            reminders_sent = 0
            async for subscription_doc in cursor:
                user_id = subscription_doc["user_id"]
                end_date = subscription_doc["end_date"]

                # Check if reminder already sent
                existing_reminder = await self.notifications_collection.find_one({
                    "user_id": user_id,
                    "type": NotificationType.REMINDER.value,
                    "metadata.subscription_expiry": end_date.isoformat()
                })

                if existing_reminder:
                    self.logger.debug("Renewal reminder already sent", user_id=user_id)
                    continue

                # Get user info
                user_doc = await self.db.users.find_one({"user_id": user_id})
                user_name = user_doc.get("username", "querido/a") if user_doc else "querido/a"

                # Calculate days remaining
                days_remaining = (end_date - datetime.utcnow()).days

                # Send renewal reminder
                notification = await self.send_notification(
                    user_id=user_id,
                    template_name="renewal_reminder_3_days",
                    variables={
                        "user_name": user_name,
                        "days_remaining": days_remaining
                    },
                    priority=NotificationPriority.HIGH
                )

                if notification:
                    # Mark with subscription expiry for deduplication
                    await self.notifications_collection.update_one(
                        {"notification_id": notification.notification_id},
                        {
                            "$set": {
                                "metadata.subscription_expiry": end_date.isoformat(),
                                "metadata.reminder_type": "3_day_renewal"
                            }
                        }
                    )
                    reminders_sent += 1

                    self.logger.info(
                        "Renewal reminder sent",
                        user_id=user_id,
                        days_remaining=days_remaining,
                        expires_at=end_date
                    )

            self.logger.info(f"Sent {reminders_sent} renewal reminders")
            return reminders_sent

        except Exception as e:
            self.logger.error(
                "Error sending renewal reminders",
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    async def send_admin_alert(self, alert_type: str, severity: str, component: str,
                             details: str, action_required: str = "Review and take action",
                             admin_users: Optional[List[str]] = None) -> int:
        """
        Send alert notifications to administrators

        Args:
            alert_type: Type of alert
            severity: Severity level
            component: Component that generated the alert
            details: Detailed information
            action_required: Required action
            admin_users: List of admin user IDs (if None, sends to all admins)

        Returns:
            Number of alerts sent
        """
        try:
            # Get admin users if not provided
            if admin_users is None:
                cursor = self.db.users.find({"role": "admin"})
                admin_users = []
                async for user_doc in cursor:
                    admin_users.append(user_doc["user_id"])

            if not admin_users:
                self.logger.warning("No admin users found for alert")
                return 0

            alerts_sent = 0
            for admin_user_id in admin_users:
                notification = await self.send_notification(
                    user_id=admin_user_id,
                    template_name="admin_alert",
                    variables={
                        "alert_type": alert_type,
                        "severity": severity,
                        "component": component,
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "details": details,
                        "action_required": action_required
                    },
                    priority=NotificationPriority.CRITICAL if severity.lower() == "critical" else NotificationPriority.HIGH
                )

                if notification:
                    alerts_sent += 1

            self.logger.info(
                "Admin alerts sent",
                alert_type=alert_type,
                severity=severity,
                alerts_sent=alerts_sent
            )

            return alerts_sent

        except Exception as e:
            self.logger.error(
                "Error sending admin alerts",
                alert_type=alert_type,
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    async def send_system_notification(self, message: str, recipients: Union[List[str], str] = "all",
                                     notification_type: NotificationType = NotificationType.INFO,
                                     priority: NotificationPriority = NotificationPriority.NORMAL) -> int:
        """
        Send system-wide notifications

        Args:
            message: Notification message
            recipients: List of user IDs or "all" for broadcast
            notification_type: Type of notification
            priority: Priority level

        Returns:
            Number of notifications sent
        """
        try:
            # Get recipients
            if recipients == "all":
                cursor = self.db.users.find({"active": {"$ne": False}})
                user_ids = []
                async for user_doc in cursor:
                    user_ids.append(user_doc["user_id"])
            else:
                user_ids = recipients if isinstance(recipients, list) else [recipients]

            notifications_sent = 0
            for user_id in user_ids:
                notification = await self.send_custom_notification(
                    user_id=user_id,
                    message=message,
                    notification_type=notification_type,
                    priority=priority
                )

                if notification:
                    notifications_sent += 1

            self.logger.info(
                "System notifications sent",
                notifications_sent=notifications_sent,
                total_recipients=len(user_ids)
            )

            return notifications_sent

        except Exception as e:
            self.logger.error(
                "Error sending system notifications",
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    async def process_scheduled_notifications(self) -> int:
        """
        Process notifications scheduled for delivery

        Returns:
            Number of notifications processed
        """
        try:
            current_time = datetime.utcnow()

            # Find notifications ready to be sent
            cursor = self.notifications_collection.find({
                "status": NotificationStatus.PENDING.value,
                "scheduled_for": {"$lte": current_time}
            })

            processed_count = 0
            async for notification_doc in cursor:
                notification = Notification(**notification_doc)
                await self._deliver_notification(notification)
                processed_count += 1

            if processed_count > 0:
                self.logger.info(f"Processed {processed_count} scheduled notifications")

            return processed_count

        except Exception as e:
            self.logger.error(
                "Error processing scheduled notifications",
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    async def _deliver_notification(self, notification: Notification) -> NotificationResult:
        """
        Deliver a single notification

        Args:
            notification: Notification to deliver

        Returns:
            NotificationResult with delivery status
        """
        try:
            self.logger.debug(
                "Delivering notification",
                notification_id=notification.notification_id,
                user_id=notification.user_id,
                type=notification.type.value
            )

            # Send via Telegram
            message = None
            if notification.channel == DeliveryChannel.TELEGRAM_PRIVATE:
                message = await self.telegram_bot.send_message(
                    chat_id=int(notification.user_id),
                    text=notification.message,
                    reply_markup=notification.buttons,
                    parse_mode="Markdown"
                )
            elif notification.channel == DeliveryChannel.TELEGRAM_CHANNEL:
                # For channel posting
                channel_id = notification.metadata.get("channel_id")
                if channel_id:
                    message = await self.telegram_bot.send_message(
                        chat_id=channel_id,
                        text=notification.message,
                        reply_markup=notification.buttons,
                        parse_mode="Markdown"
                    )

            # Update notification status
            await self.notifications_collection.update_one(
                {"notification_id": notification.notification_id},
                {
                    "$set": {
                        "status": NotificationStatus.SENT.value,
                        "sent_at": datetime.utcnow(),
                        "metadata.message_id": str(message.message_id) if message else None
                    }
                }
            )

            # Log to history
            await self._log_notification_history(
                notification_id=notification.notification_id,
                action="sent",
                success=True,
                message_id=str(message.message_id) if message else None,
                user_id=notification.user_id
            )

            # Publish event
            await self._publish_notification_event(
                notification_id=notification.notification_id,
                user_id=notification.user_id,
                notification_type=notification.type.value,
                delivery_channel=notification.channel.value,
                success=True
            )

            self.logger.info(
                "Notification delivered successfully",
                notification_id=notification.notification_id,
                user_id=notification.user_id,
                message_id=message.message_id if message else None
            )

            return NotificationResult(
                notification_id=notification.notification_id,
                success=True,
                message_id=str(message.message_id) if message else None,
                delivered_at=datetime.utcnow(),
                user_id=notification.user_id
            )

        except Exception as e:
            self.logger.error(
                "Error delivering notification",
                notification_id=notification.notification_id,
                user_id=notification.user_id,
                error=str(e),
                error_type=type(e).__name__
            )

            # Handle retry logic
            if notification.retry_count < notification.max_retries:
                # Schedule retry
                retry_delay = (notification.retry_count + 1) * 5  # 5, 10, 15 minutes
                retry_time = datetime.utcnow() + timedelta(minutes=retry_delay)

                await self.notifications_collection.update_one(
                    {"notification_id": notification.notification_id},
                    {
                        "$set": {
                            "status": NotificationStatus.PENDING.value,
                            "retry_count": notification.retry_count + 1,
                            "last_error": str(e),
                            "scheduled_for": retry_time
                        }
                    }
                )

                self.logger.info(
                    "Notification scheduled for retry",
                    notification_id=notification.notification_id,
                    retry_count=notification.retry_count + 1,
                    retry_time=retry_time
                )
            else:
                # Mark as failed
                await self.notifications_collection.update_one(
                    {"notification_id": notification.notification_id},
                    {
                        "$set": {
                            "status": NotificationStatus.FAILED.value,
                            "last_error": str(e)
                        }
                    }
                )

            # Log failure
            await self._log_notification_history(
                notification_id=notification.notification_id,
                action="failed",
                success=False,
                error=str(e),
                user_id=notification.user_id
            )

            # Publish failure event
            await self._publish_notification_event(
                notification_id=notification.notification_id,
                user_id=notification.user_id,
                notification_type=notification.type.value,
                delivery_channel=notification.channel.value,
                success=False
            )

            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                error=str(e),
                user_id=notification.user_id
            )

    async def _render_template(self, template_text: str, variables: Dict[str, Any]) -> str:
        """
        Render a template with variables using Jinja2

        Args:
            template_text: Template text
            variables: Variables for rendering

        Returns:
            Rendered text
        """
        try:
            if self.template_env:
                template = self.template_env.from_string(template_text)
                return template.render(**variables)
            else:
                # Fallback: simple string replacement
                result = template_text
                for key, value in variables.items():
                    result = result.replace(f"{{{{{key}}}}}", str(value))
                return result
        except Exception as e:
            self.logger.error(f"Error rendering template: {e}")
            return template_text  # Return original text on error

    async def _create_notification_buttons(self, button_template: Dict[str, Any],
                                         variables: Dict[str, Any]) -> InlineKeyboardMarkup:
        """
        Create inline keyboard buttons for notifications

        Args:
            button_template: Button template configuration
            variables: Variables for button text rendering

        Returns:
            InlineKeyboardMarkup with rendered buttons
        """
        try:
            builder = InlineKeyboardBuilder()

            if isinstance(button_template, dict):
                # Single button
                text = await self._render_template(button_template.get("text", ""), variables)
                callback_data = button_template.get("callback_data", "")
                builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
            elif isinstance(button_template, list):
                # Multiple buttons
                for btn in button_template:
                    text = await self._render_template(btn.get("text", ""), variables)
                    callback_data = btn.get("callback_data", "")
                    url = btn.get("url")

                    if url:
                        builder.add(InlineKeyboardButton(text=text, url=url))
                    else:
                        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))

            return builder.as_markup()

        except Exception as e:
            self.logger.error(f"Error creating notification buttons: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def _log_notification_history(self, notification_id: str, action: str, success: bool,
                                      message_id: Optional[str] = None, error: Optional[str] = None,
                                      user_id: Optional[str] = None) -> None:
        """
        Log notification delivery to history

        Args:
            notification_id: Notification ID
            action: Action performed
            success: Whether action was successful
            message_id: Telegram message ID
            error: Error message if failed
            user_id: User ID
        """
        try:
            history_doc = {
                "notification_id": notification_id,
                "action": action,
                "success": success,
                "message_id": message_id,
                "error": error,
                "user_id": user_id,
                "timestamp": datetime.utcnow()
            }

            await self.notification_history_collection.insert_one(history_doc)

        except Exception as e:
            self.logger.error(
                "Error logging notification history",
                notification_id=notification_id,
                action=action,
                error=str(e)
            )

    async def _publish_notification_event(self, notification_id: str, user_id: str,
                                        notification_type: str, delivery_channel: str,
                                        success: bool) -> None:
        """
        Publish notification events

        Args:
            notification_id: Notification ID
            user_id: User ID
            notification_type: Type of notification
            delivery_channel: Delivery channel
            success: Whether delivery was successful
        """
        try:
            event_payload = {
                "notification_id": notification_id,
                "user_id": user_id,
                "notification_type": notification_type,
                "delivery_channel": delivery_channel,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            }

            event = BaseEvent(
                event_type="notification_sent",
                user_id=user_id,
                payload=event_payload
            )

            await self.event_bus.publish("notification_sent", event)

            self.logger.debug(
                "Notification event published",
                notification_id=notification_id,
                user_id=user_id,
                success=success
            )

        except Exception as e:
            self.logger.error(
                "Error publishing notification event",
                notification_id=notification_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )

    async def get_notification_stats(self) -> Dict[str, int]:
        """
        Get notification statistics

        Returns:
            Dictionary with notification statistics
        """
        try:
            stats = {}

            # Count notifications by status
            for status in NotificationStatus:
                count = await self.notifications_collection.count_documents({
                    "status": status.value
                })
                stats[f"notifications_{status.value}"] = count

            # Count notifications by type
            for notification_type in NotificationType:
                count = await self.notifications_collection.count_documents({
                    "type": notification_type.value
                })
                stats[f"notifications_{notification_type.value}"] = count

            # Total notifications
            stats["total_notifications"] = await self.notifications_collection.count_documents({})

            return stats

        except Exception as e:
            self.logger.error(
                "Error getting notification stats",
                error=str(e),
                error_type=type(e).__name__
            )
            return {}

    async def cleanup_old_notifications(self, days_old: int = 30) -> int:
        """
        Clean up old notifications

        Args:
            days_old: Remove notifications older than this many days

        Returns:
            Number of notifications cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            result = await self.notifications_collection.delete_many({
                "status": {"$in": [NotificationStatus.SENT.value, NotificationStatus.FAILED.value, NotificationStatus.CANCELLED.value]},
                "created_at": {"$lt": cutoff_date}
            })

            if result.deleted_count > 0:
                self.logger.info(
                    "Cleaned up old notifications",
                    count=result.deleted_count,
                    days_old=days_old
                )

            return result.deleted_count

        except Exception as e:
            self.logger.error(
                "Error cleaning up old notifications",
                days_old=days_old,
                error=str(e),
                error_type=type(e).__name__
            )
            return 0
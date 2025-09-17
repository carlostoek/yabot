"""
Base handler class for the Telegram bot framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from src.utils.logger import get_logger
from src.core.models import CommandResponse

logger = get_logger(__name__)


class BaseHandler(ABC):
    """Abstract base class for all handlers."""
    
    def __init__(self):
        """Initialize the base handler."""
        pass
    
    @abstractmethod
    async def handle(self, update: Any) -> Optional[CommandResponse]:
        """Handle an incoming update.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Optional[CommandResponse]: The response to send back to the user
        """
        pass
    
    async def _create_response(
        self,
        text: str,
        parse_mode: Optional[str] = "HTML",
        reply_markup: Optional[Any] = None,
        disable_notification: bool = False
    ) -> CommandResponse:
        """Create a standardized response.
        
        Args:
            text (str): The response text
            parse_mode (Optional[str]): The parse mode for the text
            reply_markup (Optional[Any]): Reply markup (buttons, etc.)
            disable_notification (bool): Whether to disable notification
            
        Returns:
            CommandResponse: The standardized response
        """
        return CommandResponse(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_notification=disable_notification
        )
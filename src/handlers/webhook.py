"""
Webhook handler for the Telegram bot framework.
"""

import json
import hashlib
import hmac
import time
from typing import Any, Optional, Dict
from urllib.parse import urlparse
from src.handlers.base import BaseHandler
from src.core.models import CommandResponse
from src.utils.logger import get_logger
from src.utils.validators import InputValidator

logger = get_logger(__name__)


class WebhookHandler(BaseHandler):
    """Handles webhook endpoint for receiving Telegram updates with security validation."""
    
    def __init__(self):
        """Initialize the webhook handler."""
        super().__init__()
        self._webhook_config = None
        self._rate_limit_cache: Dict[str, list] = {}
        self._max_requests_per_minute = 60
    
    async def handle(self, update: Any) -> Optional[CommandResponse]:
        """Handle an incoming update.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Optional[CommandResponse]: The response to send back to the user
        """
        # This method would typically be called by the webhook endpoint
        # For now, we'll just return None as the specific processing
        # will be handled by other components
        return None
    
    def setup_webhook(self, url: str, certificate: Optional[str] = None) -> bool:
        """Configure webhook.
        
        Args:
            url (str): The webhook URL
            certificate (Optional[str]): SSL certificate if needed
            
        Returns:
            bool: True if webhook setup was successful
        """
        logger.info("Setting up webhook at URL: %s", url)
        
        # In a real implementation, this would:
        # 1. Validate the URL (must be HTTPS)
        # 2. Validate the certificate if provided
        # 3. Register the webhook with Telegram's API
        # 4. Store the configuration
        
        if not url.startswith("https://"):
            logger.error("Invalid webhook URL: Must use HTTPS protocol")
            return False
        
        self._webhook_config = {
            "url": url,
            "certificate": certificate
        }
        
        logger.info("Webhook setup completed successfully")
        return True
    
    def validate_request(self, request: Any) -> bool:
        """Validate incoming webhook requests.
        
        Args:
            request (Any): The incoming request to validate
            
        Returns:
            bool: True if the request is valid, False otherwise
        """
        logger.debug("Validating incoming webhook request")
        
        # In a real implementation, this would:
        # 1. Check request signature/headers for security
        # 2. Validate the request format
        # 3. Check if the request is from Telegram
        # 4. Validate any secret tokens
        
        # For now, we'll implement a basic validation
        if not hasattr(request, 'headers'):
            logger.warning("Invalid request: Missing headers")
            return False
        
        # Check if this is a POST request (webhooks should be POST)
        if hasattr(request, 'method') and request.method != 'POST':
            logger.warning("Invalid request method: %s", request.method)
            return False
        
        # In a real implementation, we would also check:
        # - X-Telegram-Bot-Api-Secret-Token header if configured
        # - Content-Type header
        # - Request body format
        
        logger.debug("Webhook request validation passed")
        return True
    
    async def process_update(self, update: Any) -> Optional[CommandResponse]:
        """Process received updates.
        
        Args:
            update (Any): The update to process
            
        Returns:
            Optional[CommandResponse]: The response to the update
        """
        logger.info("Processing webhook update")
        
        # In a real implementation, this would:
        # 1. Parse the update from the request body
        # 2. Route the update to the appropriate handler
        # 3. Process the update asynchronously
        # 4. Return the response
        
        # For now, we'll just log the update and return None
        logger.debug("Received update: %s", str(update))
        
        # The actual processing would be done by the router and handlers
        # This is just a placeholder implementation
        
        logger.info("Webhook update processed successfully")
        return None
    
    def validate_webhook_url(self, url: str) -> bool:
        """Validate webhook URL for security."""
        return InputValidator.validate_webhook_url(url)
    
    def add_security_headers(self, response: Any) -> None:
        """Add security headers to webhook response."""
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        current_time = time.time()
        
        # Clean old entries
        if user_id in self._rate_limit_cache:
            self._rate_limit_cache[user_id] = [
                req_time for req_time in self._rate_limit_cache[user_id]
                if current_time - req_time < 60  # Keep last minute
            ]
        else:
            self._rate_limit_cache[user_id] = []
        
        # Check if under limit
        if len(self._rate_limit_cache[user_id]) >= self._max_requests_per_minute:
            logger.warning("Rate limit exceeded for user %s", user_id)
            return False
        
        # Add current request
        self._rate_limit_cache[user_id].append(current_time)
        return True
    
    def sanitize_input(self, input_text: str) -> str:
        """Sanitize user input for security."""
        return InputValidator.sanitize_html_input(input_text)
    
    def generate_signature(self, payload: bytes, secret: str) -> str:
        """Generate HMAC signature for webhook validation."""
        return hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
    
    def validate_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Validate webhook signature."""
        expected_signature = self.generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    async def process_user_input(self, user_input: str) -> str:
        """Process user input safely."""
        # Sanitize the input
        sanitized_input = self.sanitize_input(user_input)
        
        # Additional security checks
        if len(sanitized_input) > 4096:
            return "Input too long"
        
        return sanitized_input
    
    def validate_payload_size(self, payload: str, max_size: int = 1024 * 1024) -> bool:
        """Validate payload size to prevent DoS attacks."""
        return len(payload.encode('utf-8')) <= max_size
    
    def validate_and_sanitize_payload(self, payload: str) -> str:
        """Validate and sanitize webhook payload."""
        if not self.validate_payload_size(payload):
            return "{}"
        
        try:
            # Parse and re-serialize to ensure valid JSON
            data = json.loads(payload)
            
            # Recursively sanitize string values
            def sanitize_recursive(obj):
                if isinstance(obj, dict):
                    return {k: sanitize_recursive(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [sanitize_recursive(item) for item in obj]
                elif isinstance(obj, str):
                    return self.sanitize_input(obj)
                else:
                    return obj
            
            sanitized_data = sanitize_recursive(data)
            return json.dumps(sanitized_data)
            
        except (json.JSONDecodeError, ValueError):
            logger.warning("Invalid JSON payload received")
            return "{}"
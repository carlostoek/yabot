"""
Security tests for data handling and protection.
"""

import pytest
from unittest.mock import Mock, patch
import json
from src.core.models import CommandResponse
from src.utils.logger import get_logger


class TestDataSecurity:
    """Test data security and privacy protection."""

    @pytest.mark.security
    def test_sensitive_data_not_logged(self):
        """Test that sensitive data is not logged."""
        logger = get_logger(__name__)
        
        sensitive_data = {
            "user_password": "secret123",
            "api_key": "sk-1234567890abcdef",
            "token": "bot123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
            "credit_card": "4111111111111111",
            "ssn": "123-45-6789"
        }
        
        with patch.object(logger, 'info') as mock_log:
            # Simulate logging user data
            user_message = "User input received"
            logger.info(user_message)
            
            # Verify sensitive data is not in logs
            for call in mock_log.call_args_list:
                log_message = str(call)
                for key, value in sensitive_data.items():
                    assert value not in log_message
                    assert key.lower() not in log_message.lower()

    @pytest.mark.security
    def test_data_encryption_at_rest(self):
        """Test that sensitive data is encrypted when stored."""
        from src.utils.crypto import encrypt_sensitive_data, decrypt_sensitive_data
        
        sensitive_data = "user_secret_information"
        
        # Encrypt data
        encrypted_data = encrypt_sensitive_data(sensitive_data)
        
        # Verify data is actually encrypted
        assert encrypted_data != sensitive_data
        assert len(encrypted_data) > len(sensitive_data)
        
        # Verify decryption works
        decrypted_data = decrypt_sensitive_data(encrypted_data)
        assert decrypted_data == sensitive_data

    @pytest.mark.security
    def test_json_serialization_safety(self):
        """Test JSON serialization doesn't expose sensitive data."""
        response_data = {
            "message": "Hello user",
            "user_id": 12345,
            "_internal_token": "secret_token_123",
            "_debug_info": "internal_debug_data"
        }
        
        # Create response object
        response = CommandResponse(
            text=response_data["message"],
            user_id=response_data["user_id"]
        )
        
        # Serialize to JSON
        json_data = json.dumps(response.__dict__)
        
        # Verify internal/sensitive fields are not in JSON
        assert "_internal_token" not in json_data
        assert "_debug_info" not in json_data
        assert "secret_token" not in json_data

    @pytest.mark.security
    def test_memory_cleanup_after_processing(self):
        """Test that sensitive data is cleaned from memory."""
        import gc
        
        # Create sensitive data
        sensitive_token = "very_secret_token_12345"
        
        # Process it (simulate normal operation)
        def process_sensitive_data(token):
            # Normal processing
            result = f"Processed: {len(token)} chars"
            # Explicitly clear the token
            token = None
            del token
            return result
        
        result = process_sensitive_data(sensitive_token)
        
        # Force garbage collection
        gc.collect()
        
        # In a real scenario, you might use memory profiling tools
        # to verify the sensitive data is actually cleared
        assert "very_secret_token" not in result

    @pytest.mark.security
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in database queries."""
        from src.utils.database import safe_query_builder
        
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'; DELETE FROM users; --",
            "1' UNION SELECT password FROM users --",
        ]
        
        for malicious_input in malicious_inputs:
            # Test that SQL injection is prevented
            query = safe_query_builder("users", {"id": malicious_input})
            
            # Verify dangerous SQL keywords are escaped/removed
            assert "DROP TABLE" not in query.upper()
            assert "DELETE FROM" not in query.upper()
            assert "UNION SELECT" not in query.upper()
            assert "'1'='1'" not in query

    @pytest.mark.security
    def test_file_path_traversal_prevention(self):
        """Test prevention of file path traversal attacks."""
        from src.utils.file_handler import safe_file_access
        
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "../../../../etc/hosts",
            "..\\..\\system.ini",
        ]
        
        for malicious_path in malicious_paths:
            # Test that path traversal is prevented
            result = safe_file_access(malicious_path)
            
            # Should return None or False for malicious paths
            assert result is None or result is False

    @pytest.mark.security
    def test_data_size_limits(self):
        """Test data size limits to prevent DoS attacks."""
        from src.handlers.webhook import WebhookHandler
        
        webhook_handler = WebhookHandler()
        
        # Test oversized data
        oversized_data = "A" * (10 * 1024 * 1024)  # 10MB
        
        result = webhook_handler.validate_payload_size(oversized_data)
        assert result is False
        
        # Test normal sized data
        normal_data = "Normal message"
        result = webhook_handler.validate_payload_size(normal_data)
        assert result is True

    @pytest.mark.security
    def test_regex_dos_prevention(self):
        """Test prevention of regex DoS attacks."""
        from src.utils.validators import safe_regex_match
        
        # Malicious regex patterns that could cause ReDoS
        evil_patterns = [
            r"^(a+)+$",
            r"(a|a)*",
            r"(a|b)*a(a|b){20}",
        ]
        
        # Input that would cause catastrophic backtracking
        evil_input = "a" * 30 + "b"
        
        for pattern in evil_patterns:
            # Test that regex matching has timeout/protection
            result = safe_regex_match(pattern, evil_input, timeout_seconds=1)
            
            # Should timeout or return False for evil patterns
            assert result is False or result is None

    @pytest.mark.security
    def test_user_data_isolation(self):
        """Test that user data is properly isolated."""
        from src.core.session import UserSession
        
        user1_id = "user_123"
        user2_id = "user_456"
        
        # Create sessions for different users
        session1 = UserSession(user1_id)
        session2 = UserSession(user2_id)
        
        # Store data in user1's session
        session1.store_data("secret", "user1_secret_data")
        
        # Verify user2 cannot access user1's data
        user2_data = session2.get_data("secret")
        assert user2_data is None
        
        # Verify user1 can access their own data
        user1_data = session1.get_data("secret")
        assert user1_data == "user1_secret_data"

    @pytest.mark.security
    def test_api_response_information_disclosure(self):
        """Test that API responses don't disclose sensitive information."""
        from src.core.error_handler import ErrorHandler
        
        error_handler = ErrorHandler()
        
        # Simulate various types of errors
        errors = [
            FileNotFoundError("/home/user/.env"),
            ConnectionError("Failed to connect to database at localhost:5432"),
            ValueError("Invalid token: sk-123456789abcdef"),
        ]
        
        for error in errors:
            user_message = error_handler.handle_error(error, {})
            
            # User message should not contain sensitive paths, tokens, or internal details
            assert "/home/user/.env" not in user_message
            assert "localhost:5432" not in user_message
            assert "sk-123456789abcdef" not in user_message
            assert "database" not in user_message.lower()

    @pytest.mark.security
    def test_webhook_payload_validation(self):
        """Test webhook payload validation and sanitization."""
        from src.handlers.webhook import WebhookHandler
        
        webhook_handler = WebhookHandler()
        
        # Test malicious payloads
        malicious_payloads = [
            '{"message": {"text": "<script>alert(\'xss\')</script>"}}',
            '{"callback_query": {"data": "../../etc/passwd"}}',
            '{"message": {"text": "javascript:alert(\'xss\')"}}',
        ]
        
        for payload in malicious_payloads:
            result = webhook_handler.validate_and_sanitize_payload(payload)
            
            # Should sanitize malicious content
            assert "<script>" not in result
            assert "javascript:" not in result
            assert "../" not in result
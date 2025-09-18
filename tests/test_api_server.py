"""
Tests for the API server.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.server import APIServer
from src.api.auth import JWTAuthService


class TestAPIServer:
    """Test cases for APIServer."""

    def test_api_server_initialization(self):
        """Test API server initialization."""
        with patch('src.api.server.ConfigManager') as mock_config_manager:
            api_server = APIServer(mock_config_manager)
            
            assert api_server is not None
            assert isinstance(api_server.app, FastAPI)
            assert api_server.config_manager == mock_config_manager
            assert isinstance(api_server.jwt_auth_service, JWTAuthService)

    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        with patch('src.api.server.ConfigManager'):
            api_server = APIServer()
            client = TestClient(api_server.app)
            
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "yabot-api"

    def test_api_info_endpoint(self):
        """Test API info endpoint."""
        with patch('src.api.server.ConfigManager'):
            api_server = APIServer()
            client = TestClient(api_server.app)
            
            response = client.get("/info")
            assert response.status_code == 200
            
            data = response.json()
            assert data["title"] == "YABOT Internal API"
            assert data["version"] == "1.0.0"

    def test_protected_health_check_without_auth(self):
        """Test protected health check without authentication."""
        with patch('src.api.server.ConfigManager'):
            api_server = APIServer()
            client = TestClient(api_server.app)
            
            response = client.get("/health/protected")
            assert response.status_code == 401

    def test_protected_health_check_with_invalid_auth(self):
        """Test protected health check with invalid authentication."""
        with patch('src.api.server.ConfigManager'):
            api_server = APIServer()
            client = TestClient(api_server.app)
            
            response = client.get("/health/protected", headers={"Authorization": "Invalid"})
            assert response.status_code == 401

    def test_get_api_config(self):
        """Test getting API configuration."""
        with patch('src.api.server.ConfigManager'):
            api_server = APIServer()
            
            # Test default configuration
            config = api_server.get_api_config()
            assert config["host"] == "127.0.0.1"
            assert config["port"] == 8000
            assert config["reload"] is False
            assert config["log_level"] == "info"
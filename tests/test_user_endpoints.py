"""
Tests for the user API endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.endpoints.users import router


class TestUserAPIEndpoints:
    """Test cases for user API endpoints."""

    def setup_method(self):
        """Set up test client with user router."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_router_prefix_and_tags(self):
        """Test that router has correct prefix and tags."""
        assert router.prefix == "/api/v1/user"
        assert "Users" in router.tags
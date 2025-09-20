"""
Tests for the narrative API endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.endpoints.narrative import router


class TestNarrativeAPIEndpoints:
    """Test cases for narrative API endpoints."""

    def setup_method(self):
        """Set up test client with narrative router."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_router_prefix_and_tags(self):
        """Test that router has correct prefix and tags."""
        assert router.prefix == "/api/v1/narrative"
        assert "Narrative" in router.tags
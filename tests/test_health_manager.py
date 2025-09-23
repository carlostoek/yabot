"""
Tests for the HealthCheckManager.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from src.utils.health import HealthCheckManager


class TestHealthCheckManager:
    """Test cases for the HealthCheckManager."""
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.health_check = AsyncMock(return_value={"mongodb": True, "sqlite": True})
        return db_manager
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        event_bus = Mock()
        event_bus.health_check = AsyncMock(return_value={"connected": True, "redis_healthy": True})
        return event_bus
    
    @pytest.mark.asyncio
    async def test_health_check_manager_initialization(self):
        """Test HealthCheckManager initialization."""
        # Test with no parameters
        health_manager = HealthCheckManager()
        assert health_manager is not None
        assert health_manager.database_manager is None
        assert health_manager.event_bus is None
        
        # Test with parameters
        mock_db = Mock()
        mock_eb = Mock()
        health_manager = HealthCheckManager(mock_db, mock_eb)
        assert health_manager.database_manager == mock_db
        assert health_manager.event_bus == mock_eb
    
    @pytest.mark.asyncio
    async def test_check_database_health(self, mock_database_manager):
        """Test database health check."""
        health_manager = HealthCheckManager(mock_database_manager)
        result = await health_manager.check_database_health()
        
        assert result["status"] == "healthy"
        assert "details" in result
        assert result["details"]["mongodb"] is True
        assert result["details"]["sqlite"] is True
        mock_database_manager.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_event_bus_health(self, mock_event_bus):
        """Test event bus health check."""
        health_manager = HealthCheckManager(event_bus=mock_event_bus)
        result = await health_manager.check_event_bus_health()
        
        assert result["status"] == "healthy"
        assert "details" in result
        assert result["details"]["connected"] is True
        assert result["details"]["redis_healthy"] is True
        mock_event_bus.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_all_health(self, mock_database_manager, mock_event_bus):
        """Test comprehensive health check."""
        health_manager = HealthCheckManager(mock_database_manager, mock_event_bus)
        result = await health_manager.check_all_health()
        
        assert result["overall_status"] == "healthy"
        assert "components" in result
        assert "database" in result["components"]
        assert "event_bus" in result["components"]
        assert "api_server" in result["components"]
        
        # Verify database check
        assert result["components"]["database"]["status"] == "healthy"
        
        # Verify event bus check
        assert result["components"]["event_bus"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_check_database_health_with_no_manager(self):
        """Test database health check when no database manager is available."""
        health_manager = HealthCheckManager()
        result = await health_manager.check_database_health()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["error"] == "Database manager not initialized"
    
    @pytest.mark.asyncio
    async def test_check_event_bus_health_with_no_bus(self):
        """Test event bus health check when no event bus is available."""
        health_manager = HealthCheckManager()
        result = await health_manager.check_event_bus_health()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["error"] == "Event bus not initialized"
    
    @pytest.mark.asyncio
    async def test_get_health_summary(self, mock_database_manager, mock_event_bus):
        """Test health summary generation."""
        health_manager = HealthCheckManager(mock_database_manager, mock_event_bus)
        result = await health_manager.get_health_summary()
        
        assert "status" in result
        assert "timestamp" in result
        assert "database" in result
        assert "event_bus" in result
        assert "api_server" in result
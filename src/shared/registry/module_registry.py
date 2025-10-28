"""
Module registry for the YABOT system.
Implements requirement 5.6: WHEN modules restart THEN they SHALL resume from their last known state.

This module provides a registry for tracking and managing atomic modules,
allowing for module discovery, health monitoring, and state persistence.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import os

from src.utils.logger import get_logger
from src.events.bus import EventBus
from src.events.models import create_event

logger = get_logger(__name__)


class ModuleState(Enum):
    """Enumeration of possible module states."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


class ModuleHealthStatus(Enum):
    """Enumeration of possible module health statuses."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class ModuleInfo:
    """Information about a registered module."""
    
    def __init__(self, 
                 name: str,
                 module_type: str,
                 version: str = "1.0.0",
                 dependencies: List[str] = None,
                 health_check_endpoint: Optional[str] = None):
        self.name = name
        self.module_type = module_type
        self.version = version
        self.dependencies = dependencies or []
        self.health_check_endpoint = health_check_endpoint
        self.state = ModuleState.UNKNOWN
        self.health_status = ModuleHealthStatus.UNKNOWN
        self.last_heartbeat = None
        self.last_health_check = None
        self.start_time = None
        self.restart_count = 0
        self.metadata = {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert module info to dictionary."""
        return {
            "name": self.name,
            "module_type": self.module_type,
            "version": self.version,
            "dependencies": self.dependencies,
            "health_check_endpoint": self.health_check_endpoint,
            "state": self.state.value,
            "health_status": self.health_status.value,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "restart_count": self.restart_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModuleInfo':
        """Create module info from dictionary."""
        module_info = cls(
            name=data["name"],
            module_type=data["module_type"],
            version=data.get("version", "1.0.0"),
            dependencies=data.get("dependencies", []),
            health_check_endpoint=data.get("health_check_endpoint")
        )
        module_info.state = ModuleState(data.get("state", "unknown"))
        module_info.health_status = ModuleHealthStatus(data.get("health_status", "unknown"))
        
        # Convert string timestamps back to datetime objects
        if data.get("last_heartbeat"):
            module_info.last_heartbeat = datetime.fromisoformat(data["last_heartbeat"])
        if data.get("last_health_check"):
            module_info.last_health_check = datetime.fromisoformat(data["last_health_check"])
        if data.get("start_time"):
            module_info.start_time = datetime.fromisoformat(data["start_time"])
            
        module_info.restart_count = data.get("restart_count", 0)
        module_info.metadata = data.get("metadata", {})
        
        return module_info


class ModuleRegistry:
    """Registry for managing atomic modules in the YABOT system.
    
    Implements requirement 5.6: WHEN modules restart THEN they SHALL resume from their last known state.
    """
    
    def __init__(self, event_bus: EventBus, registry_file: str = "./module_registry.json"):
        """Initialize the module registry.
        
        Args:
            event_bus: Event bus for publishing module events
            registry_file: File to persist module registry state
        """
        self.event_bus = event_bus
        self.registry_file = registry_file
        self.modules: Dict[str, ModuleInfo] = {}
        self.health_check_interval = 30  # seconds
        self.is_monitoring = False
        self._health_check_callbacks: Dict[str, Callable] = {}
        
        # Load existing registry state
        self._load_registry_state()
        
        logger.info("ModuleRegistry initialized with %d registered modules", len(self.modules))
    
    def register_module(self, 
                       name: str,
                       module_type: str,
                       version: str = "1.0.0",
                       dependencies: List[str] = None,
                       health_check_endpoint: Optional[str] = None,
                       health_check_callback: Optional[Callable] = None) -> ModuleInfo:
        """Register a module with the registry.
        
        Args:
            name: Unique name of the module
            module_type: Type of the module (e.g., 'narrative', 'gamification', 'admin')
            version: Version of the module
            dependencies: List of module dependencies
            health_check_endpoint: HTTP endpoint for health checks
            health_check_callback: Function to call for health checks
            
        Returns:
            ModuleInfo: Registered module information
        """
        logger.info("Registering module: %s (type: %s, version: %s)", name, module_type, version)
        
        # Create or update module info
        if name in self.modules:
            module_info = self.modules[name]
            # Update existing module info
            module_info.module_type = module_type
            module_info.version = version
            module_info.dependencies = dependencies or []
            module_info.health_check_endpoint = health_check_endpoint
        else:
            # Create new module info
            module_info = ModuleInfo(
                name=name,
                module_type=module_type,
                version=version,
                dependencies=dependencies,
                health_check_endpoint=health_check_endpoint
            )
            self.modules[name] = module_info
        
        # Store health check callback if provided
        if health_check_callback:
            self._health_check_callbacks[name] = health_check_callback
        
        # Set initial state
        module_info.state = ModuleState.STARTING
        module_info.start_time = datetime.utcnow()
        
        # Save registry state
        self._save_registry_state()
        
        # Publish module registered event
        asyncio.create_task(self._publish_module_event("module_registered", module_info))
        
        logger.info("Module registered successfully: %s", name)
        return module_info
    
    def unregister_module(self, name: str) -> bool:
        """Unregister a module from the registry.
        
        Args:
            name: Name of the module to unregister
            
        Returns:
            bool: True if module was unregistered, False if not found
        """
        logger.info("Unregistering module: %s", name)
        
        if name not in self.modules:
            logger.warning("Module not found for unregistration: %s", name)
            return False
        
        module_info = self.modules[name]
        module_info.state = ModuleState.STOPPING
        
        # Remove module
        del self.modules[name]
        
        # Remove health check callback
        if name in self._health_check_callbacks:
            del self._health_check_callbacks[name]
        
        # Save registry state
        self._save_registry_state()
        
        # Publish module unregistered event
        asyncio.create_task(self._publish_module_event("module_unregistered", module_info))
        
        logger.info("Module unregistered successfully: %s", name)
        return True
    
    def update_module_state(self, name: str, state: ModuleState) -> bool:
        """Update the state of a registered module.
        
        Args:
            name: Name of the module
            state: New state of the module
            
        Returns:
            bool: True if state was updated, False if module not found
        """
        if name not in self.modules:
            logger.warning("Module not found for state update: %s", name)
            return False
        
        module_info = self.modules[name]
        old_state = module_info.state
        module_info.state = state
        module_info.last_heartbeat = datetime.utcnow()
        
        # Handle restart counting
        if state == ModuleState.RESTARTING:
            module_info.restart_count += 1
        
        # Save registry state
        self._save_registry_state()
        
        # Publish state change event
        asyncio.create_task(self._publish_state_change_event(module_info, old_state, state))
        
        logger.debug("Module state updated: %s -> %s", name, state.value)
        return True
    
    def update_module_health(self, name: str, health_status: ModuleHealthStatus) -> bool:
        """Update the health status of a registered module.
        
        Args:
            name: Name of the module
            health_status: New health status of the module
            
        Returns:
            bool: True if health status was updated, False if module not found
        """
        if name not in self.modules:
            logger.warning("Module not found for health update: %s", name)
            return False
        
        module_info = self.modules[name]
        old_health = module_info.health_status
        module_info.health_status = health_status
        module_info.last_health_check = datetime.utcnow()
        
        # Save registry state
        self._save_registry_state()
        
        # Publish health change event
        asyncio.create_task(self._publish_health_change_event(module_info, old_health, health_status))
        
        logger.debug("Module health updated: %s -> %s", name, health_status.value)
        return True
    
    def get_module(self, name: str) -> Optional[ModuleInfo]:
        """Get information about a registered module.
        
        Args:
            name: Name of the module
            
        Returns:
            Optional[ModuleInfo]: Module information or None if not found
        """
        return self.modules.get(name)
    
    def get_modules_by_type(self, module_type: str) -> List[ModuleInfo]:
        """Get all modules of a specific type.
        
        Args:
            module_type: Type of modules to retrieve
            
        Returns:
            List[ModuleInfo]: List of modules of the specified type
        """
        return [module for module in self.modules.values() if module.module_type == module_type]
    
    def get_all_modules(self) -> List[ModuleInfo]:
        """Get information about all registered modules.
        
        Returns:
            List[ModuleInfo]: List of all registered modules
        """
        return list(self.modules.values())
    
    def heartbeat(self, name: str) -> bool:
        """Record a heartbeat from a module.
        
        Args:
            name: Name of the module sending heartbeat
            
        Returns:
            bool: True if heartbeat was recorded, False if module not found
        """
        if name not in self.modules:
            logger.warning("Module not found for heartbeat: %s", name)
            return False
        
        module_info = self.modules[name]
        module_info.last_heartbeat = datetime.utcnow()
        
        # Update state if it was previously unknown
        if module_info.state == ModuleState.UNKNOWN:
            module_info.state = ModuleState.RUNNING
        
        logger.debug("Heartbeat received from module: %s", name)
        return True
    
    async def start_health_monitoring(self) -> None:
        """Start periodic health monitoring of registered modules."""
        logger.info("Starting module health monitoring")
        self.is_monitoring = True
        
        while self.is_monitoring:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error("Error during health monitoring: %s", str(e))
    
    async def stop_health_monitoring(self) -> None:
        """Stop periodic health monitoring."""
        logger.info("Stopping module health monitoring")
        self.is_monitoring = False
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered modules."""
        logger.debug("Performing health checks on %d modules", len(self.modules))
        
        for name, module_info in self.modules.items():
            try:
                # Skip modules that don't have health check mechanisms
                if not module_info.health_check_endpoint and name not in self._health_check_callbacks:
                    continue
                
                health_status = ModuleHealthStatus.HEALTHY
                
                # Perform health check via callback if available
                if name in self._health_check_callbacks:
                    try:
                        health_result = await self._health_check_callbacks[name]()
                        if not health_result.get("healthy", True):
                            health_status = ModuleHealthStatus.UNHEALTHY
                    except Exception as e:
                        logger.warning("Health check callback failed for module %s: %s", name, str(e))
                        health_status = ModuleHealthStatus.UNHEALTHY
                
                # Update module health status
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.update_module_health, 
                    name, 
                    health_status
                )
                
            except Exception as e:
                logger.error("Error performing health check for module %s: %s", name, str(e))
    
    def _save_registry_state(self) -> None:
        """Save the current registry state to file."""
        try:
            # Convert modules to serializable format
            modules_data = {name: module.to_dict() for name, module in self.modules.items()}
            
            # Save to file
            with open(self.registry_file, 'w') as f:
                json.dump(modules_data, f, indent=2)
                
            logger.debug("Registry state saved to %s", self.registry_file)
        except Exception as e:
            logger.warning("Failed to save registry state: %s", str(e))
    
    def _load_registry_state(self) -> None:
        """Load registry state from file."""
        try:
            if not os.path.exists(self.registry_file):
                logger.debug("Registry file not found, starting with empty registry")
                return
            
            with open(self.registry_file, 'r') as f:
                modules_data = json.load(f)
            
            # Convert data back to ModuleInfo objects
            for name, data in modules_data.items():
                try:
                    self.modules[name] = ModuleInfo.from_dict(data)
                except Exception as e:
                    logger.warning("Failed to load module info for %s: %s", name, str(e))
            
            logger.info("Loaded %d modules from registry file", len(self.modules))
        except Exception as e:
            logger.warning("Failed to load registry state: %s", str(e))
    
    async def _publish_module_event(self, event_type: str, module_info: ModuleInfo) -> None:
        """Publish a module-related event.
        
        Args:
            event_type: Type of event to publish
            module_info: Module information
        """
        try:
            event = create_event(
                event_type,
                module_name=module_info.name,
                module_type=module_info.module_type,
                version=module_info.version,
                timestamp=datetime.utcnow()
            )
            await self.event_bus.publish(event_type, event.dict())
            logger.debug("Published %s event for module: %s", event_type, module_info.name)
        except Exception as e:
            logger.warning("Failed to publish %s event: %s", event_type, str(e))
    
    async def _publish_state_change_event(self, module_info: ModuleInfo, 
                                         old_state: ModuleState, new_state: ModuleState) -> None:
        """Publish a module state change event.
        
        Args:
            module_info: Module information
            old_state: Previous state
            new_state: New state
        """
        try:
            event = create_event(
                "module_state_changed",
                module_name=module_info.name,
                old_state=old_state.value,
                new_state=new_state.value,
                timestamp=datetime.utcnow()
            )
            await self.event_bus.publish("module_state_changed", event.dict())
            logger.debug("Published state change event for module: %s (%s -> %s)", 
                        module_info.name, old_state.value, new_state.value)
        except Exception as e:
            logger.warning("Failed to publish state change event: %s", str(e))
    
    async def _publish_health_change_event(self, module_info: ModuleInfo, 
                                          old_health: ModuleHealthStatus, new_health: ModuleHealthStatus) -> None:
        """Publish a module health change event.
        
        Args:
            module_info: Module information
            old_health: Previous health status
            new_health: New health status
        """
        try:
            event = create_event(
                "module_health_changed",
                module_name=module_info.name,
                old_health=old_health.value,
                new_health=new_health.value,
                timestamp=datetime.utcnow()
            )
            await self.event_bus.publish("module_health_changed", event.dict())
            logger.debug("Published health change event for module: %s (%s -> %s)", 
                        module_info.name, old_health.value, new_health.value)
        except Exception as e:
            logger.warning("Failed to publish health change event: %s", str(e))


# Factory function for dependency injection
async def create_module_registry(event_bus: EventBus, registry_file: str = "./module_registry.json") -> ModuleRegistry:
    """Factory function to create a ModuleRegistry instance.
    
    Args:
        event_bus: Event bus instance
        registry_file: File to persist module registry state
        
    Returns:
        ModuleRegistry: Initialized module registry instance
    """
    return ModuleRegistry(event_bus, registry_file)
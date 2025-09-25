"""
API Endpoints Module Initialization

This module initializes the API endpoints layer of the application,
providing the base structure for internal REST API endpoints.
"""

# Import specific endpoint modules
from . import users
from . import narrative
from . import health

# Define what gets imported with "from src.api.endpoints import *"
__all__ = [
    "users",
    "narrative", 
    "health"
]

# API endpoints version information
ENDPOINTS_VERSION = "1.0.0"
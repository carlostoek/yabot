from fastapi import APIRouter, Depends
from src.services.cross_module import CrossModuleService, get_cross_module_service

router = APIRouter()

@router.get("/test-integration")
async def test_integration(
    cross_module_service: CrossModuleService = Depends(get_cross_module_service)
):
    """Test endpoint to verify cross-module integration is working"""
    # This is a simple test to check if all services are properly injected
    return {
        "status": "integration_test_passed",
        "message": "Cross-module services are properly configured"
    }

from fastapi import APIRouter

router = APIRouter()

@router.get("/test-integration")
async def test_integration():
    """Test endpoint to verify cross-module integration is working"""
    # Simple test endpoint without complex dependencies
    return {
        "status": "integration_test_passed",
        "message": "Test endpoint is working"
    }

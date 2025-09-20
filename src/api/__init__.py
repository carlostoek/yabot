from fastapi import APIRouter
from src.api.cross_module import router as cross_module_router
from src.api.test_integration import router as test_integration_router

router = APIRouter()
router.include_router(cross_module_router, prefix="/cross-module", tags=["cross-module"])
router.include_router(test_integration_router, prefix="/test", tags=["test"])

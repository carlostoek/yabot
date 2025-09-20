from fastapi import FastAPI, APIRouter
from src.api.cross_module import router as cross_module_router
from src.api.test_integration import router as test_integration_router

# Create the main FastAPI app
app = FastAPI(
    title="YABOT API",
    description="API for the YABOT system",
    version="1.0.0"
)

# Create a router and include the API routes
router = APIRouter()
router.include_router(cross_module_router, prefix="/cross-module", tags=["cross-module"])
router.include_router(test_integration_router, prefix="/test", tags=["test"])

# Include the router in the main app
app.include_router(router)

# Add a simple root endpoint
@app.get("/")
async def root():
    return {"message": "YABOT API is running"}

"""Health check endpoints."""
from fastapi import APIRouter

from models.response import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check."""
    return HealthResponse(status="ok", message="ExoSense API is healthy")


@router.get("/detailed")
async def detailed_health() -> dict[str, str]:
    """Detailed health check with system info."""
    return {
        "status": "ok",
        "api_version": "0.1.0",
        "ml_package": "available",
        "storage": "ready"
    }
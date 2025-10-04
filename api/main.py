"""ExoSense API - FastAPI backend for exoplanet detection."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import analyze, health, report, sonify

app = FastAPI(
    title="ExoSense API",
    description="FastAPI backend for exoplanet detection and analysis",
    version="0.1.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(report.router)
app.include_router(sonify.router)


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "ExoSense API - Ready for development!"}

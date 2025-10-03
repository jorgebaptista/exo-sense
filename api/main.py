"""ExoSense API - FastAPI backend for exoplanet detection."""

from fastapi import FastAPI

app = FastAPI(
    title="ExoSense API",
    description="FastAPI backend for exoplanet detection and analysis",
    version="0.1.0"
)


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "ExoSense API - Ready for development!"}
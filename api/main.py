"""ExoSense API - FastAPI backend for exoplanet detection."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import analyze, health, report

app = FastAPI(
    title="ExoSense API",
    description="FastAPI backend for exoplanet detection and analysis",
    version="0.1.0",
)

# CORS Configuration
# Add production Vercel URL after deployment
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://exosense.vercel.app",  # Your desired Vercel domain
    "https://exo-sense.vercel.app",  # Alternative domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(report.router)


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "ExoSense API - Ready for development!"}

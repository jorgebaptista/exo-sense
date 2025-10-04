"""API response models."""
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


class AnalysisResult(BaseModel):
    """Exoplanet analysis result."""
    exoplanet_detected: bool
    confidence: float
    transit_depth: float | None = None
    orbital_period: float | None = None
    label: str  # "planet", "binary", "variable", "systematics"
    reasons: list[str]  # Reason codes for classification


class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint."""
    analysis_id: str
    filename: str
    result: AnalysisResult
    plots: dict[str, str]  # plot_name -> base64_image
    metrics: dict[str, Any]
    processing_time: float


class ReportResponse(BaseModel):
    """Response model for report generation."""
    report_url: str
    filename: str
    size_bytes: int

"""API response models."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


class AnalysisResult(BaseModel):
    """Exoplanet analysis result."""
    exoplanet_detected: bool
    confidence: float
    transit_depth: Optional[float] = None
    orbital_period: Optional[float] = None
    label: str  # "planet", "binary", "variable", "systematics"
    reasons: List[str]  # Reason codes for classification
    

class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint."""
    analysis_id: str
    filename: str
    result: AnalysisResult
    plots: Dict[str, str]  # plot_name -> base64_image
    metrics: Dict[str, Any]
    processing_time: float


class ReportResponse(BaseModel):
    """Response model for report generation."""
    report_url: str
    filename: str
    size_bytes: int
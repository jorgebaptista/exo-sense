"""Pydantic response models for the API."""

from typing import Any, Literal

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


class TransitEvent(BaseModel):
    """Summary of a detected transit event."""

    index: int
    start_index: int
    end_index: int
    start_time: float
    end_time: float
    depth: float
    snr: float


class SonificationSeries(BaseModel):
    """Time series payload used for client-side sonification."""

    time: list[float]
    flux: list[float]
    phase: list[float]
    phase_folded_phase: list[float]
    phase_folded_flux: list[float]
    in_transit: list[bool]
    odd_even: list[Literal["odd", "even"] | None]
    secondary_mask: list[bool]
    events: list[TransitEvent]
    sample_interval: float | None = None
    secondary_sigma: float | None = None


class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint."""

    analysis_id: str
    filename: str
    result: AnalysisResult
    plots: dict[str, str]  # plot_name -> base64_image
    metrics: dict[str, Any]
    processing_time: float
    sonification: SonificationSeries | None = None


class ReportResponse(BaseModel):
    """Response model for report generation."""

    report_url: str
    filename: str
    size_bytes: int

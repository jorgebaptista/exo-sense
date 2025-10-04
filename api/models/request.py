"""API request models."""

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    """Request model for exoplanet analysis."""

    tic_id: str | None = None
    file_data: str | None = None  # Base64 encoded file content
    filename: str | None = None


class ReportRequest(BaseModel):
    """Request model for PDF report generation."""

    analysis_id: str
    include_plots: bool = True
    format: str = "pdf"

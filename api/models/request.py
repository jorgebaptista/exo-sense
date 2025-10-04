"""API request models."""
from pydantic import BaseModel
from typing import Optional


class AnalyzeRequest(BaseModel):
    """Request model for exoplanet analysis."""
    tic_id: Optional[str] = None
    file_data: Optional[str] = None  # Base64 encoded file content
    filename: Optional[str] = None


class ReportRequest(BaseModel):
    """Request model for PDF report generation."""
    analysis_id: str
    include_plots: bool = True
    format: str = "pdf"
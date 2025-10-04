"""Report generation endpoints."""

import base64
import io
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report", tags=["report"])

# Storage paths
REPORTS_DIR = Path("storage/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportRequest(BaseModel):
    """Request model for report generation."""

    analysis_id: str
    filename: str
    result: dict[str, Any]
    plots: dict[str, str]
    metrics: dict[str, Any]
    processing_time: float
    additional_notes: str | None = None


@router.post("/generate")
async def generate_report(request: ReportRequest) -> dict[str, str]:
    """Generate PDF report for exoplanet analysis."""
    try:
        report_id = str(uuid.uuid4())
        report_filename = f"exoplanet_analysis_{report_id}.pdf"
        report_path = REPORTS_DIR / report_filename

        # Create PDF document
        doc = SimpleDocTemplate(str(report_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story: list[Any] = []

        # Title
        title = Paragraph("ExoSense - Exoplanet Detection Report", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 20))

        # Analysis Information
        info_data = [
            ["Analysis ID:", request.analysis_id],
            ["Filename:", request.filename],
            ["Processing Time:", f"{request.processing_time:.2f} seconds"],
            ["Generated:", "2024"],  # Would use datetime.now() in real implementation
        ]

        info_table = Table(info_data, colWidths=[2 * 72, 4 * 72])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(info_table)
        story.append(Spacer(1, 20))

        # Results Section
        result_title = Paragraph("Detection Results", styles["Heading2"])
        story.append(result_title)
        story.append(Spacer(1, 10))

        result = request.result
        detection_status = (
            "DETECTED" if result.get("exoplanet_detected", False) else "NOT DETECTED"
        )
        confidence = result.get("confidence", 0)

        result_text = f"""
        <b>Exoplanet Status:</b> {detection_status}<br/>
        <b>Confidence:</b> {confidence:.1f}%<br/>
        <b>Transit Depth:</b> {result.get("transit_depth", 0):.6f}<br/>
        <b>Orbital Period:</b> {result.get("orbital_period", 0):.2f} days<br/>
        <b>Classification:</b> {result.get("label", "unknown").title()}
        """

        result_para = Paragraph(result_text, styles["Normal"])
        story.append(result_para)
        story.append(Spacer(1, 15))

        # Reasons
        reasons_title = Paragraph("Analysis Details", styles["Heading3"])
        story.append(reasons_title)

        reasons = result.get("reasons", [])
        for reason in reasons:
            reason_text = f"• {reason}"
            reason_para = Paragraph(reason_text, styles["Normal"])
            story.append(reason_para)

        story.append(Spacer(1, 20))

        # Metrics
        metrics_title = Paragraph("Technical Metrics", styles["Heading2"])
        story.append(metrics_title)
        story.append(Spacer(1, 10))

        metrics = request.metrics
        metrics_data = [
            ["Signal-to-Noise Ratio:", f"{metrics.get('snr', 0):.2f}"],
            ["Transit Duration:", f"{metrics.get('duration', 0):.2f} hours"],
            ["Transit Depth:", f"{metrics.get('depth', 0):.6f}"],
            ["Orbital Period:", f"{metrics.get('period', 0):.2f} days"],
            ["Data Points:", f"{metrics.get('data_points', 0)}"],
        ]

        metrics_table = Table(metrics_data, colWidths=[3 * 72, 2 * 72])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.lightblue),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(metrics_table)
        story.append(Spacer(1, 20))

        # Add plots if available
        plots_title = Paragraph("Analysis Plots", styles["Heading2"])
        story.append(plots_title)
        story.append(Spacer(1, 10))

        for plot_name, plot_data in request.plots.items():
            if plot_data and plot_data.startswith("data:image"):
                try:
                    # Extract base64 data
                    base64_data = plot_data.split(",")[1]
                    image_data = base64.b64decode(base64_data)

                    # Create image from bytes
                    img_buffer = io.BytesIO(image_data)
                    img = Image(img_buffer, width=5 * 72, height=3 * 72)

                    plot_title = Paragraph(
                        plot_name.replace("_", " ").title(), styles["Heading3"]
                    )
                    story.append(plot_title)
                    story.append(img)
                    story.append(Spacer(1, 15))

                except Exception as e:
                    logger.warning(f"Could not include plot {plot_name}: {e}")

        # Additional notes
        if request.additional_notes:
            notes_title = Paragraph("Additional Notes", styles["Heading2"])
            story.append(notes_title)
            notes_para = Paragraph(request.additional_notes, styles["Normal"])
            story.append(notes_para)

        # Build PDF
        doc.build(story)

        # Return response
        return {
            "report_id": report_id,
            "filename": report_filename,
            "download_url": f"/report/download/{report_id}",
            "status": "generated",
        }

    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Report generation failed: {str(e)}"
        ) from e


@router.get("/download/{report_id}")
async def download_report(report_id: str) -> FileResponse:
    """Download generated report."""
    # TODO: Implement file serving with proper headers
    raise HTTPException(status_code=501, detail="Report download not yet implemented")

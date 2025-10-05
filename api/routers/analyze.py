"""Analysis endpoints for exoplanet detection."""

import base64
import io
import logging
import time
import uuid
from pathlib import Path
from typing import Annotated, Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from models.response import AnalysisResponse, AnalysisResult
from services.model_service import (
    ModelOutput,
    PredictionResult,
    get_model,
)
from services.model_service import (
    analyze_light_curve as run_model_inference,
)

# Configure matplotlib for non-interactive backend
matplotlib.use("Agg")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analysis"])

# Storage paths
UPLOAD_DIR = Path("storage/uploads")
PLOTS_DIR = Path("storage/plots")
REPORTS_DIR = Path("storage/reports")

# Ensure directories exist
for directory in [UPLOAD_DIR, PLOTS_DIR, REPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
# The ML model is loaded lazily via the model service when used in endpoints.


def parse_light_curve_file(file_content: bytes, filename: str) -> dict[str, Any]:
    """Parse light curve data from uploaded file."""
    try:
        if filename.lower().endswith(".csv"):
            # Parse CSV file
            df = pd.read_csv(io.StringIO(file_content.decode("utf-8")))

            # Try to identify time and flux columns
            time_col = None
            flux_col = None

            # Common column name patterns
            time_patterns = ["time", "bjd", "mjd", "hjd", "days"]
            flux_patterns = ["flux", "mag", "magnitude", "brightness", "intensity"]

            for col in df.columns:
                col_lower = col.lower()
                if any(pattern in col_lower for pattern in time_patterns):
                    time_col = col
                elif any(pattern in col_lower for pattern in flux_patterns):
                    flux_col = col

            # If not found, use first two numeric columns
            if time_col is None or flux_col is None:
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if len(numeric_cols) >= 2:
                    time_col = numeric_cols[0]
                    flux_col = numeric_cols[1]
                else:
                    raise ValueError("Could not identify time and flux columns")

            # Extract data
            time_data = df[time_col].dropna().values
            flux_data = df[flux_col].dropna().values

            # Ensure same length
            min_length = min(len(time_data), len(flux_data))
            time_data = time_data[:min_length]
            flux_data = flux_data[:min_length]

            return {"time": time_data, "flux": flux_data}

        else:
            raise ValueError(f"Unsupported file format: {filename}")

    except Exception as e:
        logger.error(f"File parsing error for {filename}: {e}")
        raise HTTPException(
            status_code=400, detail=f"Error parsing file: {str(e)}"
        ) from e


def generate_plots(output: ModelOutput) -> dict[str, str]:
    """Generate analysis plots and return as base64 encoded strings."""
    plots: dict[str, str] = {}

    try:
        time_data = output.time
        flux_data = output.normalized_flux

        if time_data.size == 0 or flux_data.size == 0:
            logger.warning("No data available for plotting")
            return plots

        prediction = output.prediction

        # 1. Light curve plot
        plt.figure(figsize=(12, 6))
        plt.plot(time_data, flux_data, "b.", markersize=2, alpha=0.7)
        plt.xlabel("Time (days)")
        plt.ylabel("Normalized Flux")
        plt.title("Light Curve")
        plt.grid(True, alpha=0.3)

        if prediction.exoplanet_detected:
            flux_std = np.std(flux_data)
            transit_mask = flux_data < -3 * flux_std
            if np.any(transit_mask):
                plt.plot(
                    time_data[transit_mask],
                    flux_data[transit_mask],
                    "ro",
                    markersize=3,
                    label="Potential Transits",
                )
                plt.legend()

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buffer.seek(0)
        plots["light_curve"] = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # 2. Phase-folded plot (if period detected)
        period = prediction.features.dominant_period
        if period > 0:
            plt.figure(figsize=(10, 6))
            phases = ((time_data - time_data[0]) / period) % 1
            sort_idx = np.argsort(phases)
            plt.plot(
                phases[sort_idx], flux_data[sort_idx], "b.", markersize=3, alpha=0.7
            )
            plt.xlabel("Phase")
            plt.ylabel("Normalized Flux")
            plt.title(f"Phase-Folded Light Curve (Period: {period:.2f} days)")
            plt.grid(True, alpha=0.3)

            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
            plt.close()
            buffer.seek(0)
            plots["phase_folded"] = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # 3. Diagnostic plot
        plt.figure(figsize=(12, 8))

        # Subplot 1: Flux histogram
        plt.subplot(2, 2, 1)
        plt.hist(flux_data, bins=50, alpha=0.7, edgecolor="black")
        plt.xlabel("Normalized Flux")
        plt.ylabel("Count")
        plt.title("Flux Distribution")
        plt.grid(True, alpha=0.3)

        # Subplot 2: Time series with rolling mean
        plt.subplot(2, 2, 2)
        plt.plot(time_data, flux_data, "b.", markersize=1, alpha=0.5, label="Data")
        if flux_data.size > 10:
            window = min(int(flux_data.size / 10), 100)
            if window > 1:
                rolling_mean = (
                    pd.Series(flux_data).rolling(window=window, center=True).mean()
                )
                plt.plot(
                    time_data,
                    rolling_mean,
                    "r-",
                    linewidth=2,
                    label=f"Rolling Mean ({window})",
                )
        plt.xlabel("Time (days)")
        plt.ylabel("Normalized Flux")
        plt.title("Trend Analysis")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Subplot 3: Power spectrum (simple)
        plt.subplot(2, 2, 3)
        if flux_data.size > 10:
            freq = np.fft.fftfreq(flux_data.size, d=np.median(np.diff(time_data)))
            power = np.abs(np.fft.fft(flux_data - np.mean(flux_data))) ** 2
            pos_mask = freq > 0
            if np.any(pos_mask):
                plt.loglog(freq[pos_mask], power[pos_mask])
                plt.xlabel("Frequency (1/days)")
                plt.ylabel("Power")
                plt.title("Power Spectrum")
                plt.grid(True, alpha=0.3)

        # Subplot 4: Statistics summary
        plt.subplot(2, 2, 4)
        stats_text = f"""Statistics:
Mean: {np.mean(flux_data):.6f}
Std: {np.std(flux_data):.6f}
Min: {np.min(flux_data):.6f}
Max: {np.max(flux_data):.6f}
Points: {flux_data.size}

Detection:
Probability: {prediction.probability:.2%}
Depth: {prediction.features.depth:.6f}
Period: {prediction.features.dominant_period:.2f} d"""

        plt.text(
            0.1,
            0.5,
            stats_text,
            fontsize=10,
            verticalalignment="center",
            fontfamily="monospace",
        )
        plt.axis("off")
        plt.title("Analysis Summary")

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buffer.seek(0)
        plots["diagnostic"] = base64.b64encode(buffer.getvalue()).decode("utf-8")

    except Exception as e:
        logger.error(f"Plot generation error: {e}")

    for name, data in plots.items():
        plots[name] = f"data:image/png;base64,{data}"

    return plots


def _build_reasons(prediction: PredictionResult) -> list[str]:
    reasons: list[str] = []
    probability_pct = prediction.probability * 100
    reasons.append(f"Model confidence {probability_pct:.1f}%")

    if prediction.features.depth > 0:
        reasons.append(
            f"Transit depth {prediction.features.depth:.5f} (normalized flux units)"
        )

    if prediction.features.transit_ratio > 0:
        transit_pct = prediction.features.transit_ratio * 100
        reasons.append(f"Transit coverage {transit_pct:.2f}% of all cadences")

    if prediction.features.dominant_period > 0:
        reasons.append(
            f"Dominant period detected at {prediction.features.dominant_period:.2f} days"
        )

    if not prediction.exoplanet_detected:
        reasons.append("Signal below decision threshold")

    return reasons


def _build_metrics(output: ModelOutput) -> dict[str, Any]:
    prediction = output.prediction
    model = get_model()
    feature_values = prediction.features.as_array()
    feature_vector = {
        name: float(value)
        for name, value in zip(
            model.metadata.feature_names, feature_values.tolist(), strict=False
        )
    }

    metrics: dict[str, Any] = {
        "model_version": model.metadata.version,
        "probability": prediction.probability,
        "data_points": int(output.time.size),
        "feature_vector": feature_vector,
        "signal_depth": prediction.features.depth,
        "signal_snr": prediction.features.depth_snr,
        "transit_ratio": prediction.features.transit_ratio,
        "estimated_period_days": prediction.features.dominant_period,
        "trend_slope": prediction.features.trend_slope,
    }

    return metrics


@router.post("/", response_model=AnalysisResponse)
async def analyze_light_curve(file: Annotated[UploadFile, File()]) -> AnalysisResponse:
    """Analyze uploaded light curve for exoplanet detection."""
    start_time = time.time()

    # Validate file
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Supported: .csv, .txt"
        )

    # Generate unique analysis ID
    analysis_id = str(uuid.uuid4())

    try:
        # Read file content
        file_content = await file.read()

        # Save uploaded file
        file_path = UPLOAD_DIR / f"{analysis_id}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Parse light curve data
        light_curve_data = parse_light_curve_file(file_content, file.filename)

        time_array = np.asarray(light_curve_data["time"], dtype=np.float64)
        flux_array = np.asarray(light_curve_data["flux"], dtype=np.float64)

        model_output = run_model_inference(time_array, flux_array)
        prediction = model_output.prediction

        confidence = round(prediction.probability * 100, 2)
        reasons = _build_reasons(prediction)
        orbital_period_raw = prediction.features.dominant_period
        orbital_period = float(orbital_period_raw) if orbital_period_raw > 0 else None

        result = AnalysisResult(
            exoplanet_detected=prediction.exoplanet_detected,
            confidence=confidence,
            transit_depth=prediction.features.depth,
            orbital_period=orbital_period,
            label=prediction.label,
            reasons=reasons,
        )

        plots = generate_plots(model_output)
        metrics = _build_metrics(model_output)

        processing_time = time.time() - start_time

        return AnalysisResponse(
            analysis_id=analysis_id,
            filename=file.filename,
            result=result,
            plots=plots,
            metrics=metrics,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e


@router.post("/tic/{tic_id}")
async def analyze_tic_id(tic_id: str) -> AnalysisResponse:
    """Analyze TESS light curve by TIC ID."""
    # TODO: Implement TIC ID lookup and analysis with MAST API
    raise HTTPException(status_code=501, detail="TIC ID analysis not yet implemented")


@router.post("/batch")
async def analyze_batch(files: list[UploadFile]) -> dict[str, Any]:
    """Analyze multiple light curve files."""
    if len(files) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Batch size limited to 10 files")

    results = []
    total_start_time = time.time()

    for file in files:
        try:
            # Reuse single file analysis
            result = await analyze_light_curve(file)
            results.append(
                {"filename": file.filename, "success": True, "result": result}
            )
        except Exception as e:
            logger.error(f"Batch analysis error for {file.filename}: {e}")
            results.append(
                {"filename": file.filename, "success": False, "error": str(e)}
            )

    total_processing_time = time.time() - total_start_time

    return {
        "batch_id": str(uuid.uuid4()),
        "total_files": len(files),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results,
        "total_processing_time": total_processing_time,
    }

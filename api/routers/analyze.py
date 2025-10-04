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


class ExoplanetPredictor:
    """Simplified exoplanet detection using transit analysis."""

    def __init__(self) -> None:
        """Initialize the exoplanet predictor."""
        self.model_loaded = True
        logger.info("ExoplanetPredictor initialized")

    def predict(self, light_curve_data: dict[str, Any]) -> dict[str, Any]:
        """Predict exoplanet presence from light curve data."""
        try:
            # Extract time and flux arrays
            time_array = np.array(light_curve_data.get("time", []))
            flux_array = np.array(light_curve_data.get("flux", []))

            if len(time_array) == 0 or len(flux_array) == 0:
                raise ValueError("Empty time or flux arrays")

            # Normalize flux
            flux_normalized = (flux_array - np.median(flux_array)) / np.median(
                flux_array
            )

            # Simple transit detection using moving window
            prediction = self._detect_transits(time_array, flux_normalized)

            # Add data for plotting
            prediction["time"] = time_array.tolist()
            prediction["flux"] = flux_normalized.tolist()

            return prediction

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                "exoplanet_detected": False,
                "confidence": 0.0,
                "transit_depth": 0.0,
                "orbital_period": 0.0,
                "label": "error",
                "reasons": [f"Analysis failed: {str(e)}"],
                "time": [],
                "flux": [],
            }

    def _detect_transits(self, time: np.ndarray[Any, np.dtype[np.float64]], flux: np.ndarray[Any, np.dtype[np.float64]]) -> dict[str, Any]:
        """Detect transits in normalized flux data."""
        try:
            # Calculate basic statistics
            flux_std = np.std(flux)

            # Look for significant dips (potential transits)
            dip_threshold = -3 * flux_std  # 3-sigma below mean
            transit_candidates = flux < dip_threshold

            if np.any(transit_candidates):
                # Count number of potential transit points
                transit_points = np.sum(transit_candidates)
                total_points = len(flux)

                # Estimate transit depth (maximum dip)
                transit_depth = abs(np.min(flux))

                # Simple period estimation (time between first and last transit)
                transit_indices = np.where(transit_candidates)[0]
                if len(transit_indices) > 1:
                    time_span = time[transit_indices[-1]] - time[transit_indices[0]]
                    estimated_period = time_span / max(1, len(transit_indices) - 1)
                else:
                    estimated_period = 0.0

                # Calculate confidence based on transit depth and regularity
                confidence = min(95.0, (transit_depth / flux_std) * 20)

                exoplanet_detected = confidence > 50.0

                reasons = []
                if exoplanet_detected:
                    reasons.append(f"Transit depth detected: {transit_depth:.4f}")
                    reasons.append(f"Transit points: {transit_points}/{total_points}")
                    if estimated_period > 0:
                        reasons.append(f"Estimated period: {estimated_period:.2f} days")
                else:
                    reasons.append("No significant transits detected")

                return {
                    "exoplanet_detected": exoplanet_detected,
                    "confidence": round(float(confidence), 1),
                    "transit_depth": round(float(transit_depth), 6),
                    "orbital_period": round(float(estimated_period), 2),
                    "label": "planet" if exoplanet_detected else "non-planet",
                    "reasons": reasons,
                }
            else:
                return {
                    "exoplanet_detected": False,
                    "confidence": 0.0,
                    "transit_depth": 0.0,
                    "orbital_period": 0.0,
                    "label": "non-planet",
                    "reasons": ["No transit signatures detected"],
                }

        except Exception as e:
            logger.error(f"Transit detection error: {e}")
            return {
                "exoplanet_detected": False,
                "confidence": 0.0,
                "transit_depth": 0.0,
                "orbital_period": 0.0,
                "label": "error",
                "reasons": [f"Transit detection failed: {str(e)}"],
            }


# Initialize predictor
predictor = ExoplanetPredictor()


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


def generate_plots(prediction_data: dict[str, Any], analysis_id: str) -> dict[str, str]:
    """Generate analysis plots and return as base64 encoded strings."""
    plots: dict[str, str] = {}

    try:
        time_data = np.array(prediction_data.get("time", []))
        flux_data = np.array(prediction_data.get("flux", []))

        if len(time_data) == 0 or len(flux_data) == 0:
            logger.warning("No data available for plotting")
            return plots

        # 1. Light curve plot
        plt.figure(figsize=(12, 6))
        plt.plot(time_data, flux_data, "b.", markersize=2, alpha=0.7)
        plt.xlabel("Time (days)")
        plt.ylabel("Normalized Flux")
        plt.title("Light Curve")
        plt.grid(True, alpha=0.3)

        # Highlight transits if detected
        if prediction_data.get("exoplanet_detected", False):
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

        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buffer.seek(0)
        plots["light_curve"] = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # 2. Phase-folded plot (if period detected)
        period = prediction_data.get("orbital_period", 0)
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
        # Simple rolling mean for trend
        if len(flux_data) > 10:
            window = min(len(flux_data) // 10, 100)
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
        if len(flux_data) > 10:
            freq = np.fft.fftfreq(len(flux_data), d=np.median(np.diff(time_data)))
            power = np.abs(np.fft.fft(flux_data - np.mean(flux_data))) ** 2
            # Only plot positive frequencies
            pos_mask = freq > 0
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
Points: {len(flux_data)}

Detection:
Confidence: {prediction_data.get("confidence", 0):.1f}%
Depth: {prediction_data.get("transit_depth", 0):.6f}
Period: {prediction_data.get("orbital_period", 0):.2f} d"""

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

    # Convert to data URLs
    for plot_name, plot_data in plots.items():
        plots[plot_name] = f"data:image/png;base64,{plot_data}"

    return plots


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

        # Run prediction
        prediction = predictor.predict(light_curve_data)

        # Create analysis result
        result = AnalysisResult(
            exoplanet_detected=prediction["exoplanet_detected"],
            confidence=prediction["confidence"],
            transit_depth=prediction["transit_depth"],
            orbital_period=prediction["orbital_period"],
            label=prediction["label"],
            reasons=prediction["reasons"],
        )

        # Generate plots
        plots = generate_plots(prediction, analysis_id)

        # Calculate metrics
        metrics = {
            "snr": prediction.get("confidence", 0) / 10,  # Simple SNR approximation
            "duration": 0.0,  # Would need more sophisticated analysis
            "depth": prediction["transit_depth"],
            "period": prediction["orbital_period"],
            "data_points": len(prediction.get("time", [])),
        }

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

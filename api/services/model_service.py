"""Adapters for invoking the ML model from the API layer."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ML_SRC_PATH = Path(__file__).resolve().parents[2] / "ml" / "src"
if str(ML_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(ML_SRC_PATH))

# ruff: noqa: E402 - Need to add ML path before importing
from detection.model import (  # type: ignore[import-not-found]
    ExoplanetModel,
    PredictionResult,
)
from detection.types import LightCurve  # type: ignore[import-not-found]


@dataclass(frozen=True)
class ModelOutput:
    """Container for the model prediction and the processed light curve."""

    prediction: PredictionResult
    time: np.ndarray[Any, np.dtype[np.float64]]
    normalized_flux: np.ndarray[Any, np.dtype[np.float64]]
    raw_flux: np.ndarray[Any, np.dtype[np.float64]]


_MODEL: ExoplanetModel | None = None


def get_model() -> ExoplanetModel:
    """Return a singleton instance of the ML model."""

    global _MODEL
    if _MODEL is None:
        _MODEL = ExoplanetModel(auto_train=True)
    return _MODEL


def analyze_light_curve(
    time: np.ndarray[Any, np.dtype[np.float64]],
    flux: np.ndarray[Any, np.dtype[np.float64]],
) -> ModelOutput:
    """Run the ML model on a light curve."""

    model = get_model()
    light_curve = (
        LightCurve.from_sequences(time, flux).clip_non_finite().ensure_sorted()
    )
    prediction = model.predict(light_curve)

    normalized_flux = _normalize_flux(light_curve.flux)

    return ModelOutput(
        prediction=prediction,
        time=light_curve.time,
        normalized_flux=normalized_flux,
        raw_flux=light_curve.flux,
    )


def _normalize_flux(
    flux: np.ndarray[Any, np.dtype[np.float64]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Normalize flux data by median and return proper ndarray type."""
    median = float(np.median(flux))
    result: np.ndarray[Any, np.dtype[np.float64]]
    if np.isclose(median, 0.0):
        result = flux - np.mean(flux)
    else:
        result = (flux - median) / (median + 1e-8)
    return result


__all__ = [
    "analyze_light_curve",
    "get_model",
    "ModelOutput",
    "PredictionResult",
]

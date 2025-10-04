"""Adapters for invoking the ML model from the API layer."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

ML_SRC_PATH = Path(__file__).resolve().parents[2] / "ml" / "src"
if str(ML_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(ML_SRC_PATH))

from detection.model import ExoplanetModel, PredictionResult  # type: ignore[import]
from detection.types import LightCurve  # type: ignore[import]


@dataclass(frozen=True)
class ModelOutput:
    """Container for the model prediction and the processed light curve."""

    prediction: PredictionResult
    time: np.ndarray
    normalized_flux: np.ndarray
    raw_flux: np.ndarray


_MODEL: ExoplanetModel | None = None


def get_model() -> ExoplanetModel:
    """Return a singleton instance of the ML model."""

    global _MODEL
    if _MODEL is None:
        _MODEL = ExoplanetModel(auto_train=True)
    return _MODEL


def analyze_light_curve(time: np.ndarray, flux: np.ndarray) -> ModelOutput:
    """Run the ML model on a light curve."""

    model = get_model()
    light_curve = LightCurve.from_sequences(time, flux).clip_non_finite().ensure_sorted()
    prediction = model.predict(light_curve)

    normalized_flux = _normalize_flux(light_curve.flux)

    return ModelOutput(
        prediction=prediction,
        time=light_curve.time,
        normalized_flux=normalized_flux,
        raw_flux=light_curve.flux,
    )


def _normalize_flux(flux: np.ndarray) -> np.ndarray:
    median = float(np.median(flux))
    if np.isclose(median, 0.0):
        return flux - np.mean(flux)
    return (flux - median) / (median + 1e-8)


__all__ = [
    "analyze_light_curve",
    "get_model",
    "ModelOutput",
    "PredictionResult",
]

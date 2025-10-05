"""Model orchestration for exoplanet classification."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import joblib  # type: ignore[import-untyped]
import numpy as np
from numpy.typing import NDArray
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from .features import FEATURE_NAMES, LightCurveFeatures, extract_features
from .training import train_default_model
from .types import LightCurve

logger = logging.getLogger(__name__)

_MODEL_FILENAME: Final[str] = "exoplanet_classifier.joblib"
_THRESHOLD: Final[float] = 0.55


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata describing the loaded classifier."""

    version: str
    feature_names: tuple[str, ...]


@dataclass(frozen=True)
class PredictionResult:
    """Prediction output from the classifier."""

    probability: float
    label: str
    features: LightCurveFeatures

    @property
    def exoplanet_detected(self) -> bool:
        return self.label == "planet"


class ExoplanetModel:
    """Wrapper around the underlying scikit-learn pipeline."""

    def __init__(
        self,
        *,
        artifact_path: Path | None = None,
        auto_train: bool = True,
        random_state: int = 7,
    ) -> None:
        self._artifact_path = artifact_path or self._default_artifact_path()
        self._random_state = random_state
        self._metadata = ModelMetadata(
            version="0.1.0", feature_names=tuple(FEATURE_NAMES)
        )
        self._estimator = self._load_or_train(auto_train=auto_train)

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    def predict(self, light_curve: LightCurve) -> PredictionResult:
        """Generate prediction for a light curve."""

        features = extract_features(light_curve)
        feature_vector: NDArray[np.float64] = features.as_array().reshape(1, -1)
        probabilities = self._estimator.predict_proba(feature_vector)[0]
        positive_probability = float(probabilities[1])
        label = "planet" if positive_probability >= _THRESHOLD else "non-planet"
        return PredictionResult(
            probability=positive_probability, label=label, features=features
        )

    def _load_or_train(self, *, auto_train: bool) -> Pipeline:
        if self._artifact_path.exists():
            logger.info("Loading ML model from %%s", self._artifact_path)
            return joblib.load(self._artifact_path)

        if not auto_train:
            raise FileNotFoundError(f"Model artifact missing at {self._artifact_path}")

        logger.info(
            "Training new ML model because no artifact was found at %%s",
            self._artifact_path,
        )
        self._artifact_path.parent.mkdir(parents=True, exist_ok=True)
        estimator = train_default_model(
            self._artifact_path, random_state=self._random_state
        )
        return estimator

    @staticmethod
    def _default_artifact_path() -> Path:
        return Path(__file__).resolve().parents[2] / "artifacts" / _MODEL_FILENAME


__all__ = ["ExoplanetModel", "PredictionResult", "ModelMetadata"]

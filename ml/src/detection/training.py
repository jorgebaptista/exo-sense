"""Training utilities for the exoplanet classifier."""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

import joblib  # type: ignore[import-untyped]
import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-untyped]
from sklearn.metrics import classification_report  # type: ignore[import-untyped]
from sklearn.model_selection import train_test_split  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from data import ingest_light_curves, load_catalog

from .features import FEATURE_NAMES, extract_features
from .simulation import SimulationConfig, simulate_light_curve

logger = logging.getLogger(__name__)


_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
_CURATED_CATALOG = _DATA_ROOT / "kepler_curated_catalog.csv"
_CURVE_DIRECTORY = _DATA_ROOT / "light_curves"

_DISPOSITION_LABELS = {
    "confirmed": 1,
    "pc": 1,
    "planet candidate": 1,
    "kp": 1,
    "fp": 0,
    "false positive": 0,
    "fa": 0,
}


def build_training_dataset(
    *,
    random_state: int,
    synthetic_samples: int = 400,
    include_real: bool = True,
    min_curve_samples: int = 400,
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Assemble the feature matrix used for model training.

    Real Kepler light curves are ingested via the data pipeline when available
    and augmented with simulated samples to provide class balance.
    """

    feature_blocks: list[NDArray[np.float64]] = []
    label_blocks: list[NDArray[np.int64]] = []

    if include_real:
        X_real, y_real = _load_real_dataset(min_curve_samples=min_curve_samples)
        if y_real.size > 0:
            feature_blocks.append(X_real)
            label_blocks.append(y_real)
            logger.info("Loaded %d real light curves for training", y_real.size)
        else:
            logger.warning("No real light curves available; proceeding without them")

    if synthetic_samples > 0:
        X_syn, y_syn = _generate_dataset(random_state=random_state, samples=synthetic_samples)
        feature_blocks.append(X_syn)
        label_blocks.append(y_syn)
        logger.info("Generated %d synthetic samples", y_syn.size)

    if not feature_blocks:
        raise RuntimeError("No training data available; check dataset configuration")

    X = np.vstack(feature_blocks)
    y = np.concatenate(label_blocks)

    distribution = Counter(int(label) for label in y)
    logger.info("Training set class distribution (label -> count): %s", dict(distribution))

    return X, y


def train_default_model(
    artifact_path: Path,
    *,
    random_state: int = 7,
    synthetic_samples: int = 400,
    include_real: bool = True,
) -> Pipeline:
    """Train the baseline classifier and persist the artifact."""

    X, y = build_training_dataset(
        random_state=random_state,
        synthetic_samples=synthetic_samples,
        include_real=include_real,
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=random_state
    )

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=180,
                    max_depth=6,
                    min_samples_leaf=6,
                    random_state=random_state,
                    class_weight="balanced",
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    report = classification_report(y_test, y_pred, target_names=["non-planet", "planet"])
    logger.info("Synthetic validation report:\n%s", report)

    joblib.dump(pipeline, artifact_path)
    logger.info("Saved trained model to %s", artifact_path)

    return pipeline


def _generate_dataset(*, random_state: int, samples: int) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    generator = np.random.default_rng(random_state)
    config = SimulationConfig()

    feature_vectors: list[NDArray[np.float64]] = []
    labels: list[int] = []

    for _ in range(samples):
        has_transit = bool(generator.integers(0, 2))
        curve = simulate_light_curve(generator=generator, has_transit=has_transit, config=config)
        features = extract_features(curve)
        feature_vectors.append(features.as_array())
        labels.append(int(has_transit))

    X = np.vstack(feature_vectors)
    y = np.asarray(labels, dtype=np.int64)
    return X, y


def _load_real_dataset(*, min_curve_samples: int) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    if not _CURATED_CATALOG.exists() or not _CURVE_DIRECTORY.exists():
        logger.warning("Curated catalog or light-curve directory missing; skipping real data")
        return (
            np.empty((0, len(FEATURE_NAMES)), dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )

    try:
        catalog = load_catalog(
            _CURATED_CATALOG,
            survey="kepler",
            target_column="target_id",
            disposition_column="disposition",
            label_map=_DISPOSITION_LABELS,
            comment="#",
        )
    except Exception as exc:  # pragma: no cover - unexpected during CI
        logger.warning("Failed to load curated catalog: %s", exc)
        return (
            np.empty((0, len(FEATURE_NAMES)), dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )

    if not catalog:
        logger.warning("Curated catalog produced no records; skipping real data")
        return (
            np.empty((0, len(FEATURE_NAMES)), dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )

    ingested = ingest_light_curves(
        catalog,
        curve_dir=_CURVE_DIRECTORY,
        filename_column="filename",
        min_samples=min_curve_samples,
    )

    if not ingested:
        logger.warning("Curated catalog yielded no usable light curves")
        return (
            np.empty((0, len(FEATURE_NAMES)), dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )

    features = [extract_features(sample.curve).as_array() for sample in ingested]
    labels = [sample.label for sample in ingested]

    X = np.vstack(features)
    y = np.asarray(labels, dtype=np.int64)
    return X, y


__all__ = ["build_training_dataset", "train_default_model"]

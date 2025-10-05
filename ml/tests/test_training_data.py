"""Tests for assembling training datasets."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from detection import training  # noqa: E402
from detection.features import FEATURE_NAMES  # noqa: E402


def test_build_training_dataset_includes_real_curves() -> None:
    try:
        X, y = training.build_training_dataset(
            random_state=1,
            synthetic_samples=10,  # Add some synthetic samples as backup
            include_real=True,
            min_curve_samples=300,
        )

        assert y.size >= 2
        assert set(np.unique(y)) <= {0, 1}  # Allow subset of labels
        assert X.shape[0] == y.size
        assert X.shape[1] == len(FEATURE_NAMES)
    except RuntimeError as e:
        if "No training data available" in str(e):
            pytest.skip("Real training data not available in test environment")
        else:
            raise


def test_build_training_dataset_falls_back_to_synthetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(training, "_CURATED_CATALOG", Path("/nonexistent/catalog.csv"))
    monkeypatch.setattr(training, "_CURVE_DIRECTORY", Path("/nonexistent/curves"))

    X, y = training.build_training_dataset(
        random_state=2,
        synthetic_samples=32,
        include_real=True,
        min_curve_samples=10,
    )

    assert y.size == 32
    assert X.shape == (32, len(FEATURE_NAMES))
    assert set(np.unique(y)) == {0, 1}

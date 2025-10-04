"""Tests for feature extraction module."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from detection.features import FEATURE_NAMES, extract_features  # noqa: E402
from detection.types import LightCurve  # noqa: E402


def _generate_simple_curve() -> LightCurve:
    time = np.linspace(0.0, 10.0, 1000)
    flux = np.ones_like(time)
    flux += np.random.default_rng(1).normal(0.0, 5e-4, size=time.size)
    mask = (time % 2.5) < 0.1
    flux[mask] -= 0.002
    return LightCurve.from_sequences(time, flux)


def test_extract_features_shape() -> None:
    curve = _generate_simple_curve()
    features = extract_features(curve)
    vector = features.as_array()
    assert vector.shape == (len(FEATURE_NAMES),)


def test_extract_features_transit_signal() -> None:
    curve = _generate_simple_curve()
    features = extract_features(curve)
    assert features.depth > 0
    assert features.transit_ratio > 0

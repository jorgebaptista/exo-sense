"""Smoke tests for the exoplanet classifier."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from detection.model import ExoplanetModel  # noqa: E402
from detection.simulation import SimulationConfig, simulate_light_curve  # noqa: E402


def test_model_predicts_probability() -> None:
    generator = np.random.default_rng(4)
    config = SimulationConfig(duration_days=20.0)
    curve = simulate_light_curve(generator=generator, has_transit=True, config=config)

    model = ExoplanetModel(auto_train=True, random_state=3)
    prediction = model.predict(curve)

    assert 0.0 <= prediction.probability <= 1.0
    assert prediction.features.depth >= 0.0
    assert prediction.label in {"planet", "non-planet"}


def test_model_distinguishes_signals() -> None:
    generator = np.random.default_rng(8)
    config = SimulationConfig(duration_days=22.0)

    planet_curve = simulate_light_curve(
        generator=generator, has_transit=True, config=config
    )
    noise_curve = simulate_light_curve(
        generator=generator, has_transit=False, config=config
    )

    model = ExoplanetModel(auto_train=True, random_state=3)
    planet_prob = model.predict(planet_curve).probability
    noise_prob = model.predict(noise_curve).probability

    assert planet_prob > noise_prob

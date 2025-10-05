"""Unit tests for the model service adapter."""

from __future__ import annotations

import numpy as np

from services import model_service


def test_analyze_light_curve_returns_output() -> None:
    time = np.linspace(0.0, 10.0, 1000)
    flux = np.ones_like(time)
    flux += np.random.default_rng(3).normal(0.0, 4e-4, size=time.size)
    mask = (time % 2.2) < 0.1
    flux[mask] -= 0.002

    output = model_service.analyze_light_curve(time, flux)

    assert output.time.shape == time.shape
    assert output.normalized_flux.shape == flux.shape
    assert 0.0 <= output.prediction.probability <= 1.0
    assert output.prediction.label in {"planet", "non-planet"}

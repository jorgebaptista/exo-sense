"""Synthetic light curve generation utilities for training and testing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .types import LightCurve


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration for synthetic light-curve generation."""

    duration_days: float = 27.0
    cadence_minutes: float = 2.0
    noise_level: float = 5e-4
    stellar_variability: float = 2.5e-4


def simulate_light_curve(
    *, generator: np.random.Generator, has_transit: bool, config: SimulationConfig
) -> LightCurve:
    """Generate a synthetic light curve with or without a planetary transit."""

    cadence_days = config.cadence_minutes / (24.0 * 60.0)
    n_points = int(config.duration_days / cadence_days)
    time = np.linspace(0.0, config.duration_days, n_points, dtype=np.float64)

    flux = np.ones_like(time)
    flux += generator.normal(0.0, config.noise_level, size=n_points)

    rotation_period = generator.uniform(8.0, 18.0)
    flux += config.stellar_variability * np.sin(2 * np.pi * time / rotation_period)

    if has_transit:
        period = generator.uniform(1.0, 14.0)
        depth = generator.uniform(5e-4, 3.5e-3)
        duration = generator.uniform(0.05, 0.25)
        phase = generator.uniform(0.0, period)

        cycle_indices = np.mod(time - phase, period) < duration
        flux[cycle_indices] -= depth

        if generator.random() < 0.3:
            depth_secondary = depth * generator.uniform(0.3, 0.6)
            secondary_phase = phase + period / 2.0
            secondary_indices = np.mod(time - secondary_phase, period) < duration
            flux[secondary_indices] -= depth_secondary
    else:
        if generator.random() < 0.5:
            flare_center = generator.uniform(2.0, config.duration_days - 2.0)
            flare_width = generator.uniform(0.05, 0.2)
            flare_height = generator.uniform(5e-4, 2e-3)
            flux += flare_height * np.exp(
                -0.5 * ((time - flare_center) / flare_width) ** 2
            )

    return LightCurve.from_sequences(time, flux)


__all__ = ["SimulationConfig", "simulate_light_curve"]

"""Demo data and cached examples for ExoSense."""

from typing import Any

import numpy as np

# Demo TIC IDs with known exoplanets for testing
DEMO_TARGETS: dict[str, dict[str, Any]] = {
    "TIC-261136679": {
        "name": "TOI-715 b",
        "description": "Super-Earth exoplanet",
        "period": 19.3,
        "depth": 0.0008,
        "confidence": 92.5,
    },
    "TIC-307210830": {
        "name": "TOI-849 b",
        "description": "Hot Neptune",
        "period": 0.765,
        "depth": 0.0015,
        "confidence": 88.2,
    },
    "TIC-38846515": {
        "name": "TOI-451 b",
        "description": "Young hot Jupiter",
        "period": 1.86,
        "depth": 0.012,
        "confidence": 95.1,
    },
    "TIC-425933644": {
        "name": "TOI-1338 b",
        "description": "Circumbinary planet",
        "period": 95.2,
        "depth": 0.002,
        "confidence": 78.9,
    },
}


def generate_mock_light_curve(
    tic_id: str, duration_days: float = 30.0, cadence_minutes: float = 2.0
) -> dict[str, Any]:
    """Generate mock light curve data for demo purposes."""
    if tic_id not in DEMO_TARGETS:
        raise ValueError(f"Unknown TIC ID: {tic_id}")

    target = DEMO_TARGETS[tic_id]

    # Time array
    cadence_days = cadence_minutes / (24.0 * 60.0)
    n_points = int(duration_days / cadence_days)
    time = np.linspace(0, duration_days, n_points)

    # Base flux with noise
    flux = np.ones(n_points) + np.random.normal(0, 0.0001, n_points)

    # Add periodic transits
    period = float(target["period"])
    depth = float(target["depth"])
    transit_duration = 0.1  # Transit duration in days

    # Find transit times
    n_transits = int(duration_days / period)
    for i in range(n_transits):
        transit_center = i * period
        # Create box-shaped transit
        in_transit = np.abs(time - transit_center) < transit_duration / 2.0
        flux[in_transit] -= depth

    # Add some stellar variability
    stellar_period = period * 7.3  # Stellar rotation
    stellar_amplitude = 0.0002
    flux += stellar_amplitude * np.sin(2 * np.pi * time / stellar_period)

    return {
        "time": time.tolist(),
        "flux": flux.tolist(),
        "target_info": target,
        "tic_id": tic_id,
    }


def get_demo_analysis_result(tic_id: str) -> dict[str, Any] | None:
    """Get pre-computed analysis result for demo TIC ID."""
    if tic_id not in DEMO_TARGETS:
        return None

    target = DEMO_TARGETS[tic_id]

    return {
        "exoplanet_detected": True,
        "confidence": target["confidence"],
        "transit_depth": target["depth"],
        "orbital_period": target["period"],
        "label": "planet",
        "reasons": [
            f"Periodic transits detected with period {target['period']:.2f} days",
            f"Transit depth {target['depth']:.4f} consistent with planetary signal",
            "Odd/even transit test passed",
            "No significant secondary eclipse detected",
        ],
    }

"""Core data structures for light-curve based modelling."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

NDArrayFloat = NDArray[np.float64]


@dataclass(frozen=True)
class LightCurve:
    """Simple representation of a light curve.

    The object stores time and flux arrays (float64) with identical length.
    """

    time: NDArrayFloat
    flux: NDArrayFloat

    @classmethod
    def from_sequences(
        cls,
        time: Sequence[float] | NDArrayFloat,
        flux: Sequence[float] | NDArrayFloat,
    ) -> LightCurve:
        """Create a light curve from generic sequences.

        Args:
            time: Sequence of time stamps (days).
            flux: Sequence of flux values (normalized or relative).
        """
        time_array = _to_float_array(time)
        flux_array = _to_float_array(flux)

        if time_array.size == 0:
            raise ValueError("Time array cannot be empty")
        if flux_array.size == 0:
            raise ValueError("Flux array cannot be empty")
        if time_array.size != flux_array.size:
            raise ValueError("Time and flux arrays must have the same length")

        return cls(time=time_array, flux=flux_array)

    @property
    def sample_count(self) -> int:
        """Number of samples in the light curve."""

        return int(self.time.size)

    def ensure_sorted(self) -> LightCurve:
        """Return a copy where time is strictly increasing."""

        if np.all(np.diff(self.time) >= 0):
            return self

        order = np.argsort(self.time)
        return LightCurve(time=self.time[order], flux=self.flux[order])

    def clip_non_finite(self) -> LightCurve:
        """Return copy with only finite samples."""

        mask = np.isfinite(self.time) & np.isfinite(self.flux)
        if not np.any(mask):
            raise ValueError("No finite samples in light curve")
        return LightCurve(time=self.time[mask], flux=self.flux[mask])


def _to_float_array(values: Sequence[float] | NDArrayFloat) -> NDArrayFloat:
    """Convert sequence-like inputs to float64 numpy arrays."""

    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError("Light curve inputs must be 1-dimensional")
    return array


__all__ = ["LightCurve", "NDArrayFloat"]

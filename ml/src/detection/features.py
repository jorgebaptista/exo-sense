"""Feature engineering for light curve based exoplanet classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np

try:  # pragma: no cover - dependency presence is validated at import time
    from scipy import signal, stats
except ImportError as exc:  # pragma: no cover
    raise ImportError("scipy is required for feature extraction") from exc

from .types import LightCurve, NDArrayFloat

_EPS: Final[float] = 1e-8


@dataclass(frozen=True)
class LightCurveFeatures:
    """Numerical descriptors summarising a light curve."""

    mean_flux: float
    median_flux: float
    std_flux: float
    min_flux: float
    max_flux: float
    trend_slope: float
    depth: float
    depth_snr: float
    transit_ratio: float
    auto_corr_lag1: float
    auto_corr_lag5: float
    peak_power: float
    dominant_period: float
    skewness: float
    kurtosis: float

    def as_array(self) -> NDArrayFloat:
        """Return feature vector as numpy array."""

        return np.array(
            [
                self.mean_flux,
                self.median_flux,
                self.std_flux,
                self.min_flux,
                self.max_flux,
                self.trend_slope,
                self.depth,
                self.depth_snr,
                self.transit_ratio,
                self.auto_corr_lag1,
                self.auto_corr_lag5,
                self.peak_power,
                self.dominant_period,
                self.skewness,
                self.kurtosis,
            ],
            dtype=np.float64,
        )


FEATURE_NAMES: Final[list[str]] = [
    "mean_flux",
    "median_flux",
    "std_flux",
    "min_flux",
    "max_flux",
    "trend_slope",
    "depth",
    "depth_snr",
    "transit_ratio",
    "auto_corr_lag1",
    "auto_corr_lag5",
    "peak_power",
    "dominant_period",
    "skewness",
    "kurtosis",
]


def extract_features(light_curve: LightCurve) -> LightCurveFeatures:
    """Compute feature vector from a light curve.

    The function performs basic detrending, computes transit statistics and
    characterises the variability spectrum via FFT power ratios.
    """

    cleaned = light_curve.clip_non_finite().ensure_sorted()
    time = cleaned.time
    flux = cleaned.flux

    normalized = _normalize_flux(flux)

    mean_flux = float(np.mean(normalized))
    median_flux = float(np.median(normalized))
    std_flux = float(np.std(normalized))
    min_flux = float(np.min(normalized))
    max_flux = float(np.max(normalized))

    trend_slope = _estimate_trend(time, normalized)
    depth, depth_snr, transit_ratio = _detect_transits(normalized)
    auto_corr_lag1 = _autocorr(normalized, lag=1)
    auto_corr_lag5 = _autocorr(normalized, lag=5)
    peak_power, dominant_period = _periodic_signature(time, normalized)

    if normalized.size >= 3:
        skewness = float(stats.skew(normalized, bias=False))
    else:
        skewness = 0.0

    if normalized.size >= 4:
        kurtosis = float(stats.kurtosis(normalized, fisher=True, bias=False))
    else:
        kurtosis = 0.0

    skewness = float(np.nan_to_num(skewness))
    kurtosis = float(np.nan_to_num(kurtosis))

    return LightCurveFeatures(
        mean_flux=mean_flux,
        median_flux=median_flux,
        std_flux=std_flux,
        min_flux=min_flux,
        max_flux=max_flux,
        trend_slope=trend_slope,
        depth=depth,
        depth_snr=depth_snr,
        transit_ratio=transit_ratio,
        auto_corr_lag1=auto_corr_lag1,
        auto_corr_lag5=auto_corr_lag5,
        peak_power=peak_power,
        dominant_period=dominant_period,
        skewness=skewness,
        kurtosis=kurtosis,
    )


def _normalize_flux(flux: NDArrayFloat) -> NDArrayFloat:
    median = np.median(flux)
    if np.isclose(median, 0.0):
        centered = flux.astype(np.float64) - np.mean(flux)
        return centered
    return (flux - median) / (median + _EPS)


def _estimate_trend(time: NDArrayFloat, flux: NDArrayFloat) -> float:
    if time.size < 2:
        return 0.0
    slope, _ = np.polyfit(time, flux, deg=1)
    return float(slope)


def _detect_transits(flux: NDArrayFloat) -> tuple[float, float, float]:
    std_flux = np.std(flux) + _EPS
    median_flux = float(np.median(flux))
    dips = flux < (median_flux - 2.5 * std_flux)

    if not np.any(dips):
        return 0.0, 0.0, 0.0

    depth = float(np.abs(np.min(flux) - median_flux))
    depth_snr = float(depth / std_flux)
    transit_ratio = float(np.sum(dips) / flux.size)
    return depth, depth_snr, transit_ratio


def _autocorr(flux: NDArrayFloat, lag: int) -> float:
    if flux.size <= lag:
        return 0.0
    flux_centered = flux - np.mean(flux)
    numerator = np.dot(flux_centered[:-lag], flux_centered[lag:])
    denominator = np.dot(flux_centered, flux_centered) + _EPS
    return float(numerator / denominator)


def _periodic_signature(time: NDArrayFloat, flux: NDArrayFloat) -> tuple[float, float]:
    if time.size < 10:
        return 0.0, 0.0

    cadence = np.median(np.diff(time))
    if cadence <= 0:
        return 0.0, 0.0

    detrended = flux - np.mean(flux)
    freqs, power = signal.periodogram(detrended, fs=1.0 / cadence, scaling="spectrum")

    if freqs.size == 0:
        return 0.0, 0.0

    valid = freqs > 0
    if not np.any(valid):
        return 0.0, 0.0

    freqs = freqs[valid]
    power = power[valid]

    peak_idx = int(np.argmax(power))
    peak_power = float(power[peak_idx])
    dominant_period = float(1.0 / freqs[peak_idx]) if freqs[peak_idx] > 0 else 0.0

    total_power = float(np.sum(power)) + _EPS
    peak_ratio = peak_power / total_power

    return peak_ratio, dominant_period


__all__ = ["LightCurveFeatures", "FEATURE_NAMES", "extract_features"]

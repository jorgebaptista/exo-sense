"""Tests for utility functions."""

import numpy as np
import pytest

from utils import compute_rms


def test_compute_rms_simple() -> None:
    """Test RMS computation with simple data."""
    data = np.array([1.0, 2.0, 3.0])
    expected = np.sqrt((1**2 + 2**2 + 3**2) / 3)
    result = compute_rms(data)
    assert abs(result - expected) < 1e-10


def test_compute_rms_zeros() -> None:
    """Test RMS computation with zeros."""
    data = np.array([0.0, 0.0, 0.0])
    result = compute_rms(data)
    assert result == 0.0


def test_compute_rms_negative() -> None:
    """Test RMS computation with negative values."""
    data = np.array([-1.0, 1.0, -2.0, 2.0])
    expected = np.sqrt((1 + 1 + 4 + 4) / 4)
    result = compute_rms(data)
    assert abs(result - expected) < 1e-10
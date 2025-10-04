"""Utility functions for ML operations."""

from typing import Any

import numpy as np


def compute_rms(data: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
    """Compute root mean square of data array.

    Args:
        data: Input data array

    Returns:
        RMS value
    """
    return float(np.sqrt(np.mean(data**2)))

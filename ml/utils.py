"""Utility functions for mathematical operations."""

import numpy as np


def compute_rms(data: np.ndarray) -> float:
    """Compute root mean square of data array.

    Args:
        data: Input data array

    Returns:
        RMS value
    """
    return float(np.sqrt(np.mean(data**2)))

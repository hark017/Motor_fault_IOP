"""Feature engineering used by the trained models."""

from __future__ import annotations

import numpy as np


FEATURE_NAMES = (
    "I1",
    "I2",
    "I3",
    "I_sum",
    "I_max_abs",
    "I_min_abs",
    "I_range_abs",
    "I_std",
)


def build_feature_vector(i1: float, i2: float, i3: float) -> np.ndarray:
    """Build the exact 8-feature vector expected by the saved scaler/models."""
    values = np.array([i1, i2, i3], dtype=np.float32)
    abs_values = np.abs(values)
    i_sum = float(np.sum(values))
    i_max = float(np.max(abs_values))
    i_min = float(np.min(abs_values))
    i_range = i_max - i_min
    i_std = float(np.std(values))

    return np.array(
        [[i1, i2, i3, i_sum, i_max, i_min, i_range, i_std]],
        dtype=np.float32,
    )

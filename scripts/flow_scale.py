#!/usr/bin/env python3
"""Shared flow-scale transforms for forecast/retrospective pipelines.

All transforms operate on discharge in raw cms (m^3/s).
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


TRANSFORM_SCALES = ("raw_cms", "log1p_cms", "log_log1p_cms")


def _as_float_array(values: Iterable[float]) -> np.ndarray:
    return np.asarray(values, dtype="float64")


def forward_transform_cms(
    values_cms: Iterable[float],
    scale: str,
    *,
    loglog_floor_cms: float = 1e-6,
) -> np.ndarray:
    """Map raw cms values to the requested working scale.

    For ``log_log1p_cms``, non-positive values are floored to ``loglog_floor_cms``
    so the transform stays finite.
    """
    x = _as_float_array(values_cms)
    if scale == "raw_cms":
        return x
    if scale == "log1p_cms":
        out = np.full_like(x, np.nan, dtype="float64")
        ok = np.isfinite(x) & (x > -1.0)
        out[ok] = np.log1p(x[ok])
        return out
    if scale == "log_log1p_cms":
        out = np.full_like(x, np.nan, dtype="float64")
        ok = np.isfinite(x) & (x > -1.0)
        x_safe = x.copy()
        x_safe[ok & (x_safe <= 0.0)] = float(loglog_floor_cms)
        out[ok] = np.log(np.log1p(x_safe[ok]))
        return out
    raise ValueError(f"Unknown transform scale: {scale}")


def inverse_transform_to_cms(values: Iterable[float], scale: str) -> np.ndarray:
    """Map values in a working scale back to raw cms."""
    y = _as_float_array(values)
    if scale == "raw_cms":
        return y
    if scale == "log1p_cms":
        return np.expm1(y)
    if scale == "log_log1p_cms":
        return np.expm1(np.exp(y))
    raise ValueError(f"Unknown transform scale: {scale}")

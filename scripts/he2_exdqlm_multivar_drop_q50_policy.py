#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from typing import Any


Q50_REPAIR_FREEZE_TARGET = "states"
Q50_REPAIR_TERMINAL_SAMPLING_GUARD: dict[str, Any] = {
    "mode": "fail_fast",
    "min_guard_count": 1,
    "max_guard_lag_iters": 0,
    "require_frozen": True,
}
Q50_REPAIR_STABILIZATION: dict[str, Any] = {
    "median_state_hold_after_guard_iters": 10,
    "median_state_blend_alpha": 1.0,
    "median_cov_blend_alpha": 1.0,
    "median_max_abs_gamma_step": 0.075,
    "median_max_abs_log_sigma_step": 0.15,
}


def build_q50_repair_patch(model_key: str = "exdqlm_multivar") -> dict[str, Any]:
    """Return a fresh merge patch for the repaired q50 exDQLM-drop policy."""
    return {
        "fit": {
            model_key: {
                "gamma_sigma": {
                    "quantile_overrides": {
                        "q50": {
                            "freeze_target": Q50_REPAIR_FREEZE_TARGET,
                            "terminal_sampling_guard": deepcopy(Q50_REPAIR_TERMINAL_SAMPLING_GUARD),
                            "stabilization": deepcopy(Q50_REPAIR_STABILIZATION),
                        }
                    }
                }
            }
        }
    }

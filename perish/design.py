"""Rule-of-thumb sizing and exhaustive search helpers."""
import numpy as np
from .engine import evaluate


def rule_of_thumb(case, basis="mean", margin=1.1, shift_plan=1):
    """Classic sizing: each stage handles the mean (or peak) day's intake in one 8-h shift."""
    w = case.harvest_curve()
    daily = case.total_intake_t * 1000 * (1 / case.season_days if basis == "mean" else w.max())
    need = daily * margin; h = 8.0; mean_lot = np.mean(case.lot_kg_range)
    snap = lambda v, grid: min([g for g in grid if g >= v] or [max(grid)])
    cfg = {}
    for s in case.stages:
        if s["kind"] == "crew":
            v = need / h / s["rate"]
        elif s["kind"] == "units":
            v = need / (h * s["rate"])
        else:
            v = need / (24 / s["cycle_h"] * s["slots"] * mean_lot)
        cfg[s["var"]] = snap(v, case.bounds[s["var"]])
    cfg["shift_plan"] = shift_plan
    return cfg

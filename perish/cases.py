"""Case definitions. [S] = sourced (see report reference list), [A] = modelling assumption."""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Case:
    name: str
    currency: str
    stages: list
    bounds: dict
    season_days: int
    total_intake_t: float
    peak_day: float
    lot_kg_range: tuple
    arrival_window_h: tuple
    transport_h: float
    yard_capacity_t: float
    shift_windows: dict
    wage_mult: dict
    wage_shift: float
    tariff: float
    life_mean_h: float
    life_sd_h: float
    cold_slowdown: float
    cold_days: float
    retail_ambient_days: float
    price_good: float
    price_lost: float
    daily_noise_cv: float = 0.20
    service_cv: float = 0.15
    delay_multiplier: float = 1.0

    @property
    def required_life_h(self):
        return self.cold_days * 24 / self.cold_slowdown + self.retail_ambient_days * 24

    def harvest_curve(self):
        d = np.arange(self.season_days) + 0.5; x = d / self.season_days; m = self.peak_day / self.season_days
        a = 2.5; b = a * (1 - m) / m
        w = x ** (a - 1) * (1 - x) ** (b - 1)
        return w / w.sum()

    def configs(self):
        from itertools import product
        keys = list(self.bounds)
        return [dict(zip(keys, v)) for v in product(*self.bounds.values())]


def peach():
    """Representative Georgia (US) fresh-market peach packinghouse."""
    return Case(
        name="Peach (Georgia, USA)", currency="$",
        stages=[dict(name="Hydrocool", kind="units", var="n_hyd", rate=12_000.0, residence_h=0.25,  # [A] conveyor hydrocooler [S]
                     fixed=25_000.0, kw=30.0, factor_after=0.4),                                   # [A] partially cooled fruit
                dict(name="Wash, brush & sort", kind="crew", var="n_sort", rate=1000.0),            # [A] sorters on a mechanised line
                dict(name="Pack", kind="crew", var="n_pack", rate=400.0),                           # [A] ~35 x 25-lb boxes/h
                dict(name="Forced-air cool", kind="chamber", var="n_fac", slots=2, cycle_h=3.0,
                     fixed=30_000.0, kw=25.0)],                                                     # [A]
        bounds={"n_hyd": [1, 2, 3], "n_sort": list(range(4, 21, 2)), "n_pack": list(range(10, 49, 2)),
                "n_fac": [1, 2, 3], "shift_plan": [1, 2, 3]},
        season_days=84, total_intake_t=6000.0, peak_day=40.0, lot_kg_range=(4000, 8000),           # [A] mid-size house, truckloads
        arrival_window_h=(7, 17), transport_h=1.0, yard_capacity_t=60.0,                            # [A]
        shift_windows={1: [(7.0, 15.0)], 2: [(10.0, 18.0)], 3: [(7.0, 23.0)]},
        wage_mult={1: 1.0, 2: 1.05, 3: 2.10},                                                       # [A] shift differentials
        wage_shift=14.72 * 8, tariff=0.12,                                                          # [S] GA H-2A AEWR skill II 2026; [A] tariff
        life_mean_h=96.0, life_sd_h=12.0,                                                           # [S] 3-5 days at 19-20 C
        cold_slowdown=5.0,                                                                          # [S] 2-4 weeks cold vs 3-5 days warm
        cold_days=7.0, retail_ambient_days=1.0,                                                     # [A] US distribution + 1 day ambient retail
        price_good=2.43, price_lost=0.05)                                                           # [A] ~$1.10/lb packed; culls -> cattle feed [S]

"""Twin-ready operation: a closed loop of ingest -> calibrate -> re-plan, run once per day.

This is what turns the simulation model into a digital twin when it is connected to a real
facility's data (arrival/weighbridge records and stage start/finish scans).  Here the
'real facility' is a hidden simulator with parameters the twin does not know."""
import copy
import numpy as np
from .engine import simulate, generate_lots, finish_time, _segments


def working_hours(t0, t1, windows_fn):
    tot = 0.0
    for lo, hi, _ in _segments(t0, windows_fn):
        if lo >= t1:
            break
        tot += min(hi, t1) - lo
    return tot


class Twin:
    def __init__(self, nominal, base_plan, calibrate=True, n_scen=2, seed=0, prior_frac=0.10):
        self.nom, self.base, self.calibrate = nominal, dict(base_plan), calibrate
        self.n_scen, self.rng, self.prior_frac = n_scen, np.random.default_rng(seed), prior_frac
        self.crew_stages = [j for j, s in enumerate(nominal.stages) if s["kind"] == "crew"]
        self.rate_hat = {j: nominal.stages[j]["rate"] for j in self.crew_stages}
        self.scale_hat = 1.0
        self.history = []

    # -------------------------------------------------------------- candidates
    def candidates(self):
        b, B = self.base, self.nom.bounds
        out = []
        for sp in B["shift_plan"]:
            for dp in (-4, 0, 4, 8):
                for ds in (0, 2):
                    c = dict(b, shift_plan=sp)
                    c["n_pack"] = int(np.clip(b["n_pack"] + dp, min(B["n_pack"]), max(B["n_pack"])))
                    c["n_sort"] = int(np.clip(b["n_sort"] + ds, min(B["n_sort"]), max(B["n_sort"])))
                    if c not in out:
                        out.append(c)
        return out

    # -------------------------------------------------------------- ingest + calibrate
    def ingest(self, lots, rec, plans, now):
        """lots/rec: the facility's records; only events before `now` are used."""
        if not self.calibrate:
            return
        win = lambda d: self.nom.shift_windows[plans[min(d, len(plans) - 1)]["shift_plan"]]
        for j in self.crew_stages:
            s, d = rec["start"][j], rec["done"][j]
            m = (~np.isnan(d)) & (d <= now)
            if m.sum() >= 3:
                var = self.nom.stages[j]["var"]
                hrs = np.array([working_hours(a, b, win) for a, b in zip(s[m], d[m])])
                crew = np.array([plans[min(int(a // 24), len(plans) - 1)][var] for a in s[m]])
                self.rate_hat[j] = float(lots["kg"][m].sum() / np.sum(hrs * crew))
        w = self.nom.harvest_curve(); total = self.nom.total_intake_t * 1000
        d_now = now / 24.0
        frac = w[: int(d_now)].sum() + (d_now - int(d_now)) * (w[int(d_now)] if int(d_now) < len(w) else 0)
        expected = total * frac; observed = lots["kg"][lots["arr"] < now].sum()
        k = self.prior_frac * total
        self.scale_hat = float((observed + k) / (expected + k))

    # -------------------------------------------------------------- plan
    def _planning_case(self):
        c = copy.deepcopy(self.nom)
        for j, r in self.rate_hat.items():
            c.stages[j]["rate"] = r
        return c

    def plan(self, lots, rec, plans, day):
        """Choose the plan for `day` (decided at its start, time = 24*day)."""
        now = 24.0 * day; case = self._planning_case(); last = len(case.stages) - 1
        # work in progress: arrived, accepted, final cooling not yet started
        arrived = lots["arr"] < now
        acc = rec["accepted"]
        started_final = (~np.isnan(rec["start"][last])) & (rec["start"][last] <= now)
        wip = np.nonzero(arrived & acc & ~started_final)[0]
        nxt, ready, pre, f0 = [], [], [], []
        for i in wip:
            j = 0
            while j < last and not np.isnan(rec["done"][j, i]) and rec["done"][j, i] <= now:
                j += 1
            nxt.append(j)
            ready.append(max(now, rec["done"][j - 1, i]) if j > 0 else now)
            # exposure so far
            e = case.transport_h; f = 1.0; tp = lots["arr"][i]
            for jj in range(j):
                if "factor_after" in case.stages[jj]:
                    e += f * (rec["done"][jj, i] - tp); tp = rec["done"][jj, i]; f = case.stages[jj]["factor_after"]
            e += f * (now - tp); pre.append(e); f0.append(f)
        # forecast scenarios drawn ONCE per day and shared by every candidate (common random numbers)
        scen = []
        for _ in range(self.n_scen):
            rng = np.random.default_rng(self.rng.integers(1e9))
            fut = generate_lots(case, rng, scale=self.scale_hat)
            keep = fut["arr"] >= now
            lots_p = {k: (v[:, keep] if v.ndim == 2 else v[keep]) for k, v in fut.items()}
            if len(wip):
                n = len(wip)
                w = dict(arr=np.full(n, now), kg=lots["kg"][wip], life=rng.normal(case.life_mean_h, case.life_sd_h, n),
                         noise=rng.lognormal(-case.service_cv**2 / 2, case.service_cv, (len(case.stages), n)),
                         entry=np.array(nxt), ready=np.array(ready), pre_exposure=np.array(pre), factor0=np.array(f0))
                lots_p = {k: np.concatenate([w[k], lots_p[k]], axis=-1) for k in w}
            scen.append(lots_p)
        best, best_cost = None, np.inf
        for cand in self.candidates():
            P = lambda d, c=cand: plans[d] if d < day else c
            c_mean = float(np.mean([simulate(case, P, lp)["total"] if len(lp["kg"]) else 0.0 for lp in scen]))
            if c_mean < best_cost:
                best, best_cost = cand, c_mean
        self.history.append(dict(day=day, plan=best, rates={case.stages[j]["name"]: r for j, r in self.rate_hat.items()},
                                 scale=self.scale_hat, wip=len(wip)))
        return best


def run_season(true_case, nominal, base_plan, seed, mode="twin"):
    """Operate one season of the hidden 'true' facility under a policy:
    static (base plan all season), replan (twin without calibration), twin (full loop)."""
    lots = generate_lots(true_case, np.random.default_rng(seed))
    plans = [dict(base_plan)]
    twin = Twin(nominal, base_plan, calibrate=(mode == "twin"), seed=seed + 7) if mode != "static" else None
    for day in range(1, true_case.season_days + 3):
        if twin is not None:
            rec = simulate(true_case, lambda d: plans[min(d, len(plans) - 1)], lots, record=True)
            twin.ingest(lots, rec, plans, 24.0 * day)
            plans.append(twin.plan(lots, rec, plans, day))
        else:
            plans.append(dict(base_plan))
    res = simulate(true_case, lambda d: plans[min(d, len(plans) - 1)], lots, record=False)
    return res, plans, (twin.history if twin else [])

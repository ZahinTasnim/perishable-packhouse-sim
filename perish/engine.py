"""General discrete-event simulation of a perishable-produce packhouse.

A case (see cases.py) defines an ordered list of stages, each one of:
  crew    : FIFO line whose speed = workers x kg per worker-hour; works in shift hours
  units   : parallel machines (e.g. hot-water tanks, hydrocoolers): occupancy = kg / rate,
            plus a fixed residence (pipeline) delay; works in shift hours
  chamber : parallel cooling slots with a fixed cycle time; runs 24 h (final cooling)
A stage may cool the fruit ("factor_after"), slowing shelf-life loss until final cooling.

Plans can change day by day: plan(day) -> dict of decision values (crews, shift plan);
equipment counts are taken from day 0. A static layout is just a constant plan.
Lots may also start part-way through the line (work in progress), which is what the
twin-ready loop uses to re-plan from the current state of the facility."""
import heapq
import math
import numpy as np


# ------------------------------------------------------------------ calendars
def _segments(t, windows_fn):
    """Yield (start, end, day) shift segments at or after time t, in order."""
    day = math.floor(t / 24.0)
    while True:
        for a, b in windows_fn(day):
            lo, hi = max(t, 24.0 * day + a), 24.0 * day + b
            if hi > lo:
                yield lo, hi, day
        day += 1
        t = 24.0 * day


def finish_time(t, work, windows_fn, rate_fn=None):
    """Finish time for `work` (hours, or kg if rate_fn given) done only inside shifts."""
    if work <= 1e-12:
        return next(_segments(t, windows_fn))[0] if rate_fn else t
    for lo, hi, day in _segments(t, windows_fn):
        r = rate_fn(day) if rate_fn else 1.0
        cap = (hi - lo) * r
        if work <= cap:
            return lo + work / r
        work -= cap


def capacity_between(t0, t1, windows_fn, rate_fn):
    """Work capacity (kg) available between calendar times t0 and t1."""
    if t1 <= t0:
        return 0.0
    tot = 0.0
    for lo, hi, day in _segments(t0, windows_fn):
        if lo >= t1:
            break
        tot += (min(hi, t1) - lo) * rate_fn(day)
    return tot


# ------------------------------------------------------------------ lots
def generate_lots(case, rng, scale=1.0, curve=None):
    """Harvest arrivals for one season (beta-shaped daily curve x lognormal noise)."""
    days = case.season_days
    w = curve if curve is not None else case.harvest_curve()
    daily = case.total_intake_t * 1000 * scale * w * rng.lognormal(-case.daily_noise_cv**2 / 2, case.daily_noise_cv, days)
    arr, kg = [], []
    for day, target in enumerate(daily):
        tot = 0.0
        while tot < target:
            k = rng.uniform(*case.lot_kg_range); tot += k; kg.append(k)
            arr.append(24 * day + rng.uniform(*case.arrival_window_h))
    arr, kg = np.array(arr), np.array(kg)
    o = np.argsort(arr); n = len(arr)
    return dict(arr=arr[o], kg=kg[o], life=rng.normal(case.life_mean_h, case.life_sd_h, n),
                noise=rng.lognormal(-case.service_cv**2 / 2, case.service_cv, (len(case.stages), n)),
                entry=np.zeros(n, int), ready=arr[o].copy(), pre_exposure=np.zeros(n), factor0=np.ones(n))


# ------------------------------------------------------------------ simulation
def simulate(case, plan, lots, record=False):
    """plan: dict (static) or callable day -> dict.  Returns costs, losses and (optionally) a log."""
    P = plan if callable(plan) else (lambda d, _p=plan: _p)
    p0 = P(0)
    win = lambda d: case.shift_windows[P(d)["shift_plan"]]
    n = len(lots["kg"]); kg_all, nz = lots["kg"], lots["noise"]
    entry, ready0 = lots["entry"], lots["ready"]
    start = np.full((len(case.stages), n), np.nan); done = np.full((len(case.stages), n), np.nan)
    accepted = np.ones(n, bool)
    prev_done = ready0.copy()
    for j, stg in enumerate(case.stages):
        part = np.nonzero(accepted & (entry <= j))[0]
        rdy = np.where(entry[part] == j, ready0[part], prev_done[part])
        order = part[np.argsort(rdy, kind="stable")]; rdy_of = dict(zip(part, rdy))
        if stg["kind"] == "crew":
            rate = lambda d, k=stg["var"], r=stg["rate"]: P(d)[k] * r
            free = 0.0
            for i in order:
                s = max(rdy_of[i], free)
                if j == 0 and entry[i] == 0 and case.yard_capacity_t is not None and \
                        capacity_between(rdy_of[i], s, win, rate) > case.yard_capacity_t * 1000:
                    accepted[i] = False; continue
                free = finish_time(s, kg_all[i] * nz[j, i], win, rate)
                start[j, i], done[j, i] = s, free
        else:
            k = p0[stg["var"]] * stg.get("slots", 1)
            heap = [0.0] * k
            for i in order:
                f = heapq.heappop(heap); s = max(rdy_of[i], f)
                if stg["kind"] == "units":
                    tot_rate = lambda d, kk=k, r=stg["rate"]: kk * r
                    if j == 0 and entry[i] == 0 and case.yard_capacity_t is not None and \
                            capacity_between(rdy_of[i], s, win, tot_rate) > case.yard_capacity_t * 1000:
                        accepted[i] = False; heapq.heappush(heap, f); continue
                    e = finish_time(s, kg_all[i] / stg["rate"] * nz[j, i], win)
                    start[j, i], done[j, i] = s, e + stg.get("residence_h", 0.0)
                else:   # chamber, 24 h
                    e = s + stg["cycle_h"] * nz[j, i] ** 0.3
                    start[j, i], done[j, i] = s, e
                heapq.heappush(heap, e)
        prev_done = np.where(accepted & (entry <= j), done[j], prev_done)

    acc = accepted
    # ---------------- exposure (ambient-equivalent hours) ----------------
    expo = np.where(entry == 0, case.transport_h, 0.0) + lots["pre_exposure"]
    f = lots["factor0"].copy(); t_prev = ready0.copy()
    last = len(case.stages) - 1
    for j, stg in enumerate(case.stages[:-1]):
        if "factor_after" in stg:
            m = acc & (entry <= j)
            expo = np.where(m, expo + f * (done[j] - t_prev), expo)
            t_prev = np.where(m, done[j], t_prev); f = np.where(m, stg["factor_after"], f)
    expo = np.where(acc, expo + f * (start[last] - t_prev) + 0.5 * f * (done[last] - start[last]), expo)
    remaining = lots["life"] - case.delay_multiplier * expo
    good = acc & (remaining >= case.required_life_h)

    # ---------------- cost ----------------
    shift_stage_done = [done[j] for j, s in enumerate(case.stages) if s["kind"] != "chamber"]
    last_work = np.nanmax(shift_stage_done[-1][acc]) if acc.any() else 0.0
    op_days = math.ceil(max(last_work, 24 * case.season_days) / 24.0)
    wage = 0.0; unit_cost = 0.0
    for d in range(op_days):
        pd_ = P(d); sh = sum(b - a for a, b in case.shift_windows[pd_["shift_plan"]])
        crew = sum(pd_[s["var"]] for s in case.stages if s["kind"] == "crew")
        wage += crew * case.wage_shift * case.wage_mult[pd_["shift_plan"]]
        for s in case.stages:
            if s["kind"] == "units":
                unit_cost += p0[s["var"]] * s["kw"] * sh * case.tariff
            elif s["kind"] == "chamber":
                unit_cost += p0[s["var"]] * s["kw"] * 24 * case.tariff
    fixed = sum(p0[s["var"]] * s["fixed"] for s in case.stages if s["kind"] != "crew")
    lost_kg = kg_all[~good & (entry == 0)].sum() + kg_all[~good & (entry > 0)].sum()
    quality = lost_kg * (case.price_good - case.price_lost)
    total = wage + unit_cost + fixed + quality
    out = dict(total=total, wage=wage, equipment=unit_cost + fixed, quality=quality,
               lost_pct=100 * lost_kg / kg_all.sum(), diverted_pct=100 * kg_all[~acc].sum() / kg_all.sum(),
               mean_exposure_h=float(np.nanmean(np.where(acc, expo, np.nan))) if acc.any() else np.nan, op_days=op_days)
    if record:
        out.update(start=start, done=done, accepted=acc, good=good, exposure=expo)
    return out


def evaluate(case, plan, seeds, scale=1.0):
    v = [simulate(case, plan, generate_lots(case, np.random.default_rng(s), scale))["total"] for s in seeds]
    return float(np.mean(v)), float(np.std(v, ddof=1) / math.sqrt(len(v))) if len(v) > 1 else 0.0

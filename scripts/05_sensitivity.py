"""Step 5: sensitivity test. Change ONE assumption, re-run the peach design study, compare with your baseline.

    python scripts/05_sensitivity.py --list                 show the assumptions you can change
    python scripts/05_sensitivity.py wage_per_hour 22       change one assumption and re-run
(or double-click step5_sensitivity.bat, which asks you the two questions)

Your baseline files (Step 2) are never touched. Output goes to results/sensitivity_<name>.json/.csv.
The search is identical to Step 2 (all 4,860 layouts, the same 5 seasons, the best 25 re-tested on 30 seasons),
so the comparison is fair."""
import copy, json, sys, time
import numpy as np, pandas as pd
from perish.cases import peach
from perish.engine import evaluate, simulate, generate_lots
from perish.design import rule_of_thumb

# name -> (meaning, how to read the baseline value from the case)
STAGE_RATES = {"sort_rate": "n_sort", "pack_rate": "n_pack", "hydrocooler_rate": "n_hyd"}
OPTIONS = {
    "wage_per_hour":     "Hourly wage, $ (2026 Georgia H-2A minimum)",
    "yard_capacity_t":   "Holding-yard size, tonnes (trucks are turned away when it is full)",
    "pack_rate":         "Packing speed, kg per packer per hour",
    "sort_rate":         "Sorting speed, kg per sorter per hour",
    "hydrocooler_rate":  "Hydrocooler throughput, kg per hour per unit",
    "price_good":        "Value of packed fruit, $ per kg",
    "life_mean_h":       "Shelf life at room temperature, hours (96 = 4 days)",
    "total_intake_t":    "Season volume, tonnes",
    "transport_h":       "Orchard-to-packinghouse haul, hours",
    "tariff":            "Electricity price, $ per kWh",
    "cold_slowdown":     "How many times slower fruit ripens when cold",
}


def baseline_value(case, name):
    if name == "wage_per_hour":
        return case.wage_shift / 8
    if name in STAGE_RATES:
        return next(s["rate"] for s in case.stages if s["var"] == STAGE_RATES[name])
    return getattr(case, name)


def apply_change(case, name, value):
    c = copy.deepcopy(case)
    if name == "wage_per_hour":
        c.wage_shift = value * 8
    elif name in STAGE_RATES:
        for s in c.stages:
            if s["var"] == STAGE_RATES[name]:
                s["rate"] = value
    else:
        setattr(c, name, value)
    return c


def usage(msg=None):
    if msg:
        print(f"\n{msg}\n")
    base = peach()
    print("Assumptions you can change (name, current value, meaning):")
    for k, v in OPTIONS.items():
        print(f"  {k:18s} {baseline_value(base, k):>10g}   {v}")
    print("\nExample:  python scripts/05_sensitivity.py wage_per_hour 22")


if len(sys.argv) == 2 and sys.argv[1] == "--list":
    usage(); sys.exit(0)
if len(sys.argv) != 3:
    usage("Please give the assumption name and its new value."); sys.exit(1)
NAME = sys.argv[1]
if NAME not in OPTIONS:
    usage(f"'{NAME}' is not on the list."); sys.exit(1)
try:
    NEW = float(sys.argv[2])
except ValueError:
    usage(f"'{sys.argv[2]}' is not a number."); sys.exit(1)

try:
    GT = json.load(open("results/ground_truth_peach.json"))
    E0 = pd.read_csv("results/peach_base_exhaustive.csv")
except FileNotFoundError:
    sys.exit("Run Step 2 first: results/ground_truth_peach.json is missing.")

base_case = peach(); new_case = apply_change(base_case, NAME, NEW)
OLD = baseline_value(base_case, NAME)
TRUTH = list(range(1000, 1030)); KEYS = list(new_case.bounds)
print(f"\nSENSITIVITY TEST: {NAME}: {OLD:g} -> {NEW:g}   ({OPTIONS[NAME]})")
print("Re-running the design study with this change (about 6-8 minutes)...", flush=True)

t0 = time.time()
rows = [{**c, "cost": evaluate(new_case, c, range(5))[0]} for c in new_case.configs()]
E1 = pd.DataFrame(rows).sort_values("cost").reset_index(drop=True)
E1.to_csv(f"results/sensitivity_{NAME}.csv", index=False)
top = sorted([(evaluate(new_case, {k: int(r[k]) for k in KEYS}, TRUTH)[0], {k: int(r[k]) for k in KEYS}) for _, r in E1.head(25).iterrows()],
             key=lambda z: z[0])
new_cost, new_cfg = top[0]
old_cfg, old_cost = GT["peach_base"]["optimum"], GT["peach_base"]["optimum_cost"]


def stats(case, cfg):
    rs = [simulate(case, cfg, generate_lots(case, np.random.default_rng(s))) for s in TRUTH]
    return float(np.mean([r["total"] for r in rs])), float(np.mean([r["lost_pct"] for r in rs]))


rule_new = stats(new_case, rule_of_thumb(new_case, "mean"))[0]
rule_old = GT["peach_base"]["rule_mean"]["cost"]
old_layout_under_new = stats(new_case, old_cfg)
new_layout_stats = stats(new_case, new_cfg)
old_layout_stats = stats(base_case, old_cfg)
PLAN = {1: "day", 2: "late", 3: "double"}
lay = lambda c: f"{c['n_hyd']} hydro / {c['n_sort']} sort / {c['n_pack']} pack / {c['n_fac']} chambers / {PLAN[c['shift_plan']]}"
bp0 = E0.groupby("shift_plan")["cost"].min(); bp1 = E1.groupby("shift_plan")["cost"].min()
res = dict(assumption=NAME, old_value=OLD, new_value=NEW, baseline_layout=old_cfg, new_layout=new_cfg,
           baseline_cost=old_cost, new_cost=new_cost, baseline_lost_pct=old_layout_stats[1], new_lost_pct=new_layout_stats[1],
           avg_day_rule_ratio_baseline=rule_old / old_cost, avg_day_rule_ratio_new=rule_new / new_cost,
           best_by_plan_baseline={PLAN[int(k)]: float(v) for k, v in bp0.items()}, best_by_plan_new={PLAN[int(k)]: float(v) for k, v in bp1.items()},
           old_layout_cost_under_new_assumption=old_layout_under_new[0], seconds=time.time() - t0)
json.dump(res, open(f"results/sensitivity_{NAME}.json", "w"), indent=1)

best_plan_new = int(bp1.idxmin()); w = 26
print("\n" + "=" * 78)
print(f"{'':{w}s}{'BASELINE':>22s}{'AFTER YOUR CHANGE':>28s}")
print(f"{NAME + ' =':{w}s}{OLD:>22g}{NEW:>28g}")
print(f"{'Best season cost':{w}s}{'$' + format(old_cost, ',.0f'):>22s}{'$' + format(new_cost, ',.0f'):>28s}")
print(f"{'Fruit lost at the best':{w}s}{old_layout_stats[1]:>21.1f}%{new_layout_stats[1]:>27.1f}%")
print(f"{'Average-day rule costs':{w}s}{rule_old / old_cost:>21.1f}x{rule_new / new_cost:>27.1f}x the best")
print(f"\nBest layout BEFORE: {lay(old_cfg)}")
print(f"Best layout AFTER : {lay(new_cfg)}")
print(f"\nBest achievable cost under each shift plan (5-season search):")
print(f"  {'':14s}{'baseline':>14s}{'after change':>16s}")
for k in (1, 2, 3):
    print(f"  {PLAN[k] + ' shift':14s}{'$' + format(bp0[k], ',.0f'):>14s}{'$' + format(bp1[k], ',.0f'):>16s}")
print(f"\nIf you had KEPT the baseline layout after your change, the season would cost ${old_layout_under_new[0]:,.0f} "
      f"({100 * (old_layout_under_new[0] / new_cost - 1):+.1f}% vs the new best).")
print("=" * 78)
print(f"\nDid the main lessons survive your change?")
print(f"  Double shift still the best shift plan : {'YES' if best_plan_new == 3 else 'NO  -> best is now the ' + PLAN[best_plan_new] + ' shift'}")
print(f"  Average-day rule still much worse      : {'YES' if rule_new / new_cost > 2 else 'NO'}  ({rule_new / new_cost:.1f}x the best)")
print(f"  Best layout changed                    : {'NO' if new_cfg == old_cfg else 'YES'}")
print(f"\nSaved: results/sensitivity_{NAME}.json and .csv   [{time.time() - t0:.0f}s]")

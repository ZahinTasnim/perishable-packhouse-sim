"""Exhaustive ground truth for a case (and its 'surprise' variant): every layout over common
random numbers, top 25 re-evaluated over 30 independent seasons."""
import json, sys, time
import pandas as pd
from perish.cases import peach
from perish.scenarios import surprise
from perish.engine import evaluate
from perish.design import rule_of_thumb

CASES = {"peach": peach}
TRUTH = list(range(1000, 1030)); t0 = time.time(); out = {}
for key, make in CASES.items():
    base = make()
    for label, case, reps in [("base", base, range(5)), ("surprise", surprise(base), range(3))]:
        rows = [{**c, "cost": evaluate(case, c, reps)[0]} for c in case.configs()]
        df = pd.DataFrame(rows).sort_values("cost").reset_index(drop=True)
        df.to_csv(f"results/{key}_{label}_exhaustive.csv", index=False)
        top = sorted([(evaluate(case, {k: int(r[k]) for k in case.bounds}, TRUTH), {k: int(r[k]) for k in case.bounds})
                      for _, r in df.head(25).iterrows()], key=lambda z: z[0][0])
        res = dict(optimum=top[0][1], optimum_cost=top[0][0][0], optimum_se=top[0][0][1])
        for nm, c in [("rule_mean", rule_of_thumb(base, "mean")), ("rule_peak", rule_of_thumb(base, "peak")),
                      ("rule_peak_late", rule_of_thumb(base, "peak", shift_plan=2))]:
            m, se = evaluate(case, c, TRUTH); res[nm] = dict(cfg=c, cost=m, se=se)
        out[f"{key}_{label}"] = res
        print(f"{key}/{label}: optimum {res['optimum']} {res['optimum_cost']:.0f}  [{time.time()-t0:.0f}s]", flush=True)
    m, se = evaluate(surprise(base), out[f"{key}_base"]["optimum"], TRUTH)
    out[f"{key}_surprise"]["base_optimum"] = dict(cfg=out[f"{key}_base"]["optimum"], cost=m, se=se)
json.dump(out, open("results/ground_truth_peach.json", "w"), indent=1)
print("saved", flush=True)

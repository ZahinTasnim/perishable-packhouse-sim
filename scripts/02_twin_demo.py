"""Twin-ready demonstration: operate a hidden 'true' peach packinghouse whose season differs
from the plan (25% more fruit, packers 15% slower), under three policies:
  static : the design-stage optimal plan, held all season (no twin)
  replan : daily re-planning from the live state, but with the original (wrong) assumptions
  twin   : daily ingest -> calibrate -> re-plan (full twin-ready loop)
Reference: the best static layout had the surprise been known in advance (from ground truth)."""
import json, pickle, time
from perish.cases import peach
from perish.scenarios import surprise
from perish.twin import run_season

GT = json.load(open("results/ground_truth_peach.json"))
nom = peach(); tru = surprise(nom); base = GT["peach_base"]["optimum"]
SEEDS = range(6); out = {"base_plan": base, "runs": {}}
t0 = time.time()
for mode in ("static", "replan", "twin"):
    out["runs"][mode] = []
    for s in SEEDS:
        res, plans, hist = run_season(tru, nom, base, 500 + s, mode)
        out["runs"][mode].append(dict(total=res["total"], lost_pct=res["lost_pct"], wage=res["wage"],
                                      quality=res["quality"], plans=plans, history=hist))
        print(f"{mode:7s} seed {s}: ${res['total']/1e3:.0f}k lost {res['lost_pct']:.1f}%  [{time.time()-t0:.0f}s]", flush=True)
pickle.dump(out, open("results/twin_demo.pkl", "wb")); print("saved", flush=True)

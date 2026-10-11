"""Figures and summary for the peach report."""
import json, pickle
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from perish.cases import peach
from perish.scenarios import surprise
from perish.engine import simulate, generate_lots
from perish.design import rule_of_thumb

plt.rcParams.update({"font.size": 8.5, "font.family": "DejaVu Sans"})
GT = json.load(open("results/ground_truth_peach.json")); TW = pickle.load(open("results/twin_demo.pkl", "rb"))
pc = peach(); TRUTH = range(1000, 1030); S = {}


def detail(case, cfg, seeds=TRUTH):
    rs = [simulate(case, cfg, generate_lots(case, np.random.default_rng(s))) for s in seeds]
    return {k: float(np.mean([r[k] for r in rs])) for k in ("total", "wage", "equipment", "quality", "lost_pct", "diverted_pct", "mean_exposure_h")}


# ------------------------------------------------ peach process diagram
fig, ax = plt.subplots(figsize=(7.4, 1.9)); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(-3.5, 24)
boxes = [("Orchards\n(trucks of bins)", "#e8f5e9"), (f"Holding yard\n({pc.yard_capacity_t:.0f} t)", "#fff3e0")]
for s in pc.stages:
    lab = {"crew": "workers", "units": "units", "chamber": "chambers"}[s["kind"]]
    col = "#e0f7fa" if (s["kind"] == "chamber" or "factor_after" in s) else "#e3f2fd"
    boxes.append((s['name'].replace(", ", ",\n").replace(" & ", " &\n").replace("Forced-air cool", "Forced-air\ncool") + f"\n[{s['var']}]", col))
boxes.append(("Cold store ->\nmarket", "#e0f7fa"))
x = 1; wbox = 100 / len(boxes) - 1.6
for i, (t, c) in enumerate(boxes):
    ax.add_patch(FancyBboxPatch((x, 7), wbox, 12, boxstyle="round,pad=0.4", fc=c, ec="k", lw=0.7))
    ax.text(x + wbox / 2, 13, t, ha="center", va="center", fontsize=6.6)
    if i < len(boxes) - 1:
        ax.annotate("", xy=(x + wbox + 1.5, 13), xytext=(x + wbox + 0.4, 13), arrowprops=dict(arrowstyle="-|>", lw=0.8))
    x += wbox + 1.6
ax.text(1, 2.6, "Blue: works only in shift hours.  Teal: cools the fruit (after hydrocooling, shelf-life loss slows to 40%;", fontsize=6.4)
ax.text(1, -1.6, "forced-air cooling runs 24 h).  When the yard is full, arriving trucks are diverted to culls.", fontsize=6.4)
fig.tight_layout(); fig.savefig("figures/peach_process.png", dpi=230); plt.close(fig)

# ------------------------------------------------ peach designs
opt = GT["peach_base"]["optimum"]
designs = {"Rule: average day": rule_of_thumb(pc, "mean"), "Rule: peak day": rule_of_thumb(pc, "peak"),
           "Peak day + late shift": rule_of_thumb(pc, "peak", shift_plan=2), "Optimum": opt}
PD = {k: dict(cfg=v, **detail(pc, v)) for k, v in designs.items()}; S["peach_designs"] = PD
fig, ax = plt.subplots(figsize=(6.4, 2.7)); names = list(PD)
bottom = np.zeros(len(names))
for k, col, lab in [("wage", "#5b8def", "Labour"), ("equipment", "#4bb3a6", "Equipment + energy"), ("quality", "#d9534f", "Lost fruit value")]:
    vals = np.array([PD[n][k] for n in names]) / 1e3
    ax.bar(range(len(names)), vals, bottom=bottom, color=col, label=lab, width=0.6); bottom += vals
for i, n in enumerate(names):
    ax.text(i, bottom[i] * 1.12, f"${bottom[i]:,.0f}k\n({PD[n]['lost_pct']:.1f}% lost)", ha="center", fontsize=7)
ax.set_yscale("log"); ax.set_ylim(100, max(bottom) * 4); ax.set_ylabel("Season cost ($ thousand, log scale)")
ax.set_xticks(range(len(names))); ax.set_xticklabels(names, fontsize=7.5); ax.legend(fontsize=7, frameon=False, loc="upper right")
fig.tight_layout(); fig.savefig("figures/peach_costs.png", dpi=230); plt.close(fig)

# ------------------------------------------------ twin demo
runs = TW["runs"]; ref = GT["peach_surprise"]
S["twin"] = {m: dict(total_med=float(np.median([r["total"] for r in runs[m]])), lost_med=float(np.median([r["lost_pct"] for r in runs[m]])),
                     totals=[float(r["total"]) for r in runs[m]], losts=[float(r["lost_pct"]) for r in runs[m]]) for m in runs}
S["twin"]["oracle"] = dict(cfg=ref["optimum"], total=ref["optimum_cost"])
S["twin"]["static_gt"] = ref["base_optimum"]
h = runs["twin"][0]["history"]; days = [x["day"] for x in h]
fig, ax = plt.subplots(1, 3, figsize=(7.5, 2.7), gridspec_kw={"width_ratios": [1, 1, 1.25]})
packrate = [x["rates"]["Pack"] for x in h]; scale = [x["scale"] for x in h]
ax[0].plot(days, packrate, color="#d55e00", lw=1.4)
ax[0].axhline(400, color="grey", ls=":", lw=1); ax[0].text(40, 404, "assumed 400", fontsize=6.8, color="grey")
ax[0].axhline(340, color="k", ls="--", lw=0.8); ax[0].text(40, 328, "true 340", fontsize=6.8)
ax[0].set_ylim(300, 420); ax[0].set_xlabel("Day"); ax[0].set_ylabel("kg per packer-hour"); ax[0].set_title("(a) Learning packing speed", fontsize=8.5)
ax[1].plot(days, scale, color="#2e7d32", lw=1.4); ax[1].axhline(1.25, color="k", ls="--", lw=0.8); ax[1].axhline(1.0, color="grey", ls=":", lw=1)
ax[1].text(40, 1.26, "true x1.25", fontsize=6.8); ax[1].text(40, 0.975, "planned x1.00", fontsize=6.8, color="grey")
ax[1].set_xlabel("Day"); ax[1].set_ylabel("Season volume vs plan"); ax[1].set_title("(b) Learning crop size", fontsize=8.5)
labels = ["Static", "Re-plan\nonly", "Twin\nloop", "Hind-\nsight"]
vals = [S["twin"]["static"]["total_med"], S["twin"]["replan"]["total_med"], S["twin"]["twin"]["total_med"], ref["optimum_cost"]]
ax[2].bar(range(4), np.array(vals) / 1e6, color=["#9e9e9e", "#f2a541", "#d55e00", "#2e7d32"], width=0.6)
for i, v in enumerate(vals):
    ax[2].text(i, v / 1e6 * 1.15, f"${v/1e6:.2f}M", ha="center", fontsize=6.6)
ax[2].set_yscale("log"); ax[2].set_xticks(range(4)); ax[2].set_xticklabels(labels, fontsize=7); ax[2].set_ylabel("Season cost ($ million, log)")
ax[2].set_title("(c) Cost in the surprise season", fontsize=8.5); ax[2].set_ylim(0.5, max(vals) / 1e6 * 2.5)
fig.tight_layout(); fig.savefig("figures/peach_twin.png", dpi=230); plt.close(fig)

plans = runs["twin"][0]["plans"]; lots = generate_lots(surprise(pc), np.random.default_rng(500))
intake = np.bincount((lots["arr"] // 24).astype(int), weights=lots["kg"], minlength=pc.season_days)[:pc.season_days] / 1000
fig, ax = plt.subplots(figsize=(7.2, 2.4)); ax2 = ax.twinx()
ax.bar(np.arange(len(intake)), intake, color="#c8e6c9", label="Fruit arriving (t/day)")
ax2.step(range(len(plans)), [p["n_pack"] for p in plans], where="post", color="#d55e00", lw=1.3, label="Packers scheduled")
ax2.step(range(len(plans)), [10 * p["shift_plan"] for p in plans], where="post", color="#5b8def", lw=1.0, ls="--",
         label="Shift plan (10 = day, 20 = late, 30 = double)")
ax.set_xlabel("Day of season"); ax.set_ylabel("Arrivals (t/day)"); ax2.set_ylabel("Packers / shift code")
ax.set_xlim(0, pc.season_days + 2); ax2.set_ylim(0, 45)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=6.8, frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig("figures/peach_twin_decisions.png", dpi=230); plt.close(fig)

# ------------------------------------------------ best cost under each shift plan
EP = pd.read_csv("results/peach_base_exhaustive.csv")
bp = EP.groupby("shift_plan")["cost"].min()
S["best_by_plan"] = dict(peach={int(k): float(v) for k, v in bp.items()})
S["share_within_5pct"] = dict(peach=float(np.mean(EP.cost <= EP.cost.min() * 1.05)))
json.dump(S, open("results/summary.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in S.items() if k != "peach_designs"}, indent=1, default=str)[:2500])
for k, v in PD.items():
    print(k, v["cfg"], round(v["total"]), round(v["lost_pct"], 2), round(v["mean_exposure_h"], 1))

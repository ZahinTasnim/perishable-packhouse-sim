# Perishable Packhouse Simulation: Georgia Peach Case

A discrete-event simulation of a mid-size Georgia peach packinghouse: hydrocool, wash and sort, pack, forced-air cool. It includes shift calendars, a finite holding yard and a shelf-life model in which warm waiting destroys fruit value. The season is 84 days and 6,000 t, with labour costed at the 2026 Georgia H-2A wage of $14.72 an hour.

Three questions:
1. Which equipment, crew size and shift plan give the lowest season cost?
2. How do common sizing rules (average day, busiest day) compare with the best design?
3. If the season differs from the plan, can daily re-planning from the facility's own records recover?

Reports: `Peach_Packinghouse_Report.pdf` (technical report) and `Peach_Project_Summary.pdf` (short summary).

## Key findings
- **Hours matter more than headcount.** The best layout (1 hydrocooler, 8 sorters, 20 packers, 2 cooling chambers, double shift) costs about **$787k** per season and loses 0.7% of the fruit.
- **Averages hide peaks.** Sizing for the average day costs **13.5 times** the best and loses about 69% of the fruit. Moving a busiest-day crew to a shift that matches truck arrivals saves about 16% with no new equipment.
- **The best design is fragile.** In a season with 25% more fruit and packers 15% slower than planned, the fixed plan costs about $12.1M. Daily re-planning that learns packing speed and crop size from records brings it to about **$1.2M**, within about 11% of a plan made with perfect hindsight.
- **Wage sensitivity ($14.72 to $25 per hour).** Cost rises about 52% ($787k to $1.19M) and the best layout does not change. Each $1 per hour adds about $39.5k per season.

## From model to digital twin
Following Kritzinger et al. (2018):
- **Digital model:** no automatic data link to the facility.
- **Digital shadow:** live data flows automatically into the model.
- **Digital twin:** data flows both ways, and the model's decisions feed back into operations.

This repository is a digital model that already contains the twin's operating loop (`perish/twin.py`). Connected to a facility's arrival and stage records it would become a digital shadow, and once its daily plans are used to run the facility, a digital twin. A real deployment still needs data capture, validation on real records and human approval of plans. The loop is demonstrated here on **synthetic** data only.

## Reproduce
**Windows:** place the folder somewhere you own (for example `C:\Users\YOUR-NAME\Projects\`), then double-click in order:
1. `setup_windows.bat` (one-time setup and check; it must report two MATCH lines)
2. `step2_ground_truth.bat` (all 4,860 layouts, about 10 to 20 minutes)
3. `step3_twin_loop.bat` (surprise-season experiment, about 5 to 10 minutes)
4. `step4_figures_and_reports.bat` (figures and the technical report)
5. `step5_sensitivity.bat` (change one assumption and compare)
6. `make_short_report.bat` (builds the short summary from `my_report.txt`)

`run_all.bat` runs steps 2 to 4 in one go.

**Manual:**
```bash
pip install -r requirements.txt
export PYTHONPATH=.
python scripts/01_ground_truth.py      # all 4,860 layouts, planned and surprise seasons
python scripts/02_twin_demo.py         # static vs re-plan vs learn-and-re-plan
python scripts/03_analyse.py           # figures + results/summary.json
python scripts/04_reports.py           # technical report PDF
python scripts/05_sensitivity.py wage_per_hour 25
python scripts/06_short_report.py      # short summary PDF from my_report.txt
```

## Layout
```
perish/engine.py     simulation engine: crews, machines, chambers, shift calendars, yard, quality, cost
perish/cases.py      the peach case; every input tagged [S] sourced or [A] assumed
perish/design.py     rule-of-thumb sizing
perish/scenarios.py  the surprise season
perish/twin.py       ingest, calibrate, re-plan loop
scripts/             numbered pipeline 01 to 06
results/ figures/    outputs of the pipeline
```
*Representative facility, not a specific company. Assumed parameters are labelled in the code and the report.*

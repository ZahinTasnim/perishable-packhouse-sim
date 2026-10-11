"""Builds both A4 PDF reports from results/*.json and figures/."""
import json
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from PIL import Image as PI

S = json.load(open("results/summary.json")); GT = json.load(open("results/ground_truth_peach.json"))
PD = S["peach_designs"]; TW = S["twin"]
popt = GT["peach_base"]["optimum"]; pcost = GT["peach_base"]["optimum_cost"]
CD = {k: {"peach": v["total"] / pcost} for k, v in PD.items()}   # cost relative to the best layout
PLAN = {1: "day", 2: "late", 3: "double"}
K = lambda x: f"${x/1e3:,.0f}k"; M = lambda x: f"${x/1e6:.2f}M"

ss = getSampleStyleSheet()
body = ParagraphStyle("b", parent=ss["Normal"], fontName="Times-Roman", fontSize=9.6, leading=11.9, alignment=TA_JUSTIFY, spaceAfter=3.2)
h1 = ParagraphStyle("h1", parent=body, fontName="Times-Bold", fontSize=10.8, spaceBefore=5, spaceAfter=2.5, alignment=0)
h2 = ParagraphStyle("h2", parent=body, fontName="Times-BoldItalic", fontSize=9.8, spaceBefore=2.5, spaceAfter=1.5, alignment=0)
title = ParagraphStyle("t", parent=body, fontName="Times-Bold", fontSize=14, leading=17, alignment=TA_CENTER, spaceAfter=4)
auth = ParagraphStyle("a", parent=body, fontSize=9.6, alignment=TA_CENTER, spaceAfter=1)
absst = ParagraphStyle("ab", parent=body, fontSize=9.1, leading=11.1, leftIndent=8*mm, rightIndent=8*mm)
cap = ParagraphStyle("c", parent=body, fontSize=8.4, leading=10, spaceAfter=5)
ref = ParagraphStyle("r", parent=body, fontSize=8.1, leading=9.6, leftIndent=4.5*mm, firstLineIndent=-4.5*mm, spaceAfter=1.1, alignment=0)
tcell = ParagraphStyle("tc", parent=body, fontSize=8.1, leading=9.5, alignment=0, spaceAfter=0)
W = A4[0] - 36*mm


class Doc:
    def __init__(self):
        self.st = []

    def p(self, t, s=body):
        self.st.append(Paragraph(t, s))

    def fig(self, path, caption, frac=1.0, head=None):
        w, h = PI.open(path).size
        items = list(head or []) + [Image(path, width=W*frac, height=W*frac*h/w), Paragraph(caption, cap)]
        self.st.append(KeepTogether(items))

    def table(self, rows, widths, caption):
        t = Table([[Paragraph(str(c), tcell) for c in r] for r in rows], colWidths=widths, hAlign="CENTER")
        t.setStyle(TableStyle([("LINEABOVE", (0,0), (-1,0), .8, colors.black), ("LINEBELOW", (0,0), (-1,0), .5, colors.black),
                               ("LINEBELOW", (0,-1), (-1,-1), .8, colors.black), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                               ("TOPPADDING", (0,0), (-1,-1), 1.3), ("BOTTOMPADDING", (0,0), (-1,-1), 1.3)]
                              + [("BACKGROUND", (0,i), (-1,i), colors.HexColor("#f2f2f2")) for i in range(2, len(rows), 2)]))
        self.st.append(KeepTogether([t, Paragraph(caption, cap)]))

    def header(self, ttl, repo):
        self.p(ttl, title); self.p("Zahin Tasnim Ridita", auth)
        self.p("B.Sc. Industrial and Production Engineering, Islamic University of Technology (IUT), Bangladesh", auth)
        self.p(f"Independent research project &middot; October 2026 &middot; Code: github.com/&lt;username&gt;/{repo}", auth)
        self.st.append(Spacer(1, 4))

    def refs(self, items):
        self.p("References", h1)
        for i, r in enumerate(items, 1):
            self.p(f"[{i}] {r}", ref)

    def build(self, path, ttl):
        foot = lambda c, d: (c.setFont("Times-Roman", 8), c.drawCentredString(A4[0]/2, 9*mm, str(d.page)))
        SimpleDocTemplate(path, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=14*mm, bottomMargin=15*mm,
                          title=ttl, author="Zahin Tasnim Ridita").build(self.st, onFirstPage=foot, onLaterPages=foot)


tw_s, tw_r, tw_t, ora = TW["static"]["total_med"], TW["replan"]["total_med"], TW["twin"]["total_med"], TW["oracle"]["total"]
cfgp = lambda c: f"{c['n_hyd']} / {c['n_sort']} / {c['n_pack']} / {c['n_fac']} / {PLAN[c['shift_plan']]}"
TWIN_DEF = ("Following Kritzinger et al. [9], a <i>digital model</i> exchanges no data automatically with the physical system, a "
            "<i>digital shadow</i> receives live data automatically, and a <i>digital twin</i> exchanges data automatically in both "
            "directions. The model built here is a digital model that already contains the twin's operating loop "
            "(ingest &rarr; calibrate &rarr; re-plan). Connected to a facility's live records it becomes a digital shadow, and once its "
            "daily plans are fed back into operations it becomes a digital twin.")

# =============================================================================== PEACH REPORT
d = Doc()
T1 = ("Capacity, Shift Planning and a Twin-Ready Operating Loop for a Georgia Peach Packinghouse: "
      "A Simulation-Optimization Study")
d.header(T1, "perishable-packhouse-sim")
d.p(f"<b>Abstract.</b> Fresh-market peaches last only 3&ndash;5 days at room temperature, and US packinghouses face record reliance "
    f"on H-2A guest-worker labour. This study builds a discrete-event simulation of a representative Georgia peach packinghouse "
    f"(hydrocooling, sorting, packing, forced-air cooling). All 4,860 combinations of equipment, crew size and shift plan are evaluated "
    f"against total season cost (labour, equipment, energy and lost fruit value). The optimum, {cfgp(popt)} (hydrocoolers / sorters / "
    f"packers / chambers / shift), costs {K(pcost)} per season. Sizing for the average day costs "
    f"{CD['Rule: average day']['peach']:.1f}&times; as much, and peak-day sizing {CD['Rule: peak day']['peach']:.2f}&times;. "
    f"The study then adds a twin-ready operating loop that each day ingests the facility's records, recalibrates packing speed and crop "
    f"size, and re-plans crews and shifts. In a season with 25% more fruit and 15% slower packing than planned, the design-stage plan "
    f"lost {TW['static']['lost_med']:.0f}% of the fruit ({M(tw_s)}). Re-planning with the original assumptions cost {M(tw_r)}. "
    f"The full loop cost {M(tw_t)} ({TW['twin']['lost_med']:.1f}% lost), within {100*(tw_t/ora-1):.0f}% of a hindsight optimum that "
    f"could also change equipment.", absst)

d.p("1. Introduction", h1)
d.p("Worldwide, 13.3% of food is lost between harvest and retail, and fruit and vegetables have the highest loss rate of any group, "
    "at 25.4% [1]. US specialty-crop packers face a second pressure: labour. In fiscal year 2025, 398,258 H-2A positions were certified, "
    "the first year in the programme's history with more than 400,000 workers requested [2]. The 2026 Georgia minimum wage for H-2A "
    "field and livestock workers at skill level II is $14.72 per hour [3]. Peaches magnify both pressures. They keep for only 3&ndash;5 "
    "days at 19&ndash;20 &deg;C but 2&ndash;4 weeks when cold [4], so fast cooling after harvest is critical [4, 6]. Georgia produces "
    "over 130 million pounds a year [7].")
d.p("A packinghouse therefore has to decide how much equipment to install, how many workers to hire, and which hours to run, "
    "knowing that every hour fruit waits warm destroys value. It also has to keep making those decisions as the real season departs "
    "from the plan. <b>RQ1:</b> what layout minimizes total season cost, and how do common sizing rules compare? <b>RQ2:</b> how much "
    "does a twin-ready loop (live data &rarr; recalibration &rarr; daily re-planning) recover when the season surprises the planner?")

d.p("2. Model", h1)
d.fig("figures/peach_process.png", "<b>Figure 1.</b> Simulated packinghouse. The decision variables are shown in brackets.")
d.p("Trucks (4&ndash;8 t of bins) arrive between 07:00 and 17:00 after a 1-h haul. Daily volume follows a beta-shaped harvest curve "
    "over an 84-day season, peaking on day 40, with 20% day-to-day noise; the season total is 6,000 t. Lots pass first-in-first-out "
    "through four stages. The <i>conveyor hydrocooler</i> is the standard type for peaches [6], with 12 t/h per unit and a 15-min residence "
    "time. Then come <i>wash, brush and sort</i> (1,000 kg per sorter-hour) and <i>pack</i> (400 kg per packer-hour, about 35 25-lb boxes). "
    "The fourth stage is <i>forced-air cooling</i>: 3-h cycles, two truckload slots per chamber, running 24 h. Staffed stages and "
    "hydrocooling run only in shift hours: a day shift (07&ndash;15), a late shift (10&ndash;18) or a double shift (07&ndash;23). "
    "A full 60-t yard diverts arriving trucks.")
d.p("<b>Quality.</b> Each lot carries a shelf-life budget of <i>N</i>(96, 12) h at room temperature, i.e. 4 &plusmn; 0.5 days [4]. "
    "Cold storage uses this budget 5 times more slowly, consistent with 3&ndash;5 days warm against 2&ndash;4 weeks cold [4, 5]. "
    "After hydrocooling, partially cooled fruit loses life at 40% of the warm rate. A lot is marketable if it keeps enough life for "
    "7 days of cold distribution plus 1 day on a retail shelf (57.6 h). Otherwise it is culled, mainly for cattle feed [6]. "
    "<b>Cost</b> combines wages, seasonal equipment charges, electricity, and lost value at $2.38 per kg.")
d.table([["Parameter", "Value", "Basis"],
         ["Shelf life warm / cold", "3&ndash;5 days at 19&ndash;20 &deg;C (model 4 &plusmn; 0.5) / 2&ndash;4 weeks (5&times; slower)", "Sourced [4, 5]"],
         ["Cooling practice", "Conveyor hydrocooling; cool within 8 h", "Sourced [6]"],
         ["Wage", "$14.72 per hour (2026 Georgia H-2A, skill II); 5% late / 110% second-shift premium", "Sourced [3]; premiums assumed"],
         ["Fruit value", "$2.43 per kg packed (about $1.10 per lb); culls $0.05 per kg", "Assumed; culls to cattle feed [6]"],
         ["Season volume", "6,000 t over 84 days, peak on day 40", "Assumed (mid-size house)"],
         ["Work rates", "Sort 1,000; pack 400 kg per worker-hour; hydrocooler 12 t/h", "Assumed"],
         ["Equipment", "$25k per hydrocooler (30 kW) and $30k per chamber (25 kW) per season; $0.12 per kWh", "Assumed"]],
        [32*mm, 88*mm, W - 120*mm], "<b>Table 1.</b> Key inputs.")

d.p("3. Methods", h1)
d.p("<b>Design study.</b> The 4,860 layouts (1&ndash;3 hydrocoolers, 4&ndash;20 sorters, 10&ndash;48 packers, 1&ndash;3 chambers, three shift "
    "plans) were each simulated over the same 5 seasons, using common random numbers [8]. The best 25 were re-evaluated over 30 "
    "fresh seasons. <b>Twin-ready loop.</b> At the start of each day the loop takes three steps. (i) <i>Ingest</i>: it reads all arrival "
    "records and stage start and finish times up to now, the data a weighbridge and bin-scanning system would log. "
    "(ii) <i>Calibrate</i>: it estimates each crew's rate as total kilograms divided by total crew working-hours, and the season's "
    "scale as observed over expected cumulative arrivals, with a pseudo-count of 10% of the season to damp early noise. "
    "(iii) <i>Re-plan</i>: it simulates the rest of the season from the current state, with every lot in progress kept at its current "
    "stage and its warm exposure so far, and chooses today's shift plan and crew sizes from 24 options. Each option is tested on the same "
    "two forecast seasons. Equipment stays fixed.")
d.p("<b>Experiment.</b> A hidden \"true\" facility runs a surprise season with 25% more fruit and packers 15% slower than planned. "
    "Three policies are compared over 6 seasons: the design-stage optimal plan held all season; daily re-planning with the original "
    "assumptions; and the full loop. The reference is a hindsight optimum, the best layout had the surprise been known at design time, "
    "found by searching all layouts again.")

d.p("4. Results", h1)
d.p("4.1 Capacity and shift planning (RQ1)", h2)
d.fig("figures/peach_costs.png", "<b>Figure 2.</b> Season cost of four designs (30 seasons each; log scale) and the share of fruit lost.", 0.88)
rows = [["Design", "Hydro / sort / pack / chambers / shift", "Cost", "Lost (%)", "Mean warm exposure (h)"]]
for k, v in PD.items():
    rows.append([k, cfgp(v["cfg"]), K(v["total"]), f"{v['lost_pct']:.1f}", f"{v['mean_exposure_h']:.1f}"])
d.table(rows, [36*mm, 54*mm, 20*mm, 16*mm, W - 126*mm], "<b>Table 2.</b> Designs compared in the planned season.")
bp = S["best_by_plan"]["peach"]
d.p(f"Sizing every stage for the average day ({CD['Rule: average day']['peach']:.1f}&times; the optimal cost) collapses at the "
    f"peak: backlogs build, warm exposure averages {PD['Rule: average day']['mean_exposure_h']:.0f} h, and "
    f"{PD['Rule: average day']['lost_pct']:.0f}% of the fruit is lost. Peak-day sizing loses only "
    f"{PD['Rule: peak day']['lost_pct']:.1f}% but pays for a crew of 62. Moving that same layout to the late shift, aligned with truck "
    f"arrivals, saves {100*(1-PD['Peak day + late shift']['total']/PD['Rule: peak day']['total']):.0f}% at no investment. The optimum "
    f"uses a <i>smaller</i> crew than even the average-day rule (8 sorters and 20 packers) but runs a double shift: "
    f"{K(pcost)}, {PD['Optimum']['lost_pct']:.1f}% lost. The best day-shift, late-shift and double-shift layouts cost "
    f"{K(bp['1'])}, {K(bp['2'])} and {K(bp['3'])}. Only {100*S['share_within_5pct']['peach']:.1f}% of all layouts come within 5% of the optimum.")

d.fig(head=[Paragraph("4.2 The twin-ready loop in a surprise season (RQ2)", h2)], path="figures/peach_twin.png", caption= "<b>Figure 3.</b> (a, b) The loop learns the true packing speed and crop size from the facility's "
      "records, speed within about two weeks and crop size within one to two months. (c) Median season cost over 6 surprise seasons (log scale).")
d.table([["Policy", "Median cost", "Median lost (%)", "Range of cost over 6 seasons"],
         ["Design-stage plan, held all season", M(tw_s), f"{TW['static']['lost_med']:.1f}", f"{M(min(TW['static']['totals']))} &ndash; {M(max(TW['static']['totals']))}"],
         ["Daily re-planning, original assumptions", M(tw_r), f"{TW['replan']['lost_med']:.1f}", f"{M(min(TW['replan']['totals']))} &ndash; {M(max(TW['replan']['totals']))}"],
         ["Twin-ready loop (ingest, calibrate, re-plan)", M(tw_t), f"{TW['twin']['lost_med']:.1f}", f"{M(min(TW['twin']['totals']))} &ndash; {M(max(TW['twin']['totals']))}"],
         ["Hindsight optimum (may change equipment)", M(ora), "&mdash;", cfgp(TW["oracle"]["cfg"])]],
        [58*mm, 24*mm, 26*mm, W - 108*mm], "<b>Table 3.</b> Operating the surprise season.")
d.p(f"The design-stage optimum is efficient but <b>fragile</b>. Tuned to the planned volume, it has no slack: with 25% more fruit and "
    f"slower packing, queues never clear and {TW['static']['lost_med']:.0f}% of the fruit is lost. Re-planning daily from the live state "
    f"helps a great deal ({M(tw_r)}), but it keeps under-staffing because it still believes the original speed and volume. Adding "
    f"calibration halves the cost again, to {M(tw_t)}. The loop's estimates converge on the true packing speed (340 against an assumed 400 "
    f"kg/h) and crop size (&times;1.25), the speed within about two weeks and the crop size within one to two months (Fig. 3a&ndash;b). It responds by adding packers and keeping the double shift through "
    f"the peak, then scaling back as volumes fall (Fig. 4). The result is within {100*(tw_t/ora-1):.0f}% of a hindsight design that "
    f"bought a second hydrocooler.")
d.fig("figures/peach_twin_decisions.png", "<b>Figure 4.</b> Decisions taken by the loop in one surprise season: packers scheduled and "
      "shift plan each day, against daily arrivals.")

d.p("5. Discussion", h1)
d.p("<b>Implications for operations.</b> (i) In both the design and the operation of a packinghouse, <i>when</i> crews work matters as much as "
    "how many there are. (ii) A cost-optimal design has no buffer, so it should be paired with a way of detecting and reacting to deviations "
    "within days. (iii) Under labour scarcity, the cheapest reaction is adaptive scheduling of the crew you can get, rather than a "
    "larger crew hired for the whole season.")
d.p(f"<b>From model to twin.</b> {TWIN_DEF} What a real deployment would still need: automatic data capture (weighbridge or bin "
    "scans at receiving, line counters, cooler logs, quality checks on rejects); validation of the model against several weeks of real "
    "records before any recommendation is trusted; and a manager approving each day's plan at first. The calibration demonstrated here "
    "covers speed and volume only. Shelf-life parameters would need quality-inspection data.")
d.p("<b>Limitations.</b> The facility is representative, not a specific company. Work rates, volumes, prices and equipment costs are "
    "assumptions. The quality model is a simple life budget with no cultivar effects and no chilling injury. The loop is tested only on "
    "synthetic data with two deliberately introduced deviations, so performance on a real data stream (gaps, errors, delays) is untested.")
d.p("6. Conclusion", h1)
d.p(f"For a representative Georgia peach packinghouse, a modest crew on a double shift minimizes season cost ({K(pcost)}), and common "
    f"sizing rules cost 7&ndash;1,250% more. Optimal designs are fragile when the season departs from plan. A twin-ready loop that "
    f"recalibrates from operational records and re-plans daily cut a surprise season's cost from {M(tw_s)} to {M(tw_t)}. Connected to a "
    f"real facility's data, the same loop is the core of a digital shadow, and closing the feedback makes it a digital twin.")
d.p("<b>Code and data.</b> All numbers and figures are reproduced by <font face='Courier'>scripts/01&ndash;04</font>.")
d.refs(["FAO, International Day of Awareness of Food Loss and Waste 2025: 13.3% of production lost between harvest and retail; fruit and vegetables 25.4%. fao.org",
        "American Farm Bureau Federation, Market Intel: H-2A program use continues to soar (FY2025: 398,258 certified positions). fb.org",
        "Specialty Crop Grower, New AEWRs announced for southeastern states (2026; Georgia skill II $14.72). specialtycropgrower.com",
        "University of Georgia Extension, Bulletin B1555: Peaches, appropriate harvest and postharvest handling. fieldreport.caes.uga.edu",
        "UC Davis Postharvest Center, Produce Facts: Peach and Nectarine. postharvest.ucdavis.edu",
        "C.H. Crisosto, D. Valero, Harvesting and postharvest handling of peaches for the fresh market, in <i>The Peach: Botany, Production and Uses</i>, CAB International, 2008.",
        "University of Georgia Extension, Peaches (Georgia produces over 130 million pounds per year). extension.uga.edu",
        "A.M. Law, <i>Simulation Modeling and Analysis</i>, 5th ed., McGraw-Hill, 2015.",
        "W. Kritzinger, M. Karner, G. Traar, J. Henjes, W. Sihn, Digital twin in manufacturing: a categorical literature review and classification, <i>IFAC-PapersOnLine</i> 51(11) (2018) 1016&ndash;1022."])
d.build("Peach_Packinghouse_Report.pdf", T1)

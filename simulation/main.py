"""Run the whole simulation study with one command and open the results.

    python main.py              # 1000 simulated sessions per policy (about a minute)
    python main.py --quick      # 150 sessions: fast preview
    python main.py --reps 1000  # report quality
    python main.py --no-open    # do not open the browser

Steps: 1 policy comparison, 2 what each layer adds, 3 dashboard (with charts), 4 appointment templates,
5 live simulation of one clinic day (SimPy event log in the terminal + animation in the browser),
6 whole days: every real appointment record of each test day.
Everything is collected on output/index.html, which opens in the browser at the end.

Risk source: ../ml/data/processed/risks_random_forest.csv if it exists (created by ml/build_reports.py),
otherwise synthetic risks only.
"""
import argparse
import html
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
TEMPLATES = HERE / "templates"
RISKS = HERE.parent / "ml" / "data" / "processed" / "risks_random_forest.csv"
RISKS_ALL = HERE.parent / "ml" / "data" / "processed" / "risks_all_days.csv"  # out-of-sample risks for every day


def step(number: int, total: int, title: str, args: list[str]) -> None:
    print(f"\n{'=' * 78}\n[{number}/{total}] {title}\n{'=' * 78}", flush=True)
    start = time.time()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run([sys.executable, *args], cwd=HERE, env=env)
    if result.returncode != 0:
        sys.exit(f"\nStep {number} failed ({title}). Fix the error above and run main.py again.")
    print(f"-- done in {time.time() - start:.0f} s", flush=True)


PAGE_CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--mute:#667085;--line:#e4e7ec;--acc:#2a6f97}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f141c;--card:#171e29;--ink:#e8ecf3;--mute:#93a0b4;--line:#2a3445;--acc:#6bb1d8}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0}h2{font-size:17px;margin:28px 0 8px}p,small,span.d{color:var(--mute)}a.back{color:var(--acc);text-decoration:none;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;display:block;color:var(--ink);text-decoration:none}
a.link:hover{border-color:var(--acc)}a.link b{font-size:17px}a.link .d{display:block;margin-top:6px}a.link .go{display:block;margin-top:10px;color:var(--acc);font-size:13px;font-weight:600}
.badge{background:var(--acc);color:#fff;border-radius:6px;padding:1px 8px;font-size:11px;margin-left:8px;vertical-align:2px}
img{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}ul{color:var(--mute)}li{margin:4px 0}
"""


def page(title: str, intro: str, body: str, back: bool = True) -> str:
    link = '<a class="back" href="index.html">&larr; All results</a><br><br>' if back else ""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{PAGE_CSS}</style></head><body><main>{link}"
            f"<h1>{html.escape(title)}</h1><p>{intro}</p>{body}</main></body></html>")


def cards_html(cards: list[tuple]) -> str:
    """cards: (title, href, description, call to action, optional badge)."""
    out = ""
    for c in cards:
        title, href, desc, cta = c[:4]
        badge = f'<span class="badge">{html.escape(c[4])}</span>' if len(c) > 4 and c[4] else ""
        out += (f"<a class='card link' href='{href}'><b>{html.escape(title)}</b>{badge}"
                f"<span class='d'>{desc}</span><span class='go'>{html.escape(cta)} &rarr;</span></a>")
    return f"<div class='grid'>{out}</div>"


def write_index() -> Path:
    OUT.mkdir(exist_ok=True)
    winner_key, winner_html = "", ""
    info = TEMPLATES / "winner" / "result.json"
    if info.exists():
        w = json.loads(info.read_text(encoding="utf-8"))
        winner_key = w["key"]
        m, d = w["metrics"], w["vs_current_fixed"]
        winner_html = (f"<div class='card'><b>Winner: {html.escape(w['template'])}</b> (threshold {w['threshold']})<br>"
                       f"Patients seen {m['seen']:.1f} ({d['seen']:+.1f}), mean wait {m['mean_wait']:.1f} min ({d['mean_wait']:+.1f}), "
                       f"idle {m['idle']:.0f} min ({d['idle']:+.0f}), overtime {m['overtime']:.1f} min ({d['overtime']:+.1f}) per clinic session.<br>"
                       f"<small>Rule: {html.escape(w['rule'])}. Differences are against the current fixed 15-minute template.</small></div>")

    # ---- Simulation hub
    sim = page("Simulation", "Watch the clinic run. Both pages replay real appointment records and compare fixed-interval booking "
               "with overbooking on the same patients. They differ in how much you see.",
               cards_html([
                   ("Live simulation", "live_simulation.html",
                    "<b>Choose this to understand how it works.</b> One doctor, one example day with 20 patients. You see every patient arrive, "
                    "wait and get seen, one by one, and you can pause and replay it. Fixed interval and overbooking run on the same patients, one above the other.",
                    "Watch one doctor's day"),
                   ("Whole days", "whole_day.html",
                    "<b>Choose this to see the full picture.</b> Every real appointment of a day (about 4,400 patients) spread over about 220 doctors. "
                    "Each square is a doctor; counters and charts show the whole day. You also get the totals and a table of every record, "
                    "with the risk each rule and model gave.",
                    "See every record of a day")]))
    (OUT / "simulation_hub.html").write_text(sim, encoding="utf-8")

    # ---- Templates hub
    tpl = [("Template 1 - short slots", "../templates/html/t1_short_slots.html", "t1_short_slots",
            "20 slots of 12 minutes and no overbooking. The slot is matched to the real consultation length, so no patient is added on top of another."),
           ("Template 2 - staggered overbooking", "../templates/html/t2_staggered_overbooking.html", "t2_staggered_overbooking",
            "Normal 15-minute slots. When a slot is overbooked, the second patient is asked to come in the middle of the slot instead of at the same time."),
           ("Template 3 - buffer + late overbooking", "../templates/html/t3_buffer_late_overbooking.html", "t3_buffer_late_overbooking",
            "One empty slot in the middle of the session to catch up on delays. Overbooking is allowed only in the second half.")]
    tpls = page("Templates", "A template is the way a doctor's session is cut into appointment slots. These are the three we designed and tested. "
                "Open one to see how the session is laid out and which rules it uses.",
                cards_html([(t, h, d, "See how it is built", "Winner" if k == winner_key else "") for t, h, k, d in tpl]) +
                "<h2>Which one is better?</h2><p>Open <b>Template comparison</b> on the main page: it tests the three templates on every real appointment "
                "and picks the winner by a stated rule.</p>")
    (OUT / "templates_hub.html").write_text(tpls, encoding="utf-8")

    # ---- Charts: hub and one page per chart
    charts = [
        ("Idle time vs waiting time", "chart_tradeoff.html", "tradeoff.png",
         "Shows the price of overbooking. The more aggressive the rule, the less the doctor is idle, but the longer patients wait.",
         ["<b>Left chart:</b> each dot is one overbooking rule (the number is its risk threshold; &ldquo;fixed&rdquo; = no overbooking). "
          "Further left = the doctor is idle less. Higher = patients wait longer. Moving along the line trades one for the other.",
          "<b>Right chart:</b> for the same rules, blue = patients seen per session, orange = overtime in minutes. Lower thresholds see more patients but create more overtime.",
          "The small crosses are 95% confidence intervals: if they are tiny, the difference is real, not luck."]),
        ("One session, side by side", "chart_timeline.html", "timeline.png",
         "One doctor's morning with and without overbooking, drawn on a time line, so you can see where the extra patients go.",
         ["Each row is one patient. <b>Blue</b> bar: the consultation. <b>Yellow</b> bar before it: the time the patient waited. "
          "<b>Orange</b>: a patient added by overbooking. The black tick is the appointment time; the red dashed line is the planned end of the session.",
          "Top = fixed interval, bottom = overbooking, with the same patients. Look at the bottom chart: where the yellow bars appear, overbooking caused a wait; "
          "where the top chart has gaps, the doctor was idle."]),
        ("What each layer adds", "chart_ladder.html", "value_ladder.png",
         "Compares five ways of booking, from doing nothing to knowing exactly who will not come, to show what the prediction model adds.",
         ["The numbers 0 to 3 and * on the bars: <b>0</b> fixed interval (nothing applied), <b>1</b> blind overbooking (double-book without knowing who will miss), "
          "<b>2</b> overbooking with the model's risk (threshold), <b>3</b> cost rule, <b>*</b> perfect knowledge (best any model could do).",
          "Three panels: patients seen, doctor idle time, patient waiting time. Plain bars use made-up but well-calibrated risks; hatched bars use the real model.",
          "How to read it: bar 1 gains the most patients but also the longest waits; bars 2 and 3 keep most of the gain with much shorter waits; "
          "bar * shows how much better a perfect model would be."])]
    for title, fname, img, what, how in charts:
        body = (f"<div class='card'><b>What is this?</b><br>{what}</div><h2>How to read it</h2><ul>{''.join(f'<li>{h}</li>' for h in how)}</ul>"
                + (f"<img src='{img}' alt='{html.escape(title)}'>" if (OUT / img).exists() else "<p>Chart not found: run main.py.</p>"))
        (OUT / fname).write_text(page(title, what, body).replace('<a class="back" href="index.html">&larr; All results</a>',
                                  '<a class="back" href="charts_hub.html">&larr; All charts</a> &middot; <a class="back" href="index.html">Main page</a>'),
                                 encoding="utf-8")
    ch = page("Charts", "Three charts that explain the results. Pick the one that answers your question.",
              cards_html([(t, f, w, "Open the chart") for t, f, _, w, _ in charts]))
    (OUT / "charts_hub.html").write_text(ch, encoding="utf-8")

    # ---- Main page: 3 group cards + 3 result cards
    cards = [("Simulation", "simulation_hub.html",
              "Watch the clinic run on real appointment records: one doctor's example day, or every record of a whole day.", "Choose a simulation"),
             ("Templates", "templates_hub.html",
              "The three ways we designed to cut a doctor's session into appointment slots. See how each one is built.", "Choose a template"),
             ("Charts", "charts_hub.html",
              "Three charts that explain the results: the idle-time versus waiting-time trade-off, one session side by side, and what each layer adds.", "Choose a chart"),
             ("Dashboard", "dashboard.html",
              "KPI cards: pick a booking policy and see how it compares with fixed-interval booking on patients seen, waiting, idle time and overtime.", "Open the dashboard"),
             ("Template comparison", "../templates/results/comparison.html",
              "The three templates tested on all 27 real days: overall result first, then a table for each day, in counts and percentages.", "See the comparison"),
             ("Winning template", "../templates/winner/winner.html",
              "The template picked by the stated rule, with its layout and rules.", "See the winner")]
    index = page("Simulation results", f"Generated {time.strftime('%Y-%m-%d %H:%M')}. Parameters (slot length, consultation time, lateness) "
                 "are assumptions, not measured values.", winner_html + cards_html(cards), back=False)
    path = OUT / "index.html"
    path.write_text(index, encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=1000, help="simulated sessions per policy")
    ap.add_argument("--quick", action="store_true", help="150 sessions, fast preview")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = ap.parse_args()
    reps = 150 if args.quick else args.reps

    risks = ["--risks", str(RISKS)] if RISKS.exists() else []
    print(f"Sessions per policy: {reps}")
    print("Risk source:", "random forest predictions" if risks else "synthetic only (run ml/build_reports.py to create the model risks)")
    began = time.time()
    step(1, 6, "Policy comparison (fixed interval vs threshold vs cost rule)", ["clinic_sim.py", "--reps", str(reps), *risks])
    step(2, 6, "What each layer adds (blind overbooking, model, oracle)", ["value_ladder.py", "--reps", str(reps), *risks])
    step(3, 6, "Dashboard and charts", ["dashboard.py", "--reps", str(reps), *risks])
    step(4, 6, "Appointment templates (compare and pick the winner)",
         [str(TEMPLATES / "compare_templates.py"), "--reps", str(reps), *(["--risks", str(RISKS_ALL if RISKS_ALL.exists() else RISKS)] if risks else [])])
    for t in ("t1_short_slots", "t2_staggered_overbooking", "t3_buffer_late_overbooking"):
        subprocess.run([sys.executable, str(TEMPLATES / f"{t}.py")], cwd=TEMPLATES, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       stdout=subprocess.DEVNULL, check=True)

    step(5, 6, "Live simulation of one clinic day (SimPy event log, day 1)", ["live_day.py", "--trace", "--day", "1", "--no-open", *risks])

    step(6, 6, "Whole days: every real appointment record of each day", ["real_days.py", "--no-open"])

    index = write_index()
    live = OUT / "live_simulation.html"
    print(f"\nAll done in {time.time() - began:.0f} s.")
    print(f"  Live simulation (animation): {live}")
    print(f"  Results page (all outputs):  {index}")
    if not args.no_open:
        for page in (live, index):
            if not webbrowser.open(page.as_uri()) and hasattr(os, "startfile"):
                os.startfile(page)  # Windows fallback: opens the file in the default browser
        print("Opened both pages in your browser. If nothing opened, double-click the two files above.")


if __name__ == "__main__":
    main()

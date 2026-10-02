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


def write_index() -> Path:
    cards = [
        ("Live simulation (animation)", "live_simulation.html", "Watch a clinic day run: patients, waiting room, physician; fixed interval vs overbooking"),
        ("Whole days (all records)", "whole_day.html", "Every real appointment of a day over ~220 clinic sessions: totals, animation, record table"),
        ("Dashboard", "dashboard.html", "KPI cards: pick a policy and compare it with fixed-interval booking"),
        ("Template comparison", "../templates/results/comparison.html", "The three appointment templates tested on identical sessions"),
        ("Winning template", "../templates/winner/winner.html", "The template picked by the stated rule"),
        ("Template 1 - short slots", "../templates/html/t1_short_slots.html", "20 slots of 12 min, no overbooking"),
        ("Template 2 - staggered overbooking", "../templates/html/t2_staggered_overbooking.html", "Second patient starts half a slot later"),
        ("Template 3 - buffer + late overbooking", "../templates/html/t3_buffer_late_overbooking.html", "Empty buffer slot, overbooking in the second half"),
    ]
    images = [("Idle time vs waiting time", "tradeoff.png"), ("One session, side by side", "timeline.png"),
              ("What each layer adds", "value_ladder.png")]
    winner = ""
    info = TEMPLATES / "winner" / "result.json"
    if info.exists():
        w = json.loads(info.read_text(encoding="utf-8"))
        m, d = w["metrics"], w["vs_current_fixed"]
        winner = (f"<div class='card'><b>Winner: {html.escape(w['template'])}</b> (threshold {w['threshold']})<br>"
                  f"Patients seen {m['seen']:.1f} ({d['seen']:+.1f}), mean wait {m['mean_wait']:.1f} min ({d['mean_wait']:+.1f}), "
                  f"idle {m['idle']:.0f} min ({d['idle']:+.0f}), overtime {m['overtime']:.1f} min ({d['overtime']:+.1f}).<br>"
                  f"<small>Rule: {html.escape(w['rule'])}. Differences are against the current fixed 15-minute template.</small></div>")
    links = "".join(f"<a class='card link' href='{href}'><b>{html.escape(t)}</b><br><span>{html.escape(d)}</span></a>"
                    for t, href, d in cards)
    pics = "".join(f"<h2>{html.escape(t)}</h2><img src='{f}' alt='{html.escape(t)}'>" for t, f in images if (OUT / f).exists())
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Simulation results</title><style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--mute:#667085;--line:#e4e7ec;--acc:#2a6f97}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#0f141c;--card:#171e29;--ink:#e8ecf3;--mute:#93a0b4;--line:#2a3445;--acc:#6bb1d8}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}}main{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:22px;margin:0}}h2{{font-size:17px;margin:28px 0 8px}}p,small,span{{color:var(--mute)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-top:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:block;color:var(--ink);text-decoration:none}}
a.link:hover{{border-color:var(--acc)}}img{{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}}
</style></head><body><main><h1>Simulation results</h1>
<p>Generated {time.strftime('%Y-%m-%d %H:%M')}. Parameters (slot length, consultation time, lateness) are assumptions, not measured values.</p>
{winner}<div class="grid">{links}</div>{pics}</main></body></html>"""
    path = OUT / "index.html"
    OUT.mkdir(exist_ok=True)
    path.write_text(doc, encoding="utf-8")
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

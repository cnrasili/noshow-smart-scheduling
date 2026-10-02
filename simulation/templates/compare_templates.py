"""Test the three templates on identical sessions and save the winner to templates/winner/.

    python compare_templates.py --risks ../../ml/data/processed/risks_random_forest.csv

Selection rule (stated up front, change it with --max-wait / --max-overtime):
  1. a template is feasible if mean waiting time <= MAX_WAIT and mean overtime <= MAX_OVERTIME minutes;
  2. among feasible templates the winner sees the most patients per session (ties: less physician idle time);
  3. the paired difference to the current fixed-interval template is reported with a 95 % confidence interval.
"""
import argparse
import dataclasses
import html
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from template_base import REQUESTS, Template, render_html
from t1_short_slots import TEMPLATE as T1
from t2_staggered_overbooking import TEMPLATE as T2
from t3_buffer_late_overbooking import TEMPLATE as T3
from clinic_sim import SessionConfig, draw_session, simulate_session

HERE = Path(__file__).parent
RESULTS = HERE / "results"
WINNER = HERE / "winner"

# Reference: what the project does today (not eligible to win)
CURRENT_FIXED = Template("current_fixed", "Current - fixed interval 15 min", "Today's baseline.", 16, 15)
CURRENT_OB = Template("current_overbooking", "Current - same-time overbooking", "Overbooked patient starts with the first.",
                      16, 15, threshold=0.30)
METRICS = ["seen", "mean_wait", "idle", "overtime", "utilization", "overbooked_slots"]


def evaluate(templates: list[Template], pool, reps: int, seed: int, base: SessionConfig) -> pd.DataFrame:
    rows = []
    cfgs = {t.key: t.config(base) for t in templates}
    for rep in range(reps):
        # all templates share the same booking requests, attendance, arrival offsets and service times
        d = draw_session(cfgs[templates[0].key], np.random.default_rng([seed, rep]), pool)
        for t in templates:
            rows.append({"key": t.key, "rep": rep, **simulate_session(cfgs[t.key], t.policy(), d, layout=t.layout())})
    return pd.DataFrame(rows)


def summary(res: pd.DataFrame, ref_key: str) -> pd.DataFrame:
    ref = res[res.key == ref_key].set_index("rep")
    out = []
    for key, g in res.groupby("key", sort=False):
        g = g.set_index("rep")
        row = {"key": key}
        for m in METRICS:
            row[m] = g[m].mean()
            row[m + "_ci"] = 1.96 * g[m].std(ddof=1) / np.sqrt(len(g))
            diff = g[m] - ref[m]
            row[m + "_d"] = diff.mean()
            row[m + "_dci"] = 1.96 * diff.std(ddof=1) / np.sqrt(len(g)) if key != ref_key else 0.0
        out.append(row)
    return pd.DataFrame(out).set_index("key")


def best_threshold(t: Template, pool, reps, seed, base, max_wait, max_ot):
    """Tune the threshold of an overbooking template on the same sessions; return (template, summary row, all rows)."""
    if t.threshold is None:
        return t, None, []
    cands = [t.with_threshold(x) for x in t.thresholds_to_try]
    cands = [dataclasses.replace(c, key=f"{t.key}@{c.threshold:.2f}") for c in cands]
    res = evaluate(cands, pool, reps, seed, base)
    s = summary(res, cands[0].key)
    s["feasible"] = (s.mean_wait <= max_wait) & (s.overtime <= max_ot)
    pick = s[s.feasible].sort_values(["seen", "idle"], ascending=[False, True]) if s.feasible.any() else \
        s.assign(v=s.mean_wait / max_wait + s.overtime / max_ot).sort_values("v")
    best_key = pick.index[0]
    return next(c for c in cands if c.key == best_key), s, s


def fmt(v, ci=None, sign=False):
    s = f"{v:+.1f}" if sign else f"{v:.1f}"
    return s + (f" ±{ci:.1f}" if ci is not None else "")


def comparison_html(rows, winner_key, max_wait, max_ot, reps, tuned) -> str:
    head = "".join(f"<th>{h}</th>" for h in ["Template", "Patients seen", "Mean wait (min)", "Idle (min)", "Overtime (min)",
                                              "Utilization", "Feasible"])
    body = ""
    for r in rows:
        cls = ' class="win"' if r["key"] == winner_key else ""
        feas = "yes" if r["feasible"] else "no"
        body += (f"<tr{cls}><td>{html.escape(r['name'])}{' &#9733; WINNER' if r['key'] == winner_key else ''}</td>"
                 f"<td>{fmt(r['seen'], r['seen_ci'])} ({fmt(r['seen_d'], r['seen_dci'], True)})</td>"
                 f"<td>{fmt(r['mean_wait'], r['mean_wait_ci'])} ({fmt(r['mean_wait_d'], r['mean_wait_dci'], True)})</td>"
                 f"<td>{fmt(r['idle'], r['idle_ci'])} ({fmt(r['idle_d'], r['idle_dci'], True)})</td>"
                 f"<td>{fmt(r['overtime'], r['overtime_ci'])} ({fmt(r['overtime_d'], r['overtime_dci'], True)})</td>"
                 f"<td>{r['utilization'] * 100:.1f}%</td><td>{feas}</td></tr>")
    tuned_txt = "; ".join(f"{k}: threshold {v:.2f}" for k, v in tuned.items())
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Template comparison</title><style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--mute:#667085;--line:#e4e7ec;--win:#e6f4ea}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#0f141c;--card:#171e29;--ink:#e8ecf3;--mute:#93a0b4;--line:#2a3445;--win:#173a26}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}}main{{max-width:1180px;margin:0 auto;padding:24px 16px}}
h1{{font-size:21px;margin:0 0 4px}}p,small{{color:var(--mute)}}table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);font-size:13px}}
th,td{{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line)}}th:first-child,td:first-child{{text-align:left}}th{{color:var(--mute)}}tr.win td{{background:var(--win);font-weight:600}}
.wrap{{overflow-x:auto}}</style></head><body><main><h1>Template comparison</h1>
<p>{reps} simulated sessions, {REQUESTS} booking requests per session, identical sessions for every template. Values: mean ±95% CI (difference to the current fixed-interval template).</p>
<p>Winner rule: feasible = mean wait ≤ {max_wait:g} min and mean overtime ≤ {max_ot:g} min; among feasible templates, the most patients seen. Tuned: {html.escape(tuned_txt)}.</p>
<div class="wrap"><table><tr>{head}</tr>{body}</table></div>
<p><small>Thresholds, buffer position and the feasibility limits are assumptions to be agreed. Results hold for the simulation parameters in clinic_sim.py.</small></p></main></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--risks", default=str(HERE.parents[1] / "ml" / "data" / "processed" / "risks_random_forest.csv"))
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-wait", type=float, default=5.0)
    ap.add_argument("--max-overtime", type=float, default=5.0)
    args = ap.parse_args()
    base = SessionConfig()
    pool = pd.read_csv(args.risks) if Path(args.risks).exists() else None
    print("Risk source:", "random forest predictions" if pool is not None else "synthetic Beta risks")

    tuned_templates, tuned = [], {}
    for t in (T1, T2, T3):
        bt, _, _ = best_threshold(t, pool, args.reps, args.seed, base, args.max_wait, args.max_overtime)
        tuned_templates.append(bt)
        if bt.threshold is not None:
            tuned[t.key] = bt.threshold
    allt = [CURRENT_FIXED, CURRENT_OB] + tuned_templates
    res = evaluate(allt, pool, args.reps, args.seed, base)
    s = summary(res, CURRENT_FIXED.key)
    s["feasible"] = (s.mean_wait <= args.max_wait) & (s.overtime <= args.max_overtime)
    names = {t.key: t.name for t in allt}
    rows = [{"key": k, "name": names[k], **s.loc[k].to_dict()} for k in s.index]

    cand = s.loc[[t.key for t in tuned_templates]]
    pool_c = cand[cand.feasible] if cand.feasible.any() else cand.assign(v=cand.mean_wait + cand.overtime).sort_values("v")
    winner_key = pool_c.sort_values(["seen", "idle"], ascending=[False, True]).index[0] if cand.feasible.any() else pool_c.index[0]
    winner = next(t for t in tuned_templates if t.key == winner_key)
    w = s.loc[winner_key]

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "comparison.html").write_text(comparison_html(rows, winner_key, args.max_wait, args.max_overtime, args.reps, tuned),
                                            encoding="utf-8")
    s.to_csv(RESULTS / "results.csv")
    print(pd.DataFrame({"template": [names[k][:48] for k in s.index], "seen": s.seen.round(1), "wait": s.mean_wait.round(1),
                        "idle": s.idle.round(1), "overtime": s.overtime.round(1), "feasible": s.feasible}).to_string(index=False))

    # ---- save the winner under templates/winner/
    if WINNER.exists():
        shutil.rmtree(WINNER)
    WINNER.mkdir()
    render_html(winner, WINNER / "winner.html", note=f"WINNER: {winner.name} (threshold {winner.threshold})")
    src = HERE / (winner.key.split("@")[0] + ".py")
    shutil.copy(src, WINNER / ("winner_" + src.name))
    shutil.copy(HERE / "template_base.py", WINNER / "template_base.py")
    info = {"template": winner.name, "key": winner.key.split("@")[0], "threshold": winner.threshold, "slots": winner.n_slots,
            "slot_min": winner.slot_min, "blocked": winner.blocked, "overbook_slots": winner.overbook_slots, "offset": winner.offset,
            "rule": f"feasible = mean wait <= {args.max_wait} and overtime <= {args.max_overtime}; most patients seen",
            "sessions": args.reps, "metrics": {m: round(float(w[m]), 3) for m in METRICS},
            "vs_current_fixed": {m: round(float(w[m + "_d"]), 3) for m in METRICS}}
    (WINNER / "result.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    (WINNER / "result.md").write_text(
        f"# Winner: {winner.name}\n\nSelection rule: mean wait <= {args.max_wait:g} min, mean overtime <= {args.max_overtime:g} min, "
        f"then most patients seen ({args.reps} sessions, {REQUESTS} requests).\n\n"
        f"| Metric | Winner | Difference to current fixed 15 min |\n|---|---|---|\n"
        + "".join(f"| {m} | {w[m]:.2f} | {w[m + '_d']:+.2f} ± {w[m + '_dci']:.2f} |\n" for m in METRICS), encoding="utf-8")
    print("\nWinner:", winner.name, "| saved to", WINNER)


if __name__ == "__main__":
    main()

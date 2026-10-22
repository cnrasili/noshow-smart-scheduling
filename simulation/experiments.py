"""Replicated, paired simulation experiments for the IEN report.

Adds to clinic_sim.py (which is not changed): many replications on the same random sessions
(common random numbers), 95 % confidence intervals and effect sizes of the paired differences,
a threshold x daily-limit grid, short-slot and offset templates combined with overbooking,
sensitivity analyses and a hypothetical reminder scenario.

Session settings, threshold, daily limit and the waiting limit come from docs/decisions.json.

    python simulation/experiments.py            # full run (about a minute)
    python simulation/experiments.py --quick    # small run to check the code
    python simulation/experiments.py --risks ml/data/processed/risks_decision_model.csv

Risks and show-ups come from out-of-sample predictions of all 27 days. Slot length, consultation
time, lateness and demand are decisions or assumptions (docs/decision-list.md).
"""

from __future__ import annotations

import argparse
import json
import platform
from dataclasses import replace
from pathlib import Path

import clinic_sim as cs
import numpy as np
import pandas as pd
import scipy
import simpy
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
RISKS = HERE.parent / "ml" / "data" / "processed" / "risks_all_days.csv"
OUT = HERE / "results_experiments"
REPORT = DOCS / "experiment-results.md"
SUMMARY = DOCS / "results-summary.md"
METRICS = ["seen", "mean_wait", "idle", "overtime", "utilization"]
LABELS = {
    "seen": "Patients seen",
    "mean_wait": "Mean wait (min)",
    "idle": "Idle time (min)",
    "overtime": "Overtime (min)",
    "utilization": "Utilization",
}
SEED = 20261016
MODEL_NAMES = {"random_forest": "Random forest", "decision_tree": "Decision tree"}


def load_decisions(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def session_config(d: dict) -> cs.SessionConfig:
    return cs.SessionConfig(
        n_slots=int(d["n_slots"]),
        slot_min=float(d["slot_min"]),
        service_mean=float(d["service_mean_min"]),
        service_cv=float(d["service_cv"]),
        punctuality_sd=float(d["lateness_sd_min"]),
        extra_requests=int(d["extra_requests"]),
    )


def run_cases(cases, ref_cfg, reps, seed, pool, transform=None) -> pd.DataFrame:
    """Every case sees the same random session; `cases` maps name -> (cfg, policy, layout)."""
    rows = []
    for rep in range(reps):
        d = cs.draw_session(ref_cfg, np.random.default_rng([seed, rep]), pool)
        if transform is not None:
            d = transform(d, np.random.default_rng([seed, rep, 1]))
        for name, (cfg, policy, layout) in cases.items():
            rows.append(
                {"case": name, "rep": rep, **cs.simulate_session(cfg, policy, d, layout=layout)}
            )
    return pd.DataFrame(rows)


def paired(res: pd.DataFrame, base: str) -> pd.DataFrame:
    """Paired difference to `base`: mean, 95 % CI, relative change and Cohen's d_z."""
    b = res[res.case == base].set_index("rep")
    rows = []
    for name, g in res.groupby("case", sort=False):
        if name == base:
            continue
        g = g.set_index("rep")
        for m in METRICS:
            diff = g[m] - b[m]
            sd = diff.std(ddof=1)
            half = 1.96 * sd / np.sqrt(len(diff))
            rows.append(
                {
                    "case": name,
                    "metric": m,
                    "base_mean": b[m].mean(),
                    "case_mean": g[m].mean(),
                    "diff": diff.mean(),
                    "ci_low": diff.mean() - half,
                    "ci_high": diff.mean() + half,
                    "rel_pct": 100 * diff.mean() / b[m].mean() if b[m].mean() else np.nan,
                    "d_z": diff.mean() / sd if sd > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def means(res: pd.DataFrame) -> pd.DataFrame:
    return res.groupby("case", sort=False)[METRICS + ["overbooked_slots", "deferred"]].mean()


def md_table(df: pd.DataFrame, fmt: str = "{:,.2f}") -> str:
    head = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    body = [
        "| "
        + " | ".join(fmt.format(v) if isinstance(v, float | np.floating) else str(v) for v in row)
        + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join([head, sep, *body])


def paired_md(tab: pd.DataFrame) -> str:
    """One row per case, one cell per metric: difference [95 % CI] (d_z)."""
    out = []
    for name, g in tab.groupby("case", sort=False):
        row = {"Scenario": name}
        for r in g.itertuples():
            row[LABELS[r.metric]] = (
                f"{r.diff:+.2f} [{r.ci_low:+.2f}; {r.ci_high:+.2f}] (d={r.d_z:+.2f})"
            )
        out.append(row)
    return md_table(pd.DataFrame(out))


def pareto(df: pd.DataFrame) -> pd.Series:
    """Non-dominated cases: more patients seen, less waiting, idle time and overtime."""
    keep = []
    for i, a in df.iterrows():
        dominated = False
        for j, b in df.iterrows():
            if i == j:
                continue
            better = (
                b.seen >= a.seen
                and b.mean_wait <= a.mean_wait
                and b.idle <= a.idle
                and b.overtime <= a.overtime
            )
            strictly = (
                b.seen > a.seen
                or b.mean_wait < a.mean_wait
                or b.idle < a.idle
                or b.overtime < a.overtime
            )
            if better and strictly:
                dominated = True
                break
        keep.append(not dominated)
    return pd.Series(keep, index=df.index)


# --------------------------------------------------------------------------- experiments
def rule_of(d: dict):
    return cs.threshold_rule(
        d["threshold"], max_per_slot=d["max_per_slot"], daily_limit=d["daily_limit"]
    )


def rule_name(d: dict) -> str:
    return f"Decided setting (threshold {round(100 * d['threshold'])}%, limit {d['daily_limit']})"


BASE_NAME = "Fixed intervals (no rule)"


def exp_main(cfg, pool, reps, d):
    lim, mps = d["daily_limit"], d["max_per_slot"]
    lay = cs.DEFAULT_LAYOUT
    cases = {
        BASE_NAME: (cfg, cs.fixed_interval(), lay),
        rule_name(d): (cfg, rule_of(d), lay),
        "Threshold 20%": (cfg, cs.threshold_rule(0.20, mps, lim), lay),
        "Threshold 40%": (cfg, cs.threshold_rule(0.40, mps, lim), lay),
        "Cost rule r=0.5": (cfg, cs.cost_rule(0.5, mps, lim), lay),
        "Cost rule r=1.0": (cfg, cs.cost_rule(1.0, mps, lim), lay),
        "Airline rule": (cfg, cs.expected_value_rule(mps, lim), lay),
    }
    res = run_cases(cases, cfg, reps, SEED, pool)
    return res, paired(res, BASE_NAME)


def grid_key(thr: float, lim: int) -> str:
    return f"thr{round(100 * thr)}_lim{lim}"


def exp_grid(cfg, pool, reps, d):
    thresholds = sorted({0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, d["threshold"]})
    limits = sorted({1, 2, 4, 6, 8, d["daily_limit"]})
    cases = {"fixed": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT)}
    for thr in thresholds:
        for lim in limits:
            cases[grid_key(thr, lim)] = (
                cfg,
                cs.threshold_rule(thr, max_per_slot=d["max_per_slot"], daily_limit=lim),
                cs.DEFAULT_LAYOUT,
            )
    res = run_cases(cases, cfg, reps, SEED + 1, pool)
    m = means(res)
    m["pareto"] = pareto(m)
    return res, m


def exp_templates(cfg, pool, reps, d):
    n, s = cfg.n_slots, cfg.slot_min
    short = replace(
        cfg, n_slots=round(n * 1.25), slot_min=round(s * 0.8, 2), requests=cfg.n_requests
    )
    cfg = replace(cfg, requests=cfg.n_requests)  # same demand for every layout
    rule, fixed = rule_of(d), cs.fixed_interval()
    off = cs.Layout(offset=0.5)
    base = f"{n}x{s:g} fixed (base)"
    sn, ss = short.n_slots, short.slot_min
    cases = {
        base: (cfg, fixed, cs.DEFAULT_LAYOUT),
        f"{n}x{s:g} + decided setting": (cfg, rule, cs.DEFAULT_LAYOUT),
        f"{n}x{s:g} + decided setting + offset 0.5": (cfg, rule, off),
        f"{sn}x{ss:g} short slots fixed": (short, fixed, cs.DEFAULT_LAYOUT),
        f"{sn}x{ss:g} short slots + decided setting": (short, rule, cs.DEFAULT_LAYOUT),
        f"{sn}x{ss:g} short slots + decided setting + offset 0.5": (short, rule, off),
    }
    res = run_cases(cases, cfg, reps, SEED + 2, pool)
    return res, paired(res, base)


def exp_sensitivity(cfg, pool, reps, d):
    tabs = []
    lo, hi = d["service_range_min"]
    extra = d["extra_requests"]
    alt_slot = 10.0 if cfg.slot_min != 10.0 else 15.0  # the other usual slot length, same session
    alt_n = round(cfg.n_slots * cfg.slot_min / alt_slot)
    variants = {
        f"Consultation time {lo:g} min": replace(cfg, service_mean=float(lo)),
        f"Consultation time {hi:g} min": replace(cfg, service_mean=float(hi)),
        "Consultation variability 0.3": replace(cfg, service_cv=0.3),
        "Consultation variability 0.8": replace(cfg, service_cv=0.8),
        f"Demand {cfg.n_requests - 4} requests": replace(cfg, requests=cfg.n_requests - 4),
        f"Demand {cfg.n_requests + 4} requests": replace(cfg, requests=cfg.n_requests + 4),
        "Lateness deviation 8 min": replace(cfg, punctuality_sd=8.0),
        f"{alt_slot:g} min slots, {alt_n} slots": replace(
            cfg, slot_min=alt_slot, n_slots=alt_n, requests=alt_n + extra
        ),
    }
    rule = rule_of(d)
    for name, c in {"base": cfg, **variants}.items():
        cases = {
            "fixed": (c, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
            "decided setting": (c, rule, cs.DEFAULT_LAYOUT),
        }
        res = run_cases(cases, c, reps, SEED + 3, pool)
        t = paired(res, "fixed")
        t["case"] = name
        tabs.append(t)

    def scaled(factor):
        def tf(draws, rng):
            risk = np.clip(draws.risk * factor, 0.0, 0.95)
            return cs.Draws(
                risk, rng.random(len(risk)) >= risk, draws.arrival_offset, draws.service
            )

        return tf

    for factor, name in ((0.7, "No-show rate x0.7"), (1.3, "No-show rate x1.3")):
        cases = {
            "fixed": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
            "decided setting": (cfg, rule, cs.DEFAULT_LAYOUT),
        }
        res = run_cases(cases, cfg, reps, SEED + 4, pool, transform=scaled(factor))
        t = paired(res, "fixed")
        t["case"] = name
        tabs.append(t)
    return pd.concat(tabs, ignore_index=True)


def exp_reminder(cfg, pool, reps, d):
    """Hypothetical: a reminder turns a share of the reminded no-shows into show-ups."""
    rows = []
    rule = rule_of(d)
    for effect in (0.0, 0.10, 0.20, 0.30):

        def tf(draws, rng, effect=effect):
            reminded = rng.random(len(draws.risk)) < 0.5  # half of the patients (A/B design)
            flip = reminded & ~draws.shows & (rng.random(len(draws.risk)) < effect)
            risk = np.where(reminded, draws.risk * (1 - effect), draws.risk)
            return cs.Draws(risk, draws.shows | flip, draws.arrival_offset, draws.service)

        cases = {
            "fixed": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
            "decided setting": (cfg, rule, cs.DEFAULT_LAYOUT),
        }
        res = run_cases(cases, cfg, reps, SEED + 5, pool, transform=tf)
        m = means(res)
        for case in m.index:
            rows.append({"reminder effect": f"{int(effect * 100)}%", "policy": case, **m.loc[case]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- reports
def assumptions_line(d: dict, cfg: cs.SessionConfig) -> str:
    lo, hi = d["service_range_min"]
    return (
        f"{cfg.n_slots} slots x {cfg.slot_min:g} min, mean consultation "
        f"{cfg.service_mean:g} min (range {lo:g}–{hi:g} min, variability {cfg.service_cv:g}), "
        f"lateness deviation {cfg.punctuality_sd:g} min, {cfg.n_requests} booking requests"
    )


def write_report(
    parts: dict, reps: dict, d: dict, cfg: cs.SessionConfig, pool: pd.DataFrame
) -> None:
    grid = parts["grid"]
    front = grid[grid.pareto & (grid.index != "fixed")].sort_values("seen", ascending=False)
    front = front[~front[["seen", "mean_wait", "idle", "overtime"]].round(2).duplicated()]
    limits = sorted({5.0, 10.0, float(d["wait_limit_min"])})
    cons = []
    for limit in limits:
        ok = grid[(grid.mean_wait <= limit) & (grid.index != "fixed")]
        if len(ok):
            ranked = ok.sort_values(["seen", "overtime"], ascending=[False, True])
            best = ranked.iloc[0]
            cons.append(
                {
                    "Waiting limit (min)": f"≤ {limit:.0f}",
                    "Best setting": ranked.index[0],
                    "Seen": best.seen,
                    "Wait": best.mean_wait,
                    "Idle": best.idle,
                    "Overtime": best.overtime,
                }
            )
    cols = ["seen", "mean_wait", "idle", "overtime", "utilization", "overbooked_slots"]
    f = front[cols].reset_index().rename(columns={"case": "Setting"})
    f.columns = [
        "Setting",
        "Seen",
        "Wait min",
        "Idle min",
        "Overtime min",
        "Utilization",
        "Extra slots",
    ]
    sens_rows = []
    for name, g in parts["sens"].groupby("case", sort=False):
        t = g.set_index("metric")
        sens_rows.append(
            {
                "Scenario": name,
                "Seen": f"{t.loc['seen', 'diff']:+.2f}",
                "Wait (min)": f"{t.loc['mean_wait', 'diff']:+.2f}",
                "Idle (min)": f"{t.loc['idle', 'diff']:+.2f}",
                "Overtime (min)": f"{t.loc['overtime', 'diff']:+.2f}",
            }
        )
    rem = parts["reminder"][["reminder effect", "policy", "seen", "mean_wait", "idle", "overtime"]]
    rem.columns = [
        "Reminder effect",
        "Policy",
        "Seen",
        "Wait min",
        "Idle min",
        "Overtime min",
    ]
    model = MODEL_NAMES.get(d["model"], "Random forest (default risk file)")
    text = f"""# IEN experiment results (generated)

This file is generated by `simulation/experiments.py`; do not edit it by hand. Risk source: **{model}**. Seed {SEED}; Python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}, scipy {scipy.__version__}, simpy {simpy.__version__}. The settings come from `docs/decisions.json`.

**How to read it**

- Risks and show-ups come from real out-of-sample predictions and the real outcomes of the 27 days the model did not see. Session settings: {assumptions_line(d, cfg)}. The consultation time (5–10 min) comes from state hospital outpatient practice; slot length, lateness and demand are **assumptions** (`docs/decision-list.md`).
- All comparisons are **paired**: every policy sees the same random sessions (common random numbers). Differences are given against the base policy; brackets hold the 95% confidence interval, and `d` is the paired effect size (Cohen's d_z).
- Times are minutes per session; "Seen" is the number of patients per session.

## 1. Policy comparison ({reps["main"]} sessions)

{paired_md(parts["main"])}

**Interpretation.** Overbooking raises the number of patients seen and cuts the idle time of the clinic room, but when two patients come to the same slot, the mean wait and, under most policies, the overtime grow as well. The improvement and its cost have to be reported together: the rule is not "free".

## 2. Threshold x daily limit grid ({reps["grid"]} sessions)

The settings below are the **Pareto** settings, which no other setting beats on all four measures (more patients seen; less waiting, idle time and overtime):

{md_table(f)}

The setting that sees the most patients within a given waiting limit:

{md_table(pd.DataFrame(cons)) if cons else "No setting meets the limit."}

{rule_name(d)} is the `{grid_key(d["threshold"], d["daily_limit"])}` row of the grid. The whole grid is written to `simulation/results_experiments/grid_means.csv` when the script runs (the CSVs are not committed).

## 3. Templates and short slots + overbooking ({reps["templates"]} sessions)

Every template runs with the same number of requests; differences are against the base.

{paired_md(parts["templates"])}

## 4. Sensitivity analysis ({reps["sens"]} sessions per scenario)

Difference of the decided setting from fixed intervals (paired mean):

{md_table(pd.DataFrame(sens_rows))}

The confidence intervals are written to `simulation/results_experiments/sensitivity.csv`.

## 5. Reminder scenario (hypothetical, {reps["reminder"]} sessions)

**This is an assumption, not a measurement:** the reminder goes to half of the patients and turns the given share of those who would miss their appointment into patients who come. The real effect has to be measured with the A/B test; the dataset's `SMS_received` field does not come from a randomised experiment, so it cannot estimate the effect.

{md_table(rem)}
"""
    REPORT.write_text(text, encoding="utf-8")
    write_summary(parts, d, cfg, pool, model)


def write_summary(
    parts: dict, d: dict, cfg: cs.SessionConfig, pool: pd.DataFrame, model: str
) -> None:
    """Short, regenerated summary that the hand-written documents point to."""
    tab = parts["main"]
    mine = tab[tab.case == rule_name(d)].set_index("metric")
    sens = parts["sens"]
    lo, hi = d["service_range_min"]
    s_lo = sens[(sens.case == f"Consultation time {lo:g} min") & (sens.metric == "mean_wait")]
    s_hi = sens[(sens.case == f"Consultation time {hi:g} min") & (sens.metric == "mean_wait")]
    wait = mine.loc["mean_wait", "case_mean"]
    ok = wait <= d["wait_limit_min"]
    rows = []
    for m in METRICS:
        r = mine.loc[m]
        rows.append(
            {
                "Measure": LABELS[m],
                "No rule": r.base_mean,
                "Decided setting": r.case_mean,
                "Difference [95% interval]": f"{r['diff']:+.2f} [{r.ci_low:+.2f}; {r.ci_high:+.2f}]",
                "Change": f"{r.rel_pct:+.0f}%",
            }
        )
    auc = roc_auc_score(pool["y"], pool["p"])
    text = f"""# Results summary (generated)

This file is generated by `ml/apply_decisions.py` / `simulation/experiments.py`; do not edit it by hand. The hand-written documents take their numbers from here. Details: `docs/experiment-results.md`, `docs/model-comparison.md`.

## Current decided settings

- **Model:** {model}; ROC-AUC **{auc:.3f}** with out-of-fold predictions over the 27 days
- **Rule:** threshold {round(100 * d["threshold"])}%, daily overbook limit {d["daily_limit"]}, at most {d["max_per_slot"]} patients per slot
- **Session:** {assumptions_line(d, cfg)}
- **Longest accepted mean wait:** {d["wait_limit_min"]} min

## Decided setting against fixed intervals (per session)

{md_table(pd.DataFrame(rows))}

**Waiting limit check:** mean wait {wait:.2f} min; limit {d["wait_limit_min"]} min → **{"within the limit" if ok else "OVER THE LIMIT"}**.

**Consultation time sensitivity:** with a {lo:g} min consultation the difference in waiting is {s_lo["diff"].iloc[0]:+.2f} min, with {hi:g} min it is {s_hi["diff"].iloc[0]:+.2f} min.
"""
    SUMMARY.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="small run to check the code")
    ap.add_argument("--decisions", type=Path, default=DOCS / "decisions.json")
    ap.add_argument("--risks", type=Path, default=RISKS)
    args = ap.parse_args()
    reps = (
        {"main": 30, "grid": 20, "templates": 30, "sens": 20, "reminder": 20}
        if args.quick
        else {"main": 2000, "grid": 500, "templates": 1000, "sens": 600, "reminder": 600}
    )
    d = load_decisions(args.decisions)
    pool = pd.read_csv(args.risks)
    cfg = session_config(d)
    OUT.mkdir(exist_ok=True)

    parts = {}
    res, parts["main"] = exp_main(cfg, pool, reps["main"], d)
    parts["main"].to_csv(OUT / "main_paired.csv", index=False)
    res, grid = exp_grid(cfg, pool, reps["grid"], d)
    grid.to_csv(OUT / "grid_means.csv")
    parts["grid"] = grid
    res, parts["templates"] = exp_templates(cfg, pool, reps["templates"], d)
    parts["templates"].to_csv(OUT / "templates_paired.csv", index=False)
    parts["sens"] = exp_sensitivity(cfg, pool, reps["sens"], d)
    parts["sens"].to_csv(OUT / "sensitivity.csv", index=False)
    parts["reminder"] = exp_reminder(cfg, pool, reps["reminder"], d)
    parts["reminder"].to_csv(OUT / "reminder_scenario.csv", index=False)
    write_report(parts, reps, d, cfg, pool)
    print("Saved:", REPORT, "and", SUMMARY)


if __name__ == "__main__":
    main()

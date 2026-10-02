"""What does each layer add? Compare booking policies step by step on identical sessions.

Steps (each adds one idea to the previous one):
  0  fixed-interval booking                    - the starting point
  1  blind overbooking                         - double-book without knowing who will miss
  2  risk-targeted overbooking (threshold)     - use the no-show probability of the booked patient
  3  risk-targeted overbooking (cost rule R5-A)
  *  oracle (reference)                        - knows exactly who will miss: the best any model could do

Two risk sources are compared:
  synthetic  - Beta(2, 8) risks, outcomes drawn from the risk (a perfectly calibrated model)
  model      - empirical (p, y) pairs of the random forest on the test period (--risks CSV)

    python value_ladder.py --risks ../ml/data/processed/risks_random_forest.csv
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from clinic_sim import SessionConfig, cost_rule, draw_session, fixed_interval, simulate_session, threshold_rule

OUT = Path(__file__).parent / "output"


def blind_overbooking(max_per_slot: int = 2, limit: int = 4):
    """Overbook the earliest booked slots regardless of risk."""
    return lambda booked, overbooks: len(booked) < max_per_slot and overbooks < limit


def steps(source: str):
    thr = 0.30 if source == "model" else 0.30
    return [
        ("0 fixed interval", fixed_interval(), False),
        ("1 blind overbooking", blind_overbooking(), False),
        (f"2 threshold {thr:.2f}", threshold_rule(thr), False),
        ("3 cost rule r=0.5", cost_rule(0.5), False),
        ("* oracle", threshold_rule(0.5), True),
    ]


def run_source(cfg: SessionConfig, pool, reps: int, seed: int, source: str) -> pd.DataFrame:
    rows = []
    for rep in range(reps):
        d = draw_session(cfg, np.random.default_rng([seed, rep]), pool)
        oracle = type(d)(( ~d.shows).astype(float), d.shows, d.arrival_offset, d.service)   # risk 1 = will miss
        for name, policy, is_oracle in steps(source):
            res = simulate_session(cfg, policy, oracle if is_oracle else d)
            rows.append({"source": source, "policy": name, "rep": rep, **res})
    return pd.DataFrame(rows)


def table(res: pd.DataFrame) -> pd.DataFrame:
    base = res[res.policy.str.startswith("0")].set_index("rep")
    out = []
    for name, g in res.groupby("policy", sort=False):
        g = g.set_index("rep")
        row = {"policy": name}
        for m, label in [("seen", "patients seen"), ("mean_wait", "wait (min)"), ("idle", "idle (min)"),
                         ("overtime", "overtime (min)"), ("overbooked_slots", "overbooked slots")]:
            row[label] = f"{g[m].mean():.1f}"
        d_seen, d_wait, d_idle = (g[m] - base[m] for m in ("seen", "mean_wait", "idle"))
        row["d_seen"], row["d_wait"], row["d_idle"] = f"{d_seen.mean():+.2f}", f"{d_wait.mean():+.2f}", f"{d_idle.mean():+.1f}"
        # cost of an extra patient: added waiting minutes per extra patient seen
        row["wait cost / extra patient"] = f"{d_wait.mean() / d_seen.mean():.2f}" if abs(d_seen.mean()) > 0.05 else "-"
        out.append(row)
    return pd.DataFrame(out)


def chart(results: dict[str, pd.DataFrame]) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    colors = ["#8d99ae", "#e07a5f", "#2a6f97", "#3d9970", "#f2cc8f"]
    for ax, (metric, title) in zip(axes, [("seen", "Patients seen per session"), ("idle", "Physician idle time (min)"),
                                           ("mean_wait", "Mean patient waiting time (min)")]):
        width = 0.38
        for k, (source, res) in enumerate(results.items()):
            g = res.groupby("policy", sort=False)[metric]
            mean, ci = g.mean(), 1.96 * g.std() / np.sqrt(g.count())
            ax.bar(np.arange(len(mean)) + (k - 0.5) * width, mean, width, yerr=ci, capsize=2,
                   color=colors, alpha=1.0 if k == 0 else 0.55, edgecolor="black" if k else "none",
                   hatch="" if k == 0 else "//", linewidth=0.5)
        ax.set_xticks(range(len(mean)), [p.split(" ", 1)[0] for p in mean.index])
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)
    labels = list(results.values())[0].policy.unique()
    fig.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in colors], list(labels), loc="lower center", bbox_to_anchor=(0.5, -0.005), ncol=5, fontsize=9)
    fig.text(0.5, 0.062, "solid = synthetic calibrated risks, hatched = random forest risks from the test period", ha="center", fontsize=8)
    fig.suptitle("What each layer adds (same sessions, 1000 replications)")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    OUT.mkdir(exist_ok=True)
    path = OUT / "value_ladder.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--risks", help="CSV with columns p and y (model predictions and outcomes)")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    cfg = SessionConfig()
    pd.set_option("display.width", 220)
    results = {}
    for source, pool in [("synthetic", None)] + ([("model", pd.read_csv(args.risks))] if args.risks else []):
        results[source] = run_source(cfg, pool, args.reps, args.seed, source)
        print(f"\n=== Risk source: {source} ===")
        print(table(results[source]).to_string(index=False))
    print("\nSaved:", chart(results))


if __name__ == "__main__":
    main()

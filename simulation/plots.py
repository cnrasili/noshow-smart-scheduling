"""Charts for the clinic session simulation. Saves PNG files to simulation/output/.

python plots.py            # trade-off chart + one-session timeline
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from clinic_sim import (
    SessionConfig,
    draw_session,
    fixed_interval,
    run,
    simulate_session,
    threshold_rule,
)

OUT = Path(__file__).parent / "output"
THRESHOLDS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)


def tradeoff_chart(cfg: SessionConfig, reps: int = 1000, seed: int = 42) -> Path:
    policies = {"fixed": fixed_interval()}
    policies.update({f"{t:.2f}": threshold_rule(t) for t in THRESHOLDS})
    res = run(cfg, policies, reps, seed)
    g = res.groupby("policy", sort=False)
    mean, ci = g.mean(numeric_only=True), 1.96 * g.std(numeric_only=True) / np.sqrt(reps)

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8))
    a.errorbar(
        mean["idle"],
        mean["mean_wait"],
        xerr=ci["idle"],
        yerr=ci["mean_wait"],
        fmt="o-",
        color="#2a6f97",
        capsize=3,
    )
    for name in mean.index:
        a.annotate(
            "fixed" if name == "fixed" else f"τ={name}",
            (mean.loc[name, "idle"], mean.loc[name, "mean_wait"]),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=9,
        )
    a.set_xlabel("Physician idle time per session (min)")
    a.set_ylabel("Mean patient waiting time (min)")
    a.set_title("Overbooking trades waiting time for idle time")
    a.grid(alpha=0.3)

    x = np.arange(len(mean))
    b.bar(
        x - 0.2,
        mean["seen"],
        0.4,
        yerr=ci["seen"],
        label="Patients seen",
        color="#2a6f97",
        capsize=3,
    )
    b.bar(
        x + 0.2,
        mean["overtime"],
        0.4,
        yerr=ci["overtime"],
        label="Overtime (min)",
        color="#e07a5f",
        capsize=3,
    )
    b.set_xticks(x, ["fixed" if n == "fixed" else f"τ={n}" for n in mean.index])
    b.set_title("Patients seen and overtime")
    b.legend()
    b.grid(axis="y", alpha=0.3)
    fig.suptitle(
        f"Threshold rule vs fixed-interval booking "
        f"({reps} sessions, {cfg.n_slots} slots x {cfg.slot_min:.0f} min)"
    )
    fig.tight_layout()
    OUT.mkdir(exist_ok=True)
    path = OUT / "tradeoff.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def timeline_chart(cfg: SessionConfig, threshold: float = 0.30, seed: int = 42) -> Path:
    # pick the first session in which overbooking actually creates an overbooked slot
    for rep in range(200):
        d = draw_session(cfg, np.random.default_rng([seed, rep]), None)
        over = simulate_session(cfg, threshold_rule(threshold), d, detail=True)
        if over["overbooked_slots"] >= 2:
            break
    fixed = simulate_session(cfg, fixed_interval(), d, detail=True)

    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    for ax, title, r in (
        (axes[0], "Fixed-interval booking", fixed),
        (axes[1], f"Selective overbooking (threshold {threshold:.2f})", over),
    ):
        rows = sorted(r["detail"], key=lambda x: (x["start"], x["patient"]))
        for y, p in enumerate(rows):
            ax.barh(
                y,
                p["start"] - max(p["appointment"], p["arrival"]),
                left=max(p["appointment"], p["arrival"]),
                color="#f2cc8f",
                height=0.7,
                label="waiting" if y == 0 else None,
            )
            ax.barh(
                y,
                p["end"] - p["start"],
                left=p["start"],
                height=0.7,
                color="#e07a5f" if p["overbooked"] else "#2a6f97",
                label=("consultation (overbooked slot)" if p["overbooked"] else "consultation")
                if y == 0
                else None,
            )
            ax.plot(p["appointment"], y, "k|", markersize=8)
        ax.axvline(cfg.session_min, color="red", ls="--", lw=1)
        ax.text(cfg.session_min, len(rows) + 0.2, " planned end", color="red", fontsize=9)
        ax.set_yticks([])
        ax.set_title(
            f"{title}: {len(rows)} patients seen, mean wait {r['mean_wait']:.1f} min, "
            f"idle {r['idle']:.0f} min, "
            f"overtime {r['overtime']:.0f} min"
        )
        for s in range(cfg.n_slots + 1):
            ax.axvline(s * cfg.slot_min, color="grey", lw=0.3)
        handles, labels = ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles, strict=False))
        ax.legend(unique.values(), unique.keys(), loc="lower right", fontsize=8)
    axes[1].set_xlabel("Time since session start (min); black ticks = appointment time")
    fig.tight_layout()
    OUT.mkdir(exist_ok=True)
    path = OUT / "timeline.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


if __name__ == "__main__":
    cfg = SessionConfig()
    print("Saved:", tradeoff_chart(cfg))
    print("Saved:", timeline_chart(cfg))

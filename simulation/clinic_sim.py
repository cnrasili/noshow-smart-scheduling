"""Discrete-event simulation of one outpatient clinic session (SimPy).

Compares fixed-interval booking with no-show-aware overbooking on the KPIs in
docs/kpi-definitions.md: patient waiting time, physician idle time, overtime, utilization.

All policies see the same booking requests, show-ups, arrival offsets and service times
(common random numbers), so differences between policies are not sampling noise.

Usage:
    python clinic_sim.py                      # compare the default policies
    python clinic_sim.py --sweep              # sweep the threshold rule
    python clinic_sim.py --risks risks.csv    # use empirical risks (columns: p [, y])
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np
import pandas as pd
import simpy


# --------------------------------------------------------------------------- configuration
@dataclass(frozen=True)
class SessionConfig:
    n_slots: int = 16              # slots in the session
    slot_min: float = 15.0         # slot length (minutes)
    service_mean: float = 12.0     # mean consultation time (minutes)
    service_cv: float = 0.5        # coefficient of variation of consultation time
    punctuality_sd: float = 4.0    # sd of arrival offset around the slot start (minutes)
    extra_requests: int = 4        # booking requests beyond the number of slots (demand pressure)
    risk_alpha: float = 2.0        # Beta(a, b) no-show risk of a patient; mean = a / (a + b)
    risk_beta: float = 8.0

    @property
    def session_min(self) -> float:
        return self.n_slots * self.slot_min


# --------------------------------------------------------------------------- booking policies
# A policy gets the no-show risks of patients already in a slot and the number of overbooked
# slots so far; it returns True when one more patient may be added to that slot.
Policy = Callable[[Sequence[float], int], bool]


def fixed_interval() -> Policy:
    """One patient per slot, never overbook."""
    return lambda booked, overbooks: False


def threshold_rule(threshold: float, max_per_slot: int = 2, daily_limit: int = 4) -> Policy:
    """Same logic as overbooking-service rules.decide: overbook only if every booked patient is risky."""
    def allow(booked: Sequence[float], overbooks: int) -> bool:
        return (len(booked) < max_per_slot and min(booked) >= threshold and overbooks < daily_limit)
    return allow


def cost_rule(r: float, max_per_slot: int = 2, daily_limit: int = 4, capacity: int = 1) -> Policy:
    """Cost-based rule R5-A (docs/formulas/overbooking.md): add a patient if P(shows >= C) < 1/(1+r)."""
    def q(booked: Sequence[float]) -> float:
        dist = np.array([1.0])                      # P(number of shows = m), Poisson-binomial DP
        for p in booked:
            dist = np.convolve(dist, [p, 1 - p])    # index 0 = no show, 1 = show
        return float(dist[capacity:].sum())

    def allow(booked: Sequence[float], overbooks: int) -> bool:
        return len(booked) < max_per_slot and overbooks < daily_limit and q(booked) < 1 / (1 + r)
    return allow


# --------------------------------------------------------------------------- one replication
@dataclass
class Draws:
    """Random inputs of one session, shared by all policies."""
    risk: np.ndarray        # no-show risk per request
    shows: np.ndarray       # True if the patient attends
    arrival_offset: np.ndarray
    service: np.ndarray


def draw_session(cfg: SessionConfig, rng: np.random.Generator, pool: pd.DataFrame | None) -> Draws:
    n = cfg.n_slots + cfg.extra_requests
    if pool is None:
        risk = rng.beta(cfg.risk_alpha, cfg.risk_beta, n)
        shows = rng.random(n) >= risk                      # risks are assumed calibrated
    else:
        rows = pool.iloc[rng.integers(0, len(pool), n)]
        risk = rows["p"].to_numpy()
        shows = (rows["y"].to_numpy() == 0) if "y" in rows else rng.random(n) >= risk
    sigma = np.sqrt(np.log(1 + cfg.service_cv ** 2))
    service = np.maximum(3.0, rng.lognormal(np.log(cfg.service_mean) - sigma ** 2 / 2, sigma, n))
    return Draws(risk, shows, rng.normal(0, cfg.punctuality_sd, n), service)


def book(cfg: SessionConfig, policy: Policy, d: Draws) -> tuple[list[list[int]], int]:
    """Assign requests in arrival order to the earliest slot the policy allows."""
    slots: list[list[int]] = [[] for _ in range(cfg.n_slots)]
    overbooks, deferred = 0, 0
    for i, risk in enumerate(d.risk):
        for s, booked in enumerate(slots):
            if not booked:
                booked.append(i)
                break
            if policy([d.risk[j] for j in booked], overbooks):
                booked.append(i)
                overbooks += 1
                break
        else:
            deferred += 1                                  # no slot available: booked another day
    return slots, deferred


def simulate_session(cfg: SessionConfig, policy: Policy, d: Draws, detail: bool = False) -> dict:
    slots, deferred = book(cfg, policy, d)
    env = simpy.Environment()
    doctor = simpy.Resource(env, capacity=1)
    waits: list[float] = []
    busy: list[tuple[float, float]] = []
    log: list[dict] = []

    def patient(i: int, appt_time: float):
        arrival = max(0.0, appt_time + d.arrival_offset[i])
        ready = max(appt_time, arrival)                       # a consultation never starts before the appointment time
        yield env.timeout(ready)
        with doctor.request() as req:
            yield req
            start = env.now
            waits.append(start - ready)                       # KPI: start - max(appointment time, arrival)
            yield env.timeout(d.service[i])
            busy.append((start, env.now))
            log.append({"patient": i, "slot": int(appt_time // cfg.slot_min), "appointment": appt_time,
                        "arrival": arrival, "start": start, "end": env.now,
                        "overbooked": len(slots[int(appt_time // cfg.slot_min)]) > 1})

    seen = 0
    for s, booked in enumerate(slots):
        for i in booked:
            if d.shows[i]:
                env.process(patient(i, s * cfg.slot_min))
                seen += 1
    env.run()

    session_end = cfg.session_min
    last_end = max((e for _, e in busy), default=0.0)
    busy_in_session = sum(max(0.0, min(e, session_end) - min(s, session_end)) for s, e in busy)
    result = {
        "booked": sum(len(b) for b in slots),
        "seen": seen,
        "deferred": deferred,
        "overbooked_slots": sum(len(b) > 1 for b in slots),
        "mean_wait": float(np.mean(waits)) if waits else 0.0,
        "max_wait": float(np.max(waits)) if waits else 0.0,
        "idle": session_end - busy_in_session,               # minutes without a patient, within the session
        "overtime": max(0.0, last_end - session_end),
        "utilization": sum(e - s for s, e in busy) / session_end,
    }
    if detail:
        result["detail"] = log
        result["no_shows"] = [(i, s) for s, b in enumerate(slots) for i in b if not d.shows[i]]
    return result


# --------------------------------------------------------------------------- experiment
def run(cfg: SessionConfig, policies: dict[str, Policy], reps: int, seed: int,
        pool: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    for rep in range(reps):
        d = draw_session(cfg, np.random.default_rng([seed, rep]), pool)
        for name, policy in policies.items():
            rows.append({"policy": name, "rep": rep, **simulate_session(cfg, policy, d)})
    return pd.DataFrame(rows)


def summarize(res: pd.DataFrame, baseline: str) -> pd.DataFrame:
    metrics = ["seen", "mean_wait", "idle", "overtime", "utilization", "overbooked_slots", "deferred"]
    out = {}
    for name, g in res.groupby("policy", sort=False):
        row = {}
        for m in metrics:
            half = 1.96 * g[m].std(ddof=1) / np.sqrt(len(g))
            row[m] = f"{g[m].mean():.2f} +/- {half:.2f}"
        out[name] = row
    return pd.DataFrame(out).T


def paired_difference(res: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """Mean difference to the baseline over the same sessions, with a 95 % confidence interval."""
    base = res[res.policy == baseline].set_index("rep")
    rows = {}
    for name, g in res.groupby("policy", sort=False):
        if name == baseline:
            continue
        g = g.set_index("rep")
        row = {}
        for m in ["mean_wait", "idle", "overtime", "seen"]:
            diff = g[m] - base[m]
            row[f"d_{m}"] = f"{diff.mean():+.2f} +/- {1.96 * diff.std(ddof=1) / np.sqrt(len(diff)):.2f}"
        rows[name] = row
    return pd.DataFrame(rows).T


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sweep", action="store_true", help="sweep the threshold of the threshold rule")
    ap.add_argument("--risks", help="CSV with empirical risks: column p (no-show probability), optional y (1 = no-show)")
    ap.add_argument("--out", help="write per-session results to this CSV")
    args = ap.parse_args()

    cfg = SessionConfig()
    pool = pd.read_csv(args.risks) if args.risks else None
    if args.sweep:
        policies = {"fixed": fixed_interval()}
        policies.update({f"threshold {t:.2f}": threshold_rule(t) for t in (0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)})
    else:
        policies = {"fixed": fixed_interval(), "threshold 0.30": threshold_rule(0.30),
                    "cost r=1.0": cost_rule(1.0), "cost r=0.5": cost_rule(0.5)}

    res = run(cfg, policies, args.reps, args.seed, pool)
    pd.set_option("display.width", 200)
    print(f"{args.reps} sessions, {cfg.n_slots} slots x {cfg.slot_min:.0f} min, "
          f"{cfg.n_slots + cfg.extra_requests} booking requests per session\n")
    print("Mean +/- 95% CI per session\n", summarize(res, "fixed").to_string(), "\n")
    print("Difference to fixed-interval (paired over the same sessions)\n",
          paired_difference(res, "fixed").to_string())
    if args.out:
        res.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()

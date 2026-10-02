"""Day-by-day results of every rule and template on the real appointment records of each test day.

Baseline = no rule: fixed 15-minute slots, one patient per slot, every patient takes the next free slot.
Every other row applies one rule or template to the SAME patients, show-ups, lateness and consultation lengths.
"""
import dataclasses
import html

import numpy as np
import pandas as pd

from clinic_sim import SessionConfig, cost_rule, draw_session, fixed_interval, simulate_session, threshold_rule
from template_base import REQUESTS, Template

# metric key -> (label, good direction: -1 lower is better, +1 higher is better, 0 neutral)
METRICS = [("seen", "Patients seen", 1), ("noshow", "No-shows (booked, did not come)", 0), ("noslot", "No free slot", -1),
           ("wait", "Mean wait (min)", -1), ("wait_h", "Total waiting (hours)", -1), ("idle_h", "Doctor idle (hours)", -1),
           ("ot_h", "Overtime (hours)", -1)]


def scenarios(tuned: list[Template]) -> list[tuple[str, object]]:
    """(label, template or rule name) pairs; the first one is the baseline without any rule."""
    out = [("No rule: fixed interval 15 min", Template("baseline", "No rule", "", 16, 15)),
           ("Rule: threshold 0.30 (same-time overbooking)", Template("r1", "", "", 16, 15, threshold=0.30)),
           ("Rule: cost-based R5-A, r = 0.5", "cost0.5"), ("Rule: cost-based R5-A, r = 1.0", "cost1.0")]
    out += [(f"Template {i + 1}: {t.name.split(' - ', 1)[1]}", t) for i, t in enumerate(tuned)]
    return out


def run_policy(label_or_t, cfg: SessionConfig, scfg_base: SessionConfig, draws, part_len: int):
    """Return the simulate_session result for one scenario."""
    if label_or_t == "cost0.5":
        return simulate_session(dataclasses.replace(cfg, requests=part_len), cost_rule(0.5), draws)
    if label_or_t == "cost1.0":
        return simulate_session(dataclasses.replace(cfg, requests=part_len), cost_rule(1.0), draws)
    t: Template = label_or_t
    tcfg = dataclasses.replace(t.config(cfg), requests=part_len)
    return simulate_session(tcfg, t.policy(), draws, layout=t.layout())


def compute(pool: pd.DataFrame, tuned: list[Template], cfg: SessionConfig) -> tuple[list[str], dict]:
    """data[date or 'all'][scenario label] = metrics. Uses every record of each date."""
    scs = scenarios(tuned)
    labels = [s[0] for s in scs]
    acc: dict = {}
    for date, day in pool.groupby("AppointmentDay"):
        key = f"{date:%d %b %Y}"
        rng_seed = int(date.strftime("%Y%m%d"))
        idx = np.random.default_rng(rng_seed).permutation(len(day))
        rng = np.random.default_rng(rng_seed + 1)
        tot = {lab: dict(appointments=0, seen=0, booked=0, noslot=0, wait_min=0.0, idle_min=0.0, ot_min=0.0) for lab in labels}
        for start in range(0, len(day), REQUESTS):
            part = day.iloc[np.sort(idx[start:start + REQUESTS])].sort_values("ScheduledDay", kind="stable")
            draws = dataclasses.replace(draw_session(dataclasses.replace(cfg, requests=len(part)), rng, None),
                                        risk=part["p"].to_numpy(), shows=(part["y"].to_numpy() == 0))
            for lab, t in scs:
                r = run_policy(t, cfg, cfg, draws, len(part))
                a = tot[lab]
                a["appointments"] += len(part); a["seen"] += r["seen"]; a["booked"] += r["booked"]
                a["noslot"] += r["deferred"]; a["wait_min"] += r["mean_wait"] * r["seen"]
                a["idle_min"] += r["idle"]; a["ot_min"] += r["overtime"]
        acc[key] = tot
    acc["All 5 days"] = {lab: {k: sum(acc[d][lab][k] for d in list(acc)) for k in acc[next(iter(acc))][lab]} for lab in labels}
    data = {}
    for key, tot in acc.items():
        data[key] = {}
        for lab, a in tot.items():
            data[key][lab] = {"appointments": a["appointments"], "seen": a["seen"], "noshow": a["booked"] - a["seen"],
                              "noslot": a["noslot"], "wait": a["wait_min"] / max(a["seen"], 1), "wait_h": a["wait_min"] / 60,
                              "idle_h": a["idle_min"] / 60, "ot_h": a["ot_min"] / 60}
    return labels, data


def fmt(key: str, v: float) -> str:
    return f"{v:,.1f}" if key in ("wait", "wait_h", "idle_h", "ot_h") else f"{v:,.0f}"


def section_html(labels: list[str], data: dict, risk_name: str) -> str:
    base = labels[0]
    head = "".join(f"<th>{html.escape(m[1])}</th>" for m in METRICS)
    blocks = ""
    for key, rows in data.items():
        n = rows[base]["appointments"]
        body = ""
        for lab in labels:
            r, b = rows[lab], rows[base]
            cells = ""
            for k, _, good in METRICS:
                share = f"<small>{100 * r[k] / n:.1f}% of appointments</small>" if k in ("seen", "noshow", "noslot") else ""
                if lab == base:
                    cells += f"<td>{fmt(k, r[k])}{share and '<br>' + share}</td>"
                    continue
                d = r[k] - b[k]
                pct = f"{100 * d / b[k]:+.1f}%" if b[k] else "n/a"
                cls = "n" if good == 0 or abs(d) < 1e-9 else ("g" if d * good > 0 else "b")
                cells += (f"<td>{fmt(k, r[k])}{share and '<br>' + share}<br><span class='d {cls}'>{'+' if d >= 0 else ''}{fmt(k, d)} "
                          f"({pct})</span></td>")
            attr = ' class="base"' if lab == base else ""
            body += f"<tr{attr}><td>{html.escape(lab)}</td>{cells}</tr>"
        blocks += (f"<h3>{html.escape(key)} <small>({n:,} real appointments)</small></h3>"
                   f"<div class='wrap'><table class='dd'><tr><th>Scenario</th>{head}</tr>{body}</table></div>")
    return f"""<h2>Day by day, on real appointment records</h2>
<p>Every real appointment of each test day, in real booking order (risk: {html.escape(risk_name)}, attendance: real). The first row is the
<b>baseline with no rule or algorithm</b>: fixed 15-minute slots, one patient per slot, no overbooking. Each other row applies one rule or template to the same patients on the same day.
Under each number: the change against the baseline, as a count and as a percentage. <span class="d g">Green</span> = better, <span class="d b">orange</span> = worse, grey = neutral.</p>
<p><small>The data has no doctor information: the day's patients are dealt randomly to clinic sessions of {REQUESTS} booking requests (16 slots), so about 4 requests per session find no free slot.
"No-shows" counts only patients who were booked into a slot and did not come; "No free slot" patients are booked for another day. Consultation length and lateness are simulated.</small></p>
{blocks}"""


CSS = """
.dd td,.dd th{font-size:12px;vertical-align:top;white-space:normal}.dd small{color:var(--mute);font-size:11px}
.dd tr.base td{background:rgba(120,130,150,.12);font-weight:600}.d{font-size:11px;font-weight:600}.g{color:#1a7f4b}.b{color:#c2410c}.n{color:var(--mute)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .g{color:#4ade80}:root:not([data-theme=light]) .b{color:#fb923c}}
h3{font-size:15px;margin:22px 0 6px}h2{font-size:17px;margin:30px 0 6px}
"""

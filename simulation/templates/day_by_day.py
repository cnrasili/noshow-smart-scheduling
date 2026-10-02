"""Overall and day-by-day results of every rule and template on the real appointment records.

Baseline = no rule: fixed 15-minute slots, one patient per slot, every patient takes the next free slot.
Every other row applies one rule or template to the SAME patients, show-ups, lateness and consultation lengths.
"""
import dataclasses
import html

import numpy as np
import pandas as pd

from clinic_sim import SessionConfig, cost_rule, draw_session, simulate_session
from template_base import REQUESTS, Template

# metric key -> (label, good direction: -1 lower is better, +1 higher is better, 0 neutral)
METRICS = [("seen", "Patients seen", 1), ("noshow", "No-shows (booked, did not come)", 0), ("noslot", "No free slot", -1),
           ("wait", "Mean wait (min)", -1), ("wait_h", "Total waiting (hours)", -1), ("idle_h", "Doctor idle (hours)", -1),
           ("ot_h", "Overtime (hours)", -1)]
ALL = "All days"


def scenarios(tuned: list[Template]) -> list[tuple[str, object]]:
    """(label, template or rule name) pairs; the first one is the baseline without any rule."""
    out = [("No rule: fixed interval 15 min", Template("baseline", "No rule", "", 16, 15)),
           ("Rule: threshold 0.30 (same-time overbooking)", Template("r1", "", "", 16, 15, threshold=0.30)),
           ("Rule: cost-based R5-A, r = 0.5", "cost0.5"), ("Rule: cost-based R5-A, r = 1.0", "cost1.0")]
    out += [(f"Template {i + 1}: {t.name.split(' - ', 1)[1]}", t) for i, t in enumerate(tuned)]
    return out


def run_policy(what, cfg: SessionConfig, draws, part_len: int):
    """simulate_session result for one scenario."""
    if what in ("cost0.5", "cost1.0"):
        return simulate_session(dataclasses.replace(cfg, requests=part_len), cost_rule(float(what[4:])), draws)
    tcfg = dataclasses.replace(what.config(cfg), requests=part_len)
    return simulate_session(tcfg, what.policy(), draws, layout=what.layout())


def build_sessions(pool: pd.DataFrame, cfg: SessionConfig) -> dict:
    """All records of each date dealt to clinic sessions of REQUESTS requests, in real booking order.
    Returns {date label: [(draws, number of requests), ...]} (chronological)."""
    out = {}
    for date, day in pool.groupby("AppointmentDay"):
        seed = int(date.strftime("%Y%m%d"))
        idx = np.random.default_rng(seed).permutation(len(day))
        rng = np.random.default_rng(seed + 1)
        sessions = []
        for start in range(0, len(day), REQUESTS):
            part = day.iloc[np.sort(idx[start:start + REQUESTS])].sort_values("ScheduledDay", kind="stable")
            draws = dataclasses.replace(draw_session(dataclasses.replace(cfg, requests=len(part)), rng, None),
                                        risk=part["p"].to_numpy(), shows=(part["y"].to_numpy() == 0))
            sessions.append((draws, len(part)))
        out[f"{date:%d %b %Y}"] = sessions
    return out


def compute(by_date: dict, tuned: list[Template], cfg: SessionConfig) -> tuple[list[str], dict]:
    """data[date or ALL][scenario label] = metrics (sums over all sessions of the date)."""
    scs = scenarios(tuned)
    labels = [s[0] for s in scs]
    sums = {}
    for key, sessions in by_date.items():
        tot = {lab: dict(appointments=0, seen=0, booked=0, noslot=0, wait_min=0.0, idle_min=0.0, ot_min=0.0) for lab in labels}
        for draws, plen in sessions:
            for lab, what in scs:
                r = run_policy(what, cfg, draws, plen)
                a = tot[lab]
                a["appointments"] += plen; a["seen"] += r["seen"]; a["booked"] += r["booked"]; a["noslot"] += r["deferred"]
                a["wait_min"] += r["mean_wait"] * r["seen"]; a["idle_min"] += r["idle"]; a["ot_min"] += r["overtime"]
        sums[key] = tot
    first = next(iter(sums))
    allsum = {lab: {k: sum(sums[d][lab][k] for d in sums) for k in sums[first][lab]} for lab in labels}
    data = {ALL: _metrics(allsum)}
    data.update({key: _metrics(tot) for key, tot in sums.items()})
    return labels, data


def _metrics(tot: dict) -> dict:
    return {lab: {"appointments": a["appointments"], "seen": a["seen"], "noshow": a["booked"] - a["seen"], "noslot": a["noslot"],
                  "wait": a["wait_min"] / max(a["seen"], 1), "wait_h": a["wait_min"] / 60, "idle_h": a["idle_min"] / 60,
                  "ot_h": a["ot_min"] / 60} for lab, a in tot.items()}


def fmt(key: str, v: float) -> str:
    return f"{v:,.1f}" if key in ("wait", "wait_h", "idle_h", "ot_h") else f"{v:,.0f}"


def change(key: str, good: int, v: float, base: float) -> tuple[str, str]:
    """('+633 (+23.6%)', css class)."""
    d = v - base
    pct = f"{100 * d / base:+.1f}%" if base else "n/a"
    cls = "n" if good == 0 or abs(d) < 1e-9 else ("g" if d * good > 0 else "b")
    return f"{'+' if d >= 0 else ''}{fmt(key, d)} ({pct})", cls


def overall_cards(labels: list[str], data: dict, winner_label: str, n_days: int) -> str:
    """KPI cards of the winner against the baseline over all days."""
    rows, base = data[ALL][winner_label], data[ALL][labels[0]]
    cards = ""
    for k, name, good in METRICS:
        text, cls = change(k, good, rows[k], base[k])
        share = (f"<div class='s'>{100 * rows[k] / rows['appointments']:.1f}% of appointments</div>"
                 if k in ("seen", "noshow", "noslot") else "")
        cards += (f"<div class='kc'><h4>{html.escape(name)}</h4><div class='v'>{fmt(k, rows[k])}</div>{share}"
                  f"<div class='s'>no rule: {fmt(k, base[k])}</div><div class='d {cls}'>{text}</div></div>")
    n = base["appointments"]
    return (f"<p>Winner <b>{html.escape(winner_label)}</b> against the baseline with no rule, summed over all {n_days} days "
            f"({n:,} real appointments). Each card: the winner's number, the no-rule number, and the change as a count and a percentage.</p>"
            f"<div class='cards'>{cards}</div>")


def section_html(labels: list[str], data: dict, winner_label: str, risk_name: str) -> str:
    base = labels[0]
    head = "".join(f"<th>{html.escape(m[1])}</th>" for m in METRICS)

    def table(rows: dict) -> str:
        n = rows[base]["appointments"]
        body = ""
        for lab in labels:
            r, b = rows[lab], rows[base]
            cells = ""
            for k, _, good in METRICS:
                share = f"<br><small>{100 * r[k] / n:.1f}% of appointments</small>" if k in ("seen", "noshow", "noslot") else ""
                if lab == base:
                    cells += f"<td>{fmt(k, r[k])}{share}</td>"
                else:
                    text, cls = change(k, good, r[k], b[k])
                    cells += f"<td>{fmt(k, r[k])}{share}<br><span class='d {cls}'>{text}</span></td>"
            attr = ' class="base"' if lab == base else ""
            body += f"<tr{attr}><td>{html.escape(lab)}</td>{cells}</tr>"
        return f"<div class='wrap'><table class='dd'><tr><th>Scenario</th>{head}</tr>{body}</table></div>"

    blocks = ""
    for key, rows in data.items():
        n = rows[base]["appointments"]
        if key == ALL:
            blocks += f"<h3>{ALL} <small>({n:,} real appointments, {len(data) - 1} days)</small></h3>{table(rows)}<h3>Each day</h3>"
            continue
        w, b = rows[winner_label], rows[base]
        headline = (f"{html.escape(winner_label.split(':')[0])}: {w['seen'] - b['seen']:+,} patients "
                    f"({100 * (w['seen'] - b['seen']) / b['seen']:+.1f}%), wait {w['wait'] - b['wait']:+.1f} min")
        blocks += (f"<details><summary><b>{html.escape(key)}</b> <small>{n:,} appointments &middot; {headline}</small></summary>"
                   f"{table(rows)}</details>")
    return f"""<h2>Day by day, on real appointment records</h2>
<p>Every real appointment of each of the {len(data) - 1} days, in real booking order (risk: {html.escape(risk_name)}, out-of-sample; attendance: real).
The first row is the <b>baseline with no rule or algorithm</b>: fixed 15-minute slots, one patient per slot, no overbooking. Each other row applies one rule or template
to the same patients on the same day. Under each number: the change against the baseline as a count and a percentage.
<span class="d g">Green</span> = better, <span class="d b">orange</span> = worse, grey = neutral. Open a day to see its table.</p>
<p><small>The data has no doctor information: a day's patients are dealt randomly to clinic sessions of {REQUESTS} booking requests (16 slots), so about 4 requests per session find no free slot.
"No-shows" counts only patients who were booked into a slot and did not come; "No free slot" patients are booked for another day. Consultation length and lateness are simulated.</small></p>
<p><button onclick="document.querySelectorAll('details').forEach(d=>d.open=true)">Open all days</button>
<button onclick="document.querySelectorAll('details').forEach(d=>d.open=false)">Close all days</button></p>
{blocks}"""


CSS = """
.dd td,.dd th{font-size:12px;vertical-align:top;white-space:normal}.dd small{color:var(--mute);font-size:11px}
.dd tr.base td{background:rgba(120,130,150,.12);font-weight:600}.d{font-size:11px;font-weight:600}.g{color:#1a7f4b}.b{color:#c2410c}.n{color:var(--mute)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .g{color:#4ade80}:root:not([data-theme=light]) .b{color:#fb923c}}
h3{font-size:15px;margin:22px 0 6px}h2{font-size:17px;margin:30px 0 6px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:8px 0 14px}
.kc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}.kc h4{margin:0;font-size:12px;color:var(--mute);font-weight:600}
.kc .v{font-size:24px;font-weight:700}.kc .s{font-size:12px;color:var(--mute)}.kc .d{font-size:13px;margin-top:4px}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:6px 0;padding:6px 12px}summary{cursor:pointer;padding:4px 0}
summary small{color:var(--mute)}.backbtn{display:inline-block;margin-bottom:14px;padding:6px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--acc,var(--accent,#2a6f97));text-decoration:none;font-size:14px}.backbtn:hover{opacity:.8}button{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 12px;cursor:pointer}
"""

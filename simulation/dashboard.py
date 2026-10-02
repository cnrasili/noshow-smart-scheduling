"""Build a self-contained HTML dashboard: KPI cards comparing a booking policy with fixed-interval booking.

    python dashboard.py --risks ../ml/data/processed/risks_random_forest.csv
    -> simulation/output/dashboard.html (open in a browser)
"""
import argparse
import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd

import plots
import value_ladder
from clinic_sim import SessionConfig, cost_rule, draw_session, fixed_interval, simulate_session, threshold_rule

OUT = Path(__file__).parent / "output"
METRICS = {  # key: (label, unit, higher_is_better)
    "seen": ("Patients seen", "per session", True),
    "mean_wait": ("Mean waiting time", "min", False),
    "idle": ("Physician idle time", "min", False),
    "overtime": ("Overtime", "min", False),
    "utilization": ("Utilization", "of session", True),
    "overbooked_slots": ("Overbooked slots", "per session", None),
}
POLICIES = [  # name, policy, oracle?
    ("Fixed interval", fixed_interval(), False),
    ("Blind overbooking", value_ladder.blind_overbooking(), False),
    ("Threshold 0.20", threshold_rule(0.20), False),
    ("Threshold 0.30", threshold_rule(0.30), False),
    ("Threshold 0.40", threshold_rule(0.40), False),
    ("Cost rule r=1.0", cost_rule(1.0), False),
    ("Cost rule r=0.5", cost_rule(0.5), False),
    ("Oracle (knows who misses)", threshold_rule(0.5), True),
]


def simulate(cfg, pool, reps, seed) -> pd.DataFrame:
    rows = []
    for rep in range(reps):
        d = draw_session(cfg, np.random.default_rng([seed, rep]), pool)
        oracle = type(d)((~d.shows).astype(float), d.shows, d.arrival_offset, d.service)
        for name, policy, is_oracle in POLICIES:
            rows.append({"policy": name, "rep": rep, **simulate_session(cfg, policy, oracle if is_oracle else d)})
    return pd.DataFrame(rows)


def summarize(res: pd.DataFrame) -> dict:
    base = res[res.policy == POLICIES[0][0]].set_index("rep")
    out = {}
    for name, g in res.groupby("policy", sort=False):
        g = g.set_index("rep")
        out[name] = {}
        for m in METRICS:
            diff = g[m] - base[m]
            half = lambda s: float(1.96 * s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 1 else 0.0
            out[name][m] = {"mean": float(g[m].mean()), "ci": half(g[m]), "delta": float(diff.mean()), "dci": half(diff)}
    return out


def b64(name: str) -> str:
    p = OUT / name
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Overbooking Simulation Dashboard</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--mute:#667085;--line:#e4e7ec;--good:#1a7f4b;--bad:#c2410c;--neutral:#667085;--accent:#2a6f97}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f141c;--card:#171e29;--ink:#e8ecf3;--mute:#93a0b4;--line:#2a3445;--good:#4ade80;--bad:#fb923c;--neutral:#93a0b4;--accent:#6bb1d8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 20px}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end;margin-bottom:20px}label{display:block;font-size:12px;color:var(--mute);margin-bottom:4px}
select{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:14px;min-width:210px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h3{margin:0;font-size:13px;color:var(--mute);font-weight:600}.val{font-size:30px;font-weight:700;margin:6px 0 2px}
.unit{font-size:12px;color:var(--mute);font-weight:400}.base{font-size:12px;color:var(--mute)}
.delta{display:inline-block;margin-top:8px;font-weight:600;font-size:14px}.good{color:var(--good)}.bad{color:var(--bad)}.neutral{color:var(--neutral)}
.note{margin-top:18px;padding:12px 14px;border-left:3px solid var(--accent);background:var(--card);border-radius:0 8px 8px 0;color:var(--mute);font-size:13px}
h2{font-size:17px;margin:34px 0 10px}img{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13px}
th,td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--line)}th:first-child,td:first-child{text-align:left}th{color:var(--mute);font-weight:600}
</style></head><body><main>
<h1>Overbooking Simulation Dashboard</h1>
<p class="sub">__CONFIG__</p>
<div class="controls">
 <div><label for="policy">Policy</label><select id="policy"></select></div>
 <div><label for="source">Risk source</label><select id="source"></select></div>
</div>
<div class="grid" id="cards"></div>
<div class="note" id="verdict"></div>
<h2>All policies</h2><div style="overflow-x:auto"><table id="table"></table></div>
__IMAGES__
</main>
<script>
const DATA=__DATA__, METRICS=__METRICS__, SOURCES=__SOURCES__, BASE=__BASE__;
const pol=document.getElementById('policy'), src=document.getElementById('source');
Object.keys(DATA[Object.keys(DATA)[0]]).forEach(p=>pol.add(new Option(p,p)));
Object.keys(DATA).forEach(s=>src.add(new Option(SOURCES[s],s)));
pol.value=Object.keys(DATA[Object.keys(DATA)[0]])[3];
const f=(x,m)=>m==='utilization'?(x*100).toFixed(1)+'%':x.toFixed(1);
const fd=(x,m)=>(x>=0?'+':'')+(m==='utilization'?(x*100).toFixed(1)+' pp':x.toFixed(1));
function cls(m,d,dci){const hib=METRICS[m][2];if(hib===null||Math.abs(d)<=dci)return 'neutral';return ((d>0)===hib)?'good':'bad';}
function render(){
 const d=DATA[src.value], p=pol.value, cards=document.getElementById('cards'); cards.innerHTML='';
 for(const m in METRICS){const x=d[p][m], b=d[BASE][m], [label,unit]=METRICS[m];
  const c=p===BASE?'neutral':cls(m,x.delta,x.dci);
  cards.insertAdjacentHTML('beforeend',`<div class="card"><h3>${label}</h3><div class="val">${f(x.mean,m)} <span class="unit">${unit}</span></div>
  <div class="base">${BASE}: ${f(b.mean,m)}</div>${p===BASE?'':`<div class="delta ${c}">${fd(x.delta,m)} <span class="unit">&plusmn;${(m==='utilization'?x.dci*100:x.dci).toFixed(1)} (95% CI)</span></div>`}</div>`);}
 const x=d[p]; let v='';
 if(p===BASE) v='Baseline: one patient per slot, no overbooking.';
 else{const s=x.seen.delta, w=x.mean_wait.delta, i=x.idle.delta;
  v=`Compared with fixed-interval booking, this policy sees ${s.toFixed(1)} more patients and cuts physician idle time by ${Math.abs(i).toFixed(0)} min, at the price of ${w.toFixed(1)} min more average waiting${s>0.05?` (${(w/s).toFixed(2)} min of waiting per extra patient)`:''}.`;}
 document.getElementById('verdict').textContent=v;
 let h='<tr><th>Policy</th>'+Object.values(METRICS).map(m=>`<th>${m[0]}</th>`).join('')+'</tr>';
 for(const name in d){h+=`<tr><td>${name}</td>`+Object.keys(METRICS).map(m=>{const y=d[name][m];return `<td>${f(y.mean,m)}${name===BASE?'':` <span class="${cls(m,y.delta,y.dci)}">(${fd(y.delta,m)})</span>`}</td>`}).join('')+'</tr>';}
 document.getElementById('table').innerHTML=h;
}
pol.onchange=src.onchange=render; render();
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--risks", help="CSV with columns p and y (model predictions and outcomes)")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    cfg = SessionConfig()

    data, sources = {}, {}
    for key, label, pool in [("synthetic", "Synthetic (calibrated Beta risks)", None)] + (
            [("model", "Random forest (test period)", pd.read_csv(args.risks))] if args.risks else []):
        data[key], sources[key] = summarize(simulate(cfg, pool, args.reps, args.seed)), label

    plots.tradeoff_chart(cfg)
    plots.timeline_chart(cfg)
    images = "".join(
        f'<h2>{title}</h2><img alt="{title}" src="data:image/png;base64,{b64(f)}">'
        for title, f in [("Trade-off: idle time vs waiting time", "tradeoff.png"),
                         ("One session, side by side", "timeline.png"),
                         ("What each layer adds", "value_ladder.png")] if b64(f))
    config = (f"{args.reps} simulated sessions per policy · {cfg.n_slots} slots × {cfg.slot_min:.0f} min · "
              f"mean consultation {cfg.service_mean:.0f} min · {cfg.n_slots + cfg.extra_requests} booking requests per session · "
              "parameters are assumptions")
    html = (HTML.replace("__CONFIG__", config).replace("__IMAGES__", images)
            .replace("__DATA__", json.dumps(data)).replace("__METRICS__", json.dumps(METRICS))
            .replace("__SOURCES__", json.dumps(sources)).replace("__BASE__", json.dumps(POLICIES[0][0])))
    OUT.mkdir(exist_ok=True)
    path = OUT / "dashboard.html"
    path.write_text(html, encoding="utf-8")
    print("Saved:", path)


if __name__ == "__main__":
    main()

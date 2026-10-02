"""Watch a clinic day run: SimPy event log + animated replay (fixed interval vs overbooking, same day).

    python live_day.py                 # builds output/live_simulation.html and opens it
    python live_day.py --trace         # also prints the SimPy event log of one day in the terminal
    python live_day.py --day 3 --trace # trace day 3
    python live_day.py --risks ../ml/data/processed/risks_random_forest.csv

Each day is one SimPy run (simpy.Environment + a Resource for the physician). The two panels use the same
patients, show-ups, arrival times and consultation lengths; only the booking policy differs.
"""
import argparse
import dataclasses
import json
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd

from clinic_sim import SessionConfig, draw_session, fixed_interval, simulate_session, threshold_rule

OUT = Path(__file__).resolve().parent / "output"
RISKS = Path(__file__).resolve().parents[1] / "ml" / "data" / "processed" / "risks_random_forest.csv"
DAYS = 12


def clock(minutes: float) -> str:
    m = int(round(8 * 60 + minutes))
    return f"{m // 60:02d}:{m % 60:02d}"


def run_day(cfg: SessionConfig, policy, draws, info=None) -> dict:
    """info: optional per-request details (age, days booked ahead) of real appointment records."""
    r = simulate_session(cfg, policy, draws, detail=True)
    patients = [{"id": int(p["patient"]) + 1, "slot": p["slot"], "appt": p["appointment"],
                 "ready": max(p["appointment"], p["arrival"]), "start": p["start"], "end": p["end"],
                 "ob": bool(p["overbooked"]), "risk": round(float(draws.risk[p["patient"]]), 3),
                 **(info[p["patient"]] if info else {})} for p in r["detail"]]
    per_slot = {}
    for p in patients:
        per_slot[p["slot"]] = per_slot.get(p["slot"], 0) + 1
    for _, s in r["no_shows"]:
        per_slot[int(s)] = per_slot.get(int(s), 0) + 1
    noshows = [{"id": int(i) + 1, "slot": int(s), "risk": round(float(draws.risk[i]), 3), "ob": per_slot[int(s)] > 1,
                **(info[i] if info else {})} for i, s in r["no_shows"]]
    return {"patients": patients, "noshows": noshows, "seen": r["seen"], "mean_wait": r["mean_wait"], "idle": r["idle"],
            "overtime": r["overtime"], "overbooked_slots": r["overbooked_slots"]}


def real(p: dict) -> str:
    """Details of the real appointment record (only in real-data mode)."""
    return f", age {p['age']}, booked {p['lead']} days ahead" if "age" in p else ""


def print_trace(name: str, day: dict) -> None:
    events = []
    for p in day["patients"]:
        events += [(p["ready"], f"patient {p['id']:>2} arrives (slot {p['slot'] + 1}{', overbooked' if p['ob'] else ''}, risk {p['risk']:.2f}{real(p)})"),
                   (p["start"], f"doctor starts patient {p['id']:>2}  (waited {p['start'] - p['ready']:.1f} min)"),
                   (p["end"], f"doctor finishes patient {p['id']:>2}")]
    events += [(n["slot"] * 15.0, f"patient {n['id']:>2} does NOT show up (slot {n['slot'] + 1}, risk {n['risk']:.2f}{real(n)})") for n in day["noshows"]]
    print(f"\n--- SimPy event log: {name} ---")
    for t, text in sorted(events, key=lambda e: e[0]):
        print(f"{clock(t)}  {text}")
    print(f"--- {name}: seen {day['seen']}, mean wait {day['mean_wait']:.1f} min, idle {day['idle']:.0f} min, "
          f"overtime {day['overtime']:.1f} min ---")


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live clinic simulation</title><style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--mute:#667085;--line:#e4e7ec;--acc:#2a6f97}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f141c;--card:#171e29;--ink:#e8ecf3;--mute:#93a0b4;--line:#2a3445;--acc:#6bb1d8}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}main{max-width:1180px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:21px;margin:0}p{color:var(--mute);margin:4px 0 14px}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
button,select{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font-size:14px;cursor:pointer}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}input[type=range]{flex:1;min-width:200px}
.clock{font-size:26px;font-weight:700;min-width:80px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px;margin-bottom:12px}
canvas{width:100%;display:block}.legend span{display:inline-block;margin-right:14px;font-size:13px;color:var(--mute)}
.legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:-1px}
</style></head><body><main>
<h1>Live clinic simulation</h1>
<p>__NOTE__</p>
<div class="bar"><button class="primary" id="play">Pause</button><button id="restart">Restart</button>
<label>Day <select id="day"></select></label><label>Speed <select id="speed"><option value="4">x4</option><option value="8" selected>x8</option><option value="16">x16</option><option value="40">x40</option></select></label>
<span class="clock" id="clock">08:00</span><input type="range" id="scrub" min="0" max="1000" value="0"></div>
<div class="legend"><span><i style="background:#c5ccd6"></i>booked, not arrived</span><span><i style="background:#f2a93b"></i>waiting</span><span><i style="background:#2a6f97"></i>in consultation</span><span><i style="background:#3d9970"></i>done</span><span><i style="background:#d64545"></i>no-show</span><span><i style="background:none;border:2px solid #e07a5f"></i>overbooked patient</span></div>
<div class="card"><canvas id="c0" width="1100" height="270"></canvas></div>
<div class="card"><canvas id="c1" width="1100" height="270"></canvas></div>
</main><script>
if(!CanvasRenderingContext2D.prototype.roundRect){CanvasRenderingContext2D.prototype.roundRect=function(x,y,w,h){this.rect(x,y,w,h);};}
const DATA=__DATA__, CFG=__CFG__, T=CFG.session_min;
const cols=getComputedStyle(document.documentElement);
const dark=matchMedia('(prefers-color-scheme: dark)').matches;
const INK=dark?'#e8ecf3':'#1d2433', MUTE=dark?'#93a0b4':'#667085', LINE=dark?'#2a3445':'#d0d5dd', BOX=dark?'#1f2937':'#f2f4f7';
const daySel=document.getElementById('day'), speedSel=document.getElementById('speed'), scrub=document.getElementById('scrub');
DATA.days.forEach((d,i)=>daySel.add(new Option(`${d.label||('Day '+(i+1))} (${d.policy_b.overbooked_slots} overbooked slots)`,i)));
let day=DATA.days[0], t=0, playing=true, last=null, tEnd=T+20;
function setDay(i){day=DATA.days[i];tEnd=Math.max(T,...[day.fixed,day.policy_b].map(p=>Math.max(...p.patients.map(x=>x.end))))+8;t=0;}
function busy(p){return p.patients.map(x=>[x.start,x.end]);}
function stats(p,t){const done=p.patients.filter(x=>x.end<=t).length;
  const started=p.patients.filter(x=>x.start<=t);const wait=started.length?started.reduce((a,x)=>a+(x.start-x.ready),0)/started.length:0;
  const lim=Math.min(t,T);let b=0,ot=0;for(const [s,e] of busy(p)){b+=Math.max(0,Math.min(e,lim)-Math.min(s,lim));ot+=Math.max(0,Math.min(e,t)-Math.max(s,T));}
  return {done,wait,idle:lim-b,ot};}
function fmt(m){const x=Math.round(480+m);return String(Math.floor(x/60)).padStart(2,'0')+':'+String(x%60).padStart(2,'0');}
function draw(cv,p,title,t){
  const g=cv.getContext('2d'),W=cv.width,H=cv.height;g.clearRect(0,0,W,H);g.font='600 15px system-ui,sans-serif';g.fillStyle=INK;g.fillText(title,16,24);
  const n=CFG.n_slots,sw=(W-32)/n;
  for(let s=0;s<n;s++){const x=16+s*sw;g.fillStyle=BOX;g.strokeStyle=LINE;g.beginPath();g.roundRect(x+1,38,sw-2,50,6);g.fill();g.stroke();
    g.fillStyle=MUTE;g.font='10px system-ui,sans-serif';g.fillText(fmt(s*CFG.slot_min),x+4,50);}
  const chips=[];p.patients.forEach(x=>chips.push({...x,show:true}));p.noshows.forEach(x=>chips.push({...x,show:false,appt:x.slot*CFG.slot_min}));
  const idx={};chips.sort((a,b)=>a.appt-b.appt||a.id-b.id).forEach(c=>{const k=idx[c.slot]=(idx[c.slot]||0);idx[c.slot]++;
    const x=16+c.slot*sw+sw/2,y=66+k*0;const ox=(k?10:-10)*(sw>30?1:0.5);let col='#c5ccd6';
    if(!c.show){if(t>=c.appt)col='#d64545';}else if(t>=c.end)col='#3d9970';else if(t>=c.start)col='#2a6f97';else if(t>=c.ready)col='#f2a93b';
    g.beginPath();g.arc(x+ox,y+6,8,0,7);g.fillStyle=col;g.fill();if(c.ob){g.lineWidth=2.5;g.strokeStyle='#e07a5f';g.stroke();g.lineWidth=1;}
    g.fillStyle='#fff';g.font='9px system-ui,sans-serif';g.textAlign='center';g.fillText(!c.show&&t>=c.appt?'x':c.id,x+ox,y+9);g.textAlign='left';});
  g.fillStyle=MUTE;g.font='12px system-ui,sans-serif';g.fillText('Waiting room',16,122);
  g.strokeStyle=LINE;g.strokeRect(16,128,600,64);
  const wait=p.patients.filter(x=>x.ready<=t&&t<x.start).sort((a,b)=>a.ready-b.ready);
  wait.forEach((x,i)=>{const cx=34+i*40;g.beginPath();g.arc(cx,152,15,0,7);g.fillStyle='#f2a93b';g.fill();g.fillStyle='#fff';g.font='600 12px system-ui,sans-serif';g.textAlign='center';g.fillText(x.id,cx,156);g.font='10px system-ui,sans-serif';g.fillStyle=MUTE;g.fillText((t-x.ready).toFixed(0)+'m',cx,184);g.textAlign='left';});
  const cur=p.patients.find(x=>x.start<=t&&t<x.end);
  g.fillStyle=MUTE;g.font='12px system-ui,sans-serif';g.fillText('Physician',650,122);
  g.fillStyle=cur?'#2a6f97':(dark?'#374151':'#d0d5dd');g.beginPath();g.roundRect(650,128,190,64,10);g.fill();
  g.fillStyle='#fff';g.font='600 14px system-ui,sans-serif';g.fillText(cur?'Patient '+cur.id+(cur.ob?' (overbooked)':''):'Idle',664,155);
  if(cur){g.fillStyle='rgba(255,255,255,.35)';g.fillRect(664,168,162*(t-cur.start)/(cur.end-cur.start),8);}
  const s=stats(p,t);g.fillStyle=INK;g.font='13px system-ui,sans-serif';
  [['Patients seen',s.done+' / '+p.seen],['Avg wait so far',s.wait.toFixed(1)+' min'],['Idle so far',s.idle.toFixed(0)+' min'],['Overtime',s.ot.toFixed(1)+' min']].forEach((r,i)=>{g.fillStyle=MUTE;g.fillText(r[0],870,138+i*18);g.fillStyle=INK;g.fillText(r[1],985,138+i*18);});
  const bx=16,bw=W-32;g.fillStyle=BOX;g.fillRect(bx,224,bw,10);g.fillStyle=cols.getPropertyValue('--acc')||'#2a6f97';g.fillStyle='#2a6f97';g.fillRect(bx,224,bw*Math.min(1,t/tEnd),10);
  g.fillStyle='#d64545';g.fillRect(bx+bw*T/tEnd,220,2,18);g.fillStyle=MUTE;g.font='11px system-ui,sans-serif';g.fillText('planned end '+fmt(T),bx+bw*T/tEnd+4,248);
}
function frame(now){if(last===null)last=now;const dt=(now-last)/1000;last=now;
  if(playing){t+=dt*Number(speedSel.value);if(t>=tEnd){t=tEnd;playing=false;document.getElementById('play').textContent='Replay';}}
  document.getElementById('clock').textContent=fmt(t);scrub.value=1000*t/tEnd;
  draw(document.getElementById('c0'),day.fixed,'Fixed interval: one patient per slot (seen '+day.fixed.seen+', mean wait '+day.fixed.mean_wait.toFixed(1)+' min, idle '+day.fixed.idle.toFixed(0)+' min, overtime '+day.fixed.overtime.toFixed(1)+' min at the end of the day)',t);
  draw(document.getElementById('c1'),day.policy_b,CFG.policy_b_name+' (seen '+day.policy_b.seen+', mean wait '+day.policy_b.mean_wait.toFixed(1)+' min, idle '+day.policy_b.idle.toFixed(0)+' min, overtime '+day.policy_b.overtime.toFixed(1)+' min at the end of the day)',t);
  requestAnimationFrame(frame);}
document.getElementById('play').onclick=()=>{if(t>=tEnd){t=0;}playing=!playing;last=null;document.getElementById('play').textContent=playing?'Pause':'Play';};
document.getElementById('restart').onclick=()=>{t=0;playing=true;last=null;document.getElementById('play').textContent='Pause';};
daySel.onchange=()=>{setDay(Number(daySel.value));playing=true;last=null;document.getElementById('play').textContent='Pause';};
scrub.oninput=()=>{t=tEnd*scrub.value/1000;playing=false;document.getElementById('play').textContent='Play';};
setDay(0);requestAnimationFrame(frame);
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--risks", default=str(RISKS) if RISKS.exists() else None, help="CSV with columns p and y")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--trace", action="store_true", help="print the SimPy event log of one day")
    ap.add_argument("--day", type=int, default=1, help="day number used by --trace")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    cfg = SessionConfig()
    pool = pd.read_csv(args.risks) if args.risks else None
    policy_b = threshold_rule(args.threshold)
    real_data = pool is not None and "AppointmentDay" in pool.columns
    if real_data:
        pool["AppointmentDay"] = pd.to_datetime(pool["AppointmentDay"])
        pool["ScheduledDay"] = pd.to_datetime(pool["ScheduledDay"])
        dates = sorted(pool["AppointmentDay"].unique())
    days = []
    for d in range(DAYS):
        rng = np.random.default_rng([args.seed, d])
        if real_data:
            # real appointments of one real date, in the order the patients booked; risk and attendance are real
            date = dates[d % len(dates)]
            rows = pool[pool["AppointmentDay"] == date]
            rows = rows.iloc[np.sort(rng.choice(len(rows), cfg.n_requests, replace=False))] \
                .sort_values("ScheduledDay", kind="stable")
            draws = dataclasses.replace(draw_session(cfg, rng, None), risk=rows["p"].to_numpy(),
                                        shows=(rows["y"].to_numpy() == 0))
            info = [{"age": int(a), "lead": int(l)} for a, l in zip(rows["Age"], rows["LeadDays"])]
            label = f"{pd.Timestamp(date):%d %b %Y}: sample {d // len(dates) + 1}, {cfg.n_requests} of {len(pool[pool.AppointmentDay == date])} appointments"
        else:
            draws, info, label = draw_session(cfg, rng, pool), None, f"Day {d + 1}"
        days.append({"label": label, "fixed": run_day(cfg, fixed_interval(), draws, info),
                     "policy_b": run_day(cfg, policy_b, draws, info)})
    source = ("Patients, risks and attendance are real appointment records of the Medical Appointment No Shows data "
              "(test period 2-8 June 2016; risks = random forest predictions; booking order = real booking time). "
              "Consultation length and lateness are simulated: they are not in the data. "
              "This is ONE sample session of a day: open whole_day.html to see every record of the day."
              if real_data else
              "Synthetic patients (Beta-distributed risks); run ml/build_reports.py to use the real appointment records. "
              "Consultation length and lateness are simulated.")
    if args.trace:
        d = days[args.day - 1]
        print(f"Day {args.day} ({d['label']}): {cfg.n_slots} slots x {cfg.slot_min:g} min")
        print("Patients:", "real appointment records of the test period (model risk, real attendance)" if real_data else "synthetic")
        print("Simulated, not in the data: consultation length, lateness")
        print_trace("Fixed interval", d["fixed"])
        print_trace(f"Overbooking, threshold {args.threshold:.2f}", d["policy_b"])
    data = {"days": days}
    meta = {"n_slots": cfg.n_slots, "slot_min": cfg.slot_min, "session_min": cfg.session_min,
            "policy_b_name": f"Selective overbooking, threshold {args.threshold:.2f}"}
    html = (HTML.replace("__DATA__", json.dumps(data)).replace("__CFG__", json.dumps(meta))
            .replace("__NOTE__", "One clinic day replayed from a SimPy run; both panels have the same patients, only the booking "
                     "policy differs. " + source))
    OUT.mkdir(exist_ok=True)
    path = OUT / "live_simulation.html"
    path.write_text(html, encoding="utf-8")
    print("Saved:", path)
    if not args.no_open:
        webbrowser.open(path.as_uri())


if __name__ == "__main__":
    main()

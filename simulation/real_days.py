"""Whole-day simulation: every real appointment record of a day, spread over many clinic sessions.

    python real_days.py                    # builds output/whole_day.html and opens it
    python real_days.py --source r4        # decide with the rule-based risk (R4) instead of the random forest
    python real_days.py --source lr        # ... or logistic regression
    python real_days.py --threshold 0.25   # threshold of the overbooking rule shown in the animation

The data has no doctor information, so the records of a date are dealt randomly to clinic sessions of up to 20
booking requests each (16 slots of 15 minutes). Inside a session patients are in real booking order. Risk and
attendance are real; consultation length and lateness are simulated (they are not in the data).
"""
import argparse
import dataclasses
import json
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd

from clinic_sim import SessionConfig, cost_rule, draw_session, fixed_interval, simulate_session, threshold_rule

OUT = Path(__file__).resolve().parent / "output"
RISKS = Path(__file__).resolve().parents[1] / "ml" / "data" / "processed" / "risks_random_forest.csv"
SOURCES = {"rf": ("p", "random forest"), "lr": ("p_lr", "logistic regression"), "r4": ("p_r4", "rule R4")}


def sessions_of(day: pd.DataFrame, cfg: SessionConfig, seed: int):
    """Deal all records of a date to sessions; yield (session number, rows in booking order)."""
    idx = np.random.default_rng(seed).permutation(len(day))
    n = cfg.n_requests
    for s, start in enumerate(range(0, len(day), n)):
        part = day.iloc[np.sort(idx[start:start + n])]
        yield s, part.sort_values("ScheduledDay", kind="stable")


def simulate_day(day: pd.DataFrame, cfg: SessionConfig, risk_col: str, seed: int, policies: dict, animate: str):
    """Run every session with every policy. Returns aggregates per policy and per-record details of `animate`."""
    agg = {name: {"seen": 0, "deferred": 0, "wait_sum": 0.0, "idle": 0.0, "overtime": 0.0, "busy": 0.0,
                  "ob_slots": 0, "sessions": 0} for name in policies}
    records = []
    rng = np.random.default_rng(seed + 1)
    for s, part in sessions_of(day, cfg, seed):
        scfg = dataclasses.replace(cfg, requests=len(part))
        draws = dataclasses.replace(draw_session(scfg, rng, None), risk=part[risk_col].to_numpy(),
                                    shows=(part["y"].to_numpy() == 0))
        rows = [[None] * 3 + [-1, None, None, None, 0] * 2 for _ in range(len(part))]  # filled below
        for name, policy in policies.items():
            r = simulate_session(scfg, policy, draws, detail=(name in ("fixed", animate)))
            a = agg[name]
            a["seen"] += r["seen"]; a["deferred"] += r["deferred"]; a["wait_sum"] += r["mean_wait"] * r["seen"]
            a["idle"] += r["idle"]; a["overtime"] += r["overtime"]; a["busy"] += r["utilization"]
            a["ob_slots"] += r["overbooked_slots"]; a["sessions"] += 1
            if "detail" in r:
                col = 3 if name == "fixed" else 8
                for i in range(len(part)):
                    rows[i][col] = -1                                  # deferred until proven booked
                for p in r["detail"]:
                    i = p["patient"]
                    rows[i][col:col + 5] = [p["slot"], round(max(p["appointment"], p["arrival"]), 1), round(p["start"], 1),
                                            round(p["end"], 1), int(p["overbooked"])]
                for i, slot in r["no_shows"]:
                    rows[i][col] = int(slot)
        for i, (_, rec) in enumerate(part.iterrows()):
            records.append([int(rec["AppointmentID"]), rec["ScheduledDay"].strftime("%m-%d %H:%M"), int(rec["Age"]),
                            int(rec["LeadDays"]), round(float(rec["p"]), 3), round(float(rec["p_lr"]), 3),
                            round(float(rec["p_r4"]), 3), int(rec["y"]), s, *rows[i][3:]])
    return agg, records


def summarize(agg: dict, n_records: int) -> dict:
    out = {}
    for name, a in agg.items():
        out[name] = {"seen": a["seen"], "deferred": a["deferred"], "mean_wait": a["wait_sum"] / max(a["seen"], 1),
                     "idle_h": a["idle"] / 60, "overtime_h": a["overtime"] / 60, "utilization": a["busy"] / a["sessions"],
                     "ob_slots": a["ob_slots"], "sessions": a["sessions"]}
    return out


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Whole-day simulation</title><style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--mute:#667085;--line:#e4e7ec;--acc:#2a6f97;--good:#1a7f4b;--bad:#c2410c}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f141c;--card:#171e29;--ink:#e8ecf3;--mute:#93a0b4;--line:#2a3445;--acc:#6bb1d8;--good:#4ade80;--bad:#fb923c}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}main{max-width:1180px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:21px;margin:0}h2{font-size:16px;margin:22px 0 8px}p{color:var(--mute);margin:4px 0 12px}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
button,select,input{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font-size:14px}button{cursor:pointer}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}input[type=range]{flex:1;min-width:200px;padding:0}
.clock{font-size:26px;font-weight:700;min-width:80px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin-bottom:12px}
canvas{width:100%;display:block}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:900px){.two{grid-template-columns:1fr}}.stat{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--mute);margin:2px 0 6px}.stat b{color:var(--ink);font-size:17px;display:block}h3{margin:0 0 4px;font-size:14px}#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);padding:5px 9px;border-radius:6px;font-size:12px;display:none;z-index:9}canvas.tiles{cursor:pointer}
.k h3{margin:0;font-size:12px;color:var(--mute);font-weight:600}.k .v{font-size:24px;font-weight:700}.k .s{font-size:12px;color:var(--mute)}
.good{color:var(--good)}.bad{color:var(--bad)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}th{color:var(--mute);position:sticky;top:0;background:var(--card)}.scroll{overflow:auto;max-height:420px}
.legend span{display:inline-block;margin-right:14px;font-size:13px;color:var(--mute)}.legend i{display:inline-block;width:11px;height:11px;margin-right:5px;vertical-align:-1px}
.backbtn{display:inline-block;margin-bottom:14px;padding:6px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--acc,var(--accent,#2a6f97));text-decoration:none;font-size:14px}.backbtn:hover{opacity:.8}</style></head><body><main>
<a class="backbtn" href="simulation_hub.html">&larr; Back to Simulation</a>
<h1>Whole-day simulation</h1>
<p>__NOTE__</p>
<div class="bar"><label>Date <select id="day"></select></label><span id="daynote" style="color:var(--mute)"></span></div>
<h2>Day totals</h2><div class="grid" id="kpis"></div>
<div class="card" style="margin-top:12px"><div class="scroll" style="max-height:none"><table id="ptable"></table></div></div>
<h2>The day, minute by minute</h2>
<p>Each square is <b>one doctor</b> (one clinic session). <b style="color:#2a6f97">Blue</b>: seeing a patient. <b style="color:#e07a5f">Orange</b>: seeing an overbooked patient. <b style="color:#d98a97">Pink</b>: idle although the session is still running, which is wasted time. <b>Grey</b>: finished for the day. The small amber number is how many patients are waiting for that doctor. Hover a square for details; click it to list that doctor's patients below.</p>
<div class="bar"><button class="primary" id="play">Pause</button><button id="restart">Restart</button>
<label>Speed <select id="speed"><option value="10">x10</option><option value="20" selected>x20</option><option value="40">x40</option><option value="100">x100</option></select></label>
<span class="clock" id="clock">08:00</span><input type="range" id="scrub" min="0" max="1000" value="0"></div>
<div class="two">
<div class="card"><h3>Fixed interval: one patient per slot</h3><div class="stat" id="sf"></div><canvas id="cf" width="560" height="380"></canvas></div>
<div class="card"><h3 id="otitle">Selective overbooking</h3><div class="stat" id="so"></div><canvas id="co" width="560" height="380"></canvas></div>
</div>
<div class="two">
<div class="card"><canvas id="cq" width="560" height="190"></canvas></div>
<div class="card"><canvas id="ci" width="560" height="190"></canvas></div>
</div>
<h2>Every record of the day</h2>
<div class="bar"><select id="fstatus"><option value="all">All records</option><option value="seen">Seen (overbooking)</option><option value="noshow">No-show</option><option value="deferred">No slot (overbooking)</option><option value="ob">Overbooked</option></select>
<input id="fsearch" placeholder="Appointment ID" size="14"><span id="sessinfo"></span><button id="prev">&lt;</button><span id="pageinfo" style="color:var(--mute)"></span><button id="next">&gt;</button></div>
<div class="card"><div class="scroll"><table id="rtable"></table></div></div>
<p>Risk columns: random forest (RF), logistic regression (LR), rule R4. The simulation decides with __SRC__ at threshold __THR__. "Wait" is the simulated waiting time in minutes (fixed interval / overbooking). "No slot" = no free slot in the session, booked for another day.</p>
</main><div id="tip"></div><script>
if(!CanvasRenderingContext2D.prototype.roundRect){CanvasRenderingContext2D.prototype.roundRect=function(x,y,w,h){this.rect(x,y,w,h);};}
const D=__DATA__, META=__META__, T=META.session_min, dark=matchMedia('(prefers-color-scheme: dark)').matches;
const INK=dark?'#e8ecf3':'#1d2433', MUTE=dark?'#93a0b4':'#667085', BOX=dark?'#1f2937':'#eef0f3';
const f1=x=>x.toFixed(1), fm=m=>{const x=Math.round(480+m);return String(Math.floor(x/60)).padStart(2,'0')+':'+String(x%60).padStart(2,'0');};
// record columns: 0 id,1 booked,2 age,3 lead,4 rf,5 lr,6 r4,7 y,8 session, fixed:9 slot,10 ready,11 start,12 end,13 ob, over:14 slot,15 ready,16 start,17 end,18 ob
const daySel=document.getElementById('day');D.days.forEach((d,i)=>daySel.add(new Option(d.date+' ('+d.records.length+' appointments)',i)));
let day,tEnd,arr,t=0,playing=true,last=null,page=0,rows=[],sessFilter=-1;
function curves(recs,c0){const n=Math.ceil(tEnd)+2,w=new Array(n).fill(0),b=new Array(n).fill(0),dn=new Array(n).fill(0);
  for(const r of recs){if(r[c0+2]==null)continue;const rd=r[c0+1],s=r[c0+2],e=r[c0+3];
    for(let m=Math.max(0,Math.floor(rd));m<Math.min(n,Math.ceil(s));m++)w[m]++;for(let m=Math.floor(s);m<Math.min(n,Math.ceil(e));m++)b[m]++;if(Math.ceil(e)<n)dn[Math.ceil(e)]++;}
  for(let m=1;m<n;m++)dn[m]+=dn[m-1];return {w,b,dn};}
function setDay(i){day=D.days[i];sessFilter=-1;const recs=day.records;let mx=T;for(const r of recs){if(r[12]!=null)mx=Math.max(mx,r[12]);if(r[17]!=null)mx=Math.max(mx,r[17]);}
  tEnd=mx+6;arr={f:curves(recs,9),o:curves(recs,14)};t=0;page=0;
  document.getElementById('daynote').textContent=day.sessions+' clinic sessions of up to '+META.n_requests+' booking requests; real records, real attendance';renderKpis();applyFilter();}
function renderKpis(){const P=day.policies,F=P.fixed,O=P[META.animate];
  const cards=[['Patients seen',F.seen,O.seen,0,1],['Appointments without a slot',F.deferred,O.deferred,0,-1],['Mean wait (min)',F.mean_wait,O.mean_wait,1,-1],
   ['Physician idle (hours, all sessions)',F.idle_h,O.idle_h,0,-1],['Overtime (hours, all sessions)',F.overtime_h,O.overtime_h,1,-1],['Utilization',F.utilization*100,O.utilization*100,1,1]];
  document.getElementById('kpis').innerHTML=cards.map(c=>{const d=c[2]-c[1];const g=Math.abs(d)<1e-9?'':((d*c[4])>0?'good':'bad');
   return `<div class="card k"><h3>${c[0]}</h3><div class="v">${c[2].toFixed(c[3])}${c[0]==='Utilization'?'%':''}</div><div class="s">fixed interval: ${c[1].toFixed(c[3])}</div><div class="s ${g}">${d>=0?'+':''}${d.toFixed(c[3])} with overbooking</div></div>`;}).join('');
  const names=Object.keys(P);document.getElementById('ptable').innerHTML='<tr><th>Policy</th><th>Seen</th><th>No slot</th><th>Mean wait</th><th>Idle (h)</th><th>Overtime (h)</th><th>Utilization</th><th>Overbooked slots</th></tr>'+
   names.map(n=>{const p=P[n];return `<tr><td>${n}${n===META.animate?' (shown below)':''}</td><td>${p.seen}</td><td>${p.deferred}</td><td>${f1(p.mean_wait)}</td><td>${f1(p.idle_h)}</td><td>${f1(p.overtime_h)}</td><td>${(p.utilization*100).toFixed(1)}%</td><td>${p.ob_slots}</td></tr>`}).join('');}
const COL={busy:'#2a6f97',ob:'#e07a5f',idle:dark?'#8a4553':'#f1b7c0',done:dark?'#2e3645':'#d9dde4',amber:'#f2a93b'};
let tileW=30,tileCols=18;
function prep(){if(day.S)return;const S=day.sessions,mk=c0=>{const a=Array.from({length:S},()=>[]);for(const r of day.records){if(r[c0+2]!=null)a[r[8]].push([r[c0+1],r[c0+2],r[c0+3],r[c0+4]]);}return a;};
  day.S={f:mk(9),o:mk(14)};tileCols=Math.min(18,Math.ceil(S/1));tileW=Math.floor(520/tileCols);const rowsN=Math.ceil(S/tileCols);
  for(const id of['cf','co']){const cv=document.getElementById(id);cv.height=rowsN*tileW+6;cv.className='tiles';}
  const mx=Math.max(1,...arr.f.w,...arr.o.w);day.qmax=mx;}
function sstate(list,t){let cur=null,w=0,dn=0;for(const p of list){if(p[1]<=t&&t<p[2])cur=p;if(p[0]<=t&&t<p[1])w++;if(p[2]<=t)dn++;}return {cur,w,dn};}
function tiles(cv,list,t){const g=cv.getContext('2d');g.clearRect(0,0,cv.width,cv.height);
  for(let s=0;s<list.length;s++){const x=4+(s%tileCols)*tileW,y=3+Math.floor(s/tileCols)*tileW,st=sstate(list[s],t);
    let col=COL.done;if(st.cur)col=st.cur[3]?COL.ob:COL.busy;else if(t<T)col=COL.idle;
    g.fillStyle=col;g.beginPath();g.roundRect(x,y,tileW-3,tileW-3,4);g.fill();
    if(st.cur&&t>T){g.strokeStyle='#d64545';g.lineWidth=2;g.stroke();g.lineWidth=1;}
    if(st.w>0){g.fillStyle=COL.amber;g.beginPath();g.arc(x+tileW-11,y+tileW-11,8,0,7);g.fill();g.fillStyle='#1d2433';g.font='600 11px system-ui,sans-serif';g.textAlign='center';g.fillText(st.w,x+tileW-11,y+tileW-7);g.textAlign='left';}}}
function stats(el,cur,total,t){const m=Math.min(Math.floor(t),cur.b.length-1);let idle=0;for(let i=0;i<=m&&i<T;i++)idle+=day.sessions-cur.b[i];
  const idleNow=t<T?day.sessions-cur.b[m]:0;
  el.innerHTML=`<div>Patients seen<b>${cur.dn[m]} / ${total}</b></div><div>Waiting now<b>${cur.w[m]}</b></div><div>Doctors idle now<b>${idleNow} of ${day.sessions}</b></div><div>Wasted idle time so far<b>${(idle/60).toFixed(0)} h</b></div>`;}
function line(cv,title,sf,so,ymax,note){const g=cv.getContext('2d'),W=cv.width,H=cv.height,x0=44,x1=W-12,y0=34,y1=H-28,sc=(x1-x0)/tEnd;g.clearRect(0,0,W,H);
  g.fillStyle=INK;g.font='600 13px system-ui,sans-serif';g.fillText(title,10,16);g.font='11px system-ui,sans-serif';g.fillStyle=MUTE;g.fillText(note,10,30);
  g.strokeStyle=dark?'#2a3445':'#e4e7ec';g.beginPath();for(let k=0;k<=4;k++){const y=y1-(y1-y0)*k/4;g.moveTo(x0,y);g.lineTo(x1,y);g.fillStyle=MUTE;g.fillText(Math.round(ymax*k/4),6,y+4);}g.stroke();
  for(let m=0;m<=tEnd;m+=60)g.fillText(fm(m),x0+m*sc-12,H-10);
  g.strokeStyle='#d64545';g.beginPath();g.moveTo(x0+T*sc,y0);g.lineTo(x0+T*sc,y1);g.stroke();g.fillStyle='#d64545';g.fillText('planned end',x0+T*sc+3,y0+10);
  [[sf,'#8d99ae','fixed interval'],[so,'#e07a5f','overbooking']].forEach(([w,c,l],k)=>{g.strokeStyle=c;g.lineWidth=2;g.beginPath();
    for(let m=0;m<=Math.min(Math.floor(t),w.length-1);m++){const x=x0+m*sc,y=y1-(y1-y0)*w[m]/ymax;m?g.lineTo(x,y):g.moveTo(x,y);}g.stroke();
    g.fillStyle=c;g.fillRect(W-130,8+k*14,10,8);g.fillStyle=MUTE;g.fillText(l,W-116,16+k*14);});g.lineWidth=1;}
function charts(){const S=day.sessions,idle=c=>c.b.map((b,m)=>m<T?S-b:0);
  line(document.getElementById('cq'),'Patients waiting (all doctors)',arr.f.w,arr.o.w,day.qmax,'patients who have arrived and are waiting to be seen');
  const iF=idle(arr.f),iO=idle(arr.o);line(document.getElementById('ci'),'Doctors idle although the session is running',iF,iO,S,'wasted capacity: fewer is better');}
const tip=document.getElementById('tip');
function hit(cv,list,e){const r=cv.getBoundingClientRect(),k=cv.width/r.width,x=(e.clientX-r.left)*k-4,y=(e.clientY-r.top)*k-3,c=Math.floor(x/tileW),rw=Math.floor(y/tileW),s=rw*tileCols+c;return (c>=0&&c<tileCols&&rw>=0&&s>=0&&s<list.length)?s:-1;}
function wire(id,key){const cv=document.getElementById(id);
  cv.onmousemove=e=>{if(!day.S)return;const list=day.S[key],s=hit(cv,list,e);if(s<0){tip.style.display='none';return;}const st=sstate(list[s],t);
    const state=st.cur?(st.cur[3]?'seeing an overbooked patient':'seeing a patient'):(t<T?'idle (wasted time)':'finished');
    tip.textContent=`Doctor ${s+1}: ${state}; ${st.w} waiting; ${st.dn} of ${list[s].length} patients done`;tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';};
  cv.onmouseleave=()=>tip.style.display='none';
  cv.onclick=e=>{const s=hit(cv,day.S[key],e);if(s>=0){sessFilter=s;applyFilter();document.getElementById('rtable').scrollIntoView({block:'center'});}};}

function frame(now){if(last===null)last=now;const dt=(now-last)/1000;last=now;
  if(playing){t+=dt*Number(document.getElementById('speed').value);if(t>=tEnd){t=tEnd;playing=false;document.getElementById('play').textContent='Replay';}}
  document.getElementById('clock').textContent=fm(t);document.getElementById('scrub').value=1000*t/tEnd;
  prep();tiles(document.getElementById('cf'),day.S.f,t);tiles(document.getElementById('co'),day.S.o,t);stats(document.getElementById('sf'),arr.f,day.policies.fixed.seen,t);stats(document.getElementById('so'),arr.o,day.policies[META.animate].seen,t);charts();requestAnimationFrame(frame);}
function status(r){return r[14]<0?'No slot':(r[16]==null?'No-show':'Seen');}
function applyFilter(){const f=document.getElementById('fstatus').value,q=document.getElementById('fsearch').value.trim();
  rows=day.records.filter(r=>(f==='all'||(f==='seen'&&status(r)==='Seen')||(f==='noshow'&&status(r)==='No-show')||(f==='deferred'&&status(r)==='No slot')||(f==='ob'&&r[18]))&&(sessFilter<0||r[8]===sessFilter)&&(!q||String(r[0]).includes(q)));page=0;renderRows();}
function renderRows(){const PS=50,np=Math.max(1,Math.ceil(rows.length/PS));page=Math.min(page,np-1);
  document.getElementById('pageinfo').textContent=(rows.length?page*PS+1:0)+'-'+Math.min(rows.length,(page+1)*PS)+' of '+rows.length;
  const w=(a,b)=>a==null?'-':f1(a-b);
  document.getElementById('rtable').innerHTML='<tr><th>Appt ID</th><th>Booked</th><th>Age</th><th>Lead</th><th>RF</th><th>LR</th><th>R4</th><th>Attended</th><th>Session</th><th>Slot fixed</th><th>Wait fixed</th><th>Slot overb.</th><th>Wait overb.</th><th>Overbooked</th><th>Status</th></tr>'+
   rows.slice(page*PS,(page+1)*PS).map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4].toFixed(2)}</td><td>${r[5].toFixed(2)}</td><td>${r[6].toFixed(2)}</td><td>${r[7]?'no':'yes'}</td><td>${r[8]+1}</td><td>${r[9]<0?'-':r[9]+1}</td><td>${w(r[11],r[10])}</td><td>${r[14]<0?'-':r[14]+1}</td><td>${w(r[16],r[15])}</td><td>${r[18]?'yes':''}</td><td>${status(r)}</td></tr>`).join('');}
document.getElementById('play').onclick=()=>{if(t>=tEnd)t=0;playing=!playing;last=null;document.getElementById('play').textContent=playing?'Pause':'Play';};
document.getElementById('restart').onclick=()=>{t=0;playing=true;last=null;document.getElementById('play').textContent='Pause';};
document.getElementById('scrub').oninput=e=>{t=tEnd*e.target.value/1000;playing=false;document.getElementById('play').textContent='Play';};
daySel.onchange=()=>{setDay(Number(daySel.value));playing=true;last=null;};
document.getElementById('fstatus').onchange=applyFilter;document.getElementById('fsearch').oninput=applyFilter;
document.getElementById('prev').onclick=()=>{page=Math.max(0,page-1);renderRows();};document.getElementById('next').onclick=()=>{page++;renderRows();};
document.getElementById('otitle').textContent=META.animate_name;wire('cf','f');wire('co','o');setDay(0);requestAnimationFrame(frame);
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--risks", default=str(RISKS), help="CSV written by ml/build_reports.py")
    ap.add_argument("--source", choices=list(SOURCES), default="rf", help="risk used for the overbooking decision")
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    if not Path(args.risks).exists():
        raise SystemExit(f"{args.risks} not found. Run ml/build_reports.py first (it needs the Kaggle data in ml/data/raw).")

    pool = pd.read_csv(args.risks, parse_dates=["ScheduledDay", "AppointmentDay"])
    risk_col, source_name = SOURCES[args.source]
    pool["p_sim"] = pool[risk_col]
    cfg = SessionConfig()
    animate = f"threshold {args.threshold:.2f}"
    policies = {"fixed": fixed_interval(), animate: threshold_rule(args.threshold),
                "threshold 0.20": threshold_rule(0.20), "threshold 0.40": threshold_rule(0.40),
                "cost rule r=1.0": cost_rule(1.0), "cost rule r=0.5": cost_rule(0.5)}
    policies = dict(sorted(policies.items(), key=lambda kv: kv[0] != "fixed"))  # fixed first
    days = []
    for date, day in pool.groupby("AppointmentDay"):
        sim = day.copy()
        sim["p"] = day["p_sim"]                                            # the column the simulation decides with
        sim["p_rf"] = day["p"]
        agg, records = simulate_day(sim, cfg, "p", int(date.strftime("%Y%m%d")), policies, animate)
        # table columns always show RF / LR / R4: restore the RF column that the simulation column replaced
        for rec, rf in zip(records, sim.set_index("AppointmentID").loc[[r[0] for r in records], "p_rf"]):
            rec[4] = round(float(rf), 3)
        days.append({"date": f"{date:%d %b %Y}", "sessions": agg["fixed"]["sessions"], "records": records,
                     "policies": summarize(agg, len(day))})
        f, o = days[-1]["policies"]["fixed"], days[-1]["policies"][animate]
        print(f"{date:%Y-%m-%d}: {len(day)} appointments, {f['sessions']} sessions | seen {f['seen']} -> {o['seen']}, "
              f"idle {f['idle_h']:.0f} h -> {o['idle_h']:.0f} h, mean wait {f['mean_wait']:.1f} -> {o['mean_wait']:.1f} min")
    note = ("Every real appointment record of the day (test period of the Medical Appointment No Shows data) is dealt to clinic "
            "sessions; risk and attendance are real, consultation length and lateness are simulated. The data has no doctor "
            "information, so the split of patients over sessions is random.")
    meta = {"session_min": cfg.session_min, "n_requests": cfg.n_requests, "animate": animate,
            "animate_name": f"Selective overbooking ({animate}, risk: {source_name})"}
    html = (HTML.replace("__DATA__", json.dumps({"days": days}, separators=(",", ":"))).replace("__META__", json.dumps(meta))
            .replace("__NOTE__", note).replace("__SRC__", source_name).replace("__THR__", f"{args.threshold:.2f}"))
    OUT.mkdir(exist_ok=True)
    path = OUT / "whole_day.html"
    path.write_text(html, encoding="utf-8")
    print("Saved:", path, f"({path.stat().st_size / 1e6:.1f} MB)")
    if not args.no_open:
        webbrowser.open(path.as_uri())


if __name__ == "__main__":
    main()

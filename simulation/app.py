"""Interactive simulation: choose the data, the risk source, the booking rule and the appointment template,
press Run, and SimPy simulates the real appointment records with your choices.

    python app.py              # opens the simulation in its own window (like a desktop program)
    python app.py --browser    # open it in a normal browser tab instead
    python app.py --no-open    # only start the server
    python app.py --port 8800  # another port

The window is Edge or Chrome in "app mode": no address bar and no tabs, so nothing else of the web distracts you.
Closing the window stops the program.

Needs ml/data/processed/risks_all_days.csv (created by ml/build_reports.py). Stop the server with Ctrl+C.

The baseline is always "no rule": fixed 15-minute slots, one patient per slot. Both runs see the same patients,
show-ups, lateness and consultation lengths (common random numbers), so every difference comes from your choices.
"""
import argparse
import dataclasses
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from clinic_sim import (Layout, SessionConfig, cost_rule, draw_session, expected_value_rule, fixed_interval,
                        simulate_session, threshold_rule)

HERE = Path(__file__).resolve().parent
UI = HERE / "ui" / "app.html"
OUT = HERE / "output"
RISKS = HERE.parent / "ml" / "data" / "processed" / "risks_all_days.csv"
SOURCES = {  # key: (column, label)
    "rf": ("p", "Random forest"), "lr": ("p_lr", "Logistic regression"), "r1": ("p_r1", "Rule R1: patient history"),
    "r2": ("p_r2", "Rule R2: gender"), "r3": ("p_r3", "Rule R3: age group"), "r4": ("p_r4", "Rule R4: combined rules"),
    "paper": ("p_paper", "Paper-style classifier (rebalanced training)")}
RISK_COLUMNS = ["p", "p_lr", "p_r1", "p_r2", "p_r3", "p_r4", "p_paper"]
_pool = None
_lock = threading.Lock()


def pool() -> pd.DataFrame:
    global _pool
    with _lock:
        if _pool is None:
            if not RISKS.exists():
                raise SystemExit(f"{RISKS} not found. Run ml/build_reports.py first (it needs the Kaggle data in ml/data/raw).")
            _pool = pd.read_csv(RISKS, parse_dates=["ScheduledDay", "AppointmentDay"])
            for c in RISK_COLUMNS:
                if c not in _pool.columns:
                    raise SystemExit(f"Column {c} missing in {RISKS.name}. Re-run ml/build_reports.py.")
        return _pool


# ---------------------------------------------------------------------------------------------- configuration
def build_policy(rule: dict):
    kind = rule.get("type", "none")
    cap = int(rule.get("max_per_slot", 2))
    limit = int(rule.get("daily_limit", 4))
    if kind == "threshold":
        return threshold_rule(float(rule.get("threshold", 0.3)), cap, limit)
    if kind == "cost":
        return cost_rule(float(rule.get("r", 0.5)), cap, limit)
    if kind == "ev":
        return expected_value_rule(cap, limit)
    return fixed_interval()


def build_layout(t: dict) -> Layout:
    n = int(t.get("n_slots", 16))
    buffer = t.get("buffer")
    zone = t.get("zone_start")
    return Layout(blocked=frozenset([int(buffer) - 1] if buffer else []),
                  overbook_slots=frozenset(range(int(zone) - 1, n)) if zone else None,
                  offset=float(t.get("offset", 0.0)))


def session_config(cfg: dict) -> SessionConfig:
    s, t = cfg.get("session", {}), cfg.get("template", {})
    return SessionConfig(n_slots=int(t.get("n_slots", 16)), slot_min=float(t.get("slot_min", 15)),
                         service_mean=float(s.get("service_mean", 12)), service_cv=float(s.get("service_cv", 0.5)),
                         punctuality_sd=float(s.get("lateness_sd", 4)), requests=int(s.get("requests", 20)))


def deal_sessions(day: pd.DataFrame, requests: int, seed: int):
    """All records of a date dealt to sessions of `requests` booking requests, in real booking order."""
    idx = np.random.default_rng(seed).permutation(len(day))
    for s, start in enumerate(range(0, len(day), requests)):
        yield s, day.iloc[np.sort(idx[start:start + requests])].sort_values("ScheduledDay", kind="stable")


# ---------------------------------------------------------------------------------------------- simulation
def empty_acc():
    return {"appointments": 0, "seen": 0, "booked": 0, "noslot": 0, "wait_min": 0.0, "idle_min": 0.0, "ot_min": 0.0,
            "busy": 0.0, "ob_slots": 0, "sessions": 0, "planned_min": 0.0}


def add(acc, r, n_requests, session_min):
    acc["appointments"] += n_requests
    acc["seen"] += r["seen"]
    acc["booked"] += r["booked"]
    acc["noslot"] += r["deferred"]
    acc["wait_min"] += r["mean_wait"] * r["seen"]
    acc["idle_min"] += r["idle"]
    acc["ot_min"] += r["overtime"]
    acc["busy"] += r["utilization"] * session_min
    acc["ob_slots"] += r["overbooked_slots"]
    acc["sessions"] += 1
    acc["planned_min"] += session_min


def kpis(a):
    return {"appointments": a["appointments"], "seen": a["seen"], "noshow": a["booked"] - a["seen"], "noslot": a["noslot"],
            "wait": a["wait_min"] / max(a["seen"], 1), "wait_h": a["wait_min"] / 60, "idle_h": a["idle_min"] / 60,
            "ot_h": a["ot_min"] / 60, "utilization": a["busy"] / max(a["planned_min"], 1), "ob_slots": a["ob_slots"],
            "sessions": a["sessions"]}


def simulate_dates(dates, cfg: dict, detail: bool):
    risk_col = SOURCES[cfg.get("risk", "rf")][0]
    base_cfg = session_config(cfg)
    rule_cfg = base_cfg
    base_layout, rule_layout = Layout(), build_layout(cfg.get("template", {}))
    base_cfg = dataclasses.replace(base_cfg, n_slots=16, slot_min=15.0)       # baseline template: 16 x 15 min, no rule
    policy = build_policy(cfg.get("rule", {}))
    seed0 = int(cfg.get("session", {}).get("seed", 0))
    data = pool()
    per_day, records, tot0, tot1 = [], [], empty_acc(), empty_acc()
    for date in dates:
        day = data[data["AppointmentDay"] == date]
        seed = int(pd.Timestamp(date).strftime("%Y%m%d")) + seed0
        rng = np.random.default_rng(seed + 1)
        a0, a1 = empty_acc(), empty_acc()
        for s, part in deal_sessions(day, rule_cfg.n_requests, seed):
            draws = dataclasses.replace(draw_session(dataclasses.replace(base_cfg, requests=len(part)), rng, None),
                                        risk=part[risk_col].to_numpy(), shows=(part["y"].to_numpy() == 0))
            r0 = simulate_session(dataclasses.replace(base_cfg, requests=len(part)), fixed_interval(), draws, detail=detail,
                                  layout=base_layout)
            r1 = simulate_session(dataclasses.replace(rule_cfg, requests=len(part)), policy, draws, detail=detail,
                                  layout=rule_layout)
            for acc, tot, r, c in ((a0, tot0, r0, base_cfg), (a1, tot1, r1, rule_cfg)):
                add(acc, r, len(part), c.session_min)
                add(tot, r, len(part), c.session_min)
            if detail:
                rows = [[-1, None, None, None, 0] * 2 for _ in range(len(part))]
                for off, r in ((0, r0), (5, r1)):
                    for p in r["detail"]:
                        rows[p["patient"]][off:off + 5] = [p["slot"], round(max(p["appointment"], p["arrival"]), 1),
                                                           round(p["start"], 1), round(p["end"], 1), int(p["overbooked"])]
                    for i, slot in r["no_shows"]:
                        rows[i][off] = int(slot)
                for i, (_, rec) in enumerate(part.iterrows()):
                    records.append([int(rec["AppointmentID"]), rec["ScheduledDay"].strftime("%m-%d %H:%M"), int(rec["Age"]),
                                    int(rec["LeadDays"]), *[round(float(rec[c]), 3) for c in RISK_COLUMNS], int(rec["y"]), s,
                                    *rows[i]])
        per_day.append({"date": f"{pd.Timestamp(date):%d %b %Y}", "baseline": kpis(a0), "rule": kpis(a1)})
    return per_day, kpis(tot0), kpis(tot1), records, base_cfg, rule_cfg, risk_col


def risk_stats(dates, risk_col: str, rule: dict):
    d = pool()[pool()["AppointmentDay"].isin(dates)]
    thr = float(rule.get("threshold", 0.5)) if rule.get("type") == "threshold" else None
    out = {"n": int(len(d)), "no_show_rate": float(d["y"].mean()), "mean_risk": float(d[risk_col].mean()),
           "auc": float(roc_auc_score(d["y"], d[risk_col])) if d["y"].nunique() > 1 else None,
           "max_risk": float(d[risk_col].max())}
    if thr is not None:
        out["threshold"] = thr
        out["flagged_share"] = float((d[risk_col] >= thr).mean())
    return out


def run(cfg: dict) -> dict:
    started = time.time()
    data = pool()
    all_dates = sorted(data["AppointmentDay"].unique())
    day = cfg.get("day", "all")
    dates = all_dates if day == "all" else [pd.Timestamp(day)]
    detail = day != "all"
    per_day, base, rule, records, base_cfg, rule_cfg, risk_col = simulate_dates(dates, cfg, detail)
    return {"baseline": base, "rule": rule, "per_day": per_day, "records": records,
            "session_min": {"baseline": base_cfg.session_min, "rule": rule_cfg.session_min},
            "risk": risk_stats(dates, risk_col, cfg.get("rule", {})), "days": len(dates),
            "requests": rule_cfg.n_requests, "seconds": round(time.time() - started, 1)}


def meta() -> dict:
    d = pool()
    dates = sorted(d["AppointmentDay"].unique())
    aucs = {k: float(roc_auc_score(d["y"], d[col])) for k, (col, _) in SOURCES.items()}
    means = {k: float(d[col].mean()) for k, (col, _) in SOURCES.items()}
    return {"dates": [pd.Timestamp(x).strftime("%Y-%m-%d") for x in dates], "records": int(len(d)),
            "no_show_rate": float(d["y"].mean()),
            "sources": {k: {"label": lab, "auc": aucs[k], "mean": means[k]} for k, (_, lab) in SOURCES.items()}}


# ---------------------------------------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self.send(200, UI.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/meta":
            return self.send(200, meta())
        if path.startswith("/output/"):                        # the static result pages, so the Back buttons keep working
            f = (OUT / path[len("/output/"):]).resolve()
            if OUT.resolve() in f.parents and f.is_file():
                return self.send(200, f.read_bytes(), mimetypes.guess_type(str(f))[0] or "application/octet-stream")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/run":
            return self.send(404, {"error": "not found"})
        try:
            cfg = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
            self.send(200, run(cfg))
        except Exception as exc:  # report the problem to the page instead of dropping the connection
            self.send(500, {"error": f"{type(exc).__name__}: {exc}"})


def find_app_browser():
    """Edge or Chrome, which can open a page as a standalone window (app mode)."""
    candidates = [os.path.expandvars(p) for p in (
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe", r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe", r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")]
    candidates += [shutil.which(n) or "" for n in ("msedge", "google-chrome", "chromium", "chrome")]
    return next((c for c in candidates if c and Path(c).exists()), None)


def open_window(url: str):
    """Start the page as a separate app window. Returns (process, profile dir) or (None, None) when no Edge/Chrome is found."""
    exe = find_app_browser()
    if not exe:
        return None, None
    profile = tempfile.mkdtemp(prefix="noshow-sim-")          # own profile: the process lives exactly as long as the window
    proc = subprocess.Popen([exe, f"--app={url}?app=1", f"--user-data-dir={profile}", "--window-size=1500,950",
                             "--no-first-run", "--no-default-browser-check"])
    return proc, profile


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-open", action="store_true", help="only start the server")
    ap.add_argument("--browser", action="store_true", help="open in a normal browser tab instead of an app window")
    args = ap.parse_args()
    pool()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Interactive simulation running at {url}")
    proc = profile = None
    if not args.no_open and not args.browser:
        proc, profile = open_window(url)
    try:
        if proc is not None:
            print("Opened in its own window. Close the window to stop the program (or press Ctrl+C here).")
            proc.wait()
            print("Window closed.")
        else:
            if not args.no_open:
                webbrowser.open(url)
            print("Press Ctrl+C to stop.")
            while thread.is_alive():
                thread.join(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        if proc is not None and proc.poll() is None:
            proc.terminate()
        if profile:
            shutil.rmtree(profile, ignore_errors=True)
        print("Stopped.")


if __name__ == "__main__":
    main()

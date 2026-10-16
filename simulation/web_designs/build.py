"""Build the three example web designs (HTML) with real data of the project.

    python build.py        # writes docs/web-designs/*.html

The designs are static mock-ups for the web application: they show how the results of the IEN work
(no-show risk, overbooking decision, KPIs, rule comparison) can appear to patients, doctors and the
administrator. Every number comes from the real appointment records and the simulation; the
simulation parameters (slot length, consultation time, lateness, demand) are assumptions.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import app  # noqa: E402  (the interactive simulation engine)

RAW = HERE.parents[1] / "ml" / "data" / "raw" / "KaggleV2-May-2016.csv"
OUT = HERE.parents[1] / "docs" / "web-designs"
BASE = {
    "risk": "rf",
    "template": {"n_slots": 16, "slot_min": 15},
    "session": {"requests": 20, "service_mean": 12, "service_cv": 0.5, "lateness_sd": 4, "seed": 0},
}


def run(rule: dict, risk: str = "rf", day: str = "all") -> dict:
    return app.run({**BASE, "risk": risk, "day": day, "rule": rule})


def pick_session(res: dict) -> int:
    """A doctor session that shows the rule well: several overbooked patients, some no-shows."""
    score = {}
    for r in res["records"]:
        s = r[12]
        score[s] = (
            score.get(s, 0) + (10 if r[22] else 0) + (1 if (r[18] >= 0 and r[20] is None) else 0)
        )
    return max(score, key=lambda s: (score[s], -s))


def session_view(res: dict, sess: int, threshold: float) -> dict:
    slots = [
        {"time": f"{8 + (s * 15) // 60:02d}:{(s * 15) % 60:02d}", "patients": []} for s in range(16)
    ]
    waiting, rejected = [], []
    for n, r in enumerate([r for r in res["records"] if r[12] == sess], start=1):
        p = {
            "n": n,
            "id": r[0],
            "age": r[2],
            "lead": r[3],
            "risk": round(r[4] * 100),
            "ob": bool(r[22]),
            "showed": r[11] == 0,
            "wait": None if r[20] is None else round(r[20] - r[19], 1),
        }
        if r[18] < 0:
            rejected.append(p)
        else:
            slots[r[18]]["patients"].append(p)
    for sl in slots:
        for i, p in enumerate(sl["patients"]):
            p["extra"] = i > 0  # the patient added on top of the first one
        if len(sl["patients"]) > 1:
            first = sl["patients"][0]
            waiting.append(
                {
                    "time": sl["time"],
                    "first": first["id"],
                    "first_risk": first["risk"],
                    "second": sl["patients"][1]["id"],
                    "threshold": round(threshold * 100),
                }
            )
    return {"slots": slots, "overbooks": waiting, "rejected": rejected}


def main() -> None:
    if "--reuse" in sys.argv and (OUT / "data.json").exists():
        payload = json.loads((OUT / "data.json").read_text(encoding="utf-8"))
        payload.update(extras())
        if "sessions" not in payload:
            payload["sessions"] = sessions()
        write_pages(payload)
        write_records()
        (OUT / "data.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return
    meta = app.meta()
    base_run = run({"type": "none"})
    rules = {
        "none": base_run["baseline"],
        "thr15": run({"type": "threshold", "threshold": 0.15, "max_per_slot": 2, "daily_limit": 4})[
            "rule"
        ],
        "thr20": run({"type": "threshold", "threshold": 0.20, "max_per_slot": 2, "daily_limit": 4})[
            "rule"
        ],
        "thr25": run({"type": "threshold", "threshold": 0.25, "max_per_slot": 2, "daily_limit": 4})[
            "rule"
        ],
        "thr30": None,
        "thr35": run({"type": "threshold", "threshold": 0.35, "max_per_slot": 2, "daily_limit": 4})[
            "rule"
        ],
        "thr40": run({"type": "threshold", "threshold": 0.40, "max_per_slot": 2, "daily_limit": 4})[
            "rule"
        ],
        "thr45": run({"type": "threshold", "threshold": 0.45, "max_per_slot": 2, "daily_limit": 4})[
            "rule"
        ],
        "thr50": run({"type": "threshold", "threshold": 0.50, "max_per_slot": 2, "daily_limit": 4})[
            "rule"
        ],
        "cost05": run({"type": "cost", "r": 0.5, "max_per_slot": 2, "daily_limit": 4})["rule"],
        "cost10": run({"type": "cost", "r": 1.0, "max_per_slot": 2, "daily_limit": 4})["rule"],
        "ev": run({"type": "ev", "max_per_slot": 2, "daily_limit": 4})["rule"],
    }
    thr30 = run({"type": "threshold", "threshold": 0.30, "max_per_slot": 2, "daily_limit": 4})
    rules["thr30"] = thr30["rule"]
    rules["paper"] = run(
        {"type": "threshold", "threshold": 0.5, "max_per_slot": 2, "daily_limit": 99}, risk="paper"
    )["rule"]

    per_day = [
        {
            "date": d["date"],
            "base_seen": d["baseline"]["seen"],
            "rule_seen": d["rule"]["seen"],
            "base_wait": round(d["baseline"]["wait"], 2),
            "rule_wait": round(d["rule"]["wait"], 2),
            "base_idle": round(d["baseline"]["idle_h"], 1),
            "rule_idle": round(d["rule"]["idle_h"], 1),
        }
        for d in thr30["per_day"]
    ]

    day = "2016-06-07"
    one = run(
        {"type": "threshold", "threshold": 0.30, "max_per_slot": 2, "daily_limit": 4}, day=day
    )
    sess = pick_session(one)

    data = pd.read_csv(app.RISKS)
    data["bin"] = pd.qcut(data["p"], 10, duplicates="drop")
    cal = (
        data.groupby("bin", observed=True)
        .agg(pred=("p", "mean"), obs=("y", "mean"), n=("y", "size"))
        .reset_index(drop=True)
    )
    calibration = [
        {"pred": round(r.pred * 100, 1), "obs": round(r.obs * 100, 1), "n": int(r.n)}
        for r in cal.itertuples()
    ]
    risk_hist = [
        int(x)
        for x in pd.cut(
            data["p"] * 100, bins=list(range(0, 61, 5)) + [100], right=False
        ).value_counts(sort=False)
    ]

    payload = {
        "hospital": "Şehir Hastanesi",
        "model": {
            "auc": round(roc_auc_score(data["y"], data["p"]), 3),
            "records": int(len(data)),
            "days": len(meta["dates"]),
            "no_show_rate": round(float(data["y"].mean()) * 100, 1),
            "mean_risk": round(float(data["p"].mean()) * 100, 1),
            "max_risk": round(float(data["p"].max()) * 100),
        },
        "rules": rules,
        "per_day": per_day,
        "session": {
            "date": "07 Haziran 2016",
            "doctor": sess + 1,
            **session_view(one, sess, 0.30),
            "baseline": one["baseline"],
            "rule": one["rule"],
        },
        "calibration": calibration,
        "risk_hist": risk_hist,
        "assumptions": {
            "slot_min": 15,
            "slots": 16,
            "service_mean": 12,
            "service_cv": 0.5,
            "lateness_sd": 4,
            "requests": 20,
        },
    }
    payload.update(extras())
    payload["sessions"] = sessions()
    write_pages(payload)
    write_records()
    (OUT / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("Saved:", OUT / "data.json")


def sessions() -> dict:
    """One doctor session per record day (the one that shows the rule best), for the admin view."""
    rule = {"type": "threshold", "threshold": 0.30, "max_per_slot": 2, "daily_limit": 4}
    out = {}
    for day in app.meta()["dates"]:
        one = run(rule, day=day)
        sess = pick_session(one)
        out[day] = {
            "doctor": sess + 1,
            **session_view(one, sess, 0.30),
            "baseline": one["baseline"],
            "rule": one["rule"],
        }
        print("Session:", day)
    return out


def write_records() -> None:
    """All real appointments of the 27 days as [id, age, risk %, no-show] per day (records.js)."""
    data = pd.read_csv(app.RISKS, usecols=["AppointmentID", "AppointmentDay", "Age", "p", "y"])
    out = {}
    for day, g in data.sort_values("AppointmentID").groupby("AppointmentDay"):
        rows = zip(g["AppointmentID"], g["Age"], (g["p"] * 100).round(), g["y"], strict=True)
        out[str(day)[:10]] = [[int(a), int(b), int(c), int(d)] for a, b, c, d in rows]
    text = json.dumps(out, separators=(",", ":"))
    (OUT / "records.js").write_text(f"const RECORDS={text};\n", encoding="utf-8")
    print("Saved:", OUT / "records.js", f"({len(text) / 1e6:.1f} MB)")


def extras() -> dict:
    """Reminder settings and the reminder comparison in the shape of GET /ab/summary.

    The dataset has no randomised reminder test. The comparison uses its SMS_received field
    (observational, not randomised) only to show how the admin screen will read the real result.
    """
    from scipy.stats import norm

    raw = pd.read_csv(RAW)
    sms = raw["SMS_received"] == 1
    miss = raw["No-show"] == "Yes"
    groups = []
    for name, mask in (("reminder", sms), ("control", ~sms)):
        n, k = int(mask.sum()), int((mask & miss).sum())
        groups.append(
            {"group": name, "appointments": n, "no_shows": k, "no_show_rate": round(k / n, 3)}
        )
    (n1, k1), (n2, k2) = [(g["appointments"], g["no_shows"]) for g in groups]
    pooled = (k1 + k2) / (n1 + n2)
    z = (k2 / n2 - k1 / n1) / (pooled * (1 - pooled) * (1 / n1 + 1 / n2)) ** 0.5
    return {
        "ab": {
            "unit": "appointment",
            "groups": groups,
            "difference": round(groups[1]["no_show_rate"] - groups[0]["no_show_rate"], 3),
            "z": round(z, 1),
            "p_value": float(2 * norm.sf(abs(z))),
        },
        "reminder": {"hours_before": 24, "confirmation_within_min": 1},
    }


def write_pages(payload: dict) -> None:
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.mkdir(parents=True, exist_ok=True)
    common = (HERE / "common.js").read_text(encoding="utf-8")
    for stale in OUT.glob("design*.html"):
        stale.unlink()
    for src in sorted(HERE.glob("design*.html")):
        text = src.read_text(encoding="utf-8")
        assert "/*__DATA__*/null" in text, src.name
        text = text.replace("/*__COMMON__*/", common)
        (OUT / src.name).write_text(text.replace("/*__DATA__*/null", blob), encoding="utf-8")
        print("Saved:", OUT / src.name, f"({(OUT / src.name).stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()

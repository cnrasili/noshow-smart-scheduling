"""Write docs/design/records.js, the dataset days shown by docs/design/appointment-system.html.

    python build_records.py

Every real appointment of the 27 days as [AppointmentID, age, risk %, no-show], grouped by day.
The risks are the out-of-sample predictions in ml/data/processed/risks_all_days.csv, written by
ml/build_reports.py.
"""

import json
from pathlib import Path

import app  # the interactive simulation engine; app.RISKS is the risk file
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "docs" / "design" / "records.js"


def write_records() -> None:
    """All real appointments of the 27 days as [id, age, risk %, no-show] per day."""
    data = pd.read_csv(app.RISKS, usecols=["AppointmentID", "AppointmentDay", "Age", "p", "y"])
    out = {}
    for day, g in data.sort_values("AppointmentID").groupby("AppointmentDay"):
        rows = zip(g["AppointmentID"], g["Age"], (g["p"] * 100).round(), g["y"], strict=True)
        out[str(day)[:10]] = [[int(a), int(b), int(c), int(d)] for a, b, c, d in rows]
    text = json.dumps(out, separators=(",", ":"))
    OUT.write_text(f"const RECORDS={text};\n", encoding="utf-8")
    print("Saved:", OUT, f"({len(text) / 1e6:.1f} MB)")


if __name__ == "__main__":
    write_records()

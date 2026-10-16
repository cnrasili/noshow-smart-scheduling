"""Clean the raw Medical Appointment No Shows CSV and write an Excel file to data/processed/."""

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).parent / "raw" / "KaggleV2-May-2016.csv"
OUT = Path(__file__).parent / "processed" / "appointments_clean.xlsx"
AGE_BINS = [-1, 17, 24, 34, 54, 200]
AGE_LABELS = ["A0 <18", "A1 18-24", "A2 25-34", "A3 35-54", "A4 55+"]


def main() -> None:
    df = pd.read_csv(RAW)
    n_raw = len(df)
    log = [("Raw rows", n_raw)]

    df = df.rename(
        columns={"Hipertension": "Hypertension", "Handcap": "Handicap", "No-show": "NoShow"}
    )
    df["PatientId"] = df["PatientId"].astype("int64")
    df["ScheduledDay"] = pd.to_datetime(df["ScheduledDay"]).dt.tz_localize(None)
    df["AppointmentDay"] = pd.to_datetime(df["AppointmentDay"]).dt.tz_localize(None)
    df["NoShow"] = (df["NoShow"] == "Yes").astype(int)  # 1 = missed the appointment
    df["Gender"] = df["Gender"].str.strip().str.upper()
    df["Neighbourhood"] = df["Neighbourhood"].str.strip().str.upper()

    df["ScheduledDate"] = df["ScheduledDay"].dt.normalize()
    df["LeadDays"] = (df["AppointmentDay"] - df["ScheduledDate"]).dt.days

    bad = pd.Series("", index=df.index)
    bad[df["Age"] < 0] = "invalid age (negative)"
    bad[df["Age"] > 120] = "invalid age (>120)"
    bad[df["LeadDays"] < 0] = "appointment before booking date"
    bad[df.duplicated("AppointmentID", keep="first")] = "duplicate AppointmentID"
    removed = df[bad != ""].assign(Reason=bad[bad != ""])
    df = df[bad == ""].copy()
    for reason, c in removed["Reason"].value_counts().items():
        log.append((f"Removed: {reason}", int(c)))

    df["Weekday"] = df["AppointmentDay"].dt.dayofweek  # 0 = Monday
    df["AgeBand"] = pd.cut(df["Age"], AGE_BINS, labels=AGE_LABELS)
    df["ShowUp"] = 1 - df["NoShow"]

    # History features: only appointments whose date is before this booking date (outcome known)
    df = df.sort_values(
        ["PatientId", "AppointmentDay", "ScheduledDay", "AppointmentID"]
    ).reset_index(drop=True)
    prior_n = np.zeros(len(df), dtype=int)
    prior_miss = np.zeros(len(df), dtype=int)
    for _, g in df.groupby("PatientId", sort=False):
        idx = g.index.to_numpy()
        appt = g["AppointmentDay"].to_numpy()
        sched = g["ScheduledDate"].to_numpy()
        miss = g["NoShow"].to_numpy()
        order = np.argsort(appt)
        appt_s, cum_miss = appt[order], np.cumsum(miss[order])
        k = np.searchsorted(appt_s, sched, side="left")  # appointments with date < booking date
        prior_n[idx] = k
        prior_miss[idx] = np.where(k > 0, cum_miss[np.maximum(k - 1, 0)], 0)
    df["PriorApptCount"] = prior_n
    df["PriorNoShowCount"] = prior_miss

    df = df.sort_values(["AppointmentDay", "ScheduledDay", "AppointmentID"]).reset_index(drop=True)
    cols = [
        "AppointmentID",
        "PatientId",
        "ScheduledDay",
        "AppointmentDay",
        "LeadDays",
        "Weekday",
        "Gender",
        "Age",
        "AgeBand",
        "Neighbourhood",
        "Scholarship",
        "Hypertension",
        "Diabetes",
        "Alcoholism",
        "Handicap",
        "SMS_received",
        "PriorApptCount",
        "PriorNoShowCount",
        "NoShow",
        "ShowUp",
    ]
    df = df[cols]
    log += [
        ("Clean rows", len(df)),
        ("No-show rate", round(df["NoShow"].mean(), 4)),
        (
            "Appointment date range",
            f"{df.AppointmentDay.min():%Y-%m-%d} to {df.AppointmentDay.max():%Y-%m-%d}",
        ),
        ("Unique patients", df["PatientId"].nunique()),
    ]
    notes = pd.DataFrame(
        [
            ("NoShow", "1 = patient missed the appointment (target)"),
            ("ShowUp", "1 - NoShow"),
            ("LeadDays", "AppointmentDay date minus ScheduledDay date, in days"),
            ("Weekday", "0 = Monday ... 6 = Sunday"),
            (
                "PriorApptCount / PriorNoShowCount",
                "Patient's earlier appointments dated before this booking date",
            ),
            (
                "SMS_received",
                "Sent after booking: do NOT use as a model feature (see docs/features.md)",
            ),
            ("Hypertension / Handicap", "Source typos 'Hipertension' / 'Handcap' renamed"),
        ],
        columns=["Column", "Note"],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl", datetime_format="YYYY-MM-DD HH:MM") as w:
        df.to_excel(w, sheet_name="data", index=False)
        pd.DataFrame(log, columns=["Step", "Value"]).to_excel(
            w, sheet_name="cleaning_log", index=False
        )
        notes.to_excel(w, sheet_name="columns", index=False)
        removed.drop(columns=["ScheduledDate"]).to_excel(w, sheet_name="removed_rows", index=False)
        ws = w.sheets["data"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 18
    print(pd.DataFrame(log).to_string(index=False, header=False))


if __name__ == "__main__":
    main()

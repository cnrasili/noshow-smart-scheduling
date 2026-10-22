"""Waiting-time distribution of the decided policy: tails, long waits and the cost per extra patient.

The mean wait hides the patients who wait long. This script simulates the same sessions with fixed
intervals and with the decided rule (common random numbers) and looks at every single patient:
percentiles, shares above 5, 10 and 15 minutes, who waits (overbooked slots or not) and what one
extra patient costs. Output: docs/BEKLEME_DAGILIMI.md

    python simulation/wait_distribution.py [--risks PATH] [--quick]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import clinic_sim as cs
import experiments as ex
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent / "docs" / "BEKLEME_DAGILIMI.md"
CUTS = (5, 10, 15)


def collect(cfg, policy, reps, seed, pool):
    """Every seen patient's wait and the per-session totals."""
    rows, sessions = [], []
    for rep in range(reps):
        d = cs.draw_session(cfg, np.random.default_rng([seed, rep]), pool)
        res = cs.simulate_session(cfg, policy, d, detail=True)
        waits = [x["start"] - max(x["appointment"], x["arrival"]) for x in res["detail"]]
        for x, w in zip(res["detail"], waits, strict=True):
            rows.append({"rep": rep, "wait": w, "overbooked": x["overbooked"]})
        sessions.append(
            {
                "rep": rep,
                "seen": res["seen"],
                "total_wait": float(sum(waits)),
                "max_wait": float(max(waits, default=0.0)),
                "overtime": res["overtime"],
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(sessions)


def summary(w: pd.Series) -> dict:
    out = {
        "Hasta (toplam)": len(w),
        "Ortalama (dk)": w.mean(),
        "Ortanca (dk)": w.median(),
        "%90 (dk)": w.quantile(0.90),
        "%95 (dk)": w.quantile(0.95),
        "%99 (dk)": w.quantile(0.99),
        "En uzun (dk)": w.max(),
    }
    for c in CUTS:
        out[f"> {c} dk (%)"] = 100 * float((w > c).mean())
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--risks", type=Path, default=ex.RISKS)
    ap.add_argument("--decisions", type=Path, default=ex.DOCS / "decisions.json")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    d = ex.load_decisions(args.decisions)
    cfg = ex.session_config(d)
    pool = pd.read_csv(args.risks)
    reps = 100 if args.quick else 3000

    fw, fs = collect(cfg, cs.fixed_interval(), reps, ex.SEED + 7, pool)
    rw, rs = collect(cfg, ex.rule_of(d), reps, ex.SEED + 7, pool)

    tab = pd.DataFrame(
        {
            "Sabit aralık": summary(fw["wait"]),
            ex.rule_name(d): summary(rw["wait"]),
            "Kuralda ek randevulu slotlardaki hastalar": summary(rw.loc[rw.overbooked, "wait"]),
            "Kuralda diğer hastalar": summary(rw.loc[~rw.overbooked, "wait"]),
        }
    ).T.reset_index(names="Grup")
    tab["Hasta (toplam)"] = tab["Hasta (toplam)"].astype(int)

    extra = rs["seen"].mean() - fs["seen"].mean()
    dwait = rs["total_wait"].mean() - fs["total_wait"].mean()
    dover = rs["overtime"].mean() - fs["overtime"].mean()
    long_f, long_r = (
        (fs["max_wait"] > d["wait_limit_min"]).mean(),
        (rs["max_wait"] > d["wait_limit_min"]).mean(),
    )
    limit = d["wait_limit_min"]
    over = 100 * float((rw["wait"] > limit).mean())
    text = f"""# Bekleme süresi dağılımı ve fayda–maliyet (otomatik üretilir)

Bu dosya `simulation/wait_distribution.py` tarafından üretilir; elle düzenlemeyin. Ayarlar `docs/decisions.json` dosyasındandır: {ex.assumptions_line(d, cfg)}. {reps} eşleştirilmiş oturum; her satır bir **hastanın** beklemesidir (görülen hastalar).

## 1. Dağılım

{ex.md_table(tab)}

Bekleme = muayene başlangıcı − max(randevu saati, hastanın gelişi). Ortalama {limit} dk sınırının çok altında olsa da önemli olan, tek tek hastaların kaç dakika beklediğidir.

- Kuralda hastaların **%{over:.2f}**'i {limit} dk'dan uzun bekler.
- Bir oturumda en az bir hastanın {limit} dk'dan uzun beklemesi: sabit aralıkta %{100 * long_f:.1f}, kuralda %{100 * long_r:.1f} (oturum başına).
- Uzun bekleyenler ağırlıklı olarak ek randevulu slotlardaki hastalardır (üçüncü satır).

## 2. Ek hasta başına maliyet (oturum başına)

| Kalem | Sabit aralık | Karar ayarı | Fark |
|---|---|---|---|
| Görülen hasta | {fs["seen"].mean():.2f} | {rs["seen"].mean():.2f} | {extra:+.2f} |
| Toplam hasta bekleme süresi (hasta-dk) | {fs["total_wait"].mean():.1f} | {rs["total_wait"].mean():.1f} | {dwait:+.1f} |
| Mesai aşımı (dk) | {fs["overtime"].mean():.2f} | {rs["overtime"].mean():.2f} | {dover:+.2f} |

Kural oturum başına **{extra:.2f} ek hasta** görür; bunun bedeli toplam **{dwait:.1f} hasta-dakika** ek bekleme ve **{dover:.2f} dk** mesai aşımıdır. Yani ek hasta başına yaklaşık **{dwait / extra:.1f} dk** toplam bekleme ve yaklaşık **{dover / extra:.2f} dk** mesai aşımı düşer.

Bu rakamlar simülasyon varsayımlarına bağlıdır (muayene süresi 5–10 dk aralığında bekleme artışı 0,4 ile 2,2 dk arasında değişir, `docs/IEN_DENEY_SONUCLARI.md` bölüm 4).
"""
    REPORT.write_text(text, encoding="utf-8")
    print("Saved:", REPORT)
    print(tab.round(2).to_string(index=False))


if __name__ == "__main__":
    main()

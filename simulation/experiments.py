"""Replicated, paired simulation experiments for the IEN report.

Adds to clinic_sim.py (which is not changed): many replications on the same random sessions
(common random numbers), 95 % confidence intervals and effect sizes of the paired differences,
a threshold x daily-limit grid, short-slot and offset templates combined with overbooking,
sensitivity analyses and a hypothetical reminder scenario.

Session settings, threshold, daily limit and the waiting limit come from docs/decisions.json.

    python simulation/experiments.py            # full run (about a minute)
    python simulation/experiments.py --quick    # small run to check the code
    python simulation/experiments.py --risks ml/data/processed/risks_decision_model.csv

Risks and show-ups come from out-of-sample predictions of all 27 days. Slot length, consultation
time, lateness and demand are decisions or assumptions (docs/KARAR_LISTESI.md).
"""

from __future__ import annotations

import argparse
import json
import platform
from dataclasses import replace
from pathlib import Path

import clinic_sim as cs
import numpy as np
import pandas as pd
import scipy
import simpy
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
RISKS = HERE.parent / "ml" / "data" / "processed" / "risks_all_days.csv"
OUT = HERE / "results_experiments"
REPORT = DOCS / "IEN_DENEY_SONUCLARI.md"
SUMMARY = DOCS / "SONUC_OZETI.md"
METRICS = ["seen", "mean_wait", "idle", "overtime", "utilization"]
LABELS = {
    "seen": "Görülen hasta",
    "mean_wait": "Ortalama bekleme (dk)",
    "idle": "Boşta kalma (dk)",
    "overtime": "Mesai aşımı (dk)",
    "utilization": "Doluluk",
}
SEED = 20261016
MODEL_NAMES = {"random_forest": "Rastgele orman", "decision_tree": "Karar ağacı"}


def load_decisions(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def session_config(d: dict) -> cs.SessionConfig:
    return cs.SessionConfig(
        n_slots=int(d["n_slots"]),
        slot_min=float(d["slot_min"]),
        service_mean=float(d["service_mean_min"]),
        service_cv=float(d["service_cv"]),
        punctuality_sd=float(d["lateness_sd_min"]),
        extra_requests=int(d["extra_requests"]),
    )


def run_cases(cases, ref_cfg, reps, seed, pool, transform=None) -> pd.DataFrame:
    """Every case sees the same random session; `cases` maps name -> (cfg, policy, layout)."""
    rows = []
    for rep in range(reps):
        d = cs.draw_session(ref_cfg, np.random.default_rng([seed, rep]), pool)
        if transform is not None:
            d = transform(d, np.random.default_rng([seed, rep, 1]))
        for name, (cfg, policy, layout) in cases.items():
            rows.append(
                {"case": name, "rep": rep, **cs.simulate_session(cfg, policy, d, layout=layout)}
            )
    return pd.DataFrame(rows)


def paired(res: pd.DataFrame, base: str) -> pd.DataFrame:
    """Paired difference to `base`: mean, 95 % CI, relative change and Cohen's d_z."""
    b = res[res.case == base].set_index("rep")
    rows = []
    for name, g in res.groupby("case", sort=False):
        if name == base:
            continue
        g = g.set_index("rep")
        for m in METRICS:
            diff = g[m] - b[m]
            sd = diff.std(ddof=1)
            half = 1.96 * sd / np.sqrt(len(diff))
            rows.append(
                {
                    "case": name,
                    "metric": m,
                    "base_mean": b[m].mean(),
                    "case_mean": g[m].mean(),
                    "diff": diff.mean(),
                    "ci_low": diff.mean() - half,
                    "ci_high": diff.mean() + half,
                    "rel_pct": 100 * diff.mean() / b[m].mean() if b[m].mean() else np.nan,
                    "d_z": diff.mean() / sd if sd > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def means(res: pd.DataFrame) -> pd.DataFrame:
    return res.groupby("case", sort=False)[METRICS + ["overbooked_slots", "deferred"]].mean()


def md_table(df: pd.DataFrame, fmt: str = "{:,.2f}") -> str:
    head = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    body = [
        "| "
        + " | ".join(fmt.format(v) if isinstance(v, float | np.floating) else str(v) for v in row)
        + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join([head, sep, *body])


def paired_md(tab: pd.DataFrame) -> str:
    """One row per case, one cell per metric: difference [95 % CI] (d_z)."""
    out = []
    for name, g in tab.groupby("case", sort=False):
        row = {"Senaryo": name}
        for r in g.itertuples():
            row[LABELS[r.metric]] = (
                f"{r.diff:+.2f} [{r.ci_low:+.2f}; {r.ci_high:+.2f}] (d={r.d_z:+.2f})"
            )
        out.append(row)
    return md_table(pd.DataFrame(out))


def pareto(df: pd.DataFrame) -> pd.Series:
    """Non-dominated cases: more patients seen, less waiting, idle time and overtime."""
    keep = []
    for i, a in df.iterrows():
        dominated = False
        for j, b in df.iterrows():
            if i == j:
                continue
            better = (
                b.seen >= a.seen
                and b.mean_wait <= a.mean_wait
                and b.idle <= a.idle
                and b.overtime <= a.overtime
            )
            strictly = (
                b.seen > a.seen
                or b.mean_wait < a.mean_wait
                or b.idle < a.idle
                or b.overtime < a.overtime
            )
            if better and strictly:
                dominated = True
                break
        keep.append(not dominated)
    return pd.Series(keep, index=df.index)


# --------------------------------------------------------------------------- experiments
def rule_of(d: dict):
    return cs.threshold_rule(
        d["threshold"], max_per_slot=d["max_per_slot"], daily_limit=d["daily_limit"]
    )


def rule_name(d: dict) -> str:
    return f"Karar ayarı (eşik %{round(100 * d['threshold'])}, sınır {d['daily_limit']})"


BASE_NAME = "Sabit aralık (kural yok)"


def exp_main(cfg, pool, reps, d):
    lim, mps = d["daily_limit"], d["max_per_slot"]
    lay = cs.DEFAULT_LAYOUT
    cases = {
        BASE_NAME: (cfg, cs.fixed_interval(), lay),
        rule_name(d): (cfg, rule_of(d), lay),
        "Eşik %20": (cfg, cs.threshold_rule(0.20, mps, lim), lay),
        "Eşik %40": (cfg, cs.threshold_rule(0.40, mps, lim), lay),
        "Maliyet kuralı r=0,5": (cfg, cs.cost_rule(0.5, mps, lim), lay),
        "Maliyet kuralı r=1,0": (cfg, cs.cost_rule(1.0, mps, lim), lay),
        "Havayolu kuralı": (cfg, cs.expected_value_rule(mps, lim), lay),
    }
    res = run_cases(cases, cfg, reps, SEED, pool)
    return res, paired(res, BASE_NAME)


def grid_key(thr: float, lim: int) -> str:
    return f"thr{round(100 * thr)}_lim{lim}"


def exp_grid(cfg, pool, reps, d):
    thresholds = sorted({0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, d["threshold"]})
    limits = sorted({1, 2, 4, 6, 8, d["daily_limit"]})
    cases = {"fixed": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT)}
    for thr in thresholds:
        for lim in limits:
            cases[grid_key(thr, lim)] = (
                cfg,
                cs.threshold_rule(thr, max_per_slot=d["max_per_slot"], daily_limit=lim),
                cs.DEFAULT_LAYOUT,
            )
    res = run_cases(cases, cfg, reps, SEED + 1, pool)
    m = means(res)
    m["pareto"] = pareto(m)
    return res, m


def exp_templates(cfg, pool, reps, d):
    n, s = cfg.n_slots, cfg.slot_min
    short = replace(
        cfg, n_slots=round(n * 1.25), slot_min=round(s * 0.8, 2), requests=cfg.n_requests
    )
    cfg = replace(cfg, requests=cfg.n_requests)  # same demand for every layout
    rule, fixed = rule_of(d), cs.fixed_interval()
    off = cs.Layout(offset=0.5)
    base = f"{n}x{s:g} sabit (taban)"
    sn, ss = short.n_slots, short.slot_min
    cases = {
        base: (cfg, fixed, cs.DEFAULT_LAYOUT),
        f"{n}x{s:g} + karar ayarı": (cfg, rule, cs.DEFAULT_LAYOUT),
        f"{n}x{s:g} + karar ayarı + kaydırma 0,5": (cfg, rule, off),
        f"{sn}x{ss:g} kısa slot sabit": (short, fixed, cs.DEFAULT_LAYOUT),
        f"{sn}x{ss:g} kısa slot + karar ayarı": (short, rule, cs.DEFAULT_LAYOUT),
        f"{sn}x{ss:g} kısa slot + karar ayarı + kaydırma 0,5": (short, rule, off),
    }
    res = run_cases(cases, cfg, reps, SEED + 2, pool)
    return res, paired(res, base)


def exp_sensitivity(cfg, pool, reps, d):
    tabs = []
    lo, hi = d["service_range_min"]
    extra = d["extra_requests"]
    alt_slot = 10.0 if cfg.slot_min != 10.0 else 15.0  # the other usual slot length, same session
    alt_n = round(cfg.n_slots * cfg.slot_min / alt_slot)
    variants = {
        f"Muayene süresi {lo:g} dk": replace(cfg, service_mean=float(lo)),
        f"Muayene süresi {hi:g} dk": replace(cfg, service_mean=float(hi)),
        "Muayene değişkenliği 0,3": replace(cfg, service_cv=0.3),
        "Muayene değişkenliği 0,8": replace(cfg, service_cv=0.8),
        f"Talep {cfg.n_requests - 4} istek": replace(cfg, requests=cfg.n_requests - 4),
        f"Talep {cfg.n_requests + 4} istek": replace(cfg, requests=cfg.n_requests + 4),
        "Geç kalma sapması 8 dk": replace(cfg, punctuality_sd=8.0),
        f"{alt_slot:g} dk slot, {alt_n} slot": replace(
            cfg, slot_min=alt_slot, n_slots=alt_n, requests=alt_n + extra
        ),
    }
    rule = rule_of(d)
    for name, c in {"taban": cfg, **variants}.items():
        cases = {
            "sabit": (c, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
            "karar ayarı": (c, rule, cs.DEFAULT_LAYOUT),
        }
        res = run_cases(cases, c, reps, SEED + 3, pool)
        t = paired(res, "sabit")
        t["case"] = name
        tabs.append(t)

    def scaled(factor):
        def tf(draws, rng):
            risk = np.clip(draws.risk * factor, 0.0, 0.95)
            return cs.Draws(
                risk, rng.random(len(risk)) >= risk, draws.arrival_offset, draws.service
            )

        return tf

    for factor, name in ((0.7, "No-show oranı x0,7"), (1.3, "No-show oranı x1,3")):
        cases = {
            "sabit": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
            "karar ayarı": (cfg, rule, cs.DEFAULT_LAYOUT),
        }
        res = run_cases(cases, cfg, reps, SEED + 4, pool, transform=scaled(factor))
        t = paired(res, "sabit")
        t["case"] = name
        tabs.append(t)
    return pd.concat(tabs, ignore_index=True)


def exp_reminder(cfg, pool, reps, d):
    """Hypothetical: a reminder turns a share of the reminded no-shows into show-ups."""
    rows = []
    rule = rule_of(d)
    for effect in (0.0, 0.10, 0.20, 0.30):

        def tf(draws, rng, effect=effect):
            reminded = rng.random(len(draws.risk)) < 0.5  # half of the patients (A/B design)
            flip = reminded & ~draws.shows & (rng.random(len(draws.risk)) < effect)
            risk = np.where(reminded, draws.risk * (1 - effect), draws.risk)
            return cs.Draws(risk, draws.shows | flip, draws.arrival_offset, draws.service)

        cases = {
            "sabit": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
            "karar ayarı": (cfg, rule, cs.DEFAULT_LAYOUT),
        }
        res = run_cases(cases, cfg, reps, SEED + 5, pool, transform=tf)
        m = means(res)
        for case in m.index:
            rows.append(
                {"hatırlatma etkisi": f"%{int(effect * 100)}", "politika": case, **m.loc[case]}
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- reports
def assumptions_line(d: dict, cfg: cs.SessionConfig) -> str:
    lo, hi = d["service_range_min"]
    return (
        f"{cfg.n_slots} slot x {cfg.slot_min:g} dk, ortalama {cfg.service_mean:g} dk muayene "
        f"(aralık {lo:g}–{hi:g} dk, değişkenlik {cfg.service_cv:g}), geç kalma sapması "
        f"{cfg.punctuality_sd:g} dk, {cfg.n_requests} randevu isteği"
    )


def write_report(
    parts: dict, reps: dict, d: dict, cfg: cs.SessionConfig, pool: pd.DataFrame
) -> None:
    grid = parts["grid"]
    front = grid[grid.pareto & (grid.index != "fixed")].sort_values("seen", ascending=False)
    front = front[~front[["seen", "mean_wait", "idle", "overtime"]].round(2).duplicated()]
    limits = sorted({5.0, 10.0, float(d["wait_limit_min"])})
    cons = []
    for limit in limits:
        ok = grid[(grid.mean_wait <= limit) & (grid.index != "fixed")]
        if len(ok):
            ranked = ok.sort_values(["seen", "overtime"], ascending=[False, True])
            best = ranked.iloc[0]
            cons.append(
                {
                    "Bekleme sınırı (dk)": f"≤ {limit:.0f}",
                    "En iyi ayar": ranked.index[0],
                    "Görülen": best.seen,
                    "Bekleme": best.mean_wait,
                    "Boşta": best.idle,
                    "Mesai aşımı": best.overtime,
                }
            )
    cols = ["seen", "mean_wait", "idle", "overtime", "utilization", "overbooked_slots"]
    f = front[cols].reset_index().rename(columns={"case": "Ayar"})
    f.columns = [
        "Ayar",
        "Görülen",
        "Bekleme dk",
        "Boşta dk",
        "Mesai aşımı dk",
        "Doluluk",
        "Ek slot",
    ]
    sens_rows = []
    for name, g in parts["sens"].groupby("case", sort=False):
        t = g.set_index("metric")
        sens_rows.append(
            {
                "Senaryo": name,
                "Görülen": f"{t.loc['seen', 'diff']:+.2f}",
                "Bekleme (dk)": f"{t.loc['mean_wait', 'diff']:+.2f}",
                "Boşta (dk)": f"{t.loc['idle', 'diff']:+.2f}",
                "Mesai aşımı (dk)": f"{t.loc['overtime', 'diff']:+.2f}",
            }
        )
    rem = parts["reminder"][
        ["hatırlatma etkisi", "politika", "seen", "mean_wait", "idle", "overtime"]
    ]
    rem.columns = [
        "Hatırlatma etkisi",
        "Politika",
        "Görülen",
        "Bekleme dk",
        "Boşta dk",
        "Mesai aşımı dk",
    ]
    model = MODEL_NAMES.get(d["model"], "Rastgele orman (varsayılan risk dosyası)")
    text = f"""# IEN deney sonuçları (otomatik üretilir)

Bu dosya `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. Risk kaynağı: **{model}**. Tohum {SEED}; Python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}, scipy {scipy.__version__}, simpy {simpy.__version__}. Ayarlar `docs/decisions.json` dosyasındandır.

**Okuma kuralları**

- Risk ve gelme/gelmeme bilgisi, modelin görmediği 27 günün gerçek tahminlerinden ve gerçek sonuçlarından gelir. Oturum ayarı: {assumptions_line(d, cfg)}. Muayene süresi (5–10 dk) devlet hastanesi poliklinik uygulamasından alınmıştır; slot, geç kalma ve talep **varsayımdır** (`docs/KARAR_LISTESI.md`).
- Tüm karşılaştırmalar **eşleştirilmiş**dir: her politika aynı rastgele oturumları görür (ortak rastgele sayılar). Farklar `taban politikaya göre` verilir; köşeli parantez %95 güven aralığı, `d` eşleştirilmiş etki büyüklüğüdür (Cohen d_z).
- Süreler oturum başına dakikadır; "Görülen" oturum başına hasta sayısıdır.

## 1. Politika karşılaştırması ({reps["main"]} oturum)

{paired_md(parts["main"])}

**Yorum.** Ek randevu hem hasta sayısını artırır hem muayene odasının boşta kalmasını azaltır, ancak aynı slota iki hasta gelince ortalama bekleme ve çoğu politikada mesai aşımı da artar. İyileşme ve bedeli birlikte raporlanmalıdır: kural "bedava" değildir.

## 2. Eşik x günlük limit ızgarası ({reps["grid"]} oturum)

Aşağıdaki ayarlar, dört ölçütte (hasta sayısı yüksek; bekleme, boşta kalma, mesai aşımı düşük) başka hiçbir ayar tarafından geçilmeyen **Pareto** ayarlarıdır:

{md_table(f)}

Bir bekleme sınırı verilirse en çok hasta gören ayar:

{md_table(pd.DataFrame(cons)) if cons else "Sınırı karşılayan ayar yok."}

{rule_name(d)} ızgarada `{grid_key(d["threshold"], d["daily_limit"])}` satırıdır. Tüm ızgara betik çalışınca `simulation/results_experiments/grid_means.csv` olarak üretilir (CSV'ler git'e eklenmez).

## 3. Şablonlar ve kısa slot + overbooking ({reps["templates"]} oturum)

Her şablon aynı istek sayısıyla çalışır; fark tabana göredir.

{paired_md(parts["templates"])}

## 4. Duyarlılık analizi ({reps["sens"]} oturum her senaryo)

Karar ayarının sabit aralığa göre farkı (eşleştirilmiş ortalama):

{md_table(pd.DataFrame(sens_rows))}

Güven aralıkları `simulation/results_experiments/sensitivity.csv` dosyasında üretilir.

## 5. Hatırlatma senaryosu (varsayımsal, {reps["reminder"]} oturum)

**Bu bir ölçüm değil, varsayımdır:** hatırlatma, hastaların yarısına gider ve gelmeyecek olanların belirtilen payını gelen hastaya çevirir. Gerçek etki A/B testiyle ölçülmelidir; veri setindeki `SMS_received` alanı rastgele bir deney olmadığından etkiyi tahmin etmeye uygun değildir.

{md_table(rem)}
"""
    REPORT.write_text(text, encoding="utf-8")
    write_summary(parts, d, cfg, pool, model)


def write_summary(
    parts: dict, d: dict, cfg: cs.SessionConfig, pool: pd.DataFrame, model: str
) -> None:
    """Short, regenerated summary that the hand-written documents point to."""
    tab = parts["main"]
    mine = tab[tab.case == rule_name(d)].set_index("metric")
    sens = parts["sens"]
    lo, hi = d["service_range_min"]
    s_lo = sens[(sens.case == f"Muayene süresi {lo:g} dk") & (sens.metric == "mean_wait")]
    s_hi = sens[(sens.case == f"Muayene süresi {hi:g} dk") & (sens.metric == "mean_wait")]
    wait = mine.loc["mean_wait", "case_mean"]
    ok = wait <= d["wait_limit_min"]
    rows = []
    for m in METRICS:
        r = mine.loc[m]
        rows.append(
            {
                "Ölçüt": LABELS[m],
                "Kural yok": r.base_mean,
                "Karar ayarı": r.case_mean,
                "Fark [%95 aralık]": f"{r['diff']:+.2f} [{r.ci_low:+.2f}; {r.ci_high:+.2f}]",
                "Değişim": f"%{r.rel_pct:+.0f}",
            }
        )
    auc = roc_auc_score(pool["y"], pool["p"])
    text = f"""# Sonuç özeti (otomatik üretilir)

Bu dosya `ml/apply_decisions.py` / `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. El yazısı belgeler sayıları buradan alır. Ayrıntı: `docs/IEN_DENEY_SONUCLARI.md`, `docs/MODEL_KARSILASTIRMA.md`.

## Güncel karar ayarları

- **Model:** {model}; 27 günde katlama dışı tahminle ROC-AUC **{auc:.3f}**
- **Kural:** eşik %{round(100 * d["threshold"])}, günlük ek randevu sınırı {d["daily_limit"]}, slot başına en çok {d["max_per_slot"]} hasta
- **Oturum:** {assumptions_line(d, cfg)}
- **Kabul edilen en uzun ortalama bekleme:** {d["wait_limit_min"]} dk

## Karar ayarı, sabit aralığa göre (oturum başına)

{md_table(pd.DataFrame(rows))}

**Bekleme sınırı kontrolü:** ortalama bekleme {wait:.2f} dk; sınır {d["wait_limit_min"]} dk → **{"sınır içinde" if ok else "SINIRI AŞIYOR"}**.

**Muayene süresi duyarlılığı:** muayene {lo:g} dk iken bekleme farkı {s_lo["diff"].iloc[0]:+.2f} dk, {hi:g} dk iken {s_hi["diff"].iloc[0]:+.2f} dk.
"""
    SUMMARY.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="small run to check the code")
    ap.add_argument("--decisions", type=Path, default=DOCS / "decisions.json")
    ap.add_argument("--risks", type=Path, default=RISKS)
    args = ap.parse_args()
    reps = (
        {"main": 30, "grid": 20, "templates": 30, "sens": 20, "reminder": 20}
        if args.quick
        else {"main": 2000, "grid": 500, "templates": 1000, "sens": 600, "reminder": 600}
    )
    d = load_decisions(args.decisions)
    pool = pd.read_csv(args.risks)
    cfg = session_config(d)
    OUT.mkdir(exist_ok=True)

    parts = {}
    res, parts["main"] = exp_main(cfg, pool, reps["main"], d)
    parts["main"].to_csv(OUT / "main_paired.csv", index=False)
    res, grid = exp_grid(cfg, pool, reps["grid"], d)
    grid.to_csv(OUT / "grid_means.csv")
    parts["grid"] = grid
    res, parts["templates"] = exp_templates(cfg, pool, reps["templates"], d)
    parts["templates"].to_csv(OUT / "templates_paired.csv", index=False)
    parts["sens"] = exp_sensitivity(cfg, pool, reps["sens"], d)
    parts["sens"].to_csv(OUT / "sensitivity.csv", index=False)
    parts["reminder"] = exp_reminder(cfg, pool, reps["reminder"], d)
    parts["reminder"].to_csv(OUT / "reminder_scenario.csv", index=False)
    write_report(parts, reps, d, cfg, pool)
    print("Saved:", REPORT, "and", SUMMARY)


if __name__ == "__main__":
    main()

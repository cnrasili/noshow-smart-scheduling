# Tekrar üretim kılavuzu

Amaç: ekipten biri, kendi bilgisayarında IEN sonuçlarını sıfırdan üretip burada yazan sayılarla karşılaştırabilsin. Süre: yaklaşık 15 dakika. Yapılan her tekrar, en alttaki tabloya eklenir.

**Temiz sonuç ne demektir?** Rastgele sayılar sabit tohumlu olduğundan sonuçlar aynı çıkar. Kütüphane sürümleri farklıysa yalnızca üçüncü ondalıkta (ör. kalibrasyon eğimi 1,103 → 1,102) ve eşit değerli satırların sırasında fark görülebilir. Başka bir fark varsa not edin.

## 0. Hazırlık

- Python 3.11 ya da üstü, Git.
- Depoyu çekin ve **`IEN` dalına** geçin (ya da PR #62 birleştikten sonra `main`).

```bash
git clone https://github.com/cnrasili/noshow-smart-scheduling.git
cd noshow-smart-scheduling
git checkout IEN
git log -1 --format=%H        # aşağıdaki tabloya yazın
```

- Yeni bir sanal ortam kurun (mevcut ortamınızı kullanmayın):

```bash
python -m venv .venv
.venv\Scripts\activate         # Linux/macOS: source .venv/bin/activate
pip install -r ml/requirements.txt -r simulation/requirements.txt
pip install pydantic pydantic-settings pyyaml   # modelin servis kabul kontrolü için
```

Veri `ml/data/raw/KaggleV2-May-2016.csv` içinde depoyla birlikte gelir; ayrıca indirmeniz gerekmez.

## 1. Adımlar ve beklenen değerler

Her adımın çıktısını aşağıdaki değerlerle karşılaştırın.

### 1.1 Veri temizliği

```bash
python ml/data/clean_data.py
```

| Beklenen |
|---|
| Raw rows 110527, Clean rows 110521 (5 randevu "alınmadan önce", 1 negatif yaş çıkarıldı) |
| No-show rate 0.2019 |
| Appointment date range 2016-04-29 to 2016-06-08 |
| Unique patients 62298 |
| Department (every row) General Practice |

### 1.2 Raporlar ve gün bazlı riskler

```bash
cd ml
python build_reports.py
```

| Beklenen (test kümesi) | AUC | Brier | LogLoss |
|---|---|---|---|
| LogisticRegression | 0.6576 | 0.1451 | 0.461 |
| RandomForest | 0.7296 | 0.1361 | 0.4233 |
| R4_rules | 0.5767 | 0.1499 | 0.475 |

Son satırlar: `All-days out-of-sample risks: 110521 appointments, 27 days, AUC RF 0.728, LR 0.663, R4 0.572, paper-style 0.719`.

### 1.3 Model karşılaştırması (sızıntısız protokol)

```bash
python evaluate_models.py          # ml/ klasöründe; yaklaşık 5 dakika
```

`docs/MODEL_KARSILASTIRMA.md` yenilenir. Beklenen: seçilen hiperparametreler Lojistik `C=0.01`, Orman `n_estimators=150, min_samples_leaf=20, max_depth=14`, Ağaç `max_depth=4, min_samples_leaf=200`; test ROC-AUC Orman 0.729 (güven aralığı 0.721–0.736), Ağaç 0.720, Lojistik 0.658.

### 1.4 Modelin teslimi, deneyler ve bekleme dağılımı

```bash
python apply_decisions.py          # ml/ klasöründe; yaklaşık 3 dakika
```

| Beklenen çıktı satırı |
|---|
| `Rastgele orman: out-of-sample AUC 0.728` |
| `Service acceptance checks passed ... (random_forest-v1)` (servisin kabul kontrolleri) |
| `20000 random slots compared: 0 differences` (servis kuralı ile simülasyon kuralı aynı karar) |

Uyarı satırları: `main` dalında servis ayarları `daily_overbook_limit 2` ve `service_minutes 12` iken `DIFFERS` yazar. PR #64 birleştikten sonra `ok` olmalıdır; bu bir hata değildir.

`docs/SONUC_OZETI.md` (oturum başına, karar ayarı eşik %30 / sınır 4, kural yokla karşılaştırma):

| Ölçüt | Kural yok | Karar ayarı | Fark [%95 aralık] |
|---|---|---|---|
| Görülen hasta | 12.81 | 15.60 | +2.78 [+2.74; +2.82] |
| Ortalama bekleme (dk) | 0.22 | 1.13 | +0.91 [+0.87; +0.95] |
| Boşta kalma (dk) | 144.07 | 123.66 | −20.42 [−20.82; −20.01] |
| Mesai aşımı (dk) | 0.25 | 0.46 | +0.22 [+0.12; +0.31] |
| Doluluk | 0.40 | 0.49 | +0.09 |

`docs/BEKLEME_DAGILIMI.md`: kuralda hastaların %0.82'si 15 dk'dan uzun bekler; bir oturumda en az bir hastanın 15 dk'yı aşması %8.7; kural oturum başına 2.79 ek hasta görür, bedeli toplam +15.0 hasta-dakika bekleme (ek hasta başına yaklaşık 5.4 dk).

> `apply_decisions.py`, `ml/models/` altındaki model dosyalarını yeniden yazar. Bunları depoya geri koymak istemiyorsanız `git checkout -- ml/models` ya da `git restore ml/models` ile eski hâle getirin; farklı scikit-learn sürümüyle eğitilmiş bir dosyayı commit'lemeyin.

### 1.5 Zamansal sızıntı kontrolü

```bash
python leakage_check.py            # ml/ klasöründe
```

Beklenen (`docs/ZAMANSAL_SIZINTI_KONTROLU.md`): AUC dönüşümlü katlarla 0.731, yalnızca geçmiş günlerle 0.729; protokol denetimindeki beş maddenin hepsi "geçti".

### 1.6 İsteğe bağlı: tüm sonuç sayfaları ve servis testleri

```bash
cd ../simulation
python main.py --no-open           # yaklaşık 90 saniye; simulation/output/ altına sayfalar yazar
python parity_check.py             # servis kuralı ile simülasyon kuralı
```

Servis testleri (`overbooking-service/`) PR #64 ile birlikte 150 testin geçmesi beklenir; çalıştırmak için servisin kendi bağımlılıkları (FastAPI, SQLAlchemy, pytest) gerekir ve `PYTHONPATH` içine `overbooking-service`, `db` ve `ml` klasörleri eklenir (ayrıntı: `docs/SERVIS_UYUM_RAPORU.md`).

## 2. Üretilen dosyaları karşılaştırma

Adımlardan sonra:

```bash
git status --short docs ml
git diff --stat docs
```

- `docs/SONUC_OZETI.md` ve `docs/BEKLEME_DAGILIMI.md` **hiç değişmemeli** (ya da yalnızca sürüm satırı).
- `docs/MODEL_KARSILASTIRMA.md` ve `docs/IEN_DENEY_SONUCLARI.md` yalnızca üçüncü ondalıkta ve eşit satırların sırasında değişebilir.
- Başka bir fark çıkarsa bir sorun vardır: aşağıdaki tabloya sürümleri ve farkı yazın.

Dosyaları temizlemek için: `git restore docs ml/models`.

## 3. Tekrar kayıtları

Önceki tekrar: 17 Ekim 2026, `IEN` dalı, Windows, Python 3.11.2, pandas 3.0.6, numpy 2.4.6, scikit-learn 1.9.1, scipy 1.17.1, simpy 4.1.2 (yeni sanal ortam, aynı bilgisayar). Sonuç: SONUC_OZETI ve BEKLEME_DAGILIMI birebir aynı; diğerleri üçüncü ondalıkta farklı.

| Tarih | Kişi | İşletim sistemi | Python / pandas / scikit-learn | Commit (kısa) | Sonuç (tuttu / fark) | Not |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |

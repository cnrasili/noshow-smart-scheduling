# Sonuç özeti (otomatik üretilir)

Bu dosya `ml/apply_decisions.py` / `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. El yazısı belgeler sayıları buradan alır. Ayrıntı: `docs/IEN_DENEY_SONUCLARI.md`, `docs/MODEL_KARSILASTIRMA.md`.

## Güncel karar ayarları

- **Model:** Karar ağacı; 27 günde katlama dışı tahminle ROC-AUC **0.718**
- **Kural:** eşik %30, günlük ek randevu sınırı 4, slot başına en çok 2 hasta
- **Oturum:** 16 slot x 15 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 20 randevu isteği
- **Kabul edilen en uzun ortalama bekleme:** 15 dk

## Karar ayarı, sabit aralığa göre (oturum başına)

| Ölçüt | Kural yok | Karar ayarı | Fark [%95 aralık] | Değişim |
|---|---|---|---|---|
| Görülen hasta | 12.81 | 15.43 | +2.61 [+2.57; +2.66] | %+20 |
| Ortalama bekleme (dk) | 0.22 | 1.08 | +0.86 [+0.82; +0.90] | %+395 |
| Boşta kalma (dk) | 144.07 | 124.95 | -19.12 [-19.54; -18.71] | %-13 |
| Mesai aşımı (dk) | 0.25 | 0.48 | +0.23 [+0.13; +0.32] | %+93 |
| Doluluk | 0.40 | 0.48 | +0.08 [+0.08; +0.08] | %+20 |

**Bekleme sınırı kontrolü:** ortalama bekleme 1.08 dk; sınır 15 dk → **sınır içinde**.

**Muayene süresi duyarlılığı:** muayene 5 dk iken bekleme farkı +0.40 dk, 10 dk iken +2.07 dk.

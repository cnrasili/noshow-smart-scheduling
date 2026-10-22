# Sonuç özeti (otomatik üretilir)

Bu dosya `ml/apply_decisions.py` / `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. El yazısı belgeler sayıları buradan alır. Ayrıntı: `docs/IEN_DENEY_SONUCLARI.md`, `docs/MODEL_KARSILASTIRMA.md`.

## Güncel karar ayarları

- **Model:** Rastgele orman; 27 günde katlama dışı tahminle ROC-AUC **0.728**
- **Kural:** eşik %30, günlük ek randevu sınırı 4, slot başına en çok 2 hasta
- **Oturum:** 16 slot x 15 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 20 randevu isteği
- **Kabul edilen en uzun ortalama bekleme:** 15 dk

## Karar ayarı, sabit aralığa göre (oturum başına)

| Ölçüt | Kural yok | Karar ayarı | Fark [%95 aralık] | Değişim |
|---|---|---|---|---|
| Görülen hasta | 12.81 | 15.60 | +2.78 [+2.74; +2.82] | %+22 |
| Ortalama bekleme (dk) | 0.22 | 1.13 | +0.91 [+0.87; +0.95] | %+418 |
| Boşta kalma (dk) | 144.07 | 123.66 | -20.42 [-20.82; -20.01] | %-14 |
| Mesai aşımı (dk) | 0.25 | 0.46 | +0.22 [+0.12; +0.31] | %+87 |
| Doluluk | 0.40 | 0.49 | +0.09 [+0.08; +0.09] | %+21 |

**Bekleme sınırı kontrolü:** ortalama bekleme 1.13 dk; sınır 15 dk → **sınır içinde**.

**Muayene süresi duyarlılığı:** muayene 5 dk iken bekleme farkı +0.41 dk, 10 dk iken +2.18 dk.

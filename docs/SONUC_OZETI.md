# Sonuç özeti (otomatik üretilir)

Bu dosya `ml/apply_decisions.py` / `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. El yazısı belgeler sayıları buradan alır. Ayrıntı: `docs/IEN_DENEY_SONUCLARI.md`, `docs/MODEL_KARSILASTIRMA.md`.

## Güncel karar ayarları

- **Model:** Rastgele orman (varsayılan risk dosyası); 27 günde katlama dışı tahminle ROC-AUC **0.728**
- **Kural:** eşik %30, günlük ek randevu sınırı 4, slot başına en çok 2 hasta
- **Oturum:** 24 slot x 10 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 28 randevu isteği
- **Kabul edilen en uzun ortalama bekleme:** 15 dk

## Karar ayarı, sabit aralığa göre (oturum başına)

| Ölçüt | Kural yok | Karar ayarı | Fark [%95 aralık] | Değişim |
|---|---|---|---|---|
| Görülen hasta | 19.19 | 22.31 | +3.12 [+3.08; +3.15] | %+16 |
| Ortalama bekleme (dk) | 1.25 | 2.97 | +1.72 [+1.64; +1.79] | %+137 |
| Boşta kalma (dk) | 98.23 | 75.31 | -22.92 [-23.28; -22.57] | %-23 |
| Mesai aşımı (dk) | 1.90 | 2.25 | +0.34 [+0.13; +0.56] | %+18 |
| Doluluk | 0.60 | 0.70 | +0.10 [+0.10; +0.10] | %+16 |

**Bekleme sınırı kontrolü:** ortalama bekleme 2.97 dk; sınır 15 dk → **sınır içinde**.

**Muayene süresi duyarlılığı:** muayene 5 dk iken bekleme farkı +0.43 dk, 10 dk iken +6.74 dk.

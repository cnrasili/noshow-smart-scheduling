# Zamansal sızıntı kontrolü (otomatik üretilir)

Bu dosya `ml/leakage_check.py` tarafından üretilir; elle düzenlemeyin. Model: **random_forest** (`docs/decisions.json`).

## Soru

Simülasyonun kullandığı 27 günlük riskler, günleri 5 kata dönüşümlü dağıtarak üretiliyor. Bir gün, **kendisinden sonraki günlerle de eğitilmiş** bir modelle tahmin ediliyor. Günün kendi satırları eğitime girmez, ama gelecekteki günlerin bilgisi girer. Gerçek kullanımda model yalnızca geçmişi görür.

## Yöntem

İlk 7 gün yalnızca eğitimde kalır; sonraki günler 4'er günlük bloklarla tahmin edilir ve her blok için model **yalnızca önceki günlerle** eğitilir (ileri doğru genişleyen pencere). Dönüşümlü katlarla aynı satırlar (81,818 randevu, 20 gün) karşılaştırılır.

## Tahmin kalitesi (aynı satırlar)

| Risk üretimi | AUC | Brier | Ortalama tahmin | Gerçek oran | Kalibrasyon kesişimi | Kalibrasyon eğimi |
|---|---|---|---|---|---|---|
| Dönüşümlü katlar (şu an) | 0.731 | 0.143 | 0.203 | 0.200 | -0.018 | 1.077 |
| Yalnızca geçmiş günlerle | 0.729 | 0.144 | 0.210 | 0.200 | -0.068 | 1.127 |

AUC farkı çok küçük: dönüşümlü katlar sonuçları belirgin biçimde şişirmiyor. (Fark +0.002.)

## Simülasyon sonucuna etkisi (karar ayarı, sabit aralığa göre, 600 eşleştirilmiş oturum)

| Risk üretimi | Görülen (fark) | Bekleme dk (fark) | Boşta dk (fark) | Mesai aşımı dk (fark) |
|---|---|---|---|---|
| Dönüşümlü katlar (şu an) | +3.13 | +1.87 | -23.12 | +0.36 |
| Yalnızca geçmiş günlerle | +3.17 | +1.97 | -23.49 | +0.28 |

## Sonuç

AUC farkı çok küçük: dönüşümlü katlar sonuçları belirgin biçimde şişirmiyor. Karar ayarının hasta kazancı iki yöntemde +3.13 ve +3.17; bekleme farkı +1.87 ve +1.97 dk. Ayrıca iki sınırlılık sürer: (1) yalnızca 27 gün vardır, ilk günlerin tahmini için az eğitim verisi vardır; (2) her iki yöntem de hasta geçmişi özelliklerini randevu tarihinden önceki kayıtlarla hesaplar (`ml/data/clean_data.py`), bu yüzden özelliklerde sızıntı yoktur.

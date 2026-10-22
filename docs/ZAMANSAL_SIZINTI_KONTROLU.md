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
| Dönüşümlü katlar (şu an) | +2.81 | +0.89 | -21.03 | +0.10 |
| Yalnızca geçmiş günlerle | +2.88 | +0.91 | -21.60 | +0.09 |

## Değerlendirme protokolü denetimi

| Denetim | Sonuç | Ayrıntı |
|---|---|---|
| Özellik listesi hedefi, SMS'i, mahalleyi ve kimlikleri içermez | geçti | 11 özellik: LeadDays, Weekday, Age, GenderMale, Scholarship, Hypertension, Diabetes, Alcoholism, Handicap, PriorApptCount, PriorNoShowCount |
| Eğitim günleri test günlerinden önce (zamana göre ayrım) | geçti | eğitim son gün 01.06.2016, test ilk gün 02.06.2016 |
| Geçmiş özellikleri yalnızca randevu alınma gününden önceki randevulardan hesaplanır | geçti | 3.000 rastgele satır bağımsız olarak yeniden hesaplandı, 0 fark |
| Ölçekleme yalnızca eğitimde öğrenilir; yeniden örnekleme yok | geçti | lojistik regresyon boru hattı (StandardScaler + model) eğitimle kurulur; orman ve ağaç ölçekleme kullanmaz; test kümesi doğal dağılımını korur |
| Karar eşiği testten seçilmez | geçti | F1 eşiği eğitim dönemindeki katlama dışı tahminlerden seçilir (`ml/evaluate_models.py`) |

## Sonuç

AUC farkı çok küçük: dönüşümlü katlar sonuçları belirgin biçimde şişirmiyor. Karar ayarının hasta kazancı iki yöntemde +2.81 ve +2.88; bekleme farkı +0.89 ve +0.91 dk. Ayrıca iki sınırlılık sürer: (1) yalnızca 27 gün vardır, ilk günlerin tahmini için az eğitim verisi vardır; (2) her iki yöntem de hasta geçmişi özelliklerini randevu tarihinden önceki kayıtlarla hesaplar (`ml/data/clean_data.py`), bu yüzden özelliklerde sızıntı yoktur.

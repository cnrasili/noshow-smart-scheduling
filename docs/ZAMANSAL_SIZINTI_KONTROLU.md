# Zamansal sızıntı kontrolü (otomatik üretilir)

Bu dosya `ml/leakage_check.py` tarafından üretilir; elle düzenlemeyin. Model: **decision_tree** (`docs/decisions.json`).

## Soru

Simülasyonun kullandığı 27 günlük riskler, günleri 5 kata dönüşümlü dağıtarak üretiliyor. Bir gün, **kendisinden sonraki günlerle de eğitilmiş** bir modelle tahmin ediliyor. Günün kendi satırları eğitime girmez, ama gelecekteki günlerin bilgisi girer. Gerçek kullanımda model yalnızca geçmişi görür.

## Yöntem

İlk 7 gün yalnızca eğitimde kalır; sonraki günler 4'er günlük bloklarla tahmin edilir ve her blok için model **yalnızca önceki günlerle** eğitilir (ileri doğru genişleyen pencere). Dönüşümlü katlarla aynı satırlar (81,818 randevu, 20 gün) karşılaştırılır.

## Tahmin kalitesi (aynı satırlar)

| Risk üretimi | AUC | Brier | Ortalama tahmin | Gerçek oran | Kalibrasyon kesişimi | Kalibrasyon eğimi |
|---|---|---|---|---|---|---|
| Dönüşümlü katlar (şu an) | 0.719 | 0.144 | 0.205 | 0.200 | -0.033 | 0.995 |
| Yalnızca geçmiş günlerle | 0.719 | 0.145 | 0.213 | 0.200 | -0.082 | 1.029 |

AUC farkı çok küçük: dönüşümlü katlar sonuçları belirgin biçimde şişirmiyor. (Fark -0.000.)

## Simülasyon sonucuna etkisi (karar ayarı, sabit aralığa göre, 600 eşleştirilmiş oturum)

| Risk üretimi | Görülen (fark) | Bekleme dk (fark) | Boşta dk (fark) | Mesai aşımı dk (fark) |
|---|---|---|---|---|
| Dönüşümlü katlar (şu an) | +2.71 | +0.88 | -20.33 | +0.17 |
| Yalnızca geçmiş günlerle | +2.95 | +0.97 | -22.17 | +0.15 |

## Değerlendirme protokolü denetimi

| Denetim | Sonuç | Ayrıntı |
|---|---|---|
| Özellik listesi hedefi, SMS'i, mahalleyi ve kimlikleri içermez | geçti | 11 özellik: LeadDays, Weekday, Age, GenderMale, Scholarship, Hypertension, Diabetes, Alcoholism, Handicap, PriorApptCount, PriorNoShowCount |
| Eğitim günleri test günlerinden önce (zamana göre ayrım) | geçti | eğitim son gün 01.06.2016, test ilk gün 02.06.2016 |
| Geçmiş özellikleri yalnızca randevu alınma gününden önceki randevulardan hesaplanır | geçti | 3.000 rastgele satır bağımsız olarak yeniden hesaplandı, 0 fark |
| Ölçekleme yalnızca eğitimde öğrenilir; yeniden örnekleme yok | geçti | lojistik regresyon boru hattı (StandardScaler + model) eğitimle kurulur; orman ve ağaç ölçekleme kullanmaz; test kümesi doğal dağılımını korur |
| Karar eşiği testten seçilmez | geçti | F1 eşiği eğitim dönemindeki katlama dışı tahminlerden seçilir (`ml/evaluate_models.py`) |

## Sonuç

AUC farkı çok küçük: dönüşümlü katlar sonuçları belirgin biçimde şişirmiyor. Karar ayarının hasta kazancı iki yöntemde +2.71 ve +2.95; bekleme farkı +0.88 ve +0.97 dk. Ayrıca iki sınırlılık sürer: (1) yalnızca 27 gün vardır, ilk günlerin tahmini için az eğitim verisi vardır; (2) her iki yöntem de hasta geçmişi özelliklerini randevu tarihinden önceki kayıtlarla hesaplar (`ml/data/clean_data.py`), bu yüzden özelliklerde sızıntı yoktur.

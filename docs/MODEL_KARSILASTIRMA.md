# Model karşılaştırması (otomatik üretilir)

Bu dosya `ml/evaluate_models.py` tarafından üretilir; elle düzenlemeyin. Python 3.11.2, scikit-learn 1.2.2, pandas 2.0.1.

## 1. Değerlendirme protokolü (veri sızıntısı yok)

- **Zamana göre ayrım:** 29.04.2016 – 01.06.2016 arası eğitim (88,535 randevu), sonrası test (21,986 randevu). Test kümesi doğal sınıf dağılımını korur; hiçbir yeniden örnekleme yapılmaz. (Literatürdeki %95 doğruluk, bölmeden önce tüm veriyi dengelemekten gelir; bkz. `docs/LITERATUR_INCELEMESI.md`.)
- **Dönüşümler yalnızca eğitimde öğrenilir:** ölçekleme boru hattının içindedir.
- **Özellikler** `docs/features.md`'ye uyar; `SMS_received` kullanılmaz. Hasta geçmişi (`PriorApptCount`, `PriorNoShowCount`) yalnızca randevu tarihi, bu randevunun alındığı günden önce olan randevulardan hesaplanır.
- **Hiperparametreler:** eğitim dönemi tarihe göre 5 bloğa bölünür; genişleyen pencereyle 4 doğrulama katı. Seçim ölçütü ortalama doğrulama log-loss'u (kalibre olasılıklar için doğru puan), AUC yanında verilir.
- **Eşik:** F1'i en yükseğe çıkaran eşik, eğitimin katlama dışı tahminlerinden seçilir; test kümesi seçime karışmaz. 0,20 / 0,30 / 0,40 sabit eşikleri de verilir.
- Test kümesindeki gerçek no-show oranı %18.5; eğitimde %20.6.

## 2. Seçilen hiperparametreler

- **Logistic Regression:** `{'C': 0.01}`
- **Random Forest:** `{'n_estimators': 150, 'min_samples_leaf': 20, 'max_depth': 14}`
- **Decision Tree:** `{'max_depth': 4, 'min_samples_leaf': 200}`

Tüm adaylar:

| Model | Parametreler | CV LogLoss | CV AUC |
|---|---|---|---|
| Logistic Regression | {'C': 0.01} | 0.4915 | 0.6629 |
| Logistic Regression | {'C': 0.1} | 0.4918 | 0.6625 |
| Logistic Regression | {'C': 1.0} | 0.4918 | 0.6624 |
| Logistic Regression | {'C': 10.0} | 0.4918 | 0.6624 |
| Random Forest | {'n_estimators': 150, 'min_samples_leaf': 20, 'max_depth': 8} | 0.4524 | 0.7289 |
| Random Forest | {'n_estimators': 150, 'min_samples_leaf': 20, 'max_depth': 14} | 0.4518 | 0.7285 |
| Random Forest | {'n_estimators': 150, 'min_samples_leaf': 50, 'max_depth': 8} | 0.4532 | 0.7285 |
| Random Forest | {'n_estimators': 150, 'min_samples_leaf': 50, 'max_depth': 14} | 0.4526 | 0.7282 |
| Random Forest | {'n_estimators': 150, 'min_samples_leaf': 100, 'max_depth': 8} | 0.4545 | 0.7269 |
| Random Forest | {'n_estimators': 150, 'min_samples_leaf': 100, 'max_depth': 14} | 0.4538 | 0.7275 |
| Decision Tree | {'max_depth': 4, 'min_samples_leaf': 50} | 0.4543 | 0.7203 |
| Decision Tree | {'max_depth': 4, 'min_samples_leaf': 200} | 0.4537 | 0.7204 |
| Decision Tree | {'max_depth': 4, 'min_samples_leaf': 500} | 0.4545 | 0.7194 |
| Decision Tree | {'max_depth': 6, 'min_samples_leaf': 50} | 0.4605 | 0.7215 |
| Decision Tree | {'max_depth': 6, 'min_samples_leaf': 200} | 0.4563 | 0.7216 |
| Decision Tree | {'max_depth': 6, 'min_samples_leaf': 500} | 0.4553 | 0.7193 |
| Decision Tree | {'max_depth': 8, 'min_samples_leaf': 50} | 0.4751 | 0.7167 |
| Decision Tree | {'max_depth': 8, 'min_samples_leaf': 200} | 0.4582 | 0.7188 |
| Decision Tree | {'max_depth': 8, 'min_samples_leaf': 500} | 0.4557 | 0.7188 |
| Decision Tree | {'max_depth': 12, 'min_samples_leaf': 50} | 0.5172 | 0.7081 |
| Decision Tree | {'max_depth': 12, 'min_samples_leaf': 200} | 0.4593 | 0.7175 |
| Decision Tree | {'max_depth': 12, 'min_samples_leaf': 500} | 0.4558 | 0.7189 |

## 3. Test sonuçları

| Model | ROC-AUC | AUC alt | AUC üst | PR-AUC | Brier | LogLoss | Kalibrasyon kesişimi | Kalibrasyon eğimi |
|---|---|---|---|---|---|---|---|---|
| Logistic Regression | 0.658 | 0.648 | 0.667 | 0.295 | 0.145 | 0.461 | -0.140 | 0.897 |
| Random Forest | 0.729 | 0.721 | 0.736 | 0.339 | 0.136 | 0.423 | -0.139 | 1.103 |
| Decision Tree | 0.720 | 0.713 | 0.727 | 0.305 | 0.138 | 0.426 | -0.165 | 1.055 |
| Kural R4 (referans) | 0.577 | 0.567 | 0.587 | 0.234 | 0.150 | 0.475 | -0.119 | 0.684 |
| Sabit oran (referans) | 0.500 | 0.500 | 0.500 | 0.185 | 0.151 | 0.480 | -0.133 | 0.709 |

Log-loss ölçütüne göre en iyi model: **Random Forest**. AUC güven aralığı 200 bootstrap ile alınmıştır. Kalibrasyon eğimi 1'e, kesişim 0'a yakınsa olasılıklar güvenilirdir; eğim 1'den küçükse tahminler fazla uçtadır.

## 4. Karar eşiği: precision, recall, F1

No-show sınıfı için (pozitif = gelmeyecek):

| Model | Eşik | Precision | Recall | F1 | İşaretlenen pay |
|---|---|---|---|---|---|
| Logistic Regression | F1-eşiği (0.20) | 0.285 | 0.587 | 0.384 | 0.381 |
| Logistic Regression | 0.20 | 0.284 | 0.601 | 0.386 | 0.392 |
| Logistic Regression | 0.30 | 0.336 | 0.240 | 0.280 | 0.132 |
| Logistic Regression | 0.40 | 0.348 | 0.082 | 0.132 | 0.043 |
| Random Forest | F1-eşiği (0.22) | 0.289 | 0.792 | 0.424 | 0.507 |
| Random Forest | 0.20 | 0.277 | 0.860 | 0.419 | 0.576 |
| Random Forest | 0.30 | 0.331 | 0.476 | 0.390 | 0.266 |
| Random Forest | 0.40 | 0.411 | 0.084 | 0.140 | 0.038 |
| Decision Tree | F1-eşiği (0.23) | 0.285 | 0.791 | 0.419 | 0.514 |
| Decision Tree | 0.20 | 0.271 | 0.875 | 0.414 | 0.598 |
| Decision Tree | 0.30 | 0.332 | 0.414 | 0.369 | 0.231 |
| Decision Tree | 0.40 | 0.000 | 0.000 | 0.000 | 0.000 |
| Kural R4 (referans) | F1-eşiği (0.24) | 0.236 | 0.273 | 0.253 | 0.215 |
| Kural R4 (referans) | 0.20 | 0.219 | 0.597 | 0.321 | 0.504 |
| Kural R4 (referans) | 0.30 | 0.264 | 0.112 | 0.158 | 0.079 |
| Kural R4 (referans) | 0.40 | 0.350 | 0.030 | 0.055 | 0.016 |
| Sabit oran (referans) | F1-eşiği (0.21) | 0.185 | 1.000 | 0.312 | 1.000 |
| Sabit oran (referans) | 0.20 | 0.185 | 1.000 | 0.312 | 1.000 |
| Sabit oran (referans) | 0.30 | 0.000 | 0.000 | 0.000 | 0.000 |
| Sabit oran (referans) | 0.40 | 0.000 | 0.000 | 0.000 | 0.000 |

## 5. Alt gruplar (eşik 0,30)

| Model | Grup | n | Gerçek no-show | Ortalama tahmin | ROC-AUC | Brier | Kalibrasyon kesişimi | Kalibrasyon eğimi |
|---|---|---|---|---|---|---|---|---|
| Logistic Regression | Yeni hasta (geçmişi yok) | 11889 | 0.196 | 0.230 | 0.661 | 0.153 | -0.216 | 0.903 |
| Logistic Regression | Tekrar gelen hasta | 10097 | 0.172 | 0.177 | 0.655 | 0.136 | -0.038 | 0.991 |
| Random Forest | Yeni hasta (geçmişi yok) | 11889 | 0.196 | 0.223 | 0.721 | 0.143 | -0.181 | 1.121 |
| Random Forest | Tekrar gelen hasta | 10097 | 0.172 | 0.183 | 0.737 | 0.128 | -0.083 | 1.122 |
| Decision Tree | Yeni hasta (geçmişi yok) | 11889 | 0.196 | 0.222 | 0.713 | 0.144 | -0.171 | 1.089 |
| Decision Tree | Tekrar gelen hasta | 10097 | 0.172 | 0.193 | 0.723 | 0.130 | -0.157 | 1.022 |
| Kural R4 (referans) | Yeni hasta (geçmişi yok) | 11889 | 0.196 | 0.206 | 0.552 | 0.157 | -0.060 | 0.996 |
| Kural R4 (referans) | Tekrar gelen hasta | 10097 | 0.172 | 0.200 | 0.600 | 0.142 | -0.196 | 0.645 |

Geçmişi olmayan hastalarda hasta geçmişi özelliği bilgi taşımaz; bu grubun sonucu ayrı değerlendirilmelidir.

## 6. Kalibrasyon (onluk dilimler, test kümesi)

**Logistic Regression**

| Dilim | Tahmin | Gerçek | n |
|---|---|---|---|
| 1 | 0.093 | 0.091 | 2199 |
| 2 | 0.132 | 0.099 | 2199 |
| 3 | 0.147 | 0.116 | 2198 |
| 4 | 0.162 | 0.125 | 2200 |
| 5 | 0.176 | 0.148 | 2197 |
| 6 | 0.191 | 0.144 | 2199 |
| 7 | 0.210 | 0.220 | 2198 |
| 8 | 0.242 | 0.249 | 2199 |
| 9 | 0.290 | 0.323 | 2198 |
| 10 | 0.417 | 0.337 | 2199 |

**Random Forest**

| Dilim | Tahmin | Gerçek | n |
|---|---|---|---|
| 1 | 0.028 | 0.022 | 2199 |
| 2 | 0.043 | 0.030 | 2199 |
| 3 | 0.060 | 0.034 | 2198 |
| 4 | 0.144 | 0.134 | 2199 |
| 5 | 0.208 | 0.179 | 2198 |
| 6 | 0.238 | 0.222 | 2200 |
| 7 | 0.269 | 0.262 | 2197 |
| 8 | 0.307 | 0.273 | 2199 |
| 9 | 0.350 | 0.314 | 2198 |
| 10 | 0.401 | 0.382 | 2199 |

**Decision Tree**

| Dilim | Tahmin | Gerçek | n |
|---|---|---|---|
| 1 | 0.040 | 0.028 | 6273 |
| 2 | 0.051 | 0.046 | 717 |
| 3 | 0.178 | 0.162 | 1845 |
| 4 | 0.239 | 0.209 | 4410 |
| 5 | 0.280 | 0.261 | 3441 |
| 6 | 0.334 | 0.282 | 1015 |
| 7 | 0.377 | 0.340 | 4285 |

## 7. Sınırlılıklar

- Tek bir zaman bölmesi kullanıldı; farklı kesim tarihleri sonucu değiştirebilir.
- Veri 27 günü kapsıyor; mevsimsellik değerlendirilemez.
- Nihai model seçimi (#7) ve operasyonel eşik (#8) bir ekip kararıdır; bu rapor veri sağlar, karar vermez.

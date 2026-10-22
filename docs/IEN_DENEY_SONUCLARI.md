# IEN deney sonuçları (otomatik üretilir)

Bu dosya `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. Risk kaynağı: **Rastgele orman**. Tohum 20261016; Python 3.11.2, numpy 1.24.4, pandas 2.0.1, scipy 1.10.1, simpy 4.1.2. Ayarlar `docs/decisions.json` dosyasındandır.

**Okuma kuralları**

- Risk ve gelme/gelmeme bilgisi, modelin görmediği 27 günün gerçek tahminlerinden ve gerçek sonuçlarından gelir. Oturum ayarı: 16 slot x 15 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 20 randevu isteği. Muayene süresi (5–10 dk) devlet hastanesi poliklinik uygulamasından alınmıştır; slot, geç kalma ve talep **varsayımdır** (`docs/KARAR_LISTESI.md`).
- Tüm karşılaştırmalar **eşleştirilmiş**dir: her politika aynı rastgele oturumları görür (ortak rastgele sayılar). Farklar `taban politikaya göre` verilir; köşeli parantez %95 güven aralığı, `d` eşleştirilmiş etki büyüklüğüdür (Cohen d_z).
- Süreler oturum başına dakikadır; "Görülen" oturum başına hasta sayısıdır.

## 1. Politika karşılaştırması (2000 oturum)

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +2.78 [+2.74; +2.82] (d=+2.84) | +0.91 [+0.87; +0.95] (d=+1.01) | -20.42 [-20.82; -20.01] (d=-2.22) | +0.22 [+0.12; +0.31] (d=+0.10) | +0.09 [+0.08; +0.09] (d=+2.18) |
| Eşik %20 | +3.19 [+3.15; +3.22] (d=+3.95) | +1.23 [+1.18; +1.28] (d=+1.07) | -23.60 [-23.97; -23.22] (d=-2.77) | +0.06 [-0.02; +0.14] (d=+0.03) | +0.10 [+0.10; +0.10] (d=+2.70) |
| Eşik %40 | +0.39 [+0.36; +0.42] (d=+0.63) | +0.12 [+0.11; +0.14] (d=+0.36) | -2.87 [-3.08; -2.65] (d=-0.59) | +0.03 [-0.01; +0.07] (d=+0.03) | +0.01 [+0.01; +0.01] (d=+0.58) |
| Maliyet kuralı r=0,5 | +2.09 [+2.04; +2.14] (d=+1.85) | +0.69 [+0.65; +0.72] (d=+0.85) | -15.27 [-15.69; -14.85] (d=-1.60) | +0.27 [+0.18; +0.36] (d=+0.13) | +0.06 [+0.06; +0.07] (d=+1.56) |
| Maliyet kuralı r=1,0 | +0.02 [+0.01; +0.02] (d=+0.14) | +0.00 [+0.00; +0.01] (d=+0.06) | -0.14 [-0.19; -0.10] (d=-0.13) | +0.01 [-0.00; +0.02] (d=+0.04) | +0.00 [+0.00; +0.00] (d=+0.13) |
| Havayolu kuralı | +3.19 [+3.15; +3.22] (d=+3.95) | +1.61 [+1.54; +1.68] (d=+1.04) | -23.62 [-23.99; -23.25] (d=-2.77) | +0.05 [-0.03; +0.13] (d=+0.03) | +0.10 [+0.10; +0.10] (d=+2.70) |

**Yorum.** Ek randevu hem hasta sayısını artırır hem muayene odasının boşta kalmasını azaltır, ancak aynı slota iki hasta gelince ortalama bekleme ve çoğu politikada mesai aşımı da artar. İyileşme ve bedeli birlikte raporlanmalıdır: kural "bedava" değildir.

## 2. Eşik x günlük limit ızgarası (500 oturum)

Aşağıdaki ayarlar, dört ölçütte (hasta sayısı yüksek; bekleme, boşta kalma, mesai aşımı düşük) başka hiçbir ayar tarafından geçilmeyen **Pareto** ayarlarıdır:

| Ayar | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk | Doluluk | Ek slot |
|---|---|---|---|---|---|---|
| thr15_lim4 | 15.87 | 1.45 | 120.68 | 0.29 | 0.50 | 4.00 |
| thr15_lim6 | 15.87 | 2.17 | 120.38 | 0.00 | 0.50 | 5.98 |
| thr20_lim4 | 15.87 | 1.37 | 120.74 | 0.31 | 0.50 | 4.00 |
| thr20_lim6 | 15.87 | 1.99 | 120.44 | 0.02 | 0.50 | 5.87 |
| thr25_lim6 | 15.79 | 1.61 | 121.17 | 0.22 | 0.50 | 5.29 |
| thr25_lim4 | 15.79 | 1.21 | 121.38 | 0.43 | 0.50 | 3.92 |
| thr30_lim6 | 15.47 | 1.26 | 123.84 | 0.42 | 0.49 | 4.13 |
| thr30_lim4 | 15.47 | 1.08 | 123.92 | 0.50 | 0.49 | 3.51 |
| thr35_lim4 | 14.33 | 0.69 | 132.58 | 0.55 | 0.45 | 2.08 |
| thr35_lim6 | 14.33 | 0.72 | 132.56 | 0.53 | 0.45 | 2.13 |
| thr25_lim2 | 14.25 | 0.74 | 132.82 | 0.38 | 0.45 | 2.00 |
| thr30_lim2 | 14.22 | 0.70 | 133.12 | 0.40 | 0.45 | 1.95 |
| thr35_lim2 | 13.90 | 0.54 | 135.56 | 0.36 | 0.44 | 1.55 |
| thr25_lim1 | 13.45 | 0.45 | 138.73 | 0.38 | 0.42 | 1.00 |
| thr35_lim1 | 13.37 | 0.41 | 139.32 | 0.34 | 0.42 | 0.90 |
| thr40_lim8 | 13.06 | 0.31 | 141.82 | 0.32 | 0.41 | 0.48 |
| thr40_lim2 | 13.05 | 0.31 | 141.85 | 0.33 | 0.41 | 0.47 |
| thr40_lim1 | 12.98 | 0.29 | 142.34 | 0.34 | 0.41 | 0.39 |
| thr45_lim1 | 12.71 | 0.21 | 144.36 | 0.32 | 0.40 | 0.05 |
| thr50_lim1 | 12.68 | 0.19 | 144.57 | 0.33 | 0.40 | 0.00 |

Bir bekleme sınırı verilirse en çok hasta gören ayar:

| Bekleme sınırı (dk) | En iyi ayar | Görülen | Bekleme | Boşta | Mesai aşımı |
|---|---|---|---|---|---|
| ≤ 5 | thr15_lim6 | 15.87 | 2.17 | 120.38 | 0.00 |
| ≤ 10 | thr15_lim6 | 15.87 | 2.17 | 120.38 | 0.00 |
| ≤ 15 | thr15_lim6 | 15.87 | 2.17 | 120.38 | 0.00 |

Karar ayarı (eşik %30, sınır 4) ızgarada `thr30_lim4` satırıdır. Tüm ızgara betik çalışınca `simulation/results_experiments/grid_means.csv` olarak üretilir (CSV'ler git'e eklenmez).

## 3. Şablonlar ve kısa slot + overbooking (1000 oturum)

Her şablon aynı istek sayısıyla çalışır; fark tabana göredir.

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| 16x15 + karar ayarı | +2.77 [+2.70; +2.83] (d=+2.77) | +0.88 [+0.82; +0.93] (d=+1.02) | -20.87 [-21.47; -20.27] (d=-2.16) | +0.21 [+0.05; +0.36] (d=+0.08) | +0.09 [+0.09; +0.09] (d=+2.13) |
| 16x15 + karar ayarı + kaydırma 0,5 | +2.77 [+2.70; +2.83] (d=+2.77) | +0.69 [+0.64; +0.74] (d=+0.85) | -20.62 [-21.22; -20.02] (d=-2.13) | +0.45 [+0.28; +0.63] (d=+0.16) | +0.09 [+0.09; +0.09] (d=+2.13) |
| 20x12 kısa slot sabit | +3.20 [+3.15; +3.25] (d=+3.90) | +0.40 [+0.37; +0.44] (d=+0.75) | -23.76 [-24.30; -23.23] (d=-2.77) | +0.56 [+0.38; +0.74] (d=+0.19) | +0.10 [+0.10; +0.10] (d=+2.65) |
| 20x12 kısa slot + karar ayarı | +3.20 [+3.15; +3.25] (d=+3.90) | +1.69 [+1.59; +1.79] (d=+1.05) | -24.69 [-25.28; -24.10] (d=-2.60) | -0.37 [-0.49; -0.25] (d=-0.19) | +0.10 [+0.10; +0.10] (d=+2.65) |
| 20x12 kısa slot + karar ayarı + kaydırma 0,5 | +3.20 [+3.15; +3.25] (d=+3.90) | +1.62 [+1.52; +1.72] (d=+1.01) | -24.69 [-25.28; -24.10] (d=-2.60) | -0.37 [-0.49; -0.25] (d=-0.19) | +0.10 [+0.10; +0.10] (d=+2.65) |

## 4. Duyarlılık analizi (600 oturum her senaryo)

Karar ayarının sabit aralığa göre farkı (eşleştirilmiş ortalama):

| Senaryo | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| taban | +2.76 | +0.95 | -20.68 | +0.27 |
| Muayene süresi 5 dk | +2.76 | +0.41 | -14.29 | -0.00 |
| Muayene süresi 10 dk | +2.76 | +2.18 | -26.73 | +1.14 |
| Muayene değişkenliği 0,3 | +2.76 | +0.78 | -20.70 | +0.10 |
| Muayene değişkenliği 0,8 | +2.76 | +1.37 | -20.80 | +0.63 |
| Talep 16 istek | +0.00 | +0.96 | -0.36 | -0.36 |
| Talep 24 istek | +2.76 | +0.91 | -20.96 | +0.24 |
| Geç kalma sapması 8 dk | +2.76 | +0.90 | -20.45 | +0.55 |
| 10 dk slot, 24 slot | +3.12 | +1.71 | -22.82 | +0.68 |
| No-show oranı x0,7 | +0.11 | +0.05 | -0.85 | -0.01 |
| No-show oranı x1,3 | +2.91 | +0.97 | -21.41 | +0.13 |

Güven aralıkları `simulation/results_experiments/sensitivity.csv` dosyasında üretilir.

## 5. Hatırlatma senaryosu (varsayımsal, 600 oturum)

**Bu bir ölçüm değil, varsayımdır:** hatırlatma, hastaların yarısına gider ve gelmeyecek olanların belirtilen payını gelen hastaya çevirir. Gerçek etki A/B testiyle ölçülmelidir; veri setindeki `SMS_received` alanı rastgele bir deney olmadığından etkiyi tahmin etmeye uygun değildir.

| Hatırlatma etkisi | Politika | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk |
|---|---|---|---|---|---|
| %0 | sabit | 12.86 | 0.25 | 143.46 | 0.30 |
| %0 | karar ayarı | 15.63 | 1.20 | 122.55 | 0.63 |
| %10 | sabit | 13.03 | 0.24 | 142.18 | 0.31 |
| %10 | karar ayarı | 15.61 | 1.12 | 122.78 | 0.74 |
| %20 | sabit | 13.19 | 0.25 | 140.92 | 0.32 |
| %20 | karar ayarı | 15.35 | 0.97 | 124.82 | 0.67 |
| %30 | sabit | 13.32 | 0.25 | 140.02 | 0.32 |
| %30 | karar ayarı | 15.19 | 0.89 | 126.04 | 0.70 |

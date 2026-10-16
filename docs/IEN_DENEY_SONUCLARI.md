# IEN deney sonuçları (otomatik üretilir)

Bu dosya `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. Risk kaynağı: **Rastgele orman**. Tohum 20261016; Python 3.11.2, numpy 1.24.4, pandas 2.0.1, scipy 1.10.1, simpy 4.1.2. Ayarlar `docs/decisions.json` dosyasındandır.

**Okuma kuralları**

- Risk ve gelme/gelmeme bilgisi, modelin görmediği 27 günün gerçek tahminlerinden ve gerçek sonuçlarından gelir. Oturum ayarı: 24 slot x 10 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 28 randevu isteği. Muayene süresi (5–10 dk) devlet hastanesi poliklinik uygulamasından alınmıştır; slot, geç kalma ve talep **varsayımdır** (`docs/KARAR_LISTESI.md`).
- Tüm karşılaştırmalar **eşleştirilmiş**dir: her politika aynı rastgele oturumları görür (ortak rastgele sayılar). Farklar `taban politikaya göre` verilir; köşeli parantez %95 güven aralığı, `d` eşleştirilmiş etki büyüklüğüdür (Cohen d_z).
- Süreler oturum başına dakikadır; "Görülen" oturum başına hasta sayısıdır.

## 1. Politika karşılaştırması (2000 oturum)

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +3.14 [+3.10; +3.18] (d=+3.76) | +1.76 [+1.68; +1.84] (d=+0.98) | -23.17 [-23.53; -22.82] (d=-2.86) | +0.26 [+0.04; +0.47] (d=+0.05) | +0.10 [+0.10; +0.10] (d=+2.58) |
| Eşik %20 | +3.22 [+3.18; +3.25] (d=+4.02) | +2.33 [+2.23; +2.44] (d=+0.99) | -24.07 [-24.42; -23.72] (d=-2.98) | -0.07 [-0.28; +0.13] (d=-0.02) | +0.10 [+0.10; +0.10] (d=+2.69) |
| Eşik %40 | +0.57 [+0.54; +0.60] (d=+0.78) | +0.26 [+0.23; +0.28] (d=+0.45) | -4.00 [-4.24; -3.76] (d=-0.74) | +0.27 [+0.15; +0.39] (d=+0.10) | +0.02 [+0.02; +0.02] (d=+0.70) |
| Maliyet kuralı r=0,5 | +2.74 [+2.70; +2.79] (d=+2.68) | +1.41 [+1.34; +1.48] (d=+0.90) | -19.80 [-20.18; -19.41] (d=-2.27) | +0.68 [+0.46; +0.90] (d=+0.14) | +0.09 [+0.08; +0.09] (d=+2.08) |
| Maliyet kuralı r=1,0 | +0.03 [+0.02; +0.03] (d=+0.17) | +0.01 [+0.00; +0.01] (d=+0.08) | -0.19 [-0.24; -0.14] (d=-0.16) | +0.02 [-0.01; +0.04] (d=+0.03) | +0.00 [+0.00; +0.00] (d=+0.15) |
| Havayolu kuralı | +3.22 [+3.18; +3.25] (d=+4.02) | +2.89 [+2.77; +3.01] (d=+1.07) | -24.09 [-24.44; -23.73] (d=-2.98) | -0.09 [-0.30; +0.12] (d=-0.02) | +0.10 [+0.10; +0.10] (d=+2.69) |

**Yorum.** Ek randevu hem hasta sayısını artırır hem muayene odasının boşta kalmasını azaltır, ancak aynı slota iki hasta gelince ortalama bekleme ve çoğu politikada mesai aşımı da artar. İyileşme ve bedeli birlikte raporlanmalıdır: kural "bedava" değildir.

## 2. Eşik x günlük limit ızgarası (500 oturum)

Aşağıdaki ayarlar, dört ölçütte (hasta sayısı yüksek; bekleme, boşta kalma, mesai aşımı düşük) başka hiçbir ayar tarafından geçilmeyen **Pareto** ayarlarıdır:

| Ayar | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk | Doluluk | Ek slot |
|---|---|---|---|---|---|---|
| thr15_lim8 | 22.28 | 7.94 | 73.09 | 0.00 | 0.70 | 8.00 |
| thr20_lim4 | 22.28 | 3.64 | 75.02 | 1.94 | 0.70 | 4.00 |
| thr20_lim6 | 22.28 | 5.49 | 73.17 | 0.09 | 0.70 | 6.00 |
| thr20_lim8 | 22.28 | 7.33 | 73.11 | 0.02 | 0.70 | 7.93 |
| thr15_lim6 | 22.28 | 5.77 | 73.15 | 0.07 | 0.70 | 6.00 |
| thr25_lim4 | 22.28 | 3.34 | 75.06 | 1.95 | 0.70 | 3.99 |
| thr25_lim6 | 22.28 | 4.75 | 73.29 | 0.19 | 0.70 | 5.91 |
| thr30_lim4 | 22.21 | 3.13 | 75.81 | 2.25 | 0.69 | 3.92 |
| thr30_lim6 | 22.21 | 3.93 | 74.71 | 1.15 | 0.69 | 5.34 |
| thr35_lim6 | 21.39 | 2.55 | 82.10 | 1.87 | 0.67 | 3.13 |
| thr35_lim4 | 21.39 | 2.44 | 82.26 | 2.03 | 0.67 | 2.87 |
| thr25_lim2 | 20.70 | 2.11 | 86.59 | 1.59 | 0.65 | 2.00 |
| thr35_lim2 | 20.55 | 2.01 | 87.85 | 1.68 | 0.64 | 1.82 |
| thr15_lim1 | 19.87 | 1.64 | 92.56 | 1.34 | 0.62 | 1.00 |
| thr40_lim8 | 19.64 | 1.54 | 94.45 | 1.59 | 0.61 | 0.73 |
| thr40_lim2 | 19.61 | 1.53 | 94.63 | 1.53 | 0.61 | 0.68 |
| thr40_lim1 | 19.49 | 1.49 | 95.44 | 1.47 | 0.61 | 0.53 |
| thr45_lim1 | 19.13 | 1.33 | 98.02 | 1.52 | 0.60 | 0.06 |
| thr50_lim1 | 19.09 | 1.31 | 98.32 | 1.55 | 0.60 | 0.01 |

Bir bekleme sınırı verilirse en çok hasta gören ayar:

| Bekleme sınırı (dk) | En iyi ayar | Görülen | Bekleme | Boşta | Mesai aşımı |
|---|---|---|---|---|---|
| ≤ 5 | thr15_lim4 | 22.28 | 3.73 | 75.02 | 1.94 |
| ≤ 10 | thr15_lim8 | 22.28 | 7.94 | 73.09 | 0.00 |
| ≤ 15 | thr15_lim8 | 22.28 | 7.94 | 73.09 | 0.00 |

Karar ayarı (eşik %30, sınır 4) ızgarada `thr30_lim4` satırıdır. Tüm ızgara betik çalışınca `simulation/results_experiments/grid_means.csv` olarak üretilir (CSV'ler git'e eklenmez).

## 3. Şablonlar ve kısa slot + overbooking (1000 oturum)

Her şablon aynı istek sayısıyla çalışır; fark tabana göredir.

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| 24x10 + karar ayarı | +3.05 [+2.99; +3.10] (d=+3.51) | +1.80 [+1.69; +1.92] (d=+0.99) | -22.51 [-23.03; -22.00] (d=-2.71) | +0.69 [+0.36; +1.01] (d=+0.13) | +0.10 [+0.09; +0.10] (d=+2.35) |
| 24x10 + karar ayarı + kaydırma 0,5 | +3.05 [+2.99; +3.10] (d=+3.51) | +1.80 [+1.69; +1.91] (d=+0.98) | -22.41 [-22.93; -21.90] (d=-2.69) | +0.79 [+0.46; +1.12] (d=+0.15) | +0.10 [+0.09; +0.10] (d=+2.35) |
| 30x8 kısa slot sabit | +3.12 [+3.07; +3.18] (d=+3.79) | +1.94 [+1.84; +2.05] (d=+1.19) | -24.94 [-25.51; -24.37] (d=-2.71) | -1.13 [-1.35; -0.91] (d=-0.32) | +0.10 [+0.10; +0.10] (d=+2.49) |
| 30x8 kısa slot + karar ayarı | +3.12 [+3.07; +3.18] (d=+3.79) | +5.93 [+5.64; +6.23] (d=+1.26) | -25.38 [-26.01; -24.75] (d=-2.51) | -1.57 [-1.77; -1.37] (d=-0.48) | +0.10 [+0.10; +0.10] (d=+2.49) |
| 30x8 kısa slot + karar ayarı + kaydırma 0,5 | +3.12 [+3.07; +3.18] (d=+3.79) | +5.98 [+5.68; +6.28] (d=+1.25) | -25.38 [-26.00; -24.75] (d=-2.51) | -1.57 [-1.77; -1.36] (d=-0.48) | +0.10 [+0.10; +0.10] (d=+2.49) |

## 4. Duyarlılık analizi (600 oturum her senaryo)

Karar ayarının sabit aralığa göre farkı (eşleştirilmiş ortalama):

| Senaryo | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| taban | +3.12 | +1.71 | -22.82 | +0.68 |
| Muayene süresi 5 dk | +3.12 | +0.43 | -15.85 | +0.20 |
| Muayene süresi 10 dk | +3.12 | +6.88 | -24.50 | +6.74 |
| Muayene değişkenliği 0,3 | +3.12 | +1.35 | -22.95 | +0.45 |
| Muayene değişkenliği 0,8 | +3.12 | +2.47 | -22.56 | +1.43 |
| Talep 24 istek | +0.00 | +1.98 | -1.86 | -1.87 |
| Talep 32 istek | +3.12 | +1.83 | -23.06 | +0.65 |
| Geç kalma sapması 8 dk | +3.12 | +1.74 | -22.74 | +0.93 |
| 15 dk slot, 16 slot | +2.76 | +0.95 | -20.68 | +0.27 |
| No-show oranı x0,7 | +0.18 | +0.11 | -1.21 | +0.14 |
| No-show oranı x1,3 | +2.90 | +1.69 | -21.96 | -0.29 |

Güven aralıkları `simulation/results_experiments/sensitivity.csv` dosyasında üretilir.

## 5. Hatırlatma senaryosu (varsayımsal, 600 oturum)

**Bu bir ölçüm değil, varsayımdır:** hatırlatma, hastaların yarısına gider ve gelmeyecek olanların belirtilen payını gelen hastaya çevirir. Gerçek etki A/B testiyle ölçülmelidir; veri setindeki `SMS_received` alanı rastgele bir deney olmadığından etkiyi tahmin etmeye uygun değildir.

| Hatırlatma etkisi | Politika | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk |
|---|---|---|---|---|---|
| %0 | sabit | 19.26 | 1.29 | 97.00 | 1.59 |
| %0 | karar ayarı | 22.37 | 3.06 | 73.94 | 1.86 |
| %10 | sabit | 19.48 | 1.36 | 95.26 | 1.65 |
| %10 | karar ayarı | 22.53 | 3.10 | 72.89 | 2.03 |
| %20 | sabit | 19.70 | 1.39 | 93.56 | 1.73 |
| %20 | karar ayarı | 22.50 | 2.95 | 73.39 | 2.52 |
| %30 | sabit | 19.95 | 1.43 | 91.72 | 1.80 |
| %30 | karar ayarı | 22.50 | 2.81 | 73.52 | 2.79 |

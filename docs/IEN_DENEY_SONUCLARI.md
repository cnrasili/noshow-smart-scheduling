# IEN deney sonuçları (otomatik üretilir)

Bu dosya `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. Risk kaynağı: **Rastgele orman (varsayılan risk dosyası)**. Tohum 20261016; Python 3.11.2, numpy 1.24.4, pandas 2.0.1, scipy 1.10.1, simpy 4.1.2. Ayarlar `docs/decisions.json` dosyasındandır.

**Okuma kuralları**

- Risk ve gelme/gelmeme bilgisi, modelin görmediği 27 günün gerçek tahminlerinden ve gerçek sonuçlarından gelir. Oturum ayarı: 24 slot x 10 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 28 randevu isteği. Muayene süresi (5–10 dk) devlet hastanesi poliklinik uygulamasından alınmıştır; slot, geç kalma ve talep **varsayımdır** (`docs/KARAR_LISTESI.md`).
- Tüm karşılaştırmalar **eşleştirilmiş**dir: her politika aynı rastgele oturumları görür (ortak rastgele sayılar). Farklar `taban politikaya göre` verilir; köşeli parantez %95 güven aralığı, `d` eşleştirilmiş etki büyüklüğüdür (Cohen d_z).
- Süreler oturum başına dakikadır; "Görülen" oturum başına hasta sayısıdır.

## 1. Politika karşılaştırması (2000 oturum)

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +3.12 [+3.08; +3.15] (d=+3.72) | +1.72 [+1.64; +1.79] (d=+0.96) | -22.92 [-23.28; -22.57] (d=-2.84) | +0.34 [+0.13; +0.56] (d=+0.07) | +0.10 [+0.10; +0.10] (d=+2.57) |
| Eşik %20 | +3.22 [+3.18; +3.25] (d=+4.02) | +2.35 [+2.24; +2.45] (d=+0.98) | -24.06 [-24.42; -23.71] (d=-2.98) | -0.06 [-0.27; +0.14] (d=-0.01) | +0.10 [+0.10; +0.10] (d=+2.69) |
| Eşik %40 | +0.40 [+0.38; +0.43] (d=+0.64) | +0.17 [+0.15; +0.20] (d=+0.36) | -2.81 [-3.02; -2.61] (d=-0.61) | +0.19 [+0.09; +0.29] (d=+0.08) | +0.01 [+0.01; +0.01] (d=+0.58) |
| Maliyet kuralı r=0,5 | +2.66 [+2.61; +2.71] (d=+2.51) | +1.36 [+1.29; +1.42] (d=+0.91) | -19.19 [-19.58; -18.80] (d=-2.16) | +0.70 [+0.48; +0.91] (d=+0.14) | +0.08 [+0.08; +0.08] (d=+1.99) |
| Maliyet kuralı r=1,0 | +0.00 [+0.00; +0.01] (d=+0.05) | +0.00 [-0.00; +0.00] (d=+0.03) | -0.02 [-0.04; -0.00] (d=-0.05) | +0.00 [-0.01; +0.01] (d=+0.01) | +0.00 [+0.00; +0.00] (d=+0.05) |
| Havayolu kuralı | +3.22 [+3.18; +3.25] (d=+4.02) | +2.89 [+2.77; +3.01] (d=+1.07) | -24.09 [-24.44; -23.73] (d=-2.97) | -0.09 [-0.29; +0.12] (d=-0.02) | +0.10 [+0.10; +0.10] (d=+2.69) |

**Yorum.** Ek randevu hem hasta sayısını artırır hem doktorun boşta kalmasını azaltır, ancak aynı slota iki hasta gelince ortalama bekleme ve çoğu politikada mesai aşımı da artar. İyileşme ve bedeli birlikte raporlanmalıdır: kural "bedava" değildir.

## 2. Eşik x günlük limit ızgarası (500 oturum)

Aşağıdaki ayarlar, dört ölçütte (hasta sayısı yüksek; bekleme, boşta kalma, mesai aşımı düşük) başka hiçbir ayar tarafından geçilmeyen **Pareto** ayarlarıdır:

| Ayar | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk | Doluluk | Ek slot |
|---|---|---|---|---|---|---|
| thr15_lim8 | 22.27 | 7.91 | 73.18 | 0.00 | 0.70 | 8.00 |
| thr20_lim4 | 22.27 | 3.63 | 75.11 | 1.94 | 0.70 | 4.00 |
| thr20_lim6 | 22.27 | 5.50 | 73.26 | 0.09 | 0.70 | 6.00 |
| thr20_lim8 | 22.27 | 7.35 | 73.20 | 0.02 | 0.70 | 7.94 |
| thr15_lim6 | 22.27 | 5.75 | 73.24 | 0.07 | 0.70 | 6.00 |
| thr25_lim4 | 22.27 | 3.32 | 75.16 | 1.98 | 0.70 | 3.99 |
| thr25_lim6 | 22.27 | 4.72 | 73.39 | 0.20 | 0.70 | 5.91 |
| thr30_lim4 | 22.18 | 3.09 | 76.10 | 2.26 | 0.69 | 3.89 |
| thr30_lim6 | 22.18 | 3.85 | 75.07 | 1.23 | 0.69 | 5.25 |
| thr35_lim6 | 21.22 | 2.42 | 83.32 | 1.86 | 0.66 | 2.89 |
| thr35_lim4 | 21.22 | 2.33 | 83.45 | 2.00 | 0.66 | 2.69 |
| thr25_lim2 | 20.69 | 2.11 | 86.68 | 1.58 | 0.65 | 2.00 |
| thr35_lim2 | 20.50 | 1.95 | 88.24 | 1.57 | 0.64 | 1.77 |
| thr15_lim1 | 19.86 | 1.63 | 92.64 | 1.34 | 0.62 | 1.00 |
| thr40_lim8 | 19.45 | 1.47 | 95.83 | 1.58 | 0.61 | 0.49 |
| thr40_lim2 | 19.44 | 1.47 | 95.89 | 1.55 | 0.61 | 0.48 |
| thr40_lim1 | 19.37 | 1.45 | 96.34 | 1.47 | 0.60 | 0.40 |
| thr45_lim1 | 19.08 | 1.31 | 98.37 | 1.55 | 0.60 | 0.02 |
| thr50_lim1 | 19.07 | 1.31 | 98.46 | 1.56 | 0.60 | 0.00 |

Bir bekleme sınırı verilirse en çok hasta gören ayar:

| Bekleme sınırı (dk) | En iyi ayar | Görülen | Bekleme | Boşta | Mesai aşımı |
|---|---|---|---|---|---|
| ≤ 5 | thr15_lim4 | 22.27 | 3.72 | 75.11 | 1.94 |
| ≤ 10 | thr15_lim8 | 22.27 | 7.91 | 73.18 | 0.00 |
| ≤ 15 | thr15_lim8 | 22.27 | 7.91 | 73.18 | 0.00 |

Karar ayarı (eşik %30, sınır 4) ızgarada `thr30_lim4` satırıdır. Tüm ızgara betik çalışınca `simulation/results_experiments/grid_means.csv` olarak üretilir (CSV'ler git'e eklenmez).

## 3. Şablonlar ve kısa slot + overbooking (1000 oturum)

Her şablon aynı istek sayısıyla çalışır; fark tabana göredir.

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| 24x10 + karar ayarı | +3.03 [+2.97; +3.08] (d=+3.46) | +1.76 [+1.65; +1.87] (d=+0.99) | -22.38 [-22.90; -21.87] (d=-2.69) | +0.71 [+0.38; +1.04] (d=+0.13) | +0.10 [+0.09; +0.10] (d=+2.35) |
| 24x10 + karar ayarı + kaydırma 0,5 | +3.03 [+2.97; +3.08] (d=+3.46) | +1.76 [+1.65; +1.87] (d=+0.98) | -22.26 [-22.77; -21.74] (d=-2.67) | +0.84 [+0.51; +1.18] (d=+0.16) | +0.10 [+0.09; +0.10] (d=+2.35) |
| 30x8 kısa slot sabit | +3.13 [+3.07; +3.18] (d=+3.79) | +1.94 [+1.84; +2.05] (d=+1.19) | -24.94 [-25.51; -24.37] (d=-2.71) | -1.13 [-1.35; -0.91] (d=-0.32) | +0.10 [+0.10; +0.10] (d=+2.49) |
| 30x8 kısa slot + karar ayarı | +3.13 [+3.07; +3.18] (d=+3.79) | +5.83 [+5.54; +6.12] (d=+1.25) | -25.38 [-26.01; -24.76] (d=-2.51) | -1.57 [-1.77; -1.36] (d=-0.48) | +0.10 [+0.10; +0.10] (d=+2.49) |
| 30x8 kısa slot + karar ayarı + kaydırma 0,5 | +3.13 [+3.07; +3.18] (d=+3.79) | +5.88 [+5.59; +6.18] (d=+1.24) | -25.38 [-26.00; -24.75] (d=-2.52) | -1.56 [-1.77; -1.36] (d=-0.48) | +0.10 [+0.10; +0.10] (d=+2.49) |

## 4. Duyarlılık analizi (600 oturum her senaryo)

Karar ayarının sabit aralığa göre farkı (eşleştirilmiş ortalama):

| Senaryo | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| taban | +3.10 | +1.68 | -22.70 | +0.66 |
| Muayene süresi 5 dk | +3.10 | +0.43 | -15.78 | +0.18 |
| Muayene süresi 10 dk | +3.10 | +6.74 | -24.21 | +6.84 |
| Muayene değişkenliği 0,3 | +3.10 | +1.32 | -22.84 | +0.42 |
| Muayene değişkenliği 0,8 | +3.10 | +2.43 | -22.36 | +1.46 |
| Talep 24 istek | +0.00 | +1.93 | -1.86 | -1.87 |
| Talep 32 istek | +3.10 | +1.80 | -22.90 | +0.71 |
| Geç kalma sapması 8 dk | +3.10 | +1.72 | -22.63 | +0.88 |
| 15 dk slot, 16 slot | +2.72 | +0.94 | -20.23 | +0.35 |
| No-show oranı x0,7 | +0.05 | +0.03 | -0.32 | +0.04 |
| No-show oranı x1,3 | +2.90 | +1.69 | -21.94 | -0.30 |

Güven aralıkları `simulation/results_experiments/sensitivity.csv` dosyasında üretilir.

## 5. Hatırlatma senaryosu (varsayımsal, 600 oturum)

**Bu bir ölçüm değil, varsayımdır:** hatırlatma, hastaların yarısına gider ve gelmeyecek olanların belirtilen payını gelen hastaya çevirir. Gerçek etki A/B testiyle ölçülmelidir; veri setindeki `SMS_received` alanı rastgele bir deney olmadığından etkiyi tahmin etmeye uygun değildir.

| Hatırlatma etkisi | Politika | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk |
|---|---|---|---|---|---|
| %0 | sabit | 19.25 | 1.30 | 97.02 | 1.60 |
| %0 | karar ayarı | 22.37 | 3.04 | 74.08 | 1.99 |
| %10 | sabit | 19.48 | 1.36 | 95.28 | 1.65 |
| %10 | karar ayarı | 22.51 | 3.07 | 73.17 | 2.21 |
| %20 | sabit | 19.70 | 1.39 | 93.58 | 1.73 |
| %20 | karar ayarı | 22.42 | 2.89 | 74.02 | 2.62 |
| %30 | sabit | 19.95 | 1.43 | 91.74 | 1.81 |
| %30 | karar ayarı | 22.39 | 2.76 | 74.32 | 2.78 |

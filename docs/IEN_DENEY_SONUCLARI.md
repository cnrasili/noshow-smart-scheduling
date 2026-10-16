# IEN deney sonuçları (otomatik üretilir)

Bu dosya `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. Risk kaynağı: **Karar ağacı**. Tohum 20261016; Python 3.11.2, numpy 1.24.4, pandas 2.0.1, scipy 1.10.1, simpy 4.1.2. Ayarlar `docs/decisions.json` dosyasındandır.

**Okuma kuralları**

- Risk ve gelme/gelmeme bilgisi, modelin görmediği 27 günün gerçek tahminlerinden ve gerçek sonuçlarından gelir. Oturum ayarı: 24 slot x 10 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 28 randevu isteği. Muayene süresi (5–10 dk) devlet hastanesi poliklinik uygulamasından alınmıştır; slot, geç kalma ve talep **varsayımdır** (`docs/KARAR_LISTESI.md`).
- Tüm karşılaştırmalar **eşleştirilmiş**dir: her politika aynı rastgele oturumları görür (ortak rastgele sayılar). Farklar `taban politikaya göre` verilir; köşeli parantez %95 güven aralığı, `d` eşleştirilmiş etki büyüklüğüdür (Cohen d_z).
- Süreler oturum başına dakikadır; "Görülen" oturum başına hasta sayısıdır.

## 1. Politika karşılaştırması (2000 oturum)

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +3.07 [+3.03; +3.11] (d=+3.49) | +1.68 [+1.61; +1.76] (d=+0.99) | -22.55 [-22.91; -22.18] (d=-2.72) | +0.38 [+0.16; +0.60] (d=+0.08) | +0.10 [+0.09; +0.10] (d=+2.48) |
| Eşik %20 | +3.22 [+3.18; +3.25] (d=+4.02) | +2.34 [+2.23; +2.44] (d=+0.99) | -24.07 [-24.42; -23.71] (d=-2.98) | -0.07 [-0.28; +0.14] (d=-0.01) | +0.10 [+0.10; +0.10] (d=+2.69) |
| Eşik %40 | +0.57 [+0.54; +0.60] (d=+0.77) | +0.27 [+0.24; +0.30] (d=+0.43) | -4.04 [-4.29; -3.80] (d=-0.73) | +0.27 [+0.14; +0.40] (d=+0.09) | +0.02 [+0.02; +0.02] (d=+0.68) |
| Maliyet kuralı r=0,5 | +2.93 [+2.89; +2.97] (d=+3.08) | +1.55 [+1.48; +1.62] (d=+0.97) | -21.33 [-21.71; -20.96] (d=-2.49) | +0.56 [+0.34; +0.77] (d=+0.11) | +0.09 [+0.09; +0.09] (d=+2.29) |
| Maliyet kuralı r=1,0 | +0.01 [+0.00; +0.01] (d=+0.09) | +0.00 [+0.00; +0.01] (d=+0.06) | -0.05 [-0.08; -0.03] (d=-0.09) | +0.01 [-0.01; +0.02] (d=+0.02) | +0.00 [+0.00; +0.00] (d=+0.08) |
| Havayolu kuralı | +3.22 [+3.18; +3.25] (d=+4.02) | +2.89 [+2.77; +3.01] (d=+1.07) | -24.09 [-24.44; -23.73] (d=-2.98) | -0.09 [-0.30; +0.12] (d=-0.02) | +0.10 [+0.10; +0.10] (d=+2.69) |

**Yorum.** Ek randevu hem hasta sayısını artırır hem doktorun boşta kalmasını azaltır, ancak aynı slota iki hasta gelince ortalama bekleme ve çoğu politikada mesai aşımı da artar. İyileşme ve bedeli birlikte raporlanmalıdır: kural "bedava" değildir.

## 2. Eşik x günlük limit ızgarası (500 oturum)

Aşağıdaki ayarlar, dört ölçütte (hasta sayısı yüksek; bekleme, boşta kalma, mesai aşımı düşük) başka hiçbir ayar tarafından geçilmeyen **Pareto** ayarlarıdır:

| Ayar | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk | Doluluk | Ek slot |
|---|---|---|---|---|---|---|
| thr20_lim4 | 22.28 | 3.61 | 75.02 | 1.94 | 0.70 | 4.00 |
| thr20_lim6 | 22.28 | 5.38 | 73.15 | 0.07 | 0.70 | 6.00 |
| thr20_lim8 | 22.28 | 7.18 | 73.09 | 0.01 | 0.70 | 7.93 |
| thr25_lim4 | 22.28 | 3.42 | 75.04 | 1.96 | 0.70 | 4.00 |
| thr25_lim6 | 22.28 | 4.83 | 73.25 | 0.17 | 0.70 | 5.95 |
| thr15_lim8 | 22.28 | 7.99 | 73.09 | 0.00 | 0.70 | 8.00 |
| thr30_lim4 | 22.16 | 3.08 | 76.28 | 2.32 | 0.69 | 3.84 |
| thr30_lim6 | 22.16 | 3.69 | 75.23 | 1.27 | 0.69 | 5.03 |
| thr30_lim8 | 22.16 | 3.89 | 75.23 | 1.27 | 0.69 | 5.41 |
| thr35_lim4 | 22.04 | 2.99 | 77.36 | 2.49 | 0.69 | 3.70 |
| thr35_lim6 | 22.04 | 3.39 | 76.56 | 1.68 | 0.69 | 4.57 |
| thr25_lim2 | 20.70 | 2.17 | 86.59 | 1.59 | 0.65 | 2.00 |
| thr30_lim2 | 20.69 | 2.13 | 86.68 | 1.65 | 0.65 | 1.99 |
| thr15_lim1 | 19.87 | 1.63 | 92.56 | 1.34 | 0.62 | 1.00 |
| thr35_lim1 | 19.87 | 1.68 | 92.59 | 1.34 | 0.62 | 1.00 |
| thr40_lim8 | 19.63 | 1.58 | 94.49 | 1.82 | 0.61 | 0.70 |
| thr40_lim2 | 19.59 | 1.56 | 94.70 | 1.72 | 0.61 | 0.65 |
| thr40_lim1 | 19.47 | 1.50 | 95.54 | 1.59 | 0.61 | 0.50 |
| thr45_lim1 | 19.09 | 1.32 | 98.30 | 1.56 | 0.60 | 0.02 |
| thr50_lim1 | 19.08 | 1.32 | 98.35 | 1.57 | 0.60 | 0.01 |

Bir bekleme sınırı verilirse en çok hasta gören ayar:

| Bekleme sınırı (dk) | En iyi ayar | Görülen | Bekleme | Boşta | Mesai aşımı |
|---|---|---|---|---|---|
| ≤ 5 | thr25_lim6 | 22.28 | 4.83 | 73.25 | 0.17 |
| ≤ 10 | thr15_lim8 | 22.28 | 7.99 | 73.09 | 0.00 |
| ≤ 15 | thr15_lim8 | 22.28 | 7.99 | 73.09 | 0.00 |

Karar ayarı (eşik %30, sınır 4) ızgarada `thr30_lim4` satırıdır. Tüm ızgara betik çalışınca `simulation/results_experiments/grid_means.csv` olarak üretilir (CSV'ler git'e eklenmez).

## 3. Şablonlar ve kısa slot + overbooking (1000 oturum)

Her şablon aynı istek sayısıyla çalışır; fark tabana göredir.

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| 24x10 + karar ayarı | +2.99 [+2.93; +3.04] (d=+3.32) | +1.73 [+1.62; +1.84] (d=+0.97) | -21.97 [-22.49; -21.45] (d=-2.63) | +0.71 [+0.40; +1.02] (d=+0.14) | +0.09 [+0.09; +0.10] (d=+2.35) |
| 24x10 + karar ayarı + kaydırma 0,5 | +2.99 [+2.93; +3.04] (d=+3.32) | +1.74 [+1.63; +1.85] (d=+0.97) | -21.82 [-22.34; -21.30] (d=-2.60) | +0.87 [+0.55; +1.18] (d=+0.17) | +0.09 [+0.09; +0.10] (d=+2.35) |
| 30x8 kısa slot sabit | +3.12 [+3.07; +3.18] (d=+3.79) | +1.94 [+1.84; +2.05] (d=+1.19) | -24.94 [-25.51; -24.37] (d=-2.71) | -1.13 [-1.35; -0.91] (d=-0.32) | +0.10 [+0.10; +0.10] (d=+2.49) |
| 30x8 kısa slot + karar ayarı | +3.12 [+3.07; +3.18] (d=+3.79) | +5.77 [+5.48; +6.06] (d=+1.23) | -25.36 [-25.98; -24.73] (d=-2.52) | -1.55 [-1.75; -1.34] (d=-0.46) | +0.10 [+0.10; +0.10] (d=+2.49) |
| 30x8 kısa slot + karar ayarı + kaydırma 0,5 | +3.12 [+3.07; +3.18] (d=+3.79) | +5.82 [+5.53; +6.12] (d=+1.23) | -25.35 [-25.97; -24.73] (d=-2.52) | -1.54 [-1.75; -1.33] (d=-0.46) | +0.10 [+0.10; +0.10] (d=+2.49) |

## 4. Duyarlılık analizi (600 oturum her senaryo)

Karar ayarının sabit aralığa göre farkı (eşleştirilmiş ortalama):

| Senaryo | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| taban | +3.06 | +1.69 | -22.36 | +0.77 |
| Muayene süresi 5 dk | +3.06 | +0.43 | -15.58 | +0.22 |
| Muayene süresi 10 dk | +3.06 | +6.65 | -23.58 | +7.16 |
| Muayene değişkenliği 0,3 | +3.06 | +1.33 | -22.48 | +0.54 |
| Muayene değişkenliği 0,8 | +3.06 | +2.47 | -21.96 | +1.62 |
| Talep 24 istek | +0.00 | +1.93 | -1.86 | -1.87 |
| Talep 32 istek | +3.06 | +1.78 | -22.53 | +0.78 |
| Geç kalma sapması 8 dk | +3.06 | +1.74 | -22.27 | +1.00 |
| 15 dk slot, 16 slot | +2.61 | +0.91 | -19.50 | +0.25 |
| No-show oranı x0,7 | +0.04 | +0.03 | -0.29 | +0.05 |
| No-show oranı x1,3 | +2.89 | +1.74 | -21.92 | -0.33 |

Güven aralıkları `simulation/results_experiments/sensitivity.csv` dosyasında üretilir.

## 5. Hatırlatma senaryosu (varsayımsal, 600 oturum)

**Bu bir ölçüm değil, varsayımdır:** hatırlatma, hastaların yarısına gider ve gelmeyecek olanların belirtilen payını gelen hastaya çevirir. Gerçek etki A/B testiyle ölçülmelidir; veri setindeki `SMS_received` alanı rastgele bir deney olmadığından etkiyi tahmin etmeye uygun değildir.

| Hatırlatma etkisi | Politika | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk |
|---|---|---|---|---|---|
| %0 | sabit | 19.26 | 1.29 | 97.00 | 1.59 |
| %0 | karar ayarı | 22.34 | 3.01 | 74.26 | 1.93 |
| %10 | sabit | 19.48 | 1.36 | 95.26 | 1.65 |
| %10 | karar ayarı | 22.52 | 3.09 | 72.87 | 2.12 |
| %20 | sabit | 19.70 | 1.39 | 93.56 | 1.73 |
| %20 | karar ayarı | 22.29 | 2.75 | 75.08 | 2.70 |
| %30 | sabit | 19.95 | 1.43 | 91.72 | 1.80 |
| %30 | karar ayarı | 22.25 | 2.63 | 75.41 | 2.79 |

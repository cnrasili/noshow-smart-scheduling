# IEN deney sonuçları (otomatik üretilir)

Bu dosya `simulation/experiments.py` tarafından üretilir; elle düzenlemeyin. Risk kaynağı: **Karar ağacı**. Tohum 20261016; Python 3.11.2, numpy 1.24.4, pandas 2.0.1, scipy 1.10.1, simpy 4.1.2. Ayarlar `docs/decisions.json` dosyasındandır.

**Okuma kuralları**

- Risk ve gelme/gelmeme bilgisi, modelin görmediği 27 günün gerçek tahminlerinden ve gerçek sonuçlarından gelir. Oturum ayarı: 16 slot x 15 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 20 randevu isteği. Muayene süresi (5–10 dk) devlet hastanesi poliklinik uygulamasından alınmıştır; slot, geç kalma ve talep **varsayımdır** (`docs/KARAR_LISTESI.md`).
- Tüm karşılaştırmalar **eşleştirilmiş**dir: her politika aynı rastgele oturumları görür (ortak rastgele sayılar). Farklar `taban politikaya göre` verilir; köşeli parantez %95 güven aralığı, `d` eşleştirilmiş etki büyüklüğüdür (Cohen d_z).
- Süreler oturum başına dakikadır; "Görülen" oturum başına hasta sayısıdır.

## 1. Politika karşılaştırması (2000 oturum)

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +2.61 [+2.57; +2.66] (d=+2.51) | +0.86 [+0.82; +0.90] (d=+1.00) | -19.12 [-19.54; -18.71] (d=-2.04) | +0.23 [+0.13; +0.32] (d=+0.11) | +0.08 [+0.08; +0.08] (d=+1.99) |
| Eşik %20 | +3.19 [+3.15; +3.22] (d=+3.94) | +1.23 [+1.18; +1.28] (d=+1.10) | -23.59 [-23.96; -23.21] (d=-2.77) | +0.06 [-0.02; +0.14] (d=+0.03) | +0.10 [+0.10; +0.10] (d=+2.69) |
| Eşik %40 | +0.38 [+0.35; +0.40] (d=+0.64) | +0.13 [+0.12; +0.15] (d=+0.37) | -2.74 [-2.94; -2.54] (d=-0.59) | +0.04 [-0.01; +0.08] (d=+0.04) | +0.01 [+0.01; +0.01] (d=+0.58) |
| Maliyet kuralı r=0,5 | +2.35 [+2.30; +2.40] (d=+2.12) | +0.76 [+0.72; +0.80] (d=+0.92) | -17.18 [-17.60; -16.76] (d=-1.80) | +0.22 [+0.13; +0.32] (d=+0.11) | +0.07 [+0.07; +0.07] (d=+1.75) |
| Maliyet kuralı r=1,0 | +0.01 [+0.00; +0.01] (d=+0.08) | +0.00 [+0.00; +0.01] (d=+0.06) | -0.04 [-0.07; -0.02] (d=-0.07) | +0.00 [-0.00; +0.00] (d=+0.02) | +0.00 [+0.00; +0.00] (d=+0.07) |
| Havayolu kuralı | +3.19 [+3.15; +3.22] (d=+3.95) | +1.61 [+1.54; +1.68] (d=+1.04) | -23.62 [-23.99; -23.25] (d=-2.77) | +0.05 [-0.03; +0.13] (d=+0.03) | +0.10 [+0.10; +0.10] (d=+2.70) |

**Yorum.** Ek randevu hem hasta sayısını artırır hem muayene odasının boşta kalmasını azaltır, ancak aynı slota iki hasta gelince ortalama bekleme ve çoğu politikada mesai aşımı da artar. İyileşme ve bedeli birlikte raporlanmalıdır: kural "bedava" değildir.

## 2. Eşik x günlük limit ızgarası (500 oturum)

Aşağıdaki ayarlar, dört ölçütte (hasta sayısı yüksek; bekleme, boşta kalma, mesai aşımı düşük) başka hiçbir ayar tarafından geçilmeyen **Pareto** ayarlarıdır:

| Ayar | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk | Doluluk | Ek slot |
|---|---|---|---|---|---|---|
| thr15_lim4 | 15.87 | 1.45 | 120.68 | 0.29 | 0.50 | 4.00 |
| thr15_lim6 | 15.87 | 2.18 | 120.38 | 0.00 | 0.50 | 5.98 |
| thr20_lim4 | 15.87 | 1.35 | 120.70 | 0.30 | 0.50 | 4.00 |
| thr20_lim6 | 15.87 | 1.97 | 120.42 | 0.02 | 0.50 | 5.84 |
| thr25_lim4 | 15.82 | 1.27 | 121.18 | 0.34 | 0.50 | 3.94 |
| thr25_lim6 | 15.82 | 1.70 | 120.94 | 0.10 | 0.50 | 5.39 |
| thr30_lim6 | 15.32 | 1.15 | 125.08 | 0.42 | 0.48 | 3.73 |
| thr30_lim4 | 15.32 | 1.03 | 125.13 | 0.47 | 0.48 | 3.30 |
| thr35_lim4 | 15.08 | 0.96 | 126.83 | 0.58 | 0.47 | 3.02 |
| thr25_lim2 | 14.25 | 0.77 | 132.82 | 0.38 | 0.45 | 2.00 |
| thr30_lim2 | 14.19 | 0.67 | 133.27 | 0.39 | 0.45 | 1.92 |
| thr35_lim2 | 14.13 | 0.66 | 133.71 | 0.38 | 0.44 | 1.84 |
| thr30_lim1 | 13.45 | 0.45 | 138.73 | 0.38 | 0.42 | 1.00 |
| thr35_lim1 | 13.43 | 0.45 | 138.82 | 0.37 | 0.42 | 0.98 |
| thr40_lim8 | 13.04 | 0.32 | 141.92 | 0.39 | 0.41 | 0.47 |
| thr40_lim2 | 13.03 | 0.31 | 142.02 | 0.40 | 0.41 | 0.45 |
| thr40_lim1 | 12.96 | 0.28 | 142.44 | 0.35 | 0.41 | 0.37 |
| thr45_lim1 | 12.69 | 0.21 | 144.49 | 0.33 | 0.40 | 0.01 |
| thr50_lim1 | 12.69 | 0.20 | 144.51 | 0.33 | 0.40 | 0.01 |

Bir bekleme sınırı verilirse en çok hasta gören ayar:

| Bekleme sınırı (dk) | En iyi ayar | Görülen | Bekleme | Boşta | Mesai aşımı |
|---|---|---|---|---|---|
| ≤ 5 | thr15_lim6 | 15.87 | 2.18 | 120.38 | 0.00 |
| ≤ 10 | thr15_lim6 | 15.87 | 2.18 | 120.38 | 0.00 |
| ≤ 15 | thr15_lim6 | 15.87 | 2.18 | 120.38 | 0.00 |

Karar ayarı (eşik %30, sınır 4) ızgarada `thr30_lim4` satırıdır. Tüm ızgara betik çalışınca `simulation/results_experiments/grid_means.csv` olarak üretilir (CSV'ler git'e eklenmez).

## 3. Şablonlar ve kısa slot + overbooking (1000 oturum)

Her şablon aynı istek sayısıyla çalışır; fark tabana göredir.

| Senaryo | Görülen hasta | Ortalama bekleme (dk) | Boşta kalma (dk) | Mesai aşımı (dk) | Doluluk |
|---|---|---|---|---|---|
| 16x15 + karar ayarı | +2.65 [+2.58; +2.71] (d=+2.54) | +0.83 [+0.78; +0.88] (d=+0.97) | -19.89 [-20.50; -19.28] (d=-2.01) | +0.16 [-0.00; +0.33] (d=+0.06) | +0.08 [+0.08; +0.09] (d=+2.00) |
| 16x15 + karar ayarı + kaydırma 0,5 | +2.65 [+2.58; +2.71] (d=+2.54) | +0.64 [+0.60; +0.69] (d=+0.81) | -19.67 [-20.28; -19.06] (d=-1.99) | +0.39 [+0.21; +0.56] (d=+0.14) | +0.08 [+0.08; +0.09] (d=+2.00) |
| 20x12 kısa slot sabit | +3.20 [+3.15; +3.25] (d=+3.90) | +0.40 [+0.37; +0.44] (d=+0.75) | -23.76 [-24.30; -23.23] (d=-2.77) | +0.56 [+0.38; +0.74] (d=+0.19) | +0.10 [+0.10; +0.10] (d=+2.65) |
| 20x12 kısa slot + karar ayarı | +3.20 [+3.15; +3.25] (d=+3.90) | +1.59 [+1.49; +1.68] (d=+1.05) | -24.68 [-25.27; -24.10] (d=-2.60) | -0.36 [-0.48; -0.24] (d=-0.18) | +0.10 [+0.10; +0.10] (d=+2.65) |
| 20x12 kısa slot + karar ayarı + kaydırma 0,5 | +3.20 [+3.15; +3.25] (d=+3.90) | +1.51 [+1.41; +1.60] (d=+1.00) | -24.68 [-25.27; -24.10] (d=-2.60) | -0.36 [-0.48; -0.24] (d=-0.18) | +0.10 [+0.10; +0.10] (d=+2.65) |

## 4. Duyarlılık analizi (600 oturum her senaryo)

Karar ayarının sabit aralığa göre farkı (eşleştirilmiş ortalama):

| Senaryo | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| taban | +2.61 | +0.91 | -19.50 | +0.25 |
| Muayene süresi 5 dk | +2.61 | +0.40 | -13.47 | +0.00 |
| Muayene süresi 10 dk | +2.61 | +2.07 | -25.12 | +1.15 |
| Muayene değişkenliği 0,3 | +2.61 | +0.74 | -19.51 | +0.13 |
| Muayene değişkenliği 0,8 | +2.61 | +1.32 | -19.59 | +0.59 |
| Talep 16 istek | +0.00 | +0.85 | -0.36 | -0.36 |
| Talep 24 istek | +2.61 | +0.87 | -19.86 | +0.27 |
| Geç kalma sapması 8 dk | +2.61 | +0.88 | -19.32 | +0.50 |
| 10 dk slot, 24 slot | +3.06 | +1.69 | -22.36 | +0.77 |
| No-show oranı x0,7 | +0.03 | +0.01 | -0.16 | +0.01 |
| No-show oranı x1,3 | +2.91 | +0.96 | -21.48 | +0.10 |

Güven aralıkları `simulation/results_experiments/sensitivity.csv` dosyasında üretilir.

## 5. Hatırlatma senaryosu (varsayımsal, 600 oturum)

**Bu bir ölçüm değil, varsayımdır:** hatırlatma, hastaların yarısına gider ve gelmeyecek olanların belirtilen payını gelen hastaya çevirir. Gerçek etki A/B testiyle ölçülmelidir; veri setindeki `SMS_received` alanı rastgele bir deney olmadığından etkiyi tahmin etmeye uygun değildir.

| Hatırlatma etkisi | Politika | Görülen | Bekleme dk | Boşta dk | Mesai aşımı dk |
|---|---|---|---|---|---|
| %0 | sabit | 12.86 | 0.25 | 143.46 | 0.30 |
| %0 | karar ayarı | 15.50 | 1.12 | 123.60 | 0.72 |
| %10 | sabit | 13.03 | 0.24 | 142.18 | 0.31 |
| %10 | karar ayarı | 15.57 | 1.11 | 123.02 | 0.71 |
| %20 | sabit | 13.19 | 0.25 | 140.92 | 0.32 |
| %20 | karar ayarı | 15.10 | 0.88 | 126.57 | 0.70 |
| %30 | sabit | 13.32 | 0.25 | 140.02 | 0.32 |
| %30 | karar ayarı | 14.96 | 0.80 | 127.56 | 0.70 |

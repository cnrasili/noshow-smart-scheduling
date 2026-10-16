# Bekleme süresi dağılımı ve fayda–maliyet (otomatik üretilir)

Bu dosya `simulation/wait_distribution.py` tarafından üretilir; elle düzenlemeyin. Ayarlar `docs/decisions.json` dosyasındandır: 16 slot x 15 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 20 randevu isteği. 3000 eşleştirilmiş oturum; her satır bir **hastanın** beklemesidir (görülen hastalar).

## 1. Dağılım

| Grup | Hasta (toplam) | Ortalama (dk) | Ortanca (dk) | %90 (dk) | %95 (dk) | %99 (dk) | En uzun (dk) | > 5 dk (%) | > 10 dk (%) | > 15 dk (%) |
|---|---|---|---|---|---|---|---|---|---|---|
| Sabit aralık | 38374 | 0.22 | 0.00 | 0.00 | 0.73 | 6.25 | 38.94 | 1.45 | 0.38 | 0.12 |
| Karar ayarı (eşik %30, sınır 4) | 46746 | 1.14 | 0.00 | 4.75 | 7.71 | 14.16 | 68.12 | 9.45 | 2.82 | 0.82 |
| Kuralda ek randevulu slotlardaki hastalar | 15123 | 2.48 | 0.00 | 8.15 | 10.87 | 17.45 | 68.12 | 21.50 | 6.38 | 1.77 |
| Kuralda diğer hastalar | 31623 | 0.50 | 0.00 | 0.56 | 3.75 | 10.47 | 56.51 | 3.68 | 1.11 | 0.36 |

Bekleme = muayene başlangıcı − max(randevu saati, hastanın gelişi). Ortalama 15 dk sınırının çok altında olsa da önemli olan, tek tek hastaların kaç dakika beklediğidir.

- Kuralda hastaların **%0.82**'i 15 dk'dan uzun bekler.
- Bir oturumda en az bir hastanın 15 dk'dan uzun beklemesi: sabit aralıkta %1.0, kuralda %8.7 (oturum başına).
- Uzun bekleyenler ağırlıklı olarak ek randevulu slotlardaki hastalardır (üçüncü satır).

## 2. Ek hasta başına maliyet (oturum başına)

| Kalem | Sabit aralık | Karar ayarı | Fark |
|---|---|---|---|
| Görülen hasta | 12.79 | 15.58 | +2.79 |
| Toplam hasta bekleme süresi (hasta-dk) | 2.8 | 17.8 | +15.0 |
| Mesai aşımı (dk) | 0.29 | 0.50 | +0.21 |

Kural oturum başına **2.79 ek hasta** görür; bunun bedeli toplam **15.0 hasta-dakika** ek bekleme ve **0.21 dk** mesai aşımıdır. Yani ek hasta başına yaklaşık **5.4 dk** toplam bekleme ve yaklaşık **0.07 dk** mesai aşımı düşer.

Bu rakamlar simülasyon varsayımlarına bağlıdır (muayene süresi 5–10 dk aralığında bekleme artışı 0,4 ile 2,2 dk arasında değişir, `docs/IEN_DENEY_SONUCLARI.md` bölüm 4).

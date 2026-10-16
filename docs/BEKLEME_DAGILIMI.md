# Bekleme süresi dağılımı ve fayda–maliyet (otomatik üretilir)

Bu dosya `simulation/wait_distribution.py` tarafından üretilir; elle düzenlemeyin. Ayarlar `docs/decisions.json` dosyasındandır: 16 slot x 15 dk, ortalama 7.5 dk muayene (aralık 5–10 dk, değişkenlik 0.5), geç kalma sapması 4 dk, 20 randevu isteği. 3000 eşleştirilmiş oturum; her satır bir **hastanın** beklemesidir (görülen hastalar).

## 1. Dağılım

| Grup | Hasta (toplam) | Ortalama (dk) | Ortanca (dk) | %90 (dk) | %95 (dk) | %99 (dk) | En uzun (dk) | > 5 dk (%) | > 10 dk (%) | > 15 dk (%) |
|---|---|---|---|---|---|---|---|---|---|---|
| Sabit aralık | 38374 | 0.22 | 0.00 | 0.00 | 0.73 | 6.25 | 38.94 | 1.45 | 0.38 | 0.12 |
| Karar ayarı (eşik %30, sınır 4) | 46286 | 1.11 | 0.00 | 4.55 | 7.54 | 14.01 | 68.12 | 9.03 | 2.74 | 0.78 |
| Kuralda ek randevulu slotlardaki hastalar | 14288 | 2.49 | 0.00 | 8.18 | 10.90 | 17.57 | 68.12 | 21.33 | 6.46 | 1.76 |
| Kuralda diğer hastalar | 31998 | 0.49 | 0.00 | 0.47 | 3.59 | 10.40 | 56.51 | 3.53 | 1.08 | 0.35 |

Bekleme = muayene başlangıcı − max(randevu saati, hastanın gelişi). Ortalama 15 dk sınırının çok altında olsa da önemli olan, tek tek hastaların kaç dakika beklediğidir.

- Kuralda hastaların **%0.78**'i 15 dk'dan uzun bekler.
- Bir oturumda en az bir hastanın 15 dk'dan uzun beklemesi: sabit aralıkta %1.0, kuralda %8.2 (oturum başına).
- Uzun bekleyenler ağırlıklı olarak ek randevulu slotlardaki hastalardır (üçüncü satır).

## 2. Ek hasta başına maliyet (oturum başına)

| Kalem | Sabit aralık | Karar ayarı | Fark |
|---|---|---|---|
| Görülen hasta | 12.79 | 15.43 | +2.64 |
| Toplam hasta bekleme süresi (hasta-dk) | 2.8 | 17.1 | +14.2 |
| Mesai aşımı (dk) | 0.29 | 0.56 | +0.27 |

Kural oturum başına **2.64 ek hasta** görür; bunun bedeli toplam **14.2 hasta-dakika** ek bekleme ve **0.27 dk** mesai aşımıdır. Yani ek hasta başına yaklaşık **5.4 dk** toplam bekleme ve yaklaşık **0.10 dk** mesai aşımı düşer.

Bu rakamlar simülasyon varsayımlarına bağlıdır (muayene süresi 5–10 dk aralığında bekleme artışı 0,4 ile 2,2 dk arasında değişir, `docs/IEN_DENEY_SONUCLARI.md` bölüm 4).

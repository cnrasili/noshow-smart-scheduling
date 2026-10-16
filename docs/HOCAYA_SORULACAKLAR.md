# Hocaya sorulacaklar

Not defteri: soruyu, şu an ne varsaydığımızı ve cevabın neyi değiştireceğini yazdık. Cevapları "Cevap:" satırına not edin; cevap gelince `docs/decisions.json` güncellenir ve `python ml/apply_decisions.py` ile model ve sonuçlar yeniden üretilir (`docs/KARAR_LISTESI.md` bölüm 3).

## 1. Muayene süresi

**Soru:** Simülasyonda bir hastanın muayene odasında geçirdiği süreyi hangi değerle ve hangi dağılımla almalıyız? Kaynağı ne olmalı?

- **Şu an:** hasta başına 5–10 dk, ortalama 7,5 dk, değişkenlik 0,5 (log-normal). 5–10 dk ekip kararıdır; devlet hastanesi polikliniklerine dayanır.
- **Kaynak durumu:** Haber ve TBMM belgeleri bu aralığı dolaylı destekliyor (ana dallar 9 dk, cildiye 5 dk geçiyor). Hakemli ya da resmi bir ölçüm bulunamadı (`docs/KAYNAK_ARASTIRMASI.md`). Meslek örgütleri (TTB) en az 20 dk gerektiğini savunuyor.
- **Neden önemli:** Sonuçların büyüklüğünü en çok etkileyen değerlerden biri. Muayene 5 dk iken kuralın bekleme artışı +0,4 dk, 10 dk iken +2,2 dk (mesai aşımı 0,0 ve +1,1 dk).
- **Hocaya sorulacaklar:**
  - Ortalama süre olarak hangi değeri kullanmalıyız (7,5 dk makul mü)?
  - Süre dağılımı için hangi varsayım kabul edilir (log-normal, değişkenlik 0,5)?
  - Kaynak olarak ne gösterelim (Sağlık Bakanlığı verisi, bir çalışma, hastaneden alınan örnek)?
  - Gerçek ölçüm gerekiyorsa uygulamada muayene başlangıç ve bitiş saatini kaydetmeyi önerir misiniz?
- **Cevap:**

## 2. Slot süresi (randevu aralığı)

**Soru:** Takvimde randevular kaç dakikalık adımlarla verilecek? (Slot süresi muayene süresi değildir: takvimdeki her randevuya ayrılan zaman dilimidir.)

- **Şu an:** 15 dk, günde 16 slot (4 saat). Ekip bilgisine dayanıyor ("Türkiye'de genel olarak 15 dk").
- **Kaynak durumu:** Bu değeri destekleyen kaynak **bulunamadı**. Haberlere göre devlet hastanelerinde MHRS randevu aralığı 5 dk (2016'da 10 dk'dan 5 dk'ya indirilmiş, 2021 genelgesi 5 dk'da bir muayene algısından kaçınılmasını istiyor). Web uygulaması (CEN-1) 20 dk kullanıyor. Üç farklı değer var: 5, 15, 20 dk.
- **Neden önemli:**
  - Slot muayeneden uzunsa oda boş kalır: 15 dk slot ve 7,5 dk muayenede doluluk yalnızca %40–49.
  - Slot kısaysa hastalar birikir ve beklerler. Slot kısaldıkça overbooking'in kazancı da değişir (10 dk slotta +3,1 hasta ve +1,7 dk bekleme; 15 dk slotta +2,8 hasta ve +0,9 dk).
  - Slot kısaltmanın kendisi (20 slot × 12 dk) overbooking'e benzer hasta kazancı veriyor.
- **Hocaya sorulacaklar:**
  - Projede hangi slot süresini esas almalıyız (5, 10, 15, 20 dk)?
  - Devlet hastanesi mi, genel bir poliklinik mi modelliyoruz? Slot buna göre mi seçilmeli?
  - Slot süresi muayene süresinden uzun olduğunda (doluluk %40) bunu raporda nasıl yorumlamalıyız?
  - Web uygulamasındaki 20 dk'yı projenin tamamı için 15 dk'ya (ya da başka bir değere) çekmeli miyiz?
- **Cevap:**

## 3. Randevu günü sütunundaki saat bilgisi (AppointmentDay)

**Soru:** Veride `AppointmentDay` sütununda saat bilgisi yok. Proje boyunca randevulara saat girilecek mi, yoksa yalnızca gün mü kullanılacak?

- **Veride ne var (doğrulandı):** 110.527 satırın hepsinde `AppointmentDay` saati `00:00:00` (tek bir saat değeri). Yani hangi hastanın hangi saatte randevu aldığı bilinmiyor. `ScheduledDay` (randevunun alındığı an) ise saat içeriyor (06:00–21:59 arası, 37.109 farklı saat). Günde ortalama yaklaşık 4.100 randevu var (27 gün).
- **Mevcut kural:** Veri seti kuralları (`docs/features.md` → Dataset Rules): "The dataset has no appointment times and none are added." Yani saat eklememe kararı var.
- **Şu an ne yapıyoruz:** Randevu saati, oda ve slot simülasyonda üretiliyor. Bir günün randevuları rastgele muayene odası oturumlarına ve slotlara dağıtılıyor (yaklaşık 220 oturum). Web taslaklarında gerçek günlerde saat gösterilmiyor; yalnızca randevu no, yaş ve gerçek sonuç var.
- **Neden önemli:**
  - Saat olmadığı için gerçek gün içi akışı (yoğun saatler, gerçek bekleme) ölçemiyoruz; bekleme ve boşta kalma tamamen modelden gelir.
  - Saat girilirse gerçek günlük dağılım kullanılabilir; ancak veri uydurulmuş olur, bu da "veri setine sadık kal" kuralıyla çelişir.
  - Saat girilmezse sonuçlar "oturum başına simülasyon" olarak kalır ve raporda varsayım olarak belirtilmeli.
- **Hocaya sorulacaklar:**
  - Randevu saati eklemek (gerçek veriye değil, uygulama için üretilmiş) kabul edilir mi, yoksa yalnızca gün düzeyinde mi çalışmalıyız?
  - Saat eklenmeyecekse bekleme ve boşta kalma sonuçlarını "model çıktısı" olarak sunmak yeterli mi?
  - Bir günün randevularını oturumlara rastgele dağıtmak yerine başka bir yöntem (ör. randevu alınma saatine göre sıralama) önerir misiniz?
- **Cevap:**

## 4. Ek sorular (aynı konuyla ilgili)

| Soru | Şu an | Neden önemli | Cevap |
|---|---|---|---|
| Ortalama bekleme için 15 dk sınırı uygun mu? Sınır ortalama mı, hasta başına mı (ör. %95'inci yüzdelik) tanımlanmalı? | 15 dk, ortalama | Ortalama 1,1 dk iken hastaların %0,8'i 15 dk'dan uzun bekliyor (`docs/BEKLEME_DAGILIMI.md`); karar bu sınıra bağlı değil | |
| Muayene odası (oturum) sayısı nasıl belirlenmeli? Hekim adlandırılmadığı için kapasite odalarla temsil ediliyor | Günün randevularından türetilir (yaklaşık 220) | Doktor sayısı verisi yok; sonuçlar oturum başına | |
| Günlük randevu talebi (slot sayısı + 4 istek) nasıl gerekçelendirilir? | 20 istek / 16 slot | Veride yalnızca kabul edilen randevular var; talep ölçülemiyor. Talep slot sayısına eşit olunca kural hiçbir kazanç sağlamıyor | |
| Geç kalma (sapma 4 dk) için varsayım yeterli mi? | 4 dk | Veride geliş saati yok | |
| Hatırlatma etkisi nasıl ele alınmalı? | Canlı A/B testi + varsayımsal senaryo (%0–30) | `SMS_received` bir deney değil; etki ölçülemiyor | |
| Literatür ve kaynakça için hangi kaynaklar beklenir (overbooking, poliklinik çizelgeleme, Sağlık Bakanlığı verisi)? | Batool ve ark. (2020) ve ders notları | Kaynakça eksik (`docs/IEN_RAPOR_TASLAGI.md` bölüm 9) | |

## 5. Görüşme notları

Tarih: ______  Katılanlar: ______

Kararlar:

-

Yapılacaklar:

-

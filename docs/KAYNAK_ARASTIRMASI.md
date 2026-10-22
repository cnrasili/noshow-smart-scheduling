# Varsayımlar için kaynak taraması

**Durum:** 17 Ekim 2026'da web araması ile yapıldı; bulunan kaynaklar **haber, meslek örgütü ve TBMM belgeleridir, hakemli ya da resmi istatistik değildir.** Aşağıda her iddianın ne kadarının doğrulandığı ayrı yazılıdır. Rapora koymadan önce ekibin her bağlantıyı açıp elle doğrulaması gerekir. Hoca onayı yerine geçmez.

## 1. Özet

| Varsayım | Karar | Kaynak taramasının sonucu |
|---|---|---|
| Hasta başına muayene 5–10 dk (ortalama 7,5) | Ekip kararı | **Destekleniyor (dolaylı).** Devlet hastanelerinde MHRS randevu süresinin ana dallarda 9 dk, cildiyede 5 dk olduğu bildirilmiş; hekim örgütleri muayenenin birkaç dakikaya indiğini söylüyor |
| Slot (randevu aralığı) 15 dk | Ekip kararı | **Doğrulanamadı.** Bulunan kaynaklar devlet hastanelerinde MHRS randevu aralığının **5 dakika** (2016: 10 → 5 dk) olduğunu ya da öyle algılandığını yazıyor; 15 dk için kaynak çıkmadı. 15 dk başka kurumlarda (özel, üniversite) doğru olabilir |
| 15 dk ortalama bekleme sınırı | Ekip kararı | **Kaynak bulunamadı.** Sağlıkta Kalite Standartları sonuçlarında dakika cinsinden bir bekleme standardı görünmedi; resmi SKS rehberi ayrıca kontrol edilmeli |
| Aynı saate iki hasta yazma (overbooking) | — | Bir haber (13 Mayıs 2026), MHRS'de aynı saate iki hasta yazılmasını ("çifte randevu") anlatıyor; uygulama gerçekte de var |

**Çıkarım.** Simülasyon varsayımları arasında en zayıf olan **slot süresidir**. Devlet hastanesi için 5–10 dk'lık slot da savunulabilir; bu durumda talep ve kapasite ilişkisi değişir. Sonuçlar slot uzunluğuna duyarlıdır (`docs/IEN_DENEY_SONUCLARI.md` bölüm 4: 10 dk slot ile +3,1 hasta, +1,7 dk bekleme; 15 dk ile +2,8 hasta, +0,9 dk). Karar listesindeki 15 dk **geçici onaylı** kalır, kaynakla desteklenemediği raporda açıkça yazılmalıdır.

## 2. Kaynaklar ve doğrulama durumu

| # | Kaynak | Ne söylüyor | Doğrulama |
|---|---|---|---|
| 1 | [Medikal Akademi, "Sağlık Bakanlığı, hastaların muayene süresini 5 dakikaya mı indirdi?"](https://www.medikalakademi.com.tr/saglik-bakanligi-hastalarin-muayene-sueresi-5-dakikaya-indirildi/) | Bakanlığın genelgesiyle MHRS randevu aralığının 10 dk'dan 5 dk'ya indirilmesi istendiği (2016) | Arama özetinden; sayfa açılıp okunmadı |
| 2 | [Cumhuriyet, "Sağlık Bakanlığı'ndan 81 ile MHRS genelgesi: 5 dakikada bir muayene yapıldığı söylentilerinden kaçının"](https://www.cumhuriyet.com.tr/turkiye/saglik-bakanligindan-81-ile-mhrs-genelgesi-5-dakikada-bir-muayene-yapildigi-soylentilerinden-kacinin-1891361) | 2021 genelgesinde bakanlığın 5 dk'da bir muayene algısı yaratacak uygulamalardan kaçınılmasını istediği | Arama özetinden; sayfa açılıp okunmadı |
| 3 | [Bianet, "TTB: MHRS genelgesi sorunları çözmez"](https://bianet.org/haber/ttb-mhrs-genelgesi-sorunlari-cozmez-254571) ve [Bianet, "Hekimlik 5 dakikaya sığmaz"](https://bianet.org/yazi/hekimlik-5-dakikaya-sigmaz-252912) | TTB'nin uluslararası kabule göre hasta başına en az 20 dk gerektiğini savunduğu | Arama özetinden; görüştür, ölçüm değil |
| 4 | [TBMM soru önergesi (PDF)](https://cdn.tbmm.gov.tr/KKBSPublicFile/D28/Y4/T7/WebOnergeMetni/f7d920ab-b08b-437f-997a-d18e17423c52.pdf) | Ana dallar için hasta başına 9 dk, cildiye için 5 dk randevu süresi belirlendiği | **Okunamadı** (taranmış PDF); yalnızca arama özetinde; metin elle doğrulanmalı |
| 5 | [Nefes, "Hastanede çifte randevu dönemi" (13 Mayıs 2026)](https://www.nefes.com.tr/hastanede-cifte-randevu-donemi-124608) | MHRS'de aynı saate iki hasta yazılması; bir hasta "içeride sadece iki dakika kalabildim" diyor; sağlık örgütleri muayenenin birkaç dakikaya indiğini söylüyor | **Sayfa okundu**; sayı vermiyor, 5 dk aralık iddiası bu sayfada **yok** |
| 6 | [Ayaktan bakım hizmeti veren sağlık kuruluşlarında hasta memnuniyeti (YÖK Açık Bilim)](https://acikbilim.yok.gov.tr/handle/20.500.12812/212046) | Beklemeden memnun olmayan hastalarda ortalama bekleme yaklaşık 75 dk, memnun olanlarda yaklaşık 22 dk bulunmuş | Arama özetinden; yöntem ve örneklem incelenmedi |

## 3. Ne yapılmalı

1. 1, 2 ve 4 numaralı kaynakları açıp metinleri okuyun; slot ve muayene süresinin ne olduğunu netleştirin. Devlet hastanesi senaryosunda slot 5–10 dk ise `docs/decisions.json` içinde `slot_min` ve `n_slots` değiştirilip `python ml/apply_decisions.py` çalıştırılır.
2. Hoca ile slot ve 15 dk bekleme sınırını konuşun. Bekleme sınırının kararı **bağlamadığını** gösterebilirsiniz: seçilen politikada ortalama bekleme 1,1 dk, %95'inci yüzdelik 7,7 dk (`docs/BEKLEME_DAGILIMI.md`); seçilen ayar 5 dk'lık bir ortalama sınırını da karşılar. Tek hastaların %0,8'i 15 dk'dan uzun bekliyor.
3. Hakemli kaynak gerekiyorsa: poliklinik randevu çizelgeleme ve overbooking literatürü (ör. `docs/LITERATUR_INCELEMESI.md` içindeki makale) ve Sağlık Bakanlığı SKS rehberi eklenmeli; bu taramada bulunmadı.

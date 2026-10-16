# Demo ve jüri soru-cevap hazırlığı (taslak)

Sayılar `docs/IEN_RAPOR_TASLAGI.md`, `docs/MODEL_KARSILASTIRMA.md` ve `docs/IEN_DENEY_SONUCLARI.md` ile aynıdır; bunlar değişirse bu belge de güncellenmelidir. CEN tarafının uygulaması bağlandığında demo akışı birlikte prova edilmelidir `[ONAY]`.

## 1. Önerilen demo akışı (yaklaşık 8 dakika)

1. **Problem (1 dk):** hastaların yaklaşık %20'si gelmiyor; gelmeyen hasta doktorun boş kalması demek.
2. **Model (1 dk):** `docs/MODEL_KARSILASTIRMA.md` bölüm 3 tablosu. "Test kümesi zamana göre ayrıldı, dengeleme yok; AUC 0,73." Literatürdeki %95'in nedenini söyleyin (bölmeden önce dengeleme).
3. **Kural (1 dk):** "Slottaki hasta riskliyse ikinci hasta yazılır." Servis ile simülasyonun aynı kararı verdiğini gösterin: `python simulation/parity_check.py` (20.000 slot, fark 0).
4. **Simülasyon (2 dk):** `python simulation/app.py` penceresi. Bir gün seçin, "kural yok" ile eşik %30'u karşılaştırın; sayaçlarda görülen hasta ↑, boşta kalma ↓, bekleme ↑.
5. **İstatistik (1 dk):** `docs/IEN_DENEY_SONUCLARI.md` bölüm 1: eşleştirilmiş fark, güven aralığı. "2.000 oturum, aynı rastgele senaryolar."
6. **Uygulama (1 dk):** web arayüzü: hasta yalnızca müsait/dolu saati görür; karar ve risk yönetim ekranındadır (`docs/web-designs/`).
7. **Sonuç ve sınırlılıklar (1 dk):** denge eğrisi, varsayımlar, hatırlatma henüz ölçülmedi.

Hazırlık listesi:

- [ ] Demo bilgisayarında `python simulation/app.py` ve `python simulation/parity_check.py` önceden çalıştırılmış, tarayıcı/Edge yüklü.
- [ ] İnternetsiz çalışır; veri `ml/data/raw/` içinde olmalı.
- [ ] Yedek: `simulation/output/` ve `docs/` sayfalarının ekran görüntüleri.

## 2. Rakam kartı

| Konu | Değer |
|---|---|
| Veri | 110.521 randevu, 27 gün, gelmeme oranı yaklaşık %20 |
| En iyi model | Rastgele orman, test AUC 0,729 (0,721–0,736); karar ağacı 0,720; lojistik 0,658 |
| Karar ayarı (eşik %30, sınır 4): oturum başına 19,2 → 22,3 hasta | +%16; boşta −%23–24; bekleme 1,3 → 3,0 dk; mesai aşımı +0,3 dk (güncel değerler `docs/SONUC_OZETI.md`) |
| Eşik %20 | 22,4 hasta; bekleme 3,6 dk; kazanç eşik %30'dan farklı değil |
| Kısa slot (30x8) + karar ayarı | hasta sayısı yalnızca kısa slotla da +3,1; birlikte kazanç yok, bekleme +5,9 dk |
| Servis ile simülasyon | aynı karar (20.000 slot); servis ayarları güncellenecek: günlük sınır 2 → 4, muayene 12 → 7,5 dk |

## 3. Olası sorular ve yanıtlar

**Neden AUC yalnızca 0,73?** Elimizdeki özellikler (yaş, randevuya kalan gün, geçmiş vb.) gelmemeyi zayıf açıklıyor. Literatürdeki %95'i aynı veride yeniden ürettik: bölmeden önce tüm veri dengelendiği için şişiyor; sızıntısız protokolde sonuç bizimkine yakın (AUC ≈ 0,72).

**Karar ağacı neredeyse rastgele ormanla aynıysa neden orman?** (Şimdilik rastgele orman seçili; karar ağacı aday olarak hazır.) Fark küçük (0,720 ve 0,729) ve simülasyonda görülen hasta 22,3 ve 22,3. Ağaç yorumlanabilirdir; orman biraz daha yüksek PR-AUC ve düşük log-loss veriyor (0,339 ve 0,423; ağaçta 0,305 ve 0,426). Seçim ekip kararıdır (#7). Her iki aday da servisin kabul kontrollerinden geçti (`python ml/export_candidate.py`).

**Kural neden hem hasta sayısını hem beklemeyi artırıyor?** Ek hasta yalnızca ilk hasta gelmezse "bedava"dır. İkisi de gelirse ikinci hasta bekler ve bekleme sonraki slotlara taşınır. Boşta kalma azalır, bekleme ve mesai aşımı artar; ikisini birlikte raporluyoruz.

**Eşik neden %30?** Ekip kararı (#8): eşik %30, günlük sınır 4. Izgara deneyinde daha düşük eşik ya da yüksek sınır hasta sayısını artırmıyor (tavan yaklaşık 22,3); %30/4 bu tavanın %99,7'sini 3 dk beklemeyle veriyor. Kabul edilen en uzun ortalama bekleme 15 dk, karar ayarı bunun çok altında.

**Simülasyon varsayımları neye dayanıyor?** Risk ve gelme/gelmeme gerçek verilerden gelir. Muayene süresi (hasta başına 5–10 dk) Türkiye'deki devlet hastanesi poliklinik uygulamasından alınan bir ekip kararıdır; slot süresi (10 dk), geç kalma ve talep varsayımdır; duyarlılık analizinde yön değişmiyor, büyüklük değişiyor (`KPI_VE_VARSAYIM_KARSILASTIRMASI.md` bölüm 4).

**Neden Arena değil SimPy?** Hocadan izin alındı `[ONAY]`; SimPy tekrarlanabilir ve sürüm kontrollü (koddan yeniden üretilebilir).

**Veri 110 bin randevu ama tek doktor mu?** Hayır, doğrudan ölçemiyoruz: veri doktor kimliği içermiyor ve günde yaklaşık 4.100 randevu var. Ekip kararı: tek hekim kuralı uygulanmıyor (#61). Simülasyon günlük kayıtları doktor oturumlarına dağıtıyor; sonuçlar oturum başınadır, doktor sayısı varsayımdır.

**Hasta bu kuralı görüyor mu? Adil mi?** Hasta yalnızca müsait/dolu saati görür; risk ve kural yalnızca yönetimdedir. Risk yalnızca randevu anında bilinen özelliklerden hesaplanır; SMS bilgisi ve mahalle kullanılmaz. Adillik analizi (yaş ve cinsiyet gruplarında kalibrasyon) yapılmadı; yapılabilir bir sonraki adımdır.

**Hatırlatma işe yarıyor mu?** Bilmiyoruz. Veri setindeki SMS alanı rastgele bir deney değil; hatırlatan grup daha çok gelmiyor (karışıklık). Etkiyi ölçmek için serviste A/B testi var; simülasyonda yalnızca varsayımsal senaryo (%0–30 etki) çalıştırdık.

**Model gelecekte bozulursa?** Kalibrasyon kesişimi test kümesinde −0,14: gelmeme oranı eğitimden testte düştüğü için tahminler biraz yüksek. Canlıda oran düzenli izlenmeli ve model periyodik olarak yeniden kalibre edilmelidir.

**Bir sonraki adım?** Gerçek hastane verisiyle süre ve talep ölçümü, canlı A/B testi, eşik ve sınırın yönetimle belirlenmesi, adillik analizi.

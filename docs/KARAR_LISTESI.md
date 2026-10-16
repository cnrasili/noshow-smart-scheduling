# Ekip karar listesi (IEN)

Bu dosya projedeki kararların **tek kaydıdır**. Makine tarafı: `docs/decisions.json`. Bir karar değişirse ikisi birlikte güncellenir ve `python ml/apply_decisions.py` çalıştırılır; model ve sonuçlar yeniden üretilir (bölüm 3). Güncel sayılar: `docs/SONUC_OZETI.md`.

## 1. Güncel kararlar

<!-- KARARLAR:BASLA -->
| Karar | Seçim | Kim |
|---|---|---|
| 1. Model (#7) | Rastgele orman (kesin); karşılaştırma için Karar ağacı `ml/models/candidates/` altında | Ekip |
| 2. En uzun ortalama bekleme | 15 dk (poliklinik) | Ekip |
| 3. Kural ayarı (#8) | Eşik %30, günlük ek randevu sınırı 4, slot başına en çok 2 hasta | Ekip |
| 4. Muayene süresi (#9) | Ortalama 7.5 dk (aralık 5–10 dk); slot 15 dk x 16 (Türkiye'de yaygın; kaynak eklenecek) | Ekip |
| 5. Tek doktor kuralı (#61) | Uygulanmayacak; ana README kapsamı: tek bölüm, hekim adlandırılmaz ya da atanmaz | Ekip |
| 5b. Birim | Departman bazlı: `Department` = General Practice (temizlenmiş veride her satırda); hekim yok | Ekip |
| 6. Hatırlatma | Canlı A/B testi + varsayımsal senaryo | Ekip |
| 7. Teslim edilen kural | Yalnızca eşik kuralı | Ekip |
| 8. Modelin teslimi | `ml/models/` altında (seçili model); CEN `IEN` dalını çeker | IEN + CEN |
| 9. Canlıda güncel kalma | CEN2 modele API ile bağlanır | CEN2 |
| 10. Son tarih | 2026-12-16 | Ekip |
| 11. Simülasyon varsayımları ve 15 dk sınırı | Geçici olarak onaylandı (2026-10-17, IEN sorumlusu); akademik gerekçe ve kaynak (hoca onayı) sonra eklenecek | Ekip + hoca |
| 12. Uçtan uca test ve final demo | IEN görevi değildir; CEN ile birlikte, ayrı iş | CEN |
<!-- KARARLAR:BITIS -->

Yorumlar ve türetilen değerler:

- **"15k" bekleme** ifadesi **15 dakika** olarak okundu. Yanlışsa 2. satır ve `wait_limit_min` düzeltilmeli.
- **Slot 15 dk x 16 slot (4 saat):** ekip kararı (17 Ekim 2026): Türkiye'de randevu aralığı genel olarak 15 dakikadır; kaynak eklenecek. İlk taslakta 10 dk türetilmişti, geri alındı. Muayene ortalaması 7,5 dk (5–10 aralığının ortası). 10 dk'lık slot sonucu duyarlılık tablosunda ("10 dk slot, 24 slot") yer alır. Slot değişirse `docs/decisions.json` içindeki `slot_min` ve `n_slots` değişir. Web uygulaması (CEN-1) 20 dk slot kullanıyor; 15 dk ile eşitlenmesi gerekir.
- **Hatırlatma** için seçim benim önerimdir; ekip onayı gerekir.
- **Model: rastgele orman kesin** (17 Ekim 2026); CEN'e iletildi. Karar ağacı yalnızca karşılaştırma için tutuluyor (bölüm 2).
- **Kaynak taraması (17 Ekim 2026, `docs/KAYNAK_ARASTIRMASI.md`):** muayene süresi 5–10 dk haber ve TBMM belgeleriyle dolaylı destekleniyor; **15 dk slot için kaynak bulunamadı** (devlet hastanelerinde MHRS aralığının 5 dk olduğu bildiriliyor), bekleme sınırı için de kaynak yok. Kararlar geçici onaylı kalır; hoca ile konuşulmalı.
- **Varsayımlar geçici onaylı (17 Ekim 2026).** Slot, muayene süresi, gecikme, talep ve 15 dk bekleme sınırı şimdilik onaylandı; **akademik gerekçe ve kaynak (hoca onayı) sonra eklenecek.** Onay verilene kadar raporlarda "varsayım" diye anılır. Kaynak gerekenler: muayene süresi 5–10 dk, değişkenlik 0,5, geç kalma 4 dk, talep (slot + 4 istek), 10 dk slot.
- **Kapsam güncellemesi (maintainer, 17 Ekim 2026, ana `README.md`):** sistemde tek bölüm vardır, hekim adlandırılmaz ya da atanmaz; kapasite ve sonuçlar bölüme aittir. Bu, 5. kararla uyumludur. Simülasyon ve web taslaklarındaki "hekim" ifadeleri bu kapsama göre güncellenmelidir (açık iş).
- **Departman bazlı ilerleniyor (17 Ekim 2026):** temizlenmiş veride (`appointments_clean.xlsx`) her satırda `Department` = `General Practice` sütunu var (`ml/data/clean_data.py` üretir; veri setinin sütunu değildir ve model özelliği değildir). Simülasyon ve IEN belgelerindeki hekim anlatımı departman bazlıya çevrildi: "doktor" yerine **muayene odası (oturum)**; bir günün randevuları departmanın muayene odalarına dağıtılır, oda sayısı varsayımdır. Web taslakları da departman bazlıya çevrildi (hekim portalı yerine personel ekranı, "Oturum n"); taslak verileri karar ayarlarıyla (24 slot x 10 dk, 7,5 dk muayene, günlük sınır 4) yeniden üretildi.
- **Uçtan uca test ve final demo IEN görevi değildir;** CEN ile birlikte yapılacak ayrı iştir (satır 12).

## 2. Model dosyaları ve dallar

**Model:** rastgele orman, `IEN` dalında `ml/models/model.joblib` ve `feature_schema.json`. Servis bunu kurar (`python -m overbooking_service.install_model`). Karar ağacı `ml/models/candidates/decision_tree/` altında karşılaştırma için durur; silinebilir.

**Dallar** (depo artık kişi başına 3 dala izin veriyor, `.github/scripts/cleanup_branches.py`):

| Dal | Ne için |
|---|---|
| `IEN` | Ana dal: model, kodlar, belgeler. PR #62 |
| `IEN-RandomForest` | `IEN` ile aynı tutulur; CEN'e iletilen ad |
| `IEN-service-settings` | Yalnızca servis ayarı ve testleri (`overbooking-service/`): günlük sınır 4, muayene 7,5 dk. `main`'e ayrı PR |

Başka bir model dalı gerekmez: model değişirse `docs/decisions.json` içinde `model` değiştirilip `python ml/apply_decisions.py` çalıştırılır.

## 3. Bir karar değişirse

1. `docs/decisions.json` içindeki değeri değiştirin (ya da bana söyleyin).
2. `docs/KARAR_LISTESI.md` bölüm 4'te ilgili kararın notunu güncelleyin.
3. Çalıştırın:

```bash
python ml/apply_decisions.py
```

Bu komut: seçilen modelin 27 günlük tahminlerini üretir, modeli servisin kabul kontrolünden geçirip `ml/models/` altına yazar, deneyleri yeni ayarlarla yeniden çalıştırır, `docs/IEN_DENEY_SONUCLARI.md` ve `docs/SONUC_OZETI.md` dosyalarını yeniler ve yukarıdaki karar tablosunu günceller. Elle yazılmış belgelerdeki sayıları (`IEN_RAPOR_TASLAGI.md`, `DEMO_VE_JURI_HAZIRLIGI.md`) `SONUC_OZETI.md` ile karşılaştırın.

## 4. Karar kaydı (soru, karar, gerekçe)

**1. Hangi model? (#7)** *Karar: rastgele orman (kesin, 17 Ekim 2026).* Rastgele orman test AUC 0,729; karar ağacı (4 seviye) 0,720; lojistik regresyon 0,658 (`docs/MODEL_KARSILASTIRMA.md`). Lojistik elendi. İkisi de servisin kabul kontrollerinden geçti. CEN'e rastgele orman iletildi; karar ağacı yalnızca karşılaştırma için `ml/models/candidates/decision_tree/` altında.

**2. Hastalar en fazla ne kadar bekleyebilir?** *Karar: 15 dk.* Gerekçe: Türkiye'de poliklinik koşulları. Karar ayarının ortalama beklemesi bu sınırın içinde mi, `SONUC_OZETI.md` "Bekleme sınırı kontrolü" satırında yazar. Ortalama sınırın içinde olsa da bazı hastalar daha uzun bekler; tek tek hasta bekleme dağılımı ayrıca raporlanmadı.

**3. Eşik ve günlük sınır? (#8)** *Karar: eşik %30, günlük sınır 4, slot başına en çok 2 hasta.* Servisteki ayar farklı: eşik aynı (0,30), günlük sınır 2 (karar: 4) — CEN'in `config.yaml` dosyasını ve testlerini güncellemesi gerekir (bölüm 5).

**4. Muayene süresi ve talep? (#9)** *Karar: hasta başına 5–10 dk (devlet hastanesi poliklinik uygulaması), ortalama 7,5 dk.* Serviste `kpi.service_minutes` 12 (karar: 7,5). Değişkenlik 0,5, geç kalma sapması 4 dk ve talep (slot sayısı + 4 istek) ölçülmemiş varsayımlardır. 5 ve 10 dk için duyarlılık sonuçları üretilir.

**5. "Tek bölüm, tek doktor" kuralı (#61)?** *Karar: uygulanmayacak.* Simülasyon günün randevularını departmanın muayene odası oturumlarına dağıtmaya devam eder; sonuçlar oturum başınadır. Rapora "doktor sayısı varsayımdır" yazılır. Maintainer'ın 17 Ekim tarihli kapsamı (tek bölüm, hekim adlandırılmaz) bununla uyumludur; #61'in "bir doktor" kriteri bu kapsama göre güncellenmeli.

**6. Hatırlatmanın etkisi?** *Karar (benim önerim): canlı A/B testi + varsayımsal senaryo.* Senaryo (%0–30 etki) raporda açıkça "varsayım" diye etiketlidir; veri setindeki SMS alanı etki ölçmek için kullanılmaz.

**7. Hangi kural teslim edilecek?** *Karar: yalnızca eşik kuralı.* Maliyet bazlı ve havayolu kuralı raporda karşılaştırma olarak kalır.

**8. Modelin servise teslimi?** *Karar:* model `IEN` dalında `ml/models/` altındadır; CEN o dalı (birleştirildikten sonra `main`'i) çeker. Modeller servisin kullandığı scikit-learn 1.9.1 ile eğitildi (`feature_schema.json` içinde yazar); aynı koşulda test AUC'si 1.2.2 ile aynı çıktı (0,729 ve 0,720). Yeniden eğitmek için: `python ml/apply_decisions.py --model-only`; servis `python -m overbooking_service.install_model` ile kurar.

**9. Canlıda modelin güncel kalması?** *Karar:* CEN2 modele API ile bağlanarak çözer; IEN tarafında ek iş yok.

**10. Son tarih ve sorumlular?** *Karar: 16 Aralık 2026; tek kişi değil, ekip ilerletir.*

## 5. CEN tarafına iletilecekler

1. **Model:** rastgele orman `main`'de kurulu (PR #65 ve `94f9c93`: `ml/models/` ve `overbooking-service/models/`, scikit-learn 1.9.1, `random_forest-v1`); servisteki `dummy-v0` kaldırıldı.
2. **Servis ayarları:** `IEN-service-settings` dalında hazır (`config.yaml`: günlük sınır 4, `service_minutes` 7,5; README ve ilgili testler güncellendi, servis testleri 150/150 geçiyor). `main`'e ayrı PR olarak alınır.
3. **`dummy-v0` bekleyen 2 test** (`tests/test_predict_api.py`) maintainer tarafından `94f9c93` ile güncellendi.
4. **Kural kodu:** servisin `rules.decide` fonksiyonu ile simülasyonun kuralı aynı kararı veriyor (20.000 rastgele slotta fark yok); kod değişikliği gerekmez.
5. **Modele API ile bağlanma (CEN2):** özellik adları `ml/models/feature_schema.json` içindedir.

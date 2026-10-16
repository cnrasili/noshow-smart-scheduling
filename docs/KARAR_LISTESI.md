# Ekip karar listesi (IEN)

Bu dosya projedeki kararların **tek kaydıdır**. Makine tarafı: `docs/decisions.json`. Bir karar değişirse ikisi birlikte güncellenir ve `python ml/apply_decisions.py` çalıştırılır; model ve sonuçlar yeniden üretilir (bölüm 3). Güncel sayılar: `docs/SONUC_OZETI.md`.

## 1. Güncel kararlar

<!-- KARARLAR:BASLA -->
| Karar | Seçim | Kim |
|---|---|---|
| 1. Model (#7) | **Bekliyor** (iki dal: IEN-RandomForest, IEN-DecisionTree) | Ekip |
| 2. En uzun ortalama bekleme | 15 dk (poliklinik) | Ekip |
| 3. Kural ayarı (#8) | Eşik %30, günlük ek randevu sınırı 4, slot başına en çok 2 hasta | Ekip |
| 4. Muayene süresi (#9) | Ortalama 7.5 dk (aralık 5–10 dk); slot 10 dk x 24 (türetilmiş) | Ekip |
| 5. Tek doktor kuralı (#61) | Uygulanmayacak | Ekip |
| 6. Hatırlatma | Canlı A/B testi + varsayımsal senaryo | Ekip |
| 7. Teslim edilen kural | Yalnızca eşik kuralı | Ekip |
| 8. Modelin teslimi | `ml/models/` altında, seçilen dalda; CEN o dalı çeker | IEN + CEN |
| 9. Canlıda güncel kalma | CEN2 modele API ile bağlanır | CEN2 |
| 10. Son tarih | 2026-12-16 | Ekip |
<!-- KARARLAR:BITIS -->

Yorumlar ve türetilen değerler:

- **"15k" bekleme** ifadesi **15 dakika** olarak okundu. Yanlışsa 2. satır ve `wait_limit_min` düzeltilmeli.
- **Slot 10 dk x 24 slot (4 saat)** karar listesinde yoktu; "hasta başına 5–10 dk" kararından **türetildi**. Muayene ortalaması 7,5 dk alındı (aralığın ortası). 15 dk'lık slotla sonuç, duyarlılık tablosunda ("15 dk slot, 16 slot") yer alır. Ekip farklı slot isterse `docs/decisions.json` içindeki `slot_min` ve `n_slots` değişir.
- **Hatırlatma** için seçim benim önerimdir; ekip onayı gerekir.
- **Model seçimi bekliyor:** iki dal hazır, ekip seçince diğeri silinebilir (bölüm 2).

## 2. Dallar (model seçimine göre)

| Dal | `docs/decisions.json` → `model` | Ne içerir |
|---|---|---|
| `IEN` | boş (`null`) | Ortak kod, belgeler ve kararlar; model dosyası yok |
| `IEN-RandomForest` | `random_forest` | Rastgele orman: `ml/models/` altında model, bu modelin risk tahminleriyle üretilmiş sonuçlar |
| `IEN-DecisionTree` | `decision_tree` | Karar ağacı: aynı yapı, karar ağacıyla |

Kod iki dalda aynıdır; yalnızca `model` değeri, `ml/models/` dosyaları ve üretilen sonuç belgeleri farklıdır. Karar verilince seçilen dal `IEN`'e birleştirilir, diğeri silinir.

## 3. Bir karar değişirse

1. `docs/decisions.json` içindeki değeri değiştirin (ya da bana söyleyin).
2. `docs/KARAR_LISTESI.md` bölüm 4'te ilgili kararın notunu güncelleyin.
3. Çalıştırın:

```bash
python ml/apply_decisions.py
```

Bu komut: seçilen modelin 27 günlük tahminlerini üretir, modeli servisin kabul kontrolünden geçirip `ml/models/` altına yazar, deneyleri yeni ayarlarla yeniden çalıştırır, `docs/IEN_DENEY_SONUCLARI.md` ve `docs/SONUC_OZETI.md` dosyalarını yeniler ve yukarıdaki karar tablosunu günceller. Elle yazılmış belgelerdeki sayıları (`IEN_RAPOR_TASLAGI.md`, `DEMO_VE_JURI_HAZIRLIGI.md`) `SONUC_OZETI.md` ile karşılaştırın.

## 4. Karar kaydı (soru, karar, gerekçe)

**1. Hangi model? (#7)** *Bekliyor.* Rastgele orman test AUC 0,729; karar ağacı (4 seviye) 0,720; lojistik regresyon 0,658 (`docs/MODEL_KARSILASTIRMA.md`). Lojistik elendi. İkisi de servisin kabul kontrollerinden geçti. Seçim için iki dal açıldı; hangisinin çekileceği CEN'e iletilecek.

**2. Hastalar en fazla ne kadar bekleyebilir?** *Karar: 15 dk.* Gerekçe: Türkiye'de poliklinik koşulları. Karar ayarının ortalama beklemesi bu sınırın içinde mi, `SONUC_OZETI.md` "Bekleme sınırı kontrolü" satırında yazar. Ortalama sınırın içinde olsa da bazı hastalar daha uzun bekler; tek tek hasta bekleme dağılımı ayrıca raporlanmadı.

**3. Eşik ve günlük sınır? (#8)** *Karar: eşik %30, günlük sınır 4, slot başına en çok 2 hasta.* Servisteki ayar farklı: eşik aynı (0,30), günlük sınır 2 (karar: 4) — CEN'in `config.yaml` dosyasını ve testlerini güncellemesi gerekir (bölüm 5).

**4. Muayene süresi ve talep? (#9)** *Karar: hasta başına 5–10 dk (devlet hastanesi poliklinik uygulaması), ortalama 7,5 dk.* Serviste `kpi.service_minutes` 12 (karar: 7,5). Değişkenlik 0,5, geç kalma sapması 4 dk ve talep (slot sayısı + 4 istek) ölçülmemiş varsayımlardır. 5 ve 10 dk için duyarlılık sonuçları üretilir.

**5. "Tek bölüm, tek doktor" kuralı (#61)?** *Karar: uygulanmayacak.* Simülasyon günün randevularını doktor oturumlarına dağıtmaya devam eder; sonuçlar oturum başınadır. Rapora "doktor sayısı varsayımdır" yazılır. Maintainer'a bu kararın bildirilmesi gerekir (#61'e yorum).

**6. Hatırlatmanın etkisi?** *Karar (benim önerim): canlı A/B testi + varsayımsal senaryo.* Senaryo (%0–30 etki) raporda açıkça "varsayım" diye etiketlidir; veri setindeki SMS alanı etki ölçmek için kullanılmaz.

**7. Hangi kural teslim edilecek?** *Karar: yalnızca eşik kuralı.* Maliyet bazlı ve havayolu kuralı raporda karşılaştırma olarak kalır.

**8. Modelin servise teslimi?** *Karar:* kararlar bittikten sonra model üretilir; hangi dalın çekileceği CEN'e iletilir. Model `ml/models/` altındadır; servis `python -m overbooking_service.install_model` ile kurar.

**9. Canlıda modelin güncel kalması?** *Karar:* CEN2 modele API ile bağlanarak çözer; IEN tarafında ek iş yok.

**10. Son tarih ve sorumlular?** *Karar: 16 Aralık 2026; tek kişi değil, ekip ilerletir.*

## 5. CEN tarafına iletilecekler

1. **Hangi dalı çekecekler:** seçim yapılana kadar `IEN-RandomForest` ya da `IEN-DecisionTree` (ikisi de `ml/models/` altında hazır model içerir).
2. **Servis ayarları** (`overbooking-service/config.yaml`), IEN dokunmadı:
   - `overbooking.daily_overbook_limit`: 2 → **4**
   - `kpi.service_minutes`: 12 → **7,5**
   - Bu değerleri sınayan testler güncellenmeli (`tests/test_booking_api.py`, `tests/test_rules.py`, `tests/test_kpi.py`). Kontrol: `python simulation/parity_check.py` farkları yazdırır.
3. **Kural kodu:** servisin `rules.decide` fonksiyonu ile simülasyonun kuralı aynı kararı veriyor (20.000 rastgele slotta fark yok); kod değişikliği gerekmez.
4. **Modele API ile bağlanma (CEN2):** özellik adları `ml/models/feature_schema.json` içindedir.

# Anlatım: Poliklinik Randevu Sistemi, Gelmeme Tahmini ve Akıllı Randevu Planlama

**Bu belge ne için?** Projeyi hiç bilmeyen birine, ya da bir hafta sonra bu projeye geri dönen kendinize, her şeyi baştan anlatır: problem ne, ne yaptık, **neden öyle yaptık**, ne zaman fikir değiştirdik, hangi hatayı aldık ve nasıl düzelttik. Sunumda hocanın soracağı "bu fonksiyonu neden kullandınız?" türü sorulara hazırlık için kod ve formül seviyesine kadar iner.

**Kapsam.** Deponun ilk commit'inden (26 Eylül 2026) bugüne kadar olanlar. Ayrıntıyı en çok **IEN tarafına** (tahmin modeli, kurallar, simülasyon, istatistik) verdim, çünkü sunumun ve sorulacak soruların merkezi orası. Bilgisayar mühendisliği (CEN) tarafı kısa ama eksiksiz bir harita olarak var. Sayıların hepsi `docs/` altındaki üretilen raporlardan alındı; sayı değişirse kaynak dosya yazılı.

**Nasıl okunur?**

| Amaç | Bölümler |
|---|---|
| Projeyi 5 dakikada anlamak | 1, 2, 12 |
| Sunuma hazırlanmak | 1–10, 14, 15 (sorular) |
| "Neden değiştirdik?" sorusuna bakmak | 11 (karar günlüğü), 12 (hatalar) |
| Bir fonksiyonu savunmak | 8 (simülasyon kodu), 7 (model), 5–6 (formüller) |
| Her commit'in ne yaptığını görmek | 3 (zaman çizelgesi), Ek A (tüm commit'ler) |
| Komutları çalıştırmak | 16, `docs/TEKRAR_URETIM.md` |

---

## 1. Proje ne yapıyor? (Bir sayfada)

**Problem.** Poliklinik randevularına hastaların yaklaşık **%20'si gelmiyor** (veri setinde %20,19). Gelmeyen hasta, muayene kapasitesinin boş kalması demek. Çözümün kolay hâli "her slota iki hasta yaz" (overbooking): ama herkes gelirse hastalar bekler, doktor (bizim sistemde muayene odası) fazla mesai yapar.

**Fikir.** Her randevu için "bu hasta gelmez mi?" olasılığını tahmin et. Sadece **gelmeme riski yüksek** hastanın slotuna ikinci hasta yaz. Sonucu, her slota tek hasta yazan klasik takvimle (**sabit aralıklı randevu**) karşılaştır.

**Hat (pipeline).**

```
Kaggle verisi → temizle → gelmeme olasılığı modeli (RF) → overbooking kuralı (eşik %30)
        → randevu uygulaması (hasta/departman/yönetim) → KPI'lar
                      ↑
        SimPy simülasyonu: kural ile kuralsız takvimi aynı hastalarla yarıştır
```

**Roller.** İş bölümü (depoda `.github/CODEOWNERS` ve issue etiketleriyle):

| Rol | Kim | Ne yaptı |
|---|---|---|
| PM (proje yöneticisi) | cnrasili (PR birleştirmeleri "Caner Aşılıoğlu" adıyla görünür) | Depo iskeleti, Docker, CI, PR/issue kuralları, overbooking servisi, admin servisi, veri kuralları |
| CEN-1 | Davut can cüci (cen1 dalı) | Web uygulaması: hasta ve doktor ekranları, giriş, takvim |
| CEN-2 | cnrasili (cen2 dalları) | Overbooking servisi, mesajlar, A/B testi, admin paneli, KPI uç noktaları |
| **IEN** | **Hazar İkizler (siz)** | **Formüller, kurallar, veri temizliği, modeller, SimPy simülasyonu, deneyler, web taslakları, belgeler** |

**Sonuçta ne bulduk? (Özet)**

1. Gelmeme olasılığını tahmin etmek **zor**: rastgele orman (RF) test kümesinde ROC-AUC **0,729** (0,5 şans, 1 mükemmel). Lojistik regresyon 0,658, karar ağacı 0,720. Literatürdeki "%95 doğruluk" iddiası veri sızıntısından geliyor (Bölüm 7.8); doğru protokolle AUC ≈ 0,72, bizimkiyle aynı.
2. Karar ayarı **eşik %30, günlük ek randevu sınırı 4, slot başına en çok 2 hasta**, bir oturumda (16 slot × 15 dk) sabit aralığa göre ortalama **+2,8 hasta (+%22)**, boşta kalma **−20 dk**; bedeli ortalama bekleme **+0,9 dk** (0,2 → 1,1 dk) ve mesai aşımı **+0,2 dk**.
3. Ortalama küçük olsa da dağılım uzun kuyruklu: hastaların **%9,5'i 5 dk'dan**, **%0,8'i 15 dk'dan** uzun bekliyor.
4. Etki **muayene süresine** ve **gelmeme oranına** çok duyarlı. Muayene 10 dk'ya çıkarsa bekleme artışı +2,2 dk olur; gelmeme oranı %30 düşerse kural neredeyse hiç tetiklenmez.
5. Kapasite zaten bol: 15 dk slotta 7,5 dk muayene doluluğu kuralsız %40'ta bırakıyor. Slotu kısaltmak da benzer hasta kazancı veriyor (20 slot × 12 dk: +3,2 hasta). Dürüst sonuç: overbooking **bir** yöntemdir, tek yöntem değil.

---

## 2. Sözlük (sunumda lazım olacak terimler)

| Terim | Anlamı | Nerede kullanıldı |
|---|---|---|
| **No-show (gelmeme)** | Randevusuna gelmeyen hasta. Hedef değişkenimiz (`NoShow` = 1) | Her yer |
| **Lead time (`LeadDays`)** | Randevunun alındığı gün ile randevu günü arasındaki gün farkı. En güçlü özellik | Model |
| **Slot** | Takvimde bir randevuya ayrılan zaman dilimi (bizde 15 dk) | Simülasyon |
| **Muayene süresi** | Hastanın odada gerçekten geçirdiği süre (ortalama 7,5 dk). Slot ile karıştırılmaz | Simülasyon |
| **Oturum (session)** | Bir muayene odasının yarım gün çalışması: 16 slot, 4 saat | Simülasyon |
| **Overbooking** | Aynı slota ikinci hasta yazmak | Kural |
| **Eşik kuralı** | Slottaki hastanın gelmeme riski ≥ eşikse ikinci hasta yazılır | Servis ve simülasyon |
| **AUC (ROC-AUC)** | Rastgele seçilen bir gelmeyen hastaya, rastgele seçilen bir gelen hastadan daha yüksek risk verme olasılığı. 0,5 = şans | Model |
| **Brier skoru** | Tahmin olasılığı ile gerçeğin kare farkının ortalaması (küçük iyi) | Model |
| **Log-loss** | Olasılık tahminlerinin doğruluğunu ölçen puan (küçük iyi); hiperparametre seçerken kullandık | Model |
| **Kalibrasyon** | "%30 diyorsam gerçekten %30'u gelmiyor mu?" Overbooking riski olasılık olarak kullandığı için AUC'den bile önemli | Model |
| **Kalibrasyon kesişimi / eğimi** | Kalibrasyonun iki sayıyla özeti: kesişim 0, eğim 1 ise mükemmel | Model |
| **Precision / Recall / F1** | İşaretlenen hastaların ne kadarı gerçekten gelmedi / gelmeyenlerin ne kadarını yakaladık / ikisinin dengesi | Model |
| **Ortak rastgele sayılar (CRN)** | Karşılaştırılan politikalara **aynı** hastaları, aynı gelme/gelmeme ve süreleri vermek: fark şanstan değil politikadan gelir | Simülasyon |
| **Eşleştirilmiş fark** | Aynı oturumda iki politikanın farkı; güven aralığı bunun ortalaması üzerinden | Simülasyon |
| **Cohen d_z** | Eşleştirilmiş farkın etki büyüklüğü: ortalama fark ÷ farkın standart sapması | Simülasyon |
| **Pareto** | Başka hiçbir ayarın "her ölçüde aynı ya da daha iyi, en az birinde daha iyi" olmadığı ayarlar | Deney |
| **Zamansal sızıntı** | Modelin, tahmin ettiği güne ait ya da sonraki bilgiyi eğitimde görmesi | Model |
| **`SMS_received`** | Randevudan sonra oluşan bilgi; kullanılırsa sızıntı | Model |
| **Department** | Tüm satırlarda `General Practice`; sistem tek bölümdür | Veri |

---

## 3. Zaman çizelgesi: ilk commit'ten bugüne

Tarihler deponun commit zamanlarıdır (yerel saat). Kısaltma: **PM** = cnrasili, **CEN-1** = Davut can cüci, **IEN** = Hazar İkizler. Tam liste Ek A'da.

### Faz 1 · 26 Eylül – 1 Ekim: İskelet ve servisler (PM)

| Tarih | Commit | Ne oldu |
|---|---|---|
| 26 Eyl 00:40 | `16723f6` | **İlk commit:** depo oluştu |
| 26 Eyl | `67ca17a`, `026baac`, `08b235b` | Teknoloji yığını (FastAPI, React, PostgreSQL, Docker), kapsam metni, Docker taşınabilirliği |
| 26 Eyl | `048a0c1` | Tahmin uç noktası + **yer tutucu model (`dummy-v0`)**: model gelene kadar sistem çalışsın diye |
| 26 Eyl | `99dc7d5`, `c4f8ff0` | Model doğrulama ve `export_model` yardımcısı (modelin servise teslim biçimi); özellik listesi "öneri" olarak işaretlendi |
| 1 Eki | `b870a7f` | **Slot bazlı overbooking kural motoru** ve `/booking-decision` uç noktası (eşik kuralının servis tarafı: `rules.decide`) |
| 1 Eki | `0572dd2` | Onay ve hatırlatma mesajları, zamanlanmış gönderim |

*Neden önce servis?* Model daha yoktu; PM diğer parçaların çalışabilmesi için sözleşmeleri (API, özellik listesi, teslim biçimi) önce yazdı. Bu yüzden IEN tarafında yazdığımız kural, serviste zaten var olan kuralla **aynı kararı vermek zorundaydı** (Bölüm 13'te kanıtı var).

### Faz 2 · 2 Ekim: IEN günü, formüllerden simülasyona (Hazar)

Tek günde (14:49–19:45) IEN'in temeli atıldı:

| Saat | Commit | Ne oldu |
|---|---|---|
| 14:49–15:01 | `bede9fd`, `421e964` | `docs/formulas/` yapısı; **tahmin dersinden formüller** (`forecast.md`) |
| 15:12–15:19 | `c5965ea`, `c128111`, `1c1af6d`, `72b758b`, `ef87ecc` | **Gelme olasılığı kuralları R1–R3**, resmî şartname biçimine çevrildi; **R4** (birleşik "soğuk başlangıç" kuralı); örnek hesapta yuvarlama düzeltmeleri |
| 15:21 | `e3b4da8` | **Maliyet bazlı overbooking kuralı** (havayolu mantığından uyarlandı) = R5 |
| 15:56 | `bb6e673` | **İlk SimPy simülasyonu:** sabit, eşik ve maliyet politikaları |
| 15:59 | `73100c8` | Grafikler + **hata düzeltmesi:** muayene randevu saatinden önce başlıyordu (negatif bekleme) |
| 16:02–16:13 | `7b7c815`, `11e5bfd`, `5256f02` | Politikaları adım adım karşılaştırma (value ladder), KPI kartlı pano, **3 randevu şablonu ve kazanan** |
| 16:50 | `91c1986` | `docs/formulas` IEN'e birleşti; **veri temizleme ve rapor betikleri** (`ml/`) |
| 16:55–17:05 | `d3321cc`, `e5f839d`, `e6cecb8`, `ad86649` | İstatistik, olasılık ve **istatistiksel kalite kontrol** formülleri ve veriyle kontrolleri; durum özeti; simülasyon için risk dosyası |
| 17:53–18:10 | `bced142`, `cc49531`, `60c09b2`, `5dff878`, `20ba0df` | `main.py` (tek komutla tüm adımlar), **canlı animasyon + SimPy olay günlüğü**; gerçek randevu kayıtlarıyla canlı gün |
| 18:20–19:14 | `753be45`, `d836ec2`, `37e1617`, `8258799`, `be9e69b` | **Tüm günün gerçek randevuları** (her kayıt), gün gün tablo, 27 günün hepsinde şablon karşılaştırması, **her gün için örneklem dışı risk**, sonuç sayfası kümeleri |
| 19:45 | `3a8e126` | Her sayfaya geri düğmesi |

*Bu günün mantığı:* önce **kural (matematik)**, sonra **simülasyon (kural işe yarıyor mu?)**, sonra **gerçek veriyle** doğrulama. Sıralama kasıtlıydı: formülü yazmadan simülasyon yazmak, neyi simüle ettiğini bilmemek olurdu.

### Faz 3 · 3 – 12 Ekim: Entegrasyon (PM, CEN-1, CEN-2)

- **3 Eki:** IEN çalışması `integration/core-tables-and-ien` PR'ıyla (#2) ana dala girdi. PM lint (ruff) ve pandas 3 uyumu için temizlik yaptı (`7602097`).
- **3–12 Eki (CEN-1):** veritabanı tabloları, güvenlik tetikleyicileri (slot kapasitesi), hesap ve oturum tabloları, giriş, slot üretimi, hasta ve doktor ekranları, demo veri, "şehir hastanesi" arayüzü, giriş sınırlama ve güvenlik başlıkları.
- **4–12 Eki (CEN-2):** hastadan veri okuma, hatırlatma **A/B ataması** ve gelmeme özeti, KPI uç noktası, `admin-service` (güvenli giriş, KPI ekranı, Türkçe arayüz), bağımlılık sabitleme, CI'da PostgreSQL testleri, model kurulum komutu (`install_model`), mesaj kurtarma işi.
- **12 Eki (`7479654`):** PM `main`'i `IEN` dalına birleştirdi.

### Faz 4 · 15 Ekim: Veri kuralları (PM)

PM yeni **veri seti kurallarını** yazdı (`docs/features.md` → Dataset Rules): tek veri kaynağı Kaggle seti; hastalar `PatientId` ile; **uydurma hasta ya da kayıt yok**; ek sütunlar (bölüm, hekim) her satırda aynı değerde; randevu saati **eklenmez**; temizlikte 6 satır atılır. Veri depoya eklendi (`3d9b99f`), veritabanına yüklendi (`81deb71`). Bu kurallar IEN'in simülasyon varsayımlarını doğrudan etkiledi (issue #61).

### Faz 5 · 16 Ekim: IEN genişlemesi (Hazar)

| Saat | Commit | Ne oldu |
|---|---|---|
| 14:53 | `1550830` | **Literatür incelemesi** (Batool ve ark. 2020), makalenin sonuçlarının yeniden üretimi (`paper_replication.py`) ve makalenin politikasının simülasyona eklenmesi |
| 15:03–16:16 | `f80bcf9`, `d4f6567`, `3a58ae8`, `d9cf102`, `68c3c04` | **Etkileşimli simülasyon:** önce karmaşık, sonra "bir doktorun günü" olarak sadeleştirildi (geri bildirimle), her ayar değişince otomatik hesap, tek ekrana sığma, iki sütunlu ayar paneli, masaüstü uygulama gibi pencere |
| 16:20–16:28 | `500ed61`, `9696e56` | Uzak dalla birleşme (4 çakışma çözüldü), `main` birleşimi |
| 19:01 | `cf8773b` | **İki web arayüz taslağı** (hasta/departman/yönetim; risk ve kural yalnızca yönetimde) |
| 23:16 | `a29bb90` | **Model karşılaştırması** (LR/RF/DT, sızıntısız protokol), eşleştirilmiş deneyler, **karar listesi**, `apply_decisions.py` |
| 23:41–23:47 | `3b9ca01`, `63f1962` | RF seçili, iki model aynı dalda; modeller **scikit-learn 1.9.1** ile yeniden eğitildi |
| 23:57 | `4c435a2` | Zamansal sızıntı kontrolü, servis uyum raporu, temiz ortam sonucu |

### Faz 6 · 17 Ekim: Kapsam daralması ve teslim (Hazar + PM)

| Saat | Commit | Ne oldu |
|---|---|---|
| 00:33 | `6d5f48e` (PM) | **Kapsam daraldı:** tek bölüm, **hekim yok** |
| 00:38 | `641ffd4` | Rastgele orman kesin; varsayımlar geçici onaylı |
| 00:49 | `3b7382e` | Temizlenmiş Excel'e `Department = General Practice` sütunu |
| 01:03–01:12 | `deb90bd`, `6e3fead` | Simülasyon, belgeler ve web taslakları **"hekim"den "muayene odası/departman"a** çevrildi |
| 01:25–01:31 | `c82514d`, `f1436c0`, `ab983ac`, `94f9c93` | **Model teslimi (PR #65):** RF `ml/models/` altında; özellik listesi "agreed"; PM modeli serviste kurdu, `dummy-v0` kalktı |
| 01:26 | `50cba11` | **Slot 15 dk**, simülasyon varsayılanları kararlara çekildi |
| 02:04 | `51d0505` | Bekleme dağılımı, protokol denetimi, alt grup yorumu, kaynak taraması |
| 02:35–02:39 | `77dd6bf`, `c40f714`, `a71aa39` | Hocaya sorular, tekrar üretim kılavuzu, `main` birleşimi |

Neden değişti, neyi hatalı yaptık: Bölüm 11 ve 12.


## 4. Veri: ne var, neyi temizledik, neden

### 4.1 Veri seti

**Kaggle "Medical Appointment No Shows"** (`KaggleV2-May-2016.csv`): Brezilya'da bir bölgenin kamu sağlık randevuları, **110.527 satır**, **29 Nisan – 8 Haziran 2016** arası **27 randevu günü**, günde ortalama yaklaşık **4.100 randevu**. Ana sütunlar:

| Sütun | Anlamı |
|---|---|
| `PatientId`, `AppointmentID` | Hasta ve randevu numarası |
| `ScheduledDay` | Randevunun **alındığı an** (tarih + saat) |
| `AppointmentDay` | Randevu günü. **Saat bilgisi yok:** tüm satırlarda `00:00:00` (doğruladık) |
| `Gender`, `Age` | Cinsiyet ve yaş |
| `Neighbourhood` | Mahalle |
| `Scholarship` | Brezilya sosyal yardım programına kayıtlı mı (0/1) |
| `Hipertension`, `Diabetes`, `Alcoholism`, `Handcap` | Sağlık durumları (kaynakta yazım hatalı sütun adları) |
| `SMS_received` | Hastaya SMS gitti mi |
| `No-show` | `Yes` = gelmedi (hedef) |

**Veride olmayanlar (bütün tasarımı etkiledi):** randevu **saati**, **doktor** ve **bölüm**. Bu yüzden hekim bazlı bir simülasyon gerçek veriden beslenemez; kapasite, oda ve slot **simülasyonda üretilir** (Bölüm 8).

### 4.2 Temizlik (`ml/data/clean_data.py`)

| Adım | Ne yapıyoruz | Neden |
|---|---|---|
| Sütun adları | `Hipertension`→`Hypertension`, `Handcap`→`Handicap`, `No-show`→`NoShow` | Yazım hatalarını sabitlemek; kodda tutarlı adlar |
| Hedef | `NoShow = 1` gelmedi, `ShowUp = 1 − NoShow` | Model 1 = gelmedi'yi öğrenir; kurallar "gelme olasılığı" ile çalışır |
| Metin | `Gender` ve `Neighbourhood` büyük harf, boşluk temizliği | Aynı değerin farklı yazımını tek yapmak |
| `LeadDays` | `AppointmentDay` tarihi − `ScheduledDay` tarihi (gün) | Randevu **alındığı anda** bilinen tek zaman bilgisi |
| `Weekday` | Randevu gününün haftanın günü (0 = Pazartesi) | Randevu alınırken bilinir |
| `AgeBand` | 18 / 25 / 35 / 55 sınırlarıyla 5 bant | R3 kuralı için |
| **Atılan satırlar** | Yaş < 0 (1 satır), yaş > 120, randevu **alınma gününden önce** (5 satır), tekrar eden `AppointmentID` | Fiziksel olarak mümkün olmayan kayıtlar. Sonuç: **110.527 → 110.521 satır** |
| Geçmiş özellikleri | `PriorApptCount`, `PriorNoShowCount` (aşağıda) | Hastanın geçmiş davranışı en güçlü bireysel işaret |
| `Department` | Her satırda `General Practice` | 17 Ekim'de kapsam tek bölüm oldu; veri setinin gerçek sütunu değil, **projeye eklenmiş sabit** sütun; modele girmez |

**Geçmiş özelliklerinin sızıntısız hesabı** (en kritik kısım): bir randevu için "hastanın önceki kaç randevusu var, kaçına gelmedi" sorulur. Doğrusu: **bu randevunun alındığı günden (booking date) önce randevu günü olan** randevular sayılır. Kod: her hasta için randevu günleri sıralanır, `np.searchsorted(randevu_günleri, alınma_günü, side="left")` ile "alınma gününden kesin küçük" olanların sayısı bulunur, gelmeme sayısı kümülatif toplamdan okunur. **Neden önemli:** randevu alındığında henüz gerçekleşmemiş bir sonucu (gelecekteki gelmeme) modele vermek, hedefin sızması olur. 3.000 rastgele satırı bu kuraldan bağımsız yeniden hesaplayarak doğruladık: 0 fark.

**Çıktı:** `ml/data/processed/appointments_clean.xlsx` (sayfalar: `data`, `cleaning_log`, `columns`, `removed_rows`). Bu klasör `.gitignore`'dadır; herkes `clean_data.py` ile yeniden üretir.

### 4.3 Veride bulduklarımız

- Gelmeme oranı **%20,19**; son hafta %18,5'e düşüyor (eğitim döneminde %20,6): oran **kayıyor**, model biraz fazla risk veriyor (Bölüm 7.6).
- Gelmemeyi en çok **lead time** belirliyor: randevu 15 gün ve daha önce alınmışsa gelmeme %34, 2 gün ve daha yakınsa %9. Bu ilişki **doğrusal değil**, lojistik regresyonun RF'ye yenilmesinin ana sebebi.
- Gençler (%23) yaşlılardan (%16) daha çok gelmiyor. Cinsiyetin etkisi çok küçük (0,6 puan); adil olmadığı ve işe yaramadığı için kurallarda kullanmadık.
- Hastaların yalnızca bir kısmının geçmişi var; test kümesinde randevuların %54'ü "yeni hasta" (geçmişi yok), %46'sı tekrar gelen.

### 4.4 Neden bazı sütunları kullanmadık?

| Sütun | Karar | Gerekçe |
|---|---|---|
| `SMS_received` | **Kullanılmaz** | SMS, randevu alındıktan **sonra** gider; randevu alındığı anda bilinmeyen bilgi = sızıntı. Ayrıca SMS alanlar zaten daha riskli hasta (grup rastgele değil), bu yüzden etkisi veriden ölçülemez (Bölüm 10.6) |
| `Neighbourhood` | Kullanılmaz | Uygulamada karşılığı yok (hasta adresi tutulmuyor) |
| `Gender` | Modelde var, kurallarda sadece R2 yerine geçici | Etkisi çok küçük; adillik riski |
| `PatientId`, `AppointmentID` | Özellik değil, anahtar | Kimlik tahmin için anlamlı değil; geçmişi hesaplamak için lazım |

---

## 5. Gelme olasılığı kuralları R1–R4 (`docs/formulas/rules.md`)

**Amaç.** Model yokken (ya da modelin cevap veremediği "soğuk başlangıç" durumunda) gelmeme olasılığını **kural tabanlı** hesaplamak. Aynı zamanda modeller için **referans (taban) çizgisi**.

**Ortak tahminci (CE).** Bir grup $g$ için (hasta, bölüm, yaş bandı) geçmişte $n_g$ randevu ve $s_g$ gelen varsa **düzeltilmiş gelme olasılığı**:

$$\hat{s}_g = \frac{s_g + k\,\bar{s}}{n_g + k}$$

$\bar{s}$ genel gelme oranı (eğitim döneminden), $k$ "sanal gözlem" sayısı (varsayılan **5**). **Neden düzeltme (smoothing)?** Tek randevusu olup gelmemiş hastaya "%100 gelmez" dememek için: az veriyle tahmin genel orana çekilir, veri çoğaldıkça gerçek orana yaklaşır. $n_g=0$ ise çıktı tam olarak $\bar{s}$'dir (kural CE-4).

| Kural | Grup | Not |
|---|---|---|
| **R1** | Hasta geçmişi (`PatientId`) | En güçlü bireysel işaret. İsim anahtar olarak **kullanılmaz** (benzersiz değil, kişisel veri) |
| **R2** | Bölüm | Kaggle verisinde bölüm yok; geçici olarak **cinsiyet** denendi, etkisi önemsiz; sonra tek bölüm kararıyla anlamsız oldu |
| **R3** | Yaş bandı (A0 <18, A1 18–24, A2 25–34, A3 35–54, A4 ≥55) | Bantlar çakışmaz ve her geçerli yaşı kapsar; geçersiz yaş genel orana düşer |
| **R4** | R1–R3'ün birleşimi | **Yeni hasta** için de olasılık verebilen tek kural |

**R4'ün mantığı (iki adım).**

1. **Bağlam önceliği:** bölüm ve yaşın genel orandan sapmaları **log-odds** ölçeğinde toplanır:
   $z_0 = \operatorname{logit}(\bar{s}) + [\operatorname{logit}(\hat{s}_D)-\operatorname{logit}(\bar{s})] + [\operatorname{logit}(\hat{s}_A)-\operatorname{logit}(\bar{s})]$, $\pi_0 = 1/(1+e^{-z_0})$.
   *Neden log-odds?* Olasılıkları doğrudan toplamak 1'i aşabilir; log-odds ölçeğinde toplama her zaman geçerli bir olasılık verir. Bu aynı zamanda lojistik regresyonun çalışma biçimidir. **Varsayım:** bölüm ve yaş birbirinden bağımsız etki eder; kalibrasyon testiyle sınanır.
2. **Hasta güncellemesi:** hastanın kendi geçmişi, bağlam önceliğine doğru düzeltilir:
   $\hat{s}_{R4} = (s_P + k_P\pi_0)/(n_P + k_P)$. Geçmişi çok olan hastada bağlamın etkisi azalır; hiç geçmişi olmayan hastada tam $\pi_0$ çıkar.

**Sonuç (`MODEL_KARSILASTIRMA.md`).** R4'ün test AUC'si **0,577** (şansın biraz üstü): bu beklenen bir şeydir; kural tabanlı sürüm lead time gibi güçlü özellikleri bilmiyor. Rolü modelin yerine geçmek değil, **modelin gerçekten bir şey öğrendiğini** göstermek (RF 0,729) ve model olmayan durumda yedek olmak.

**Sunumda sorulabilir:** *"Neden $k=5$?"* Varsayılan değer, tek bir doğrulama kümesinde Brier'e göre ayarlanabilir diye yazıldı; tahmin dersindeki düzeltme mantığıyla uyumlu başlangıç. Ayarlanmamış, bu açık bir sınırlılık.

---

## 6. Overbooking kuralı (`docs/formulas/overbooking.md`)

Üç farklı kural yazdık; **teslim edilen yalnızca eşik kuralı**.

### 6.1 Eşik kuralı (serviste ve simülasyonda aynı)

Slotta zaten hasta(lar) varsa ikinci hasta **ancak ve ancak** şu üç koşul birlikte sağlanırsa yazılır:

1. slottaki hasta sayısı $<$ slot başına üst sınır (**2**),
2. slottaki **her** hastanın gelmeme riski $\ge$ eşik (**%30**): kodda `min(riskler) >= eşik`,
3. o günkü ek randevu sayısı $<$ günlük sınır (**4**).

*Neden "her hasta" (min)?* İkinci hastayı yazmanın amacı, birinci hasta gelmezse boşluğu doldurmak. Slottaki hastalardan biri güvenilirse çakışma kaçınılmaz olur; bu yüzden hepsinin riskli olması şartı aranır. *Neden %30?* Başlangıç ayarı servisten geldi (`config.yaml`), ızgara deneyi (Bölüm 10.3) tavanın %97'sine ulaşıldığını gösterdi.

### 6.2 Maliyet kuralı R5-A (havayolu mantığı)

Havayolları kapasiteden fazla bilet satar çünkü bazı yolcular gelmez. Mantık: bir hasta daha eklemenin **beklenen maliyeti** (fazla bekleme) ile **kazancı** (boş kalmayı önlemek) karşılaştırılır.

- Slotta $k$ hasta var, her birinin gelme olasılığı $s_i$. Gelen hasta sayısı $S_k=\sum B_i$, $B_i\sim\text{Bernoulli}(s_i)$ bağımsız ama farklı olasılıklı: **Poisson-binomial** dağılım.
- Dağılım **dinamik programlamayla** tam hesaplanır: $P_j(m)=P_{j-1}(m)\,p_j+P_{j-1}(m-1)\,s_j$. Kodda bu `np.convolve(dist, [p, 1-p])` ile yapılır (indeks 0 = gelmedi, 1 = geldi).
- Kapasite $C$ (1 hasta) için $q_k = P(S_k \ge C)$ = "en az bir hasta gelir" olasılığı.
- Maliyet oranı $r=c_W/c_I$ (c_W: fazla hastanın maliyeti, c_I: boş slotun maliyeti). **Karar:** hasta ekle $\iff q_k < 1/(1+r)$.
- Tek hastalı slot için bu, **eşik kuralına** indirgenir: $\text{ekle} \iff p > \tau$, $\tau=r/(1+r)$. Yani eşik kuralı, belirli bir maliyet oranının özel hâlidir. Türetimi elle yaptık ve küçük bir bilgisayar hesabıyla doğruladık.
- **Neden teslim edilmedi?** Modelin en yüksek riski yaklaşık %50 olduğu için $r=1$ ($\tau=0{,}5$) neredeyse hiç tetiklenmez (oturum başına +0,02 hasta); $r=0{,}5$ ise eşik %30'dan daha az hasta ekler (+2,1 vs +2,8).

### 6.3 Beklenen değer kuralı R5-B

Yolcuların beklenen gelişi kapasiteyi aşmayana kadar ekle: $\sum s_i < C$. Varyansı yok sayar. Simülasyonda **eşik %20 ile aynı hasta kazancı** (+3,2) verir ama daha çok bekleme (+1,6 dk).

### 6.4 Güvenlik sınırları

Slot başına en çok 2 hasta (kuyruğun büyümesini önler), günlük ek randevu sınırı 4 (16 slotun %25'i; formül belgesindeki başlangıç önerisi %10'du, "simülasyonla ayarlanacak" diye bırakılmıştı, karar listesinde 4 seçildi), risk tahmini kalibre olmalı. Bilgi yoksa (hastanın geçmişi yok ve kaynak "genel" ise) tek randevu.

---

## 7. Tahmin modeli

### 7.1 Özellikler (11)

`LeadDays`, `Weekday`, `Age`, `GenderMale`, `Scholarship`, `Hypertension`, `Diabetes`, `Alcoholism`, `Handicap`, `PriorApptCount`, `PriorNoShowCount`. Hepsi **randevu alındığı anda bilinen** bilgi. Servis aynı özellikleri aynı şekilde hesaplar; adlar farklıdır (`lead_days`, `weekday`, ..., `hipertension`, `handcap`). Eşleme `ml/export_candidate.py` içindedir. Bu liste 17 Ekim'de PM tarafından "agreed" yapıldı (`docs/features.md`).

### 7.2 Eğitim/test ayrımı: zamana göre

Veri randevu gününe göre sıralanır, **ilk %80'i eğitim (88.535 randevu, 29 Nisan – 1 Haziran), son %20'si test (21.986 randevu, 2 Haziran sonrası)**. *Neden rastgele bölme değil?* Gerçek hayatta model geçmişi görür, geleceği tahmin eder; rastgele bölmede gelecekteki günler eğitime sızar, sonuç iyimser olur. Test kümesi doğal dağılımını (%18,5 gelmeme) korur: **yeniden örnekleme yok**.

### 7.3 Üç model ve neden bu üçü

| Model | Ayar | Neden |
|---|---|---|
| **Lojistik regresyon (LR)** | `StandardScaler` + `LogisticRegression(C=0.01)` | Yorumlanabilir taban; olasılık verir. **Ölçekleme boru hattının içindedir**: yalnızca eğitimden öğrenilir (sızıntı olmasın) |
| **Rastgele orman (RF)** | 150 ağaç, `min_samples_leaf=20`, `max_depth=14` | Doğrusal olmayan ilişkileri (lead time) ve etkileşimleri yakalar; ayar az hassas; olasılığı ağaçların ortalaması olarak verir (kalibrasyon eğimi 1,10) |
| **Karar ağacı (DT)** | `max_depth=4`, `min_samples_leaf=200` | Çizilebilir/anlatılabilir; literatürün seçtiği model (karşılaştırma); RF ile neredeyse aynı performans |

**Hiperparametre seçimi** (`ml/evaluate_models.py`): eğitim dönemi tarihe göre 5 bloğa bölünür, **genişleyen pencere** ile 4 doğrulama katı (bloklar 1..4: önceki bloklarla eğit, o bloğu doğrula). **Seçim ölçütü log-loss:** olasılık tahminlerinin kalitesini ölçen "uygun puan" (proper scoring rule); overbooking olasılığı olduğu gibi kullandığı için AUC'den daha doğru ölçüt. AUC yanında raporlanır.

### 7.4 Değerlendirme ölçütleri ve neden

| Ölçüt | Ne ölçer | RF | DT | LR |
|---|---|---|---|---|
| ROC-AUC | Sıralama gücü | **0,729** (0,721–0,736) | 0,720 | 0,658 |
| PR-AUC | Nadir sınıfta (gelmeme %18,5) precision–recall | 0,339 | 0,305 | 0,295 |
| Brier | Olasılığın kare hatası | 0,136 | 0,138 | 0,145 |
| Log-loss | Olasılık kalitesi | 0,423 | 0,426 | 0,461 |
| Kalibrasyon eğimi | 1 = ideal | 1,10 | 1,06 | 0,90 |

(Referans: R4 AUC 0,577; "herkes gelir" tabanı AUC 0,5.)

- **Neden doğruluk (accuracy) yok?** Veride %80 gelen var; "herkes gelir" diyen kural %79,8 doğruluk alır. Doğruluk bu veride aldatıcıdır; literatürdeki %95 de bu tuzaktan (7.8).
- **AUC güven aralığı:** 200 **bootstrap** örneğiyle (test kümesinden yerine koyarak çekip AUC yeniden hesaplanır, %2,5–%97,5 yüzdelikleri).
- **Kalibrasyon kesişimi ve eğimi:** `calibration_stats`: kesişim, eğimi 1'e sabitleyip ortalama tahmini gerçek orana eşitleyen sabittir (`scipy.optimize.brentq` ile kök bulma); eğim, logit(tahmin) üzerinde lojistik regresyon katsayısıdır. Kesişim < 0: tahminler ortalamada **yüksek** (−0,14: gelmeme oranı eğitimden teste %20,6 → %18,5'e düştü). Eğim > 1: tahminler gerçek farkları **olduğundan az** gösteriyor.
- **Onluk dilim tablosu:** tahminleri 10 eşit dilime böl; her dilimde ortalama tahmin ile gerçek oranı karşılaştır (güvenilirlik diyagramı).

### 7.5 Karar eşiği ve precision/recall

Eşiği testten **seçmeyiz** (testin kendisine uydururduk). F1'i en yüksek yapan eşik, eğitim dönemindeki **katlama dışı** (out-of-fold) tahminlerden seçilir; ayrıca 0,20 / 0,30 / 0,40 sabit eşikleri raporlanır. RF için 0,30'da precision 0,33, recall 0,48; hastaların %27'si "riskli" sayılır. 0,40'ta yalnızca %3,8 işaretlenir (recall 0,08): model hiç yüksek risk üretmez (en yüksek tahmin yaklaşık %50), bu yüzden yüksek eşikler anlamsızdır.

### 7.6 Kalibrasyon ve kayma

Eğitimde %20,6, testte %18,5 gelmeme: **dağılım kayması**. Sonuç: tahminler biraz yüksek. Canlıda gelmeme oranı izlenmeli (`quality-control.md` bölüm 5: p kontrol grafiği) ve model periyodik olarak yeniden kalibre edilmelidir.

### 7.7 Alt gruplar: yeni ve tekrar gelen hasta

RF'de AUC yeni hastada **0,721**, tekrar gelende **0,737**: model yeni hastada da yaş ve lead time ile ayırır. Her iki grupta tahmin ortalaması gerçeğin biraz üstünde (yeni %22,3 vs %19,6; tekrar gelen %18,3 vs %17,2). **Operasyonel nokta:** 0,30 eşiğinde yeni hastaların %34'ü, tekrar gelenlerin %17,5'i "riskli" sayılıyor. Kural ek randevuyu çoğunlukla **yeni hastaların slotlarında** açıyor: bir adalet ve güvenilirlik notu.

### 7.8 Literatür ve %95 iddiası (`docs/LITERATUR_INCELEMESI.md`)

Batool ve ark. (2020) aynı Kaggle verisinde karar ağacıyla **%94,5 doğruluk** bildirmiş. Biz protokolünü `ml/paper_replication.py` ile yeniden çalıştırdık:

- Makalenin yöntemi: **bütün veri** önce Instance Hardness Threshold (IHT) ile dengelenir (çoğunluk sınıfı azaltılır), **sonra** rastgele bölünür ve test dengelenmiş kümeden yapılır. Test kümesinin dağılımı gerçek dağılım değildir ve eğitim ile test aynı yeniden örneklemeden gelir.
- Bizim hatasız protokolümüz: önce **gerçek veri** bölünür, dengeleme yalnızca eğitime uygulanır, test gerçek dağılımda yapılır.
- Sonuç: karar ağacı doğruluğu **%93,8 → %51,9**, AUC **0,967 → 0,716**. Yani **gerçek AUC ≈ 0,72**, bizimkiyle aynı. Tek özellikle (yalnız lead time) %95 iddiası da aynı sızıntıdan.
- Makalenin overbooking'i yalnızca bir cümle ("gelmeyecek denen slotlar açılır") ve **etkisi ölçülmemiş**; biz bunu bir politika olarak simülasyona ekleyip ölçtük (`p ≥ 0,5` işaretle, sınırsız; dengelenmiş eğitimin ürettiği kalibre olmayan olasılıklar bu politikayı aşırı overbooking'e iter).

### 7.9 Zamansal sızıntı denetimi (17 Ekim)

Simülasyon için **27 günün hepsinde örneklem dışı risk** gerekir (`risks_all_days.csv`). Günler 5 kata **dönüşümlü** dağıtılır; her fold, kendi dışındaki günlerle eğitilen modelle tahmin edilir. Bu yöntemin riski: bir gün, kendisinden **sonraki** günlerle eğitilmiş modelle tahmin edilir (günün kendi satırları eğitimde değildir ama gelecek bilgisi vardır). Denetim (`ml/leakage_check.py`): ileri doğru genişleyen pencereyle (yalnızca geçmiş günlerle eğit, sonraki bloğu tahmin et) aynı satırlarda karşılaştırdık: **AUC 0,731 (dönüşümlü) ve 0,729 (yalnız geçmiş)**; karar ayarının simülasyon kazancı +3,13 ve +3,17 hasta. Fark çok küçük, dönüşümlü katlar sonuçları şişirmiyor. Beş protokol maddesi de kodla doğrulandı (özellik listesinde hedef/SMS/mahalle/kimlik yok; eğitim günleri test günlerinden önce; geçmiş özellikleri 3.000 satırda bağımsız yeniden hesaplandı, 0 fark; ölçekleme yalnızca eğitimde; eşik testten seçilmedi).

### 7.10 Modelin teslimi

`ml/export_model.py` modeli `ml/models/model.joblib` olarak, özellik sırası, model sürümü, pozitif sınıf (`1` = gelmedi) ve **scikit-learn sürümü** ile `feature_schema.json` olarak yazar. Servis, yüklenen modeli kendi **kabul kontrolleriyle** sınar: özellik adları eşleşiyor mu, olasılıklar 0–1 aralığında mı, riskli profiller güvenilir profillerden yüksek mi skorlanıyor. Modeller **scikit-learn 1.9.1** ile eğitildi (servisin kullandığı sürüm); farklı sürümle eğitilmiş model dosyası uyarı verir. Seçilen model **rastgele orman (`random_forest-v1`)**; karar ağacı karşılaştırma için `ml/models/candidates/` ve `IEN-DecisionTree` dalında.

*Neden RF, DT değil?* Klinik sonuçta (simülasyon) neredeyse aynılar; RF'nin log-loss ve PR-AUC'si biraz iyi. Karar ağacı çok küçük (birkaç KB) ve anlatılabilir, RF yaklaşık 16 MB. Seçim ekip kararı; RF seçildi, alternatif korundu.


---

## 8. Simülasyon: nasıl çalışıyor ve her parça neden orada

### 8.1 Neden simülasyon, neden SimPy?

Soru: "Bu kural bekleme, boşta kalma ve mesai aşımını nasıl etkiler?" Kapalı formülle cevaplanamaz, çünkü sonuç **kuyruk dinamiğine** bağlı: bir hastanın gecikmesi sonrakilerin başlamasını öteler. Bu yüzden **ayrık olay simülasyonu** kullanıldı. **SimPy**: Python'da süreç tabanlı ayrık olay simülasyonu kütüphanesi (hocanın izin verdiği Arena yerine). Seçim nedenleri: kodla yeniden üretilebilir, sürüm kontrolüne girer, veriyle (pandas) doğrudan bağlanır.

**Modelin yapısı.** Bir **muayene odası** = bir SimPy `Resource(capacity=1)` (aynı anda tek hasta). Her gelen hasta bir **süreç (process)**: randevu saatini bekler, kuyrukta sırasını bekler, muayene olur. Zaman dakika olarak ilerler.

### 8.2 `simulation/clinic_sim.py` fonksiyon fonksiyon

**`SessionConfig`** (frozen dataclass): oturumun tüm ayarları.

| Alan | Değer | Anlamı ve neden |
|---|---|---|
| `n_slots`, `slot_min` | 16, 15 | 4 saatlik oturum (240 dk) |
| `service_mean`, `service_cv` | 7,5 dk, 0,5 | Muayene süresi ortalaması ve değişkenlik katsayısı (std ÷ ortalama) |
| `punctuality_sd` | 4 dk | Hastanın randevu saatine göre geliş sapması |
| `extra_requests` | 4 | Talep = slot + 4 (kapasitenin üstünde talep olmasa overbooking'in anlamı kalmaz) |
| `requests` | boşsa `n_slots + extra_requests` | Oturum başına randevu isteği (20) |
| `risk_alpha`, `risk_beta` | 2, 8 | Sentetik risk: Beta(2,8) dağılımı, ortalama 0,2 (gerçek gelmeme oranına benzesin diye) |

*Frozen:* ayarlar yanlışlıkla değişmesin; `dataclasses.replace` ile kopyalanır.

**Politikalar** (`Policy = Callable[[booked_risks, overbooks_so_far], bool]`): "bu slota bir hasta daha yazılabilir mi?" sorusuna cevap veren fonksiyonlar.

- `fixed_interval()`: her zaman `False`. Sabit aralık = **taban çizgisi**.
- `threshold_rule(thr, max_per_slot=2, daily_limit=4)`: `len(booked) < max_per_slot and min(booked) >= thr and overbooks < daily_limit`. Servisteki `rules.decide` ile aynı mantık (parity testi).
- `cost_rule(r, ...)`: Poisson-binomial dağılımı `np.convolve` ile kurar, `q = dist[capacity:].sum()`, `q < 1/(1+r)` ise ekler.
- `expected_value_rule(...)`: `sum(1 - p) < capacity`.

**`Layout`**: şablon ayrıntıları (`blocked` boş kalacak tampon slotlar, `overbook_slots` overbooking'e izin verilen slotlar, `offset` ikinci hastanın slot içinde ne kadar geç başlayacağı).

**`Draws` ve `draw_session(cfg, rng, pool)`**: bir oturumun **rastgele girdileri**: her randevu isteği için risk, geliyor mu, geliş sapması, muayene süresi.

- `pool` verilmişse (gerçek risk dosyası) satırlar rastgele çekilir: risk `p` ve gerçek sonuç `y` (`shows = y == 0`). Böylece "gelme/gelmeme" gerçek veriden; model riskinin **gerçekten bilgi taşıyıp taşımadığı** (riski yüksek olanın gerçekten gelmeme olasılığı) simülasyona yansır. `pool` yoksa Beta(2,8) risk ve `shows = rng.random(n) >= risk` (risklerin kalibre olduğu varsayımı).
- **Muayene süresi log-normal:** `sigma = sqrt(ln(1 + cv²))`, `mu = ln(mean) − sigma²/2`; ortalama tam olarak `mean` olur. *Neden log-normal?* Süre negatif olamaz ve sağa çarpıktır (çoğu muayene kısa, bazıları uzun). `np.maximum(3.0, ...)`: 3 dakikadan kısa muayene yok (alt sınır).
- **Geliş sapması normal:** `rng.normal(0, punctuality_sd)`. Veride geliş saati yok; **varsayım**.

**`book(cfg, policy, d, layout)`**: randevu isteklerini **geliş sırasıyla** slotlara yerleştirir. Her istek için slotlar sırayla taranır: tampon slotsa atla; slot boşsa yaz ve çık; doluysa ve şablon overbooking'e izin veriyorsa `policy(slottaki_riskler, ek_sayısı)` sorulur, `True` ise ikinci hasta yazılır ve sayaç artar. Hiçbir slot uygun değilse hasta **`deferred`** (başka güne yazılır). *Neden "ilk uygun slot"?* Gerçek bir takvimde hasta en erken boş saati alır; ayrıca bu, politikaların aynı kuralı adil biçimde kullanmasını sağlar.

**`simulate_session(cfg, policy, d, detail, layout)`**: oturumu SimPy ile çalıştırır.

```python
env = simpy.Environment()
room = simpy.Resource(env, capacity=1)


def patient(i, appt_time):
    arrival = max(0.0, appt_time + d.arrival_offset[i])
    ready = max(appt_time, arrival)  # muayene randevu saatinden önce başlamaz
    yield env.timeout(ready)  # hazır olana kadar bekle
    with room.request() as req:
        yield req  # odanın boşalmasını bekle (kuyruk)
        start = env.now
        waits.append(start - ready)  # BEKLEME = başlangıç − max(randevu, geliş)
        yield env.timeout(d.service[i])  # muayene
        busy.append((start, env.now))
```

- **Bekleme tanımı** (`docs/kpi-definitions.md`): muayene başlangıcı − max(randevu saati, geliş). *Neden `max`?* Erken gelen hasta randevu saatinden önce muayene edilemez; ilk simülasyonda bunu yapmayınca **negatif bekleme** çıktı (Bölüm 12, hata 1).
- **Gelmeyen hasta** için süreç hiç başlatılmaz (`if d.shows[i]`); yalnızca gelenler odayı kullanır.
- **İkinci hasta (`offset`)**: aynı slotta `k`'ıncı hasta `(s + k·offset)·slot_min` anında randevu alır; `offset=0,5` ise ikinci hasta slotun ortasında başlar (T2 şablonu).
- **KPI'lar:** `idle = session_end − busy_in_session` (oturum içinde hastasız dakika), `overtime = max(0, son_muayene_bitişi − session_end)`, `utilization = toplam_meşgul_süre ÷ session_end`, `mean_wait`, `max_wait`, ayrıca `seen`, `overbooked_slots`, `deferred`.

**`run(cfg, policies, reps, seed, pool)`**: `reps` kez oturum üretir. Her tekrar için `np.random.default_rng([seed, rep])` ile **bir** `Draws` çekilir ve **bütün politikalar aynı Draws ile** çalıştırılır (**ortak rastgele sayılar**). *Neden?* İki politikanın farkının "şanstan mı yoksa politikadan mı" geldiğini ayırmak için: aynı hastalar, aynı gelme/gelmeme, aynı süreler; yalnızca randevu kuralı değişir. Bu, güven aralıklarını çok daraltır (aynı sonucu için çok daha az tekrar yetmesi).

**`paired_difference(res, baseline)`**: tekrar bazında `politika − taban` farkını alır, `ortalama ± 1,96·std/√n` (%95 güven aralığı). *Neden eşleştirilmiş?* Aynı oturum üzerindeki fark, iki bağımsız ortalamanın farkından çok daha az gürültülüdür.

### 8.3 Gerçek verinin simülasyona bağlanması (`app.py`, `real_days.py`, `templates/day_by_day.py`)

Veride doktor, oda ve saat yok. Çözüm: bir günün **bütün gerçek randevuları** rastgele (`rng.permutation`, sabit tohumla) gruplara bölünür; her grup **bir oturum** (en çok 20 randevu isteği, yani yaklaşık 220 oturum/gün). Her oturumda hastalar **gerçek alınma sırasıyla** (`ScheduledDay`'e göre) sıralanır. Risk ve gelme/gelmeme **gerçek**, muayene süresi ve gecikme **simüle**. Sonuçlar **oturum başına**, gün için toplanır. Bu, "tek bölüm, hekim yok" kararıyla uyumludur: kapasite departmanındır, odalar kapasite birimidir; oda sayısı bir **varsayım** (verinin günlük hacminden türer).

### 8.4 Diğer simülasyon dosyaları

| Dosya | Ne yapar | Neden var |
|---|---|---|
| `value_ladder.py` | Politikaları **adım adım** karşılaştırır: 0 sabit; 1 **kör overbooking** (riske bakmadan çift yaz); 2 eşik (risk hedefli); 3 maliyet R5-A; * **oracle** (kimin gelmeyeceğini bilen en iyi durum) | "Her katman ne katıyor?" sorusu: model gerçekten işe yarıyor mu, yoksa kör overbooking aynısını yapar mı? Bulgu (ilk, 12 dk muayene varsayımıyla): hedefli overbooking ek hasta başına bekleme bedelini 2,5 dk'dan 1,6 dk'ya indirir ama sıfırlamaz |
| `dashboard.py` | KPI kartlı HTML pano | Sonuçları yönetici gözüyle okumak |
| `plots.py` | Bekleme–boşta kalma takas grafiği, bir oturumun zaman çizgisi | Takas görseli |
| `live_day.py` | Bir günü animasyonla ve SimPy olay günlüğüyle izlemek (`--trace`) | Simülasyonun **doğruluğunu gözle denetlemek** (kim ne zaman geldi, ne zaman başladı) ve sunumda anlatmak |
| `real_days.py` | Tüm günün bütün kayıtları, her oturum bir kare | Ölçek: gerçek veri hacmi |
| `templates/` | 3 randevu şablonu, karşılaştırma, kazanan, gün gün tablo | Bölüm 9 |
| `app.py` + `ui/app.html` | **Etkileşimli simülasyon:** gün, risk kaynağı, kural, şablon seç, Çalıştır; Edge/Chrome "uygulama modu" penceresi, otomatik yeniden hesap | Kuralları görerek ve oynayarak test etmek |
| `main.py` | Tüm adımları tek komutla çalıştırır, `output/index.html` sayfa kümelerini kurar | Tekrar üretilebilirlik |
| `experiments.py` | 2.000 oturumluk eşleştirilmiş deneyler, ızgara, duyarlılık, hatırlatma senaryosu | İstatistiksel kanıt (Bölüm 10) |
| `wait_distribution.py` | Tek tek hastaların bekleme dağılımı, uç değerler, ek hasta başına maliyet | Ortalama kuyruğu gizler |
| `parity_check.py` | Servisin `rules.decide`'ı ile simülasyonun eşik kuralı 20.000 rastgele slotta aynı mı? | İki kodun aynı kararı vermesi şart (Bölüm 13) |
| `web_designs/` | Uygulama arayüzü taslakları | Bölüm 13.3 |

**Risk kaynakları** (`app.py` ve `experiments.py` risk seçimi): rastgele orman (`p`), lojistik regresyon (`p_lr`), R1–R4 (`p_r1`…`p_r4`), makalenin sınıflandırıcısı (`p_paper`). *Neden birden fazla?* "Risk bilgisi olmayan/zayıf olan kural ne kadar iyi?" sorusunun cevabı, modelin katkısıdır.

### 8.5 Kullandığımız fonksiyonlar ve nedenleri

| Fonksiyon | Yer | Neden bunu kullandık |
|---|---|---|
| `simpy.Environment()`, `env.run()` | `clinic_sim.simulate_session` | Simülasyon saatini ve olay kuyruğunu yönetir; her oturum için yeni bir ortam kurulur, böylece oturumlar birbirini etkilemez |
| `simpy.Resource(env, capacity=1)` + `with room.request()` | aynı | Tek muayene odası: ikinci hasta oda doluyken kuyrukta bekler (ilk gelen önce). Bekleme süresi bu kuyruktan doğal olarak çıkar |
| `env.process(patient(...))`, `yield env.timeout(t)` | aynı | Her hasta bağımsız bir süreç: randevu saatini bekler (`timeout`), odayı ister, muayene süresi kadar (`timeout`) meşgul eder |
| `np.random.default_rng([seed, rep])` | `run`, `experiments` | Her (tohum, tekrar) çifti için **bağımsız ama tekrarlanabilir** rastgele akış. Aynı akışı tüm politikalara vermek ortak rastgele sayıları sağlar |
| `rng.lognormal`, `rng.normal`, `rng.beta`, `rng.random` | `draw_session` | Muayene süresi (log-normal), geliş sapması (normal), sentetik risk (Beta), gelme/gelmeme (Bernoulli: `random() >= risk`) |
| `np.maximum(3.0, süre)` | `draw_session` | Gerçekçi alt sınır: 3 dakikadan kısa muayene yok |
| `np.convolve(dist, [p, 1-p])` | `cost_rule` | Poisson-binomial dağılımı dinamik programlamayla kurar: her yeni hasta dağılımı bir adım kaydırıp karıştırır |
| `rng.permutation(len(day))` | `app.deal_sessions`, `real_days.sessions_of` | Bir günün kayıtlarını **rastgele** (ama sabit tohumla tekrarlanabilir) oturumlara böler; sonra her oturumda alınma sırasına göre sıralanır |
| `np.searchsorted(randevu_günleri, alınma_günü, side="left")` | `clean_data` | "Alınma gününden **kesin önce** olan randevu sayısı"nı hızlı bulur; geçmiş özelliklerinin sızıntısız hesabının çekirdeği |
| `pd.cut`, `pd.qcut` | `clean_data`, `evaluate_models` | Yaşı bantlara bölmek (sabit sınırlar); tahminleri onluk dilimlere bölmek (eşit sayıda gözlem) |
| `StandardScaler` + `make_pipeline` | `evaluate_models`, `build_reports` | Lojistik regresyon özellik ölçeğine duyarlı; ölçeği **yalnızca eğitimden** öğrenmek için boru hattı |
| `LogisticRegression`, `RandomForestClassifier(n_jobs=-1, random_state=42)`, `DecisionTreeClassifier` | `ml/` | Üç aday model; `random_state` sabit: sonuç tekrarlanabilir |
| `roc_auc_score`, `average_precision_score`, `brier_score_loss`, `log_loss` | `build_reports`, `evaluate_models` | Sırasıyla ROC-AUC, PR-AUC, Brier, log-loss |
| `scipy.optimize.brentq` | `calibration_stats` | Kalibrasyon kesişimini bulmak için kök bulma: $	ext{ortalama}(\sigma(z+a)) = 	ext{gerçek oran}$ denklemini $a$ için çözer |
| `LogisticRegression(C=1e6)` (cezasız) | `calibration_stats` | Kalibrasyon eğimi: gerçek sonucu logit(tahmin) üzerine regresyon; ceza (düzenleme) eğimi küçültmesin diye çok büyük `C` |
| `rng.integers(0, n, n)` (yerine koyarak çekme) | `bootstrap_auc_ci` | AUC için bootstrap güven aralığı (200 örnek) |
| `permutation_importance` | `build_reports` (RF raporu) | Hangi özelliğin karıştırılınca AUC'nin en çok düştüğünü ölçer (bir özelliğin modele katkısı) |
| `joblib.dump` | `export_model` | Modeli diske yazar; sürüm uyumu için scikit-learn sürümü şemaya eklenir |
| `groupby(...).agg(...)` | raporlar | Gruplara (gün, yaş bandı, dilim) göre özetler |

---

## 9. Randevu şablonları (T1, T2, T3) ve kazanan

Soru: slotları nasıl keselim ki hasta sayısı artsın, bekleme ve mesai aşımı kabul edilebilir kalsın?

| Şablon | Fikir | Ayar |
|---|---|---|
| **T1 Kısa slot** | Slot 15 dk, muayene daha kısa; slotu 12 dk yap, overbooking yok | 20 slot × 12 dk |
| **T2 Kaydırılmış overbooking** | 15 dk'lık slotlar; ikinci hasta slotun **ortasında** (+7,5 dk) başlar. Aynı dakikada başlayan iki hasta gelirse biri tam bir muayene bekler; yarım slot kaydırma çakışmayı yarıya indirir | 16 × 15 dk, eşik %30, `offset=0,5` |
| **T3 Tampon + geç overbooking** | 9. slot boş bırakılır (gecikmeleri emer); overbooking yalnızca 10–15. slotlarda, son slotta yok (kuyruk zinciri ve mesai aşımı azalsın) | 16 × 15 dk, `blocked=(8,)` |

**Seçim kuralı (önceden yazıldı):** (1) şablon "uygun" sayılır eğer ortalama bekleme ≤ MAX_WAIT ve mesai aşımı ≤ MAX_OVERTIME; (2) uygunlar arasında **en çok hasta** gören kazanır (eşitlikte az boşta kalan); (3) sabit aralığa göre eşleştirilmiş fark güven aralığıyla raporlanır. İlk çalışmada sınırlar 5 dk idi; **kazanan T2**, ancak kazancı küçüktü (+0,3 hasta). T1 en çok hastayı görüyordu ama mesai aşımı yüksekti; **T3 işe yaramadı** (hasta sayısı bile düştü, çünkü boş bırakılan slot talebi azalttı).

**Güncel (karar ayarlarıyla) şablon sonuçları** (`IEN_DENEY_SONUCLARI.md` bölüm 3, tabana göre): 16×15 + karar ayarı +2,77 hasta, +0,88 dk bekleme; kaydırma 0,5 ile bekleme +0,69 dk ama mesai aşımı +0,45 dk; **20×12 kısa slot (kuralsız)** +3,20 hasta, +0,40 dk bekleme, +0,56 dk mesai aşımı; kısa slot + karar ayarı hasta sayısını artırmaz, beklemeyi +1,69 dk'ya çıkarır. **Çıkarım:** kısa slot ile overbooking birbirinin **yerine** geçer, birlikte ek kazanç yoktur. Muayene slotun yarısı kadar sürdüğü için slotu muayeneye yaklaştırmak, kapasiteyi doğrudan açar.

---

## 10. Deneyler ve sonuçlar

Her deney `simulation/experiments.py`'de, tohum `20261016`, **2.000** eşleştirilmiş oturum (ızgara 500, duyarlılık 600, şablon 1.000). Girdi: örneklem dışı RF riskleri ve gerçek gelme/gelmeme.

### 10.1 Ana sonuç: karar ayarı, sabit aralığa göre (oturum başına)

| Ölçüt | Kural yok | Karar ayarı | Fark [%95 aralık] |
|---|---|---|---|
| Görülen hasta | 12,81 | 15,60 | **+2,78** [+2,74; +2,82] (%+22) |
| Ortalama bekleme (dk) | 0,22 | 1,13 | +0,91 [+0,87; +0,95] |
| Boşta kalma (dk) | 144,07 | 123,66 | −20,42 [−20,82; −20,01] |
| Mesai aşımı (dk) | 0,25 | 0,46 | +0,22 [+0,12; +0,31] |
| Doluluk | 0,40 | 0,49 | +0,09 |

Etki büyüklüğü (Cohen d_z): hasta sayısı +2,84, boşta kalma −2,22 (çok büyük etki), bekleme +1,01, mesai aşımı +0,10 (küçük). **Okuma:** hasta sayısı ve boşta kalma net iyileşiyor; bekleme biraz kötüleşiyor, mesai aşımı neredeyse değişmiyor. Başlangıçtaki iddiamız "bekleme **ve** boşta kalma ikisi birden iyileşir"di; bu varsayımlarla **çıkmadı**: bekleme artıyor (küçük ama istatistiksel olarak anlamlı).

### 10.2 Diğer politikalar (tabana göre fark)

| Politika | Görülen | Bekleme | Boşta | Mesai |
|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +2,78 | +0,91 | −20,4 | +0,22 |
| Eşik %20 | +3,19 | +1,23 | −23,6 | +0,06 |
| Eşik %40 | +0,39 | +0,12 | −2,9 | +0,03 |
| Maliyet r=0,5 | +2,09 | +0,69 | −15,3 | +0,27 |
| Maliyet r=1,0 | +0,02 | +0,00 | −0,1 | +0,01 |
| Havayolu (R5-B) | +3,19 | +1,61 | −23,6 | +0,05 |

### 10.3 Eşik × günlük sınır ızgarası ve Pareto

Eşik 0,15–0,50, günlük sınır 1–8. Ulaşılabilir en yüksek hasta sayısı yaklaşık **15,9** (eşik %15–%20, sınır ≥4); karar ayarı (%30/4) bunun **%97'sini 1,1 dk beklemeyle** verir. Eşik %20'ye inmek **+0,4 hasta** getirir, beklemeyi **+0,3 dk** artırır. 15 dk bekleme sınırı hiçbir ayarda **bağlayıcı değil**; seçim "kaç ek hasta kabul ederiz" sorusudur. **Pareto:** başka hiçbir ayar tarafından dört ölçütte birden geçilmeyen ayarlar; kod `experiments.pareto`.

### 10.4 Duyarlılık: hangi varsayım sonucu ne kadar değiştirir?

Karar ayarının sabit aralığa göre farkı:

| Senaryo | Görülen | Bekleme | Boşta | Mesai |
|---|---|---|---|---|
| Taban (7,5 dk, 15 dk slot) | +2,76 | +0,95 | −20,7 | +0,27 |
| Muayene 5 dk | +2,76 | +0,41 | −14,3 | 0,00 |
| Muayene 10 dk | +2,76 | +2,18 | −26,7 | +1,14 |
| Değişkenlik 0,3 / 0,8 | +2,76 | +0,78 / +1,37 | −20,7 / −20,8 | +0,10 / +0,63 |
| Talep 16 istek (= slot) | **+0,00** | +0,96 | −0,4 | −0,36 |
| Talep 24 istek | +2,76 | +0,91 | −21,0 | +0,24 |
| Geç kalma sapması 8 dk | +2,76 | +0,90 | −20,5 | +0,55 |
| 10 dk slot, 24 slot | +3,12 | +1,71 | −22,8 | +0,68 |
| No-show oranı ×0,7 | +0,11 | +0,05 | −0,9 | −0,01 |
| No-show oranı ×1,3 | +2,91 | +0,97 | −21,4 | +0,13 |

**Okuma.** Yön hiçbir senaryoda değişmez (hasta ↑, boşta ↓, bekleme ↑). **Büyüklük**, muayene süresine ve gelmeme oranına bağlıdır. Talep slot sayısına eşitse kural hiç işe yaramaz: önce talep gerekir. Gelmeme oranı %30 düşerse kural neredeyse tetiklenmez: **modelin değeri gelmeme oranı kadardır**.

### 10.5 Bekleme dağılımı (`docs/BEKLEME_DAGILIMI.md`)

3.000 oturumda her hastanın beklemesi:

| | Sabit aralık | Karar ayarı | Ek randevulu slottaki hastalar |
|---|---|---|---|
| Ortalama (dk) | 0,22 | 1,14 | 2,48 |
| %95'inci yüzdelik (dk) | 0,73 | 7,71 | 10,87 |
| %99'uncu yüzdelik (dk) | 6,25 | 14,16 | 17,45 |
| 5 dk'dan uzun bekleyen | %1,5 | %9,5 | %21,5 |
| 15 dk'dan uzun bekleyen | %0,1 | %0,8 | %1,8 |
| En uzun (dk) | 39 | 68 | 68 |

Bir oturumda en az bir hastanın 15 dk'yı aşması: sabit %1,0, kural %8,7. **Maliyet:** kural oturum başına +2,79 hasta görür, toplam **+15,0 hasta-dakika** ek bekleme (ek hasta başına yaklaşık 5,4 dk) ve +0,21 dk mesai aşımı yaratır. *Ortalama neden yetmez?* Ortalama 1,1 dk iken hastaların küçük bir kısmı uzun bekler; bir kurum hasta başına bir sınır (ör. %95'inci yüzdelik) isteyebilir.

### 10.6 Hatırlatma senaryosu (varsayımsal)

Hatırlatmanın etkisi **ölçülmedi**: veri setindeki `SMS_received` bir deney değil (SMS alanlar zaten daha riskli; fark nedensel okunamaz). Bu yüzden **varsayımsal** senaryo: hastaların yarısına hatırlatma gider ve gelmeyecek olanların `%0/10/20/30`'u gelen hastaya döner. Sonuç: etki %30 olursa sabit takvimde hasta 12,86 → 13,32 olur; karar ayarıyla 15,63 → 15,19. Yani hatırlatma etkili olursa overbooking'in **ek** kazancı küçülür (2,8 → 1,9 hasta): iki yöntem birbirinin yerine kısmen geçer. Gerçek etki **canlı A/B testiyle** ölçülür (serviste var: `GET /ab/summary`).

### 10.7 Yorum: neden hasta artarken bekleme de artıyor?

Ek hasta yalnızca ilk hasta gelmezse "bedava" olur. İlk hastanın riski yüksek bile olsa gelme ihtimali %50–70'tir; ikisi de gelirse muayene odası aynı slotta iki hastaya bakar, ikinci hasta bekler ve bekleme sonraki slotlara taşınır. Boşta kalma azalır çünkü gelmeyenlerin boşluğu dolar. Muayene ortalaması 7,5 dk iken 15 dk'lık slotta iki hasta sığabilir; bu yüzden bekleme küçük kalır. Muayene 10 dk'ya yaklaştıkça sığmaz ve bekleme/mesai artar. **Ayrıca:** kapasite zaten bol (doluluk %40): kuralın asıl işi bu kapasiteyi kullanmak; slotu kısaltmak aynı sonucu kuralsız verir.


### 10.8 Ders formülleri ve veriyle yaptığımız kontroller

`docs/formulas/` altında dört ders (tahmin, olasılık, istatistik, istatistiksel kalite kontrol) ve proje formülleri toplandı. Önemli not: **tahmin dersi zaman serisi tahminini kapsıyor; lojistik regresyon, rastgele orman, AUC, kalibrasyon, overbooking, kuyruk formülleri dersin dışında** (`overbooking.md` standart kaynaklardan; raporda kaynak gösterilmeli). Dersten **doğrudan** kullandıklarımız ve **kontrol** ettiklerimiz:

| Konu | Ne yaptık | Sonuç |
|---|---|---|
| **Düzeltme formülü** $\hat{s}=(s+k\bar{s})/(n+k)$ | Beta–Binomial modelin sonsal ortalamasıyla karşılaştırdık: ön dağılım $\text{Beta}(k\bar{s},k(1-\bar{s}))$ | **Birebir aynı**; $k$ "eşdeğer önceki randevu sayısı" olarak okunur |
| **Poisson-binomial DP** (`cost_rule`) | Eşit risklerde ikili (binomial) dağılımı vermeli | Fark $<10^{-15}$ |
| **Güven aralığı** $\bar{x}\pm1{,}96\,s/\sqrt{n}$ | Merkezî limit teoremiyle geçerli ($n=1000$) | $t_{0{,}025,999}=1{,}962$ |
| **Tekrar sayısı** $n\ge(z\sigma/E)^2$ | Eşik %30 politikasının bekleme farkı için $s=4{,}65$ dk (eski varsayımlarla) | $\pm0{,}25$ dk için ≈1.330 oturum; 1.000 tekrar ≈ ±0,29 dk. Bu yüzden ana deneyde 2.000 |
| **Muayene süresi dağılımı** | Derste üstel dağılım (CV = 1) var; biz log-normal (CV = 0,5) kullandık | **Duyarlı bir varsayım:** üstel süreyle sabit aralıkta bekleme 2,3 → 7,8 dk ve mesai aşımı 2,9 → 10,4 dk'ya çıkıyor (eski varsayımlarla); yani süre değişkenliği sonucu çok etkiler. Bu yüzden duyarlılık tablosunda 0,3 ve 0,8 değişkenlik denendi |
| **İki oran z-testi** (eğitim dönemi) | Cinsiyet, yaş, lead time, yeni/tekrar gelen, SMS karşılaştırmaları | Erkek %20,2 / kadın %20,8 (fark 0,6 puan, $p=0{,}044$ ama pratikte anlamsız); yaş <25 %23,1 / ≥55 %16,2 ($z=19{,}8$); lead ≥15 gün %33,6 / ≤2 gün %9,0 ($z=76{,}7$); yeni %22,2 / tekrar gelen %15,5 ($z=20{,}8$); SMS alan %28,0 / almayan %17,5 ($z=35{,}1$, **yanlış yönde**, çünkü SMS zaten riskli hastaya gitmiş) |
| **p kontrol grafiği** (kalite kontrol dersi) | Günlük gelmeme oranı, eğitim dönemi $\bar{p}=0{,}2061$, sınırlar $\bar p\pm3\sqrt{\bar p(1-\bar p)/n_i}$ | 22 günün 8'i sınır dışı: süreç **kontrol altında değil** (aşırı dağılım). 2–8 Haziran'ın 4/5 günü alt sınırın altında: **oran kayması**, testte tüm modellerin fazla tahmin etmesinin sebebi |

*Not:* istatistik dersindeki "çok büyük örneklemde her fark anlamlı çıkar" uyarısı gereği **etki büyüklüğü** (fark ve $d$) $p$ değerinden daha çok kullanıldı (cinsiyet farkı anlamlı ama 0,6 puan).

---

## 11. Karar günlüğü: ne zaman, neyi, neden değiştirdik

| # | Konu | Önce | Sonra | Neden değişti | Ne zaman |
|---|---|---|---|---|---|
| 1 | **Simülasyonun riski** | Sentetik Beta(2,8) risk (mükemmel kalibre varsayım) | Gerçek RF riski ve gerçek gelme/gelmeme; sonra 27 günün **hepsi için** örneklem dışı risk | Sentetik riskle modelin gerçek değeri ölçülemez; yalnızca test haftası değil bütün günler gerekliydi | 2 Eki (`ad86649`, `8258799`) |
| 2 | **Şablon karşılaştırması** | Tek oturum | 27 günün tüm gerçek kayıtları, gün gün tablo | Tek oturum sonucu tesadüfe açık; gerçek hacmi göstermek | 2 Eki |
| 3 | **Simülasyonda doktor** | "Bir doktor" oturumu → "tüm doktorlar" (günün kayıtları ~220 doktora rastgele dağıtıldı) | **Hekim yok:** tek departman, kapasite birimi "muayene odası/oturum" | Veride doktor yok. "Bir doktoru 5.500 gün çalışmış gibi göstermek" fikri **reddedildi** (günde ~4.100 randevu tek hekime sığmaz; elimizdeki veriden hareket edilmeli). PM 17 Eki'de kapsamı daralttı (hekim adlandırılmaz) | 2 Eki → 16–17 Eki |
| 4 | **Etkileşimli simülasyon ekranı** | Çok seçenekli, karışık ekran | Türkçe, "bir odanın günü", ayar değişince otomatik hesap, tek ekrana sığar | Kullanıcı geri bildirimi: "çok kafa karıştırıcı", "ayarlar simülasyonu etkilemiyor gibi", "seçilen tarih görünmeli" | 16 Eki |
| 5 | **Muayene süresi** | 12 dk (serviste `kpi.service_minutes`) | **5–10 dk, ortalama 7,5** | Ekip kararı: devlet hastanesinde hasta başına 5–10 dk. Servis varsayımı kaynaksızdı | 17 Eki |
| 6 | **Slot süresi** | 15 dk → (kısa süre) **10 dk** türetildi → **15 dk** | 15 dk, 16 slot | 10 dk, "hasta başına 5–10 dk"tan **benim türetmemdi**, ekip onaylamadı; ekip "Türkiye'de genel 15 dk" dedi. **Kaynak taraması 15 dk'yı doğrulayamadı** (devlet hastanelerinde MHRS aralığı 5 dk bildiriliyor); hocaya soru olarak yazıldı | 17 Eki |
| 7 | **Günlük ek randevu sınırı** | Simülasyon 4, servis 2 | **4** (servis PR #64'te güncelleniyor) | İkisi aynı olmalı; 4 daha çok hasta kazandırıyor (15,5 vs 14,2) ve bekleme küçük | 17 Eki |
| 8 | **Bekleme sınırı** | Şablon seçiminde 5 dk | **15 dk** (poliklinik) | Ekip kararı ("15k" = 15 dk olarak okundu). Seçilen ayar zaten 5 dk'yı da karşılıyor, yani karar sınıra bağlı değil | 17 Eki |
| 9 | **Model** | LR + RF → DT eklendi | **RF kesin** (karar ağacı alternatif) | RF en iyi log-loss/PR-AUC; DT çok yakın ve çok küçük. Klinik sonuçta aynı. İki dal açıldı; dal sınırı yüzünden tek dala indirildi | 16–17 Eki |
| 10 | **Değerlendirme protokolü** | İlk raporlar: zamana göre 80/20 | + hiperparametre taraması, log-loss ölçütü, eşik eğitimden, sızıntı denetimi, ileri-pencere karşılaştırma | Makalenin %95'ini çürütürken **bizim** protokolümüzün de sızıntısız olduğunu kanıtlamak gerekti | 16–17 Eki |
| 11 | **Hatırlatma etkisi** | SMS verisinden etki çıkarma düşüncesi | **Kullanılmaz;** canlı A/B + varsayımsal senaryo | SMS verisi deney değil; SMS zaten riskli hastaya gitmiş (yanlış yön) | 2–17 Eki |
| 12 | **Teslim edilen kural** | Eşik, maliyet, havayolu | **Yalnızca eşik** | Maliyet r=1 tetiklenmiyor; diğerleri karşılaştırma olarak kalır; servis zaten eşik uyguluyor | 17 Eki |
| 13 | **Web taslakları** | 3 taslak; hekim ve hasta aynı ekranı görüyor, risk görünür | **2 taslak;** roller ayrı portal; risk, eşik ve overbooking **yalnızca yönetimde**; hasta tam takvim görür; "bugün" boş, veri günleri salt okunur; hekim → departman | Kullanıcı kararları: roller ayrışmalı; hasta ve hekim kural/overbook görmemeli; gerçek veri günleri hekim tarafından değiştirilmemeli; bugün boş olsun ki hasta panelinden alınan randevu sisteme işleniyor mu görülsün | 16–17 Eki |
| 14 | **Veri** | Bölüm yok | `Department = General Practice` sabit sütunu | "Departman bazlı" kararı; veri kuralı: eklenen sütun her satırda aynı | 17 Eki |
| 15 | **Karar yönetimi** | Kararlar sohbette | `docs/KARAR_LISTESI.md` + `docs/decisions.json` + `apply_decisions.py` | Bir karar değişince model, sonuçlar ve belgeler **tek komutla** yenilensin; çöp kod kalmasın | 16 Eki |

---

## 12. Hatalar ve düzeltmeler

| # | Ne oldu | Nasıl fark ettik | Düzeltme | Ders |
|---|---|---|---|---|
| 1 | **Negatif bekleme süresi:** erken gelen hasta randevu saatinden önce muayene edilmişti | Bekleme ortalamaları anlamsızdı | Muayene `max(randevu, geliş)` anından önce başlayamaz; düzeltmeden önceki bekleme rakamları **yanlıştı** (`73100c8`) | KPI tanımına koşul eklemek gerekiyor; sonuçları önce mantık denetiminden geçir |
| 2 | **Hızlı (quick) çalıştırma sonuçları yanlışlıkla commit'lendi** | Şablon sonuçları 150 tekrarla üretilmişti | Tam çalıştırmayla geri yüklendi (`5dff878`) | Şablon sonuçları ve çıktı klasörleri bugün `.gitignore`'dadır |
| 3 | **`imbalanced-learn` kurulumu numpy/scikit-learn/pandas'ı yükseltip ortamı bozdu** (makale çalışmasını yeniden üretirken) | Pandas içe aktarılamadı | Sürümler sabitlendi (numpy 1.24.4, scikit-learn 1.2.2, scipy 1.10.1); AUC'ler aynı çıktı; makale betiği **ayrı sanal ortamda** çalıştırılır (`ml/paper_replication.py` açıklaması) | Aracı ortama kurmadan önce ayrı venv |
| 4 | **Excel raporunda bir karşılaştırma değeri yanlış hesaplanmıştı** | Python ile çapraz kontrolde fark çıktı | Düzeltildi | Excel formüllerini Python'la çapraz doğrula |
| 5 | **Arayüz CSS sınıf çakışması** (`.room`) | Etkileşimli ekranda bileşen bozuldu | `inroom` olarak yeniden adlandırıldı | Genel sınıf adları çakışır |
| 6 | **Push reddedildi** (uzak `IEN` dalı ayrışmıştı) | Git hatası | `origin/IEN` birleştirildi, 4 çakışma çözüldü, lint düzeltildi (`500ed61`); **force push yapılmadı** | Başkasının işini ezme |
| 7 | **`main`'e doğrudan push reddedildi** (korumalı dal) | Git hatası | PR yolu (#62) | İş akışı kuralı |
| 8 | **Web taslağı 1:** günün sonunda boş slot yoktu; "ek randevu 8" iki kez işaretlendi; **taslak 2** açıklaması yanlış (min) riski kullandı | Tarayıcıda denerken | "12. randevu anındaki durum" (sonra tamamen yeniden tasarlandı); `extra` bayrağı; 1. hastanın riski ve eşiğe duyarlı metin | Gerçek veriyle arayüzü denemek |
| 9 | **Servis ve simülasyon ayarı farklıydı:** limit 2 vs 4, muayene 12 vs 7,5 | `parity_check.py` fark yazdırdı | Karar listesi; PR #64 | Aynı kural **ve aynı ayar** |
| 10 | **`ml/models/` yanlış scikit-learn sürümüyle (1.2.2) yazıldı** ve commit'lendi (`50cba11`) | Birleşme çakışmasında boyutlar farklıydı (14,7 MB vs 16,3 MB) | `main`'deki 1.9.1 sürümü alındı; bundan sonra bu komut sanal ortamda çalıştırılır (`TEKRAR_URETIM.md` uyarısı) | Model dosyası = sürüm bağımlı |
| 11 | **Depo temizliği `IEN` ve `IEN-RandomForest` dallarını sildi** (kural: kişi başı tek dal; fazlası arşiv etiketine alınıp silinir) | GitHub'da dallar görünmüyordu | Önce tek dala indirildi (iki model aynı dalda), sonra PM 3 dala izin verdi, sonra muaf tuttu; dallar geri açıldı; PR yeniden bağlandı | CI ve iş akışı kurallarını oku |
| 12 | **PR #62 `main` ile çakıştı;** CI çalışmadı | `gh pr checks` "no checks" | `main` birleştirildi, model dosyalarında `main` sürümü alındı | Çakışan PR'da CI koşmaz |
| 13 | **Excel dosyası açıkken yazılamadı** (`Permission denied`) | `clean_data.py` hata verdi | Dosya kapatıldı, yeniden çalıştırıldı | Excel dosyayı kilitler |
| 14 | **"Doktor"→"muayene odası" toplu değişimde bozulan kod:** `clinic room = simpy.Resource(...)` geçersiz Python; "names no clinic room" anlamsız cümle | Lint ve okuma | Değişken `room`; cümle "names no physician" | Toplu metin değişimini çalıştırarak doğrula |
| 15 | **15 dk slot varsayımı kaynaksızdı** | Kaynak taraması | Karar geçici onaylı; hocaya soru | Varsayımı kaynakla destekle |
| 16 | **`dummy-v0`'a bağlı iki servis testi** model değişince kırıldı | Servis testleri | Maintainer testleri yeni sürüme çekti (`94f9c93`) | Model sürümünü testte sabit yazma |

---

## 13. Uygulama, servisler ve web taslakları (CEN tarafı ve bağlantı)

### 13.1 Mimari (kısa)

Web arayüzü (React) → web backend (FastAPI) → her randevudan önce **overbooking servisine** sorar (`/booking-decision`) → servis özellikleri hesaplar, **modeli** çalıştırır (`/predict`), **eşik kuralını** uygular, kararı **nedeniyle** kaydeder, onay ve hatırlatma mesajlarını zamanlar. **Admin servisi** (yalnızca iç ağ) KPI ekranı ve hesap yönetimi sağlar. PostgreSQL ortak veritabanıdır. Docker Compose ile ayağa kalkar, CI testleri (ruff, pytest, PostgreSQL) çalıştırır.

### 13.2 Servisin API'si (özet)

| Uç nokta | Ne yapar |
|---|---|
| `POST /predict` | Hasta ve randevu tarihinden özellik hesapla, gelmeme olasılığını döndür |
| `POST /booking-decision` | Slot ve hasta için: izin var mı, overbooking mi, **neden** |
| `POST /events/appointment-booked`, `…-cancelled` | Onay ve hatırlatma mesajlarını zamanla ya da iptal et (onay ≤1 dk, hatırlatma 24 saat önce; yakın randevuya hatırlatma yok) |
| `GET /ab/summary` | Hatırlatma ve kontrol gruplarının gelmeme oranı, iki oran z-testi |
| `GET /kpi` | Doktor/gün için doluluk, boşta kalma, mesai aşımı, ortalama bekleme (sabit süre, zamanında gelen hasta varsayımıyla) |

**A/B grupları** hastaya göre sabittir (tuzlu özet, `salt: reminder-ab-v1`): aynı hasta hep aynı gruptadır; kontrol grubu hatırlatma almaz.

### 13.3 Simülasyonla servisin aynı karar verdiğinin kanıtı

`simulation/parity_check.py` 20.000 rastgele slot üretir (risk listesi, kapasite, günlük sayaç, eşik, sınır) ve hem `overbooking_service.rules.decide` hem `clinic_sim.threshold_rule` ile karar alır: **0 fark**. Ayarlar ise ayrışıyordu (limit 2 / 4); PR #64 bunu düzeltir. Servisin kendi testleri (150) ve kabul kontrolleri, kopya üzerinde RF ile denendi: `/predict` risk 0,12 (güvenilir yaşlı hasta) ve 0,36 (geçmişinde gelmeme olan genç hasta); `/booking-decision` riskli hastanın slotunda overbook ("daily overbooks 0/4"), güvenilir hastanın slotunda ret.

### 13.4 Web taslakları (IEN'in uygulama önerisi)

`docs/web-designs/design1.html` (kurumsal portal, aylık takvim) ve `design2.html` (haftalık takvim ızgarası, karar açıklama paneli). Üretim: `simulation/web_designs/build.py` + ortak `common.js` + `records.js` (27 günün 110.521 gerçek kaydı, 1,9 MB). **Davranış kuralları:** hasta yalnızca "müsait/dolu" görür, departman ekranı günün programını (saat, no, yaş) görür; **risk, eşik, overbooking, A/B grubu yalnızca yönetimde**; veri günlerinde (29 Nisan–8 Haziran) departman ekranı "geldi/gelmedi" işaretleyemez (kayıt salt okunur); "bugün" (9 Haziran) boş başlar, hasta panelinden alınan randevu departmanın günlük listesine ve yönetim karar kaydına düşer; üç demo hasta arasında geçilebilir ki ikinci hasta ek randevu alabilsin; yönetimde 27 günden biri seçilir (o günün bir oturumu). **Sınırlar:** model API'si bağlı olmadığından yeni randevunun riski gerçek risk dağılımından örneklenir ("örnek" etiketli); A/B tablosu `SMS_received`'dan hesaplanır, gerçek deney değil.

---

## 14. Depo ve iş akışı: dallar, PR'lar

- **Dallar:** `main` (korumalı; yalnızca PR ile), `IEN` (ana çalışma dalı, PR #62), `IEN-RandomForest` (IEN ile aynı), `IEN-DecisionTree` (alternatif), `IEN-service-settings` (servis ayarı, PR #64). Eski modeller arşiv etiketlerinde (`archive/…`).
- **Commit biçimi:** tek satır `tür: Emir kipinde kısa mesaj`. Tarihsel IEN commit'leri serbest biçimliydi (squash birleştirme önerildi).
- **Önemli PR/issue'lar:** #62 (IEN çalışması), #64 (servis ayarları), #65 (model teslimi, birleşti), issue #6 (özellik listesi, "agreed"), #7 (model teslimi), #8 (kural ve eşik; karar yazıldı), #9 (KPI ve oturum parametreleri; yazıldı), #11 (main'i IEN ile güncelle), #61 (veri kuralları).
- **Üretilen dosyalar** (`.gitignore`): `ml/data/processed/` (Excel ve CSV'ler), `simulation/output/`, şablon sonuçları. Herkes betiklerle yeniden üretir.
- **Tekrar üretim:** `docs/TEKRAR_URETIM.md`. Yeni sanal ortamda (Python 3.11, pandas 3.0.6, numpy 2.4.6, scikit-learn 1.9.1) tüm hat çalıştırıldı: `SONUC_OZETI.md` ve `BEKLEME_DAGILIMI.md` **birebir aynı**; model raporu yalnızca üçüncü ondalıkta farklı.

---

## 15. Sınırlılıklar ve açık işler (dürüst liste)

| Konu | Durum |
|---|---|
| **Randevu saati yok** | Veride tüm `AppointmentDay` 00:00. Saat, oda ve slot simülasyonda üretilir; gerçek gün içi akış ölçülemez. Hocaya soru (`HOCAYA_SORULACAKLAR.md`) |
| **Muayene süresi, slot, gecikme, talep varsayım** | Muayene 5–10 dk haberle dolaylı destekli; **15 dk slot için kaynak yok**; gecikme ve talep kaynaksız. Geçici onaylı, hoca onayı bekliyor |
| **27 gün** | Mevsimsellik ve haftalık kalıp değerlendirilemez; tek zaman bölmesi |
| **Dış geçerlilik** | Veri Brezilya (2016); Türkiye için doğrudan geçerlilik yok |
| **Tahmin gücü sınırlı** | AUC 0,73; model en çok %50 civarı risk üretir; yüksek eşikler hiç tetiklenmez |
| **Kapasite bol** | Doluluk %40–49; kuralın asıl değeri bu boş kapasiteyi kullanmak, slot kısaltma benzer kazanç verir |
| **Bekleme dağılımı** | Ortalama 1,1 dk ama %0,8 hasta >15 dk; kurum hasta başına sınır isteyebilir |
| **Hatırlatma etkisi** | Ölçülmedi; canlı A/B testi gerekir |
| **Adillik** | 0,30 eşiğinde yeni hastaların %34'ü riskli sayılıyor (tekrar gelen %17,5); grup bazlı kalibrasyon analizi yapılmadı |
| **Oda sayısı** | Verinin günlük hacminden türer (~220 oturum), gerçek kapasite değil |
| **Servis ve web uyumu** | Servis ayarları PR #64'te; web uygulaması 20 dk slot kullanıyor (15'e çekilmeli); servis KPI'ı sabit süre ve zamanında gelişle hesaplıyor (simülasyon: değişken süre ve gecikme) |
| **Uçtan uca test** | IEN görevi değil; CEN ile ayrı iş (tahmin → karar → randevu → KPI) |
| **Ortak sözleşmeler** | `docs/features.md` ve `docs/api-contract.md` içinde eski "bir doktor" ifadeleri duruyor (sahibi PM/CEN) |

---

## 16. Sunumda sorulabilecek sorular ve yanıtları

**Problem ve yaklaşım**

1. **"Neden overbooking? Neden slot kısaltmıyorsunuz?"** İkisi de denendi: kısa slot (20×12) kuralsız +3,2 hasta verir; overbooking +2,8. İkisi birbirinin yerine geçer, birlikte ek kazanç yok. Kısa slot muayene sürelerinin tutarlı kısa olduğu bir kliniğe uyar; overbooking süre değişkenliği yüksekken (ve gelmeme tahmin edilebilirken) mantıklı.
2. **"Başlangıçtaki iddia 'bekleme ve boşta kalma birlikte iyileşir'di, çıktı mı?"** Hayır. Boşta kalma azalıyor (−20 dk), bekleme artıyor (+0,9 dk). Dürüstçe raporluyoruz; bedeli küçük ama sıfır değil.
3. **"Bu sonuç Türkiye için geçerli mi?"** Veri Brezilya 2016; model kalıbı (lead time, yaş) genellenebilir ama oranlar değil. Türkiye değerleri (muayene 5–10 dk) varsayım olarak girildi.

**Veri ve model**

4. **"AUC neden yalnızca 0,73?"** Elimizde yalnızca randevu alındığı anda bilinen özellikler var (yaş, lead time, geçmiş...). Gelmemenin nedenleri (unutkanlık, ulaşım) veride yok. Aynı veride literatürdeki %95 sızıntıdan; hatasız protokolle AUC ≈ 0,72.
5. **"Doğruluk yerine neden AUC ve kalibrasyon?"** %80 gelen veride "herkes gelir" %79,8 doğruluk alır. Doğruluk aldatıcı. Overbooking **olasılığı** eşikle karşılaştırdığı için kalibrasyon (tahmin ≈ gerçek oran) en kritik ölçüt.
6. **"Brier ve log-loss ne işe yarar?"** İkisi de olasılık tahminini cezalandıran "uygun" puanlardır. Log-loss ile hiperparametre seçtik çünkü olasılık kalitesini ölçüyor.
7. **"Random forest neden, karar ağacı neden değil?"** Log-loss ve PR-AUC biraz iyi; sonuçta klinik fark yok. Ağaç anlatılabilir ve 3 KB; RF 16 MB. Ekip RF'yi seçti, ağaç alternatif olarak korundu.
8. **"Veri sızıntısı var mı?"** Beş denetim yaptık: özellik listesi temiz; eğitim günleri test günlerinden önce; geçmiş özellikleri randevu alma gününden önceki randevulardan hesaplanıyor (3.000 satırda bağımsız doğrulandı); ölçekleme yalnızca eğitimde; eşik testten seçilmedi. Simülasyon riskleri dönüşümlü katlarla üretiliyor; ileri-pencereyle karşılaştırdık: AUC 0,731 vs 0,729.
9. **"SMS neden özellik değil?"** Randevu alındıktan sonra gider; alındığı anda bilinmez (sızıntı). Ayrıca SMS alan grup zaten riskli: fark nedensel okunamaz.
10. **"Gelmeme oranı değişirse model ne olur?"** Eğitimde %20,6, testte %18,5: tahminler biraz yüksek (kalibrasyon kesişimi −0,14). p kontrol grafiği ile izlenmeli, periyodik yeniden kalibrasyon önerilir.
11. **"Yeni hastalarda model çalışır mı?"** AUC 0,721 (tekrar gelen 0,737). Ama yeni hastaların %34'ü riskli sayılıyor; ek randevu çoğunlukla onların slotlarında açılır. Bunu adalet notu olarak raporluyoruz.
12. **"R4 neden var, modelden kötü ise?"** Model yokken ve yeni hastada olasılık verebilen yedek; ayrıca modelin değerini ölçen taban (AUC 0,577 vs 0,729).
13. **"Düzeltmedeki $k=5$ nereden?"** Varsayılan başlangıç; Beta–Binomial sonsal ortalamasına eşdeğer ("5 sanal randevu"). Doğrulama kümesinde ayarlanmadı: açık sınırlılık.

**Overbooking kuralı**

14. **"Neden `min(riskler) ≥ eşik`?"** İkinci hasta, ilk hasta gelmezse işe yarar. Slottakilerden biri güvenilirse çakışma olur; hepsinin riskli olması gerekir.
15. **"Neden slot başına en çok 2 hasta?"** Kuyruğun zincirleme büyümesini sınırlar; formül belgesinde başlangıç önerisi; üçüncü hasta için gerekçe yok.
16. **"Neden günlük sınır 4?"** Hasta kazancının neredeyse tamamını verir (tavanın %97'si) ve beklemeyi küçük tutar. Formül belgesindeki %10 önerisi başlangıçtı; simülasyon ızgarasıyla 4 seçildi.
17. **"Maliyet kuralı neden teslim edilmedi?"** Model riski en çok %50 olduğundan $r=1$ ($\tau=0{,}5$) hiç tetiklenmiyor; $r=0{,}5$ daha az hasta ekliyor. Eşik kuralı özel bir hâli ve serviste var.
18. **"Eşik %30 nasıl bulundu?"** Servisin varsayılanıydı; ızgara (eşik 0,15–0,50 × sınır 1–8) ile Pareto analizi yaptık. %20 +0,4 hasta daha verir, beklemeyi biraz artırır; %30 makul denge.

**Simülasyon**

19. **"Neden SimPy ve neden `Resource(capacity=1)`?"** Süreç tabanlı ayrık olay simülasyonu, kuyruk dinamiğini doğal modelliyor; bir muayene odası aynı anda tek hasta görür, kapasite 1.
20. **"Beklemeyi neden `başlangıç − max(randevu, geliş)` tanımladınız?"** Erken gelen hasta randevu saatinden önce muayene edilemez; ilk sürümde bunu yapmadığımız için negatif bekleme çıktı.
21. **"Muayene süresi neden log-normal?"** Pozitif ve sağa çarpık (çoğu kısa, bazıları uzun). Ortalamayı koruyacak şekilde ($\mu=\ln m-\sigma^2/2$) parametrelendirdik. Derste üstel var; üstel kullanılırsa bekleme belirgin artar (duyarlılık denendi).
22. **"Neden ortak rastgele sayılar?"** İki politikayı aynı hastalarla, aynı gelme ve sürelerle yarıştırmak için: fark şanstan değil politikadan gelir; güven aralıkları daralır.
23. **"Neden 2.000 tekrar?"** Güven aralığı yarı genişliği $1{,}96\,s/\sqrt{n}$; 1.000 tekrar ≈ ±0,29 dk, 2.000 daha dar. Sonuçlar tekrarlanabilir (sabit tohum).
24. **"Eşleştirilmiş fark ve $d_z$ nedir?"** Aynı oturumda politika − taban farkı; $d_z$ = ortalama fark ÷ farkın standart sapması (etki büyüklüğü).
25. **"Gelme/gelmeme gerçek mi, simüle mi?"** Gerçek: modelin riski ve gerçek sonuç. Simüle: muayene süresi, geç kalma, oda ve slot ataması (veride yok).
26. **"Oda sayısı nereden?"** Bir günün randevuları ≤20'lik gruplara rastgele bölünür (~220 oturum). Veride hekim/oda bilgisi yok; bu bir varsayım, sonuçlar oturum başına.
27. **"Neden 15 dk slot, 7,5 dk muayene? Doluluk neden düşük?"** Ekip kararı; slotun yarısı kullanılıyor. Düşük doluluk kapasitenin bol olduğunu gösterir. Slot kaynağı doğrulanamadı; hocaya soru. Devlet hastanesi senaryosunda 5–10 dk slot da olabilir; sonuçlar yeniden üretilebilir.
28. **"15 dk bekleme sınırı kararı etkiliyor mu?"** Hayır: seçilen ayarda ortalama bekleme 1,1 dk, %95'inci yüzdelik 7,7 dk; 5 dk'lık bir ortalama sınırını da karşılar. Ama hastaların %0,8'i 15 dk'dan uzun bekler; hasta başına sınır daha doğru olur.
29. **"Servisle simülasyon aynı mı?"** Kural: evet (20.000 slotta 0 fark). KPI hesabı: farklı; servis sabit muayene süresi ve zamanında gelen hasta varsayar, simülasyon değişken süre ve gecikme.

**Veri kuralları ve süreç**

30. **"Neden `Department` sabit sütunu?"** Proje kuralı: eklenen sütun her satırda aynı değer taşır, veriyi değiştirmez; sistem tek departman. Model özelliği değildir.
31. **"Neden hekim yok?"** Veri hekim bilgisi içermiyor; günde ~4.100 randevu tek hekime sığmaz; kapasite departmana aittir (PM kapsamı).
32. **"Randevu saati eklenecek mi?"** Veri kuralı: saat eklenmez. Hocaya soru (`HOCAYA_SORULACAKLAR.md`).
33. **"Sonuçlar tekrar üretilebilir mi?"** Evet; `docs/TEKRAR_URETIM.md`; yeni ortamda hat çalıştırıldı, sonuç özeti birebir aynı.
34. **"Hatırlatma işe yarıyor mu?"** Bilmiyoruz. Veride deney yok; servis A/B testi ölçecek. Simülasyonda varsayımsal senaryo: etki %30 ise overbooking'in ek kazancı 2,8 → 1,9 hastaya düşer.
35. **"En zayıf varsayımınız hangisi?"** Slot süresi (kaynak bulunamadı) ve muayene süresinin dağılımı; ikisi de sonucu büyütüp küçültür. Duyarlılık tablosu bunu gösteriyor.

---

## 17. Hızlı başvuru

### 17.1 Komutlar

```bash
python ml/data/clean_data.py                  # veriyi temizle, appointments_clean.xlsx üret (Excel kapalı olmalı)
cd ml
python build_reports.py                       # LR/RF Excel raporları, 27 gün risk dosyası
python evaluate_models.py                     # docs/MODEL_KARSILASTIRMA.md
python apply_decisions.py                     # karar listesine göre model + deneyler + bekleme dağılımı
python apply_decisions.py --model-only        # yalnızca modelleri yeniden eğit (sanal ortamda)
python leakage_check.py                       # zamansal sızıntı ve protokol denetimi
cd ../simulation
python main.py --no-open                      # tüm sonuç sayfaları
python app.py                                 # etkileşimli simülasyon (masaüstü pencere gibi)
python parity_check.py                        # servis kuralı = simülasyon kuralı mı
python web_designs/build.py                   # web taslakları (docs/web-designs/)
```

### 17.2 Dosya haritası (IEN)

```
docs/Anlatım.md                  bu dosya
docs/KARAR_LISTESI.md, decisions.json   kararlar (tek kaynak) ve makine tarafı
docs/formulas/                   forecast, probability, statistics, quality-control, rules, overbooking
docs/MODEL_KARSILASTIRMA.md      LR/RF/DT, protokol, alt gruplar (üretilir)
docs/IEN_DENEY_SONUCLARI.md, SONUC_OZETI.md, BEKLEME_DAGILIMI.md   deney sonuçları (üretilir)
docs/ZAMANSAL_SIZINTI_KONTROLU.md, SERVIS_UYUM_RAPORU.md
docs/KPI_VE_VARSAYIM_KARSILASTIRMASI.md, KAYNAK_ARASTIRMASI.md, HOCAYA_SORULACAKLAR.md
docs/IEN_RAPOR_TASLAGI.md, DEMO_VE_JURI_HAZIRLIGI.md, TEKRAR_URETIM.md, LITERATUR_INCELEMESI.md, IEN_DURUM_OZETI.md
docs/web-designs/                web taslakları (design1.html, design2.html, records.js, data.json)
ml/data/clean_data.py            temizleme
ml/build_reports.py              LR, RF, Excel raporları, 27 gün riskleri
ml/evaluate_models.py            sızıntısız karşılaştırma
ml/apply_decisions.py            karar listesinden modele ve sonuçlara
ml/export_model.py, export_candidate.py   modelin teslimi ve servis kabul kontrolü
ml/leakage_check.py, paper_replication.py
ml/models/                       model.joblib, feature_schema.json, candidates/
simulation/clinic_sim.py         SimPy çekirdeği (SessionConfig, politikalar, book, simulate_session, run)
simulation/experiments.py, wait_distribution.py, parity_check.py
simulation/app.py, ui/app.html, main.py, real_days.py, live_day.py, value_ladder.py, dashboard.py, plots.py
simulation/templates/            T1, T2, T3, karşılaştırma, gün gün
simulation/web_designs/          web taslakları üreticisi
```


---

## Ek A. Tüm commit'ler (ilk commit'ten son commit'e, 185 adet)

Faz numaraları Bölüm 3'tekilerdir (1 iskelet, 2 IEN günü, 3 entegrasyon, 4 veri kuralları, 5 IEN genişlemesi, 6 kapsam daralması ve teslim). `Merge pull request` satırları PM'in PR birleştirmeleridir. Bu liste `git log --reverse` çıktısıdır; her commit'in içeriğini görmek için `git show <hash>`.

| # | Commit | Tarih | Yazar | Mesaj | Faz |
|---|---|---|---|---|---|
| 1 | `16723f6` | 2026-09-26 00:40 | cnrasili | chore: Initialize repository structure | 1 |
| 2 | `67ca17a` | 2026-09-26 01:05 | cnrasili | chore: Set up project structure and tech stack | 1 |
| 3 | `026baac` | 2026-09-26 01:16 | cnrasili | docs: Add project scope to README | 1 |
| 4 | `08b235b` | 2026-09-26 01:21 | cnrasili | chore: Improve Docker portability across machines | 1 |
| 5 | `048a0c1` | 2026-09-26 01:42 | cnrasili | feat: Add prediction endpoint with placeholder model | 1 |
| 6 | `99dc7d5` | 2026-09-26 01:53 | cnrasili | feat: Validate delivered models and add export helper | 1 |
| 7 | `c4f8ff0` | 2026-09-26 02:04 | cnrasili | docs: Mark feature list as proposal and add required booking data | 1 |
| 8 | `181d870` | 2026-09-26 02:09 | cnrasili | chore: Add code owners | 1 |
| 9 | `b870a7f` | 2026-10-01 19:38 | cnrasili | feat: Add slot-level overbooking rule engine and booking decision endpoint | 1 |
| 10 | `0572dd2` | 2026-10-01 20:26 | cnrasili | feat: Add confirmation and reminder messages with scheduled dispatch | 1 |
| 11 | `bede9fd` | 2026-10-02 14:49 | Hazar İkizler | Add formulas docs structure and ignore local notes | 2 |
| 12 | `421e964` | 2026-10-02 15:01 | Hazar İkizler | Add formulas extracted from forecasting course | 2 |
| 13 | `c5965ea` | 2026-10-02 15:12 | Hazar İkizler | Add rule-based show-up probability rules | 2 |
| 14 | `c128111` | 2026-10-02 15:17 | Hazar İkizler | Rewrite show-up rules in formal specification form | 2 |
| 15 | `1c1af6d` | 2026-10-02 15:19 | Hazar İkizler | Add combined cold-start rule R4 | 2 |
| 16 | `72b758b` | 2026-10-02 15:19 | Hazar İkizler | Fix rounding in R4 example | 2 |
| 17 | `ef87ecc` | 2026-10-02 15:19 | Hazar İkizler | Fix rounding in R4 example | 2 |
| 18 | `e3b4da8` | 2026-10-02 15:21 | Hazar İkizler | Add cost-based overbooking rule adapted from airline practice | 2 |
| 19 | `bb6e673` | 2026-10-02 15:56 | Hazar İkizler | Add SimPy clinic session simulation with fixed, threshold and cost-based policies | 2 |
| 20 | `73100c8` | 2026-10-02 15:59 | Hazar İkizler | Add simulation charts and fix consultations starting before appointment time | 2 |
| 21 | `7b7c815` | 2026-10-02 16:02 | Hazar İkizler | Add step-by-step value comparison of booking policies | 2 |
| 22 | `11e5bfd` | 2026-10-02 16:05 | Hazar İkizler | Add KPI card dashboard for simulation results | 2 |
| 23 | `5256f02` | 2026-10-02 16:13 | Hazar İkizler | Add three appointment templates, comparison and winner | 2 |
| 24 | `91c1986` | 2026-10-02 16:50 | Hazar İkizler | Merge docs/formulas into IEN and add ml data cleaning and report scripts | 2 |
| 25 | `d3321cc` | 2026-10-02 16:55 | Hazar İkizler | Add statistics course formulas and checks of project calculations | 2 |
| 26 | `e5f839d` | 2026-10-02 16:57 | Hazar İkizler | Rename statistics.md to probability.md | 2 |
| 27 | `e6cecb8` | 2026-10-02 17:02 | Hazar İkizler | Add statistics and statistical quality control formulas with data checks | 2 |
| 28 | `ad86649` | 2026-10-02 17:05 | Hazar İkizler | Add IEN status summary and write simulation risk file from report script | 2 |
| 29 | `bced142` | 2026-10-02 17:53 | Hazar İkizler | Add simulation main.py that runs every step and builds a results page | 2 |
| 30 | `cc49531` | 2026-10-02 17:58 | Hazar İkizler | Add live SimPy clinic day animation and event log, wire into main.py | 2 |
| 31 | `60c09b2` | 2026-10-02 18:01 | Hazar İkizler | Open the live simulation directly from main.py and support older browsers | 2 |
| 32 | `5dff878` | 2026-10-02 18:02 | Hazar İkizler | Open live simulation from main.py; restore full-run template results | 2 |
| 33 | `20ba0df` | 2026-10-02 18:10 | Hazar İkizler | Live simulation replays real appointment records of the test period | 2 |
| 34 | `753be45` | 2026-10-02 18:20 | Hazar İkizler | Add whole-day simulation of every real appointment record | 2 |
| 35 | `d836ec2` | 2026-10-02 18:24 | Hazar İkizler | Make the whole-day view readable: one square per doctor, counters, tooltips and drill-down | 2 |
| 36 | `37e1617` | 2026-10-02 18:58 | Hazar İkizler | Add day-by-day baseline vs rules table with counts and percentage changes | 2 |
| 37 | `8258799` | 2026-10-02 19:07 | Hazar İkizler | Template comparison on all 27 real days: overall cards and day-by-day tables; out-of-sample risks for every day | 2 |
| 38 | `be9e69b` | 2026-10-02 19:14 | Hazar İkizler | Group the results page into Simulation, Templates and Charts hubs with explanations | 2 |
| 39 | `d933cc5` | 2026-10-02 19:36 | Davut can cüci | feat: Add patient, doctor, slot and appointment tables | 2 |
| 40 | `d9dfaf1` | 2026-10-02 19:36 | Davut can cüci | test: Add core booking table tests | 2 |
| 41 | `3a8e126` | 2026-10-02 19:45 | Hazar İkizler | Add a back button to every result page | 2 |
| 42 | `23c5c1b` | 2026-10-03 16:10 | Hazar İkizler | feat: Add SimPy clinic simulation, appointment templates and model reports | 3 |
| 43 | `7602097` | 2026-10-03 16:26 | cnrasili | chore: Clean up simulation and model scripts for lint and pandas 3 | 3 |
| 44 | `5541337` | 2026-10-03 16:45 | Caner Aşılıoğlu | Merge pull request #2 from cnrasili/integration/core-tables-and-ien | 3 |
| 45 | `bdbbb9e` | 2026-10-03 18:12 | Davut can cüci | fix: Enforce slot capacity and appointment dates in the database | 3 |
| 46 | `2aeb03b` | 2026-10-03 18:12 | Davut can cüci | test: Add PostgreSQL trigger tests for core tables | 3 |
| 47 | `90b7905` | 2026-10-04 14:30 | Caner Aşılıoğlu | Merge pull request #3 from cnrasili/fix/core-table-constraints | 3 |
| 48 | `f81a02e` | 2026-10-04 14:37 | cnrasili | chore: Add automatic cleanup of outdated branches | 3 |
| 49 | `9b188f9` | 2026-10-04 15:03 | cnrasili | feat: Read patient and slot data from booking tables | 3 |
| 50 | `300b4c2` | 2026-10-04 15:35 | cnrasili | feat: Add reminder A/B assignment and no-show summary | 3 |
| 51 | `3cec744` | 2026-10-04 18:15 | Davut can cüci | feat: Add user account and session tables | 3 |
| 52 | `18ff755` | 2026-10-04 18:16 | Davut can cüci | feat: Add password login with session tokens | 3 |
| 53 | `f4a614a` | 2026-10-04 18:17 | Davut can cüci | feat: Generate slots from doctor working hours | 3 |
| 54 | `bd503a0` | 2026-10-04 18:18 | Davut can cüci | feat: Add slot listing and patient booking endpoints | 3 |
| 55 | `508d2d7` | 2026-10-04 18:19 | Davut can cüci | feat: Add doctor calendar and attendance endpoints | 3 |
| 56 | `21ee7fe` | 2026-10-04 18:20 | Davut can cüci | feat: Add demo seed data | 3 |
| 57 | `1b56e7a` | 2026-10-04 18:20 | Davut can cüci | docs: Document demo data and login | 3 |
| 58 | `5c05d5f` | 2026-10-04 18:24 | Davut can cüci | feat: Add login and patient booking screens | 3 |
| 59 | `d8d591c` | 2026-10-04 18:26 | Davut can cüci | feat: Add doctor calendar screen | 3 |
| 60 | `42493f7` | 2026-10-04 21:54 | Davut can cüci | feat: Add patient details and working hours for the doctor views | 3 |
| 61 | `bb36a6e` | 2026-10-04 22:00 | Davut can cüci | feat: Redesign the interface as a clinic appointment system | 3 |
| 62 | `0867b84` | 2026-10-04 22:25 | cnrasili | feat: Add schedule KPI endpoint and dashboard | 3 |
| 63 | `c2bc1ce` | 2026-10-04 22:34 | cnrasili | feat: Add demo data generator and end-to-end booking flow test | 3 |
| 64 | `a972ce4` | 2026-10-04 23:02 | cnrasili | fix: Serve Chart.js locally and add per-patient A/B summary | 3 |
| 65 | `bc06a40` | 2026-10-04 23:02 | cnrasili | chore: Merge CEN-1 booking application from cen1/davut-cuci | 3 |
| 66 | `00f483f` | 2026-10-05 00:51 | Davut can cüci | test: Use a slot range start that is always in the past | 3 |
| 67 | `2a87ecc` | 2026-10-05 00:52 | Davut can cüci | feat: Ask the overbooking service before booking a slot | 3 |
| 68 | `19d5852` | 2026-10-05 00:54 | Davut can cüci | feat: Offer extra appointments in partly booked slots | 3 |
| 69 | `d7d4128` | 2026-10-05 00:54 | Davut can cüci | docs: Describe the overbooking call in the backend README | 3 |
| 70 | `9aec3fe` | 2026-10-05 01:12 | Davut can cüci | feat: Report booked and cancelled appointments to the overbooking service | 3 |
| 71 | `57e366a` | 2026-10-05 01:12 | Davut can cüci | docs: Describe the appointment event calls | 3 |
| 72 | `4d87cb1` | 2026-10-05 01:26 | Davut can cüci | feat: Add landing page, separate patient and doctor login and page addresses | 3 |
| 73 | `25ed36d` | 2026-10-05 01:26 | Davut can cüci | fix: Name the patient in attendance button labels | 3 |
| 74 | `2894a10` | 2026-10-05 01:28 | Davut can cüci | feat: Add several doctors and branches to the demo data | 3 |
| 75 | `a8a3944` | 2026-10-05 01:29 | Davut can cüci | docs: List the frontend pages and their addresses | 3 |
| 76 | `07f2fbf` | 2026-10-05 02:21 | cnrasili | docs: Extend project scope to several physicians and departments | 3 |
| 77 | `3bc1a9b` | 2026-10-05 02:27 | Caner Aşılıoğlu | Merge pull request #5 from cnrasili/cen1/davut-cuci | 3 |
| 78 | `b5bb302` | 2026-10-05 23:25 | cnrasili | docs: Refresh README with features, architecture diagram and status | 3 |
| 79 | `da4fcca` | 2026-10-06 12:49 | Davut can cüci | feat: Extend demo slots to three past weeks | 3 |
| 80 | `dc6a38f` | 2026-10-06 12:55 | Davut can cüci | feat: Build the service demo history on the web backend seed | 3 |
| 81 | `77e3932` | 2026-10-06 22:16 | cnrasili | docs: Add issue and pull request templates with scope rule | 3 |
| 82 | `c702889` | 2026-10-06 22:16 | cnrasili | docs: Deliver the trained model through ml/models | 3 |
| 83 | `9b2caee` | 2026-10-06 22:19 | Davut can cüci | revert: Remove the overbooking service demo changes | 3 |
| 84 | `2fc4930` | 2026-10-06 22:33 | Caner Aşılıoğlu | Merge pull request #12 from cnrasili/cen1/davut-cuci | 3 |
| 85 | `ff208d0` | 2026-10-06 22:58 | cnrasili | feat: Build the overbooking service demo on the web backend seed | 3 |
| 86 | `1045285` | 2026-10-06 23:02 | Caner Aşılıoğlu | Merge pull request #14 from cnrasili/cen2/demo-on-seed | 3 |
| 87 | `9177152` | 2026-10-07 13:53 | Davut can cüci | feat: Log patients in with national ID number | 3 |
| 88 | `81572d6` | 2026-10-07 13:56 | Davut can cüci | feat: Add account creation and an internal account API | 3 |
| 89 | `27c05fb` | 2026-10-07 13:58 | Davut can cüci | fix: Skip new slots that overlap existing ones | 3 |
| 90 | `d79b59f` | 2026-10-07 13:59 | Davut can cüci | feat: Make the default slot length configurable | 3 |
| 91 | `41f518b` | 2026-10-07 18:36 | cnrasili | feat: Add the admin service with secure login and the KPI screen | 3 |
| 92 | `5360364` | 2026-10-07 18:38 | Caner Aşılıoğlu | Merge pull request #25 from cnrasili/cen2/admin-service | 3 |
| 93 | `76c2b14` | 2026-10-07 19:40 | Davut can cüci | Merge remote-tracking branch 'origin/main' into cen1/davut-cuci | 3 |
| 94 | `ab0ca93` | 2026-10-07 19:41 | Davut can cüci | fix: Base the national ID migration on the admin tables | 3 |
| 95 | `5e852c0` | 2026-10-07 20:43 | Davut can cüci | fix: Keep the session token in memory only when storage fails | 3 |
| 96 | `cd5e289` | 2026-10-07 20:43 | Davut can cüci | test: Add frontend tests for the patient and doctor flows | 3 |
| 97 | `b1999d1` | 2026-10-07 22:43 | cnrasili | fix: Give demo and test patients fictional national ID numbers | 3 |
| 98 | `ed75640` | 2026-10-07 22:43 | cnrasili | chore: Configure the internal API token, slot length and frontend tests | 3 |
| 99 | `ad1e358` | 2026-10-07 22:45 | Caner Aşılıoğlu | Merge pull request #26 from cnrasili/cen1/davut-cuci | 3 |
| 100 | `fe7d7df` | 2026-10-07 22:45 | Caner Aşılıoğlu | Merge pull request #27 from cnrasili/cen2/national-id | 3 |
| 101 | `cce499e` | 2026-10-07 23:05 | cnrasili | fix: Publish internal service ports on the loopback interface only | 3 |
| 102 | `ee9f138` | 2026-10-07 23:06 | Caner Aşılıoğlu | Merge pull request #28 from cnrasili/cen2/loopback-ports | 3 |
| 103 | `bc8959c` | 2026-10-07 23:09 | cnrasili | feat: Add a command to install a delivered model | 3 |
| 104 | `66685f7` | 2026-10-07 23:11 | Caner Aşılıoğlu | Merge pull request #29 from cnrasili/cen2/install-model | 3 |
| 105 | `17dd874` | 2026-10-07 23:20 | cnrasili | feat: Add account management screens to the admin service | 3 |
| 106 | `4f95062` | 2026-10-07 23:22 | Caner Aşılıoğlu | Merge pull request #30 from cnrasili/cen2/account-screens | 3 |
| 107 | `cd99569` | 2026-10-07 23:26 | cnrasili | feat: Make the KPI session definition configurable | 3 |
| 108 | `bbc65d1` | 2026-10-07 23:28 | Caner Aşılıoğlu | Merge pull request #31 from cnrasili/cen2/kpi-session | 3 |
| 109 | `e8ebae2` | 2026-10-07 23:29 | cnrasili | docs: Finalize the API contract with the shared database and attendance | 3 |
| 110 | `2a16bce` | 2026-10-07 23:31 | Caner Aşılıoğlu | Merge pull request #32 from cnrasili/cen2/api-contract | 3 |
| 111 | `710f62d` | 2026-10-07 23:54 | cnrasili | fix: Strip Windows line endings from passwords read from standard input | 3 |
| 112 | `f788a56` | 2026-10-07 23:56 | Caner Aşılıoğlu | Merge pull request #33 from cnrasili/cen2/password-stdin | 3 |
| 113 | `82c6057` | 2026-10-08 00:23 | cnrasili | feat: Show the emails and the admin service in Turkish | 3 |
| 114 | `357dd0c` | 2026-10-08 00:25 | Caner Aşılıoğlu | Merge pull request #36 from cnrasili/cen2/turkish-ui | 3 |
| 115 | `53d6f66` | 2026-10-08 11:52 | cnrasili | chore: Pin the Python dependency versions | 3 |
| 116 | `45b6579` | 2026-10-08 11:54 | Caner Aşılıoğlu | Merge pull request #40 from cnrasili/pm/pin-dependencies | 3 |
| 117 | `64f6bd5` | 2026-10-08 12:14 | cnrasili | fix: Allow the Mac Docker network for the admin service and require Python 3.12 | 3 |
| 118 | `a383169` | 2026-10-08 12:16 | Caner Aşılıoğlu | Merge pull request #42 from cnrasili/pm/portability | 3 |
| 119 | `b80a561` | 2026-10-08 12:32 | cnrasili | docs: Turn the README setup into numbered steps for teammates | 3 |
| 120 | `cd5bba8` | 2026-10-08 12:34 | Caner Aşılıoğlu | Merge pull request #44 from cnrasili/pm/readme-setup-guide | 3 |
| 121 | `d81e7df` | 2026-10-08 16:58 | cnrasili | chore: Run the PostgreSQL tests in CI | 3 |
| 122 | `7e47405` | 2026-10-08 17:12 | Caner Aşılıoğlu | Merge pull request #46 from cnrasili/pm/ci-postgres-tests | 3 |
| 123 | `c3e029a` | 2026-10-08 18:31 | cnrasili | feat: Show the hospital name in the emails and the admin panel | 3 |
| 124 | `eb1fbc3` | 2026-10-08 18:33 | Caner Aşılıoğlu | Merge pull request #51 from cnrasili/cen2/hospital-name | 3 |
| 125 | `beec874` | 2026-10-08 20:15 | cnrasili | feat: Log the demo history's booking decisions | 3 |
| 126 | `c307467` | 2026-10-08 20:15 | cnrasili | feat: Show the model's predictions and booking decisions in the admin panel | 3 |
| 127 | `fcd97de` | 2026-10-08 20:17 | cnrasili | docs: Describe how the maintainer updates main | 3 |
| 128 | `8c89354` | 2026-10-08 23:51 | Davut can cüci | feat: Limit failed website logins per login name and client address | 3 |
| 129 | `9fb9f88` | 2026-10-08 23:52 | Davut can cüci | feat: Add security headers to web backend responses | 3 |
| 130 | `85d83d9` | 2026-10-08 23:52 | Davut can cüci | fix: Update source-map-js to resolve the npm audit advisory | 3 |
| 131 | `39b6501` | 2026-10-08 23:55 | Davut can cüci | feat: Add a doctor agenda endpoint for a date range | 3 |
| 132 | `d803844` | 2026-10-08 23:55 | Davut can cüci | feat: Show the date, week overview and upcoming appointments in the patient list | 3 |
| 133 | `e43a13f` | 2026-10-09 00:00 | Davut can cüci | feat: Turn the website into a fictional city hospital site | 3 |
| 134 | `39b2935` | 2026-10-09 00:02 | Davut can cüci | feat: Grow the demo seed to a city hospital with nine departments | 3 |
| 135 | `99db9cb` | 2026-10-09 00:02 | Davut can cüci | feat: Add a public doctor list with working hours | 3 |
| 136 | `2c6fa43` | 2026-10-09 00:05 | Davut can cüci | feat: Show the departments, doctors and working hours on the hospital site | 3 |
| 137 | `a8925fd` | 2026-10-09 00:08 | Davut can cüci | feat: Present the booking as the hospital's Online Randevu | 3 |
| 138 | `4f63b21` | 2026-10-09 00:10 | Davut can cüci | style: Line up the upcoming appointment columns | 3 |
| 139 | `67d1f5d` | 2026-10-09 11:24 | Davut can cüci | fix: Sort the booking departments in Turkish alphabetical order | 3 |
| 140 | `36e7fa7` | 2026-10-09 11:24 | Caner Aşılıoğlu | Merge pull request #54 from cnrasili/cen1/davut-cuci | 3 |
| 141 | `1e45626` | 2026-10-10 00:52 | Davut can cüci | fix: Lock failed logins per login name with a higher per-address limit | 3 |
| 142 | `c6b3e55` | 2026-10-12 18:31 | Caner Aşılıoğlu | Merge pull request #56 from cnrasili/cen1/davut-cuci | 3 |
| 143 | `7479654` | 2026-10-12 18:32 | cnrasili | chore: Merge main into the IEN branch | 3 |
| 144 | `a64cf04` | 2026-10-12 19:00 | cnrasili | fix: Treat the admin patient search as plain text | 3 |
| 145 | `bba186f` | 2026-10-12 19:00 | cnrasili | feat: Schedule messages for bookings whose booked event was lost | 3 |
| 146 | `2f26870` | 2026-10-15 17:44 | cnrasili | docs: Add the dataset rules to the feature list | 4 |
| 147 | `7e12d4c` | 2026-10-15 18:08 | cnrasili | chore: Allow committing the public no-show dataset | 4 |
| 148 | `adac309` | 2026-10-15 18:35 | cnrasili | docs: Add the dataset cleaning rule to the feature list | 4 |
| 149 | `3d9b99f` | 2026-10-15 23:04 | cnrasili | chore: Add the public no-show dataset | 4 |
| 150 | `81deb71` | 2026-10-15 23:04 | cnrasili | feat: Load the public dataset into the database | 4 |
| 151 | `fa083f0` | 2026-10-15 23:28 | cnrasili | feat: Count the dataset history and remove the generated demo data | 4 |
| 152 | `a512d57` | 2026-10-15 23:28 | cnrasili | feat: List and search patients by patient number in the admin panel | 4 |
| 153 | `ca0f36d` | 2026-10-15 23:46 | cnrasili | docs: Define the account API for dataset patients | 4 |
| 154 | `1550830` | 2026-10-16 14:53 | Hazar İkizler | Add literature review of Batool et al. 2020, its replication script and the paper's overbooking policy as a simulation baseline | 5 |
| 155 | `f80bcf9` | 2026-10-16 15:03 | Hazar İkizler | Add the interactive simulation: choose data, risk source, booking rule and template, then run SimPy on real appointments | 5 |
| 156 | `d4f6567` | 2026-10-16 15:04 | Hazar İkizler | Open the interactive simulation in its own app-mode window that stops with the window | 5 |
| 157 | `3a58ae8` | 2026-10-16 15:50 | Hazar İkizler | Redesign the interactive simulation as a simple one-doctor day in Turkish with an overview tab | 5 |
| 158 | `d9cf102` | 2026-10-16 15:59 | Hazar İkizler | Simulation screen: fit one screen, recompute automatically on every setting, show the selected day in the control card | 5 |
| 159 | `68c3c04` | 2026-10-16 16:16 | Hazar İkizler | Settings panel in two wide columns, no scrolling; right side reflows without overlap; larger default window | 5 |
| 160 | `500ed61` | 2026-10-16 16:20 | Hazar İkizler | Merge origin/IEN into IEN: keep the new simulation features, apply the repository lint style | 5 |
| 161 | `9696e56` | 2026-10-16 16:28 | Hazar İkizler | chore: Merge main into the IEN branch | 5 |
| 162 | `cf8773b` | 2026-10-16 19:01 | Hazar İkizler | feat: Add two web UI mock-ups for patient, doctor and admin screens | 5 |
| 163 | `a29bb90` | 2026-10-16 23:16 | Hazar İkizler | feat: Add model comparison, paired experiments, decision list and apply_decisions | 5 |
| 164 | `3b9ca01` | 2026-10-16 23:41 | Hazar İkizler | feat: Keep both models on IEN with random forest selected for now | 5 |
| 165 | `63f1962` | 2026-10-16 23:47 | Hazar İkizler | fix: Retrain the delivered models with scikit-learn 1.9.1 | 5 |
| 166 | `8d37947` | 2026-10-16 23:48 | cnrasili | chore: Allow up to three branches for hazarikizler in branch cleanup | 5 |
| 167 | `4c435a2` | 2026-10-16 23:57 | Hazar İkizler | feat: Add leakage check, service compatibility report and clean-environment result | 5 |
| 168 | `52a384b` | 2026-10-16 23:57 | cnrasili | fix: Keep the branch limits in the cleanup script | 5 |
| 169 | `6d5f48e` | 2026-10-17 00:33 | cnrasili | docs: Narrow the scope to one department without physicians | 6 |
| 170 | `57da99f` | 2026-10-17 00:35 | Hazar İkizler | chore: Merge main into the IEN branch | 6 |
| 171 | `641ffd4` | 2026-10-17 00:38 | Hazar İkizler | docs: Fix random forest as the model and note the provisional assumptions | 6 |
| 172 | `edd19b1` | 2026-10-17 00:44 | cnrasili | chore: Exempt hazarikizler from the branch cleanup | 6 |
| 173 | `3b7382e` | 2026-10-17 00:49 | Hazar İkizler | feat: Add the Department column to the cleaned appointments | 6 |
| 174 | `8696b39` | 2026-10-17 00:58 | Hazar İkizler | chore: Merge main into the IEN branch | 6 |
| 175 | `deb90bd` | 2026-10-17 01:03 | Hazar İkizler | refactor: Move the simulation and documents from physicians to the department | 6 |
| 176 | `6e3fead` | 2026-10-17 01:12 | Hazar İkizler | refactor: Turn the web mock-ups from physicians to the department | 6 |
| 177 | `c82514d` | 2026-10-17 01:25 | Hazar İkizler | feat: Deliver the random forest model, formula notes and room-based KPI terms | 6 |
| 178 | `f1436c0` | 2026-10-17 01:26 | cnrasili | docs: Mark the model feature list as agreed | 6 |
| 179 | `50cba11` | 2026-10-17 01:26 | Hazar İkizler | feat: Set the slot length to 15 minutes and align the simulation defaults with the decisions | 6 |
| 180 | `ab983ac` | 2026-10-17 01:29 | Caner Aşılıoğlu | Merge pull request #65 from cnrasili/IEN-model-delivery | 6 |
| 181 | `94f9c93` | 2026-10-17 01:31 | cnrasili | feat: Install the random forest model in the overbooking service | 6 |
| 182 | `51d0505` | 2026-10-17 02:04 | Hazar İkizler | feat: Add wait distribution, protocol audit, subgroup reading and source review | 6 |
| 183 | `77dd6bf` | 2026-10-17 02:35 | Hazar İkizler | docs: Add the questions for the advisor and the reproduction guide | 6 |
| 184 | `c40f714` | 2026-10-17 02:38 | Hazar İkizler | chore: Merge main into the IEN branch | 6 |
| 185 | `a71aa39` | 2026-10-17 02:39 | Hazar İkizler | docs: Record that the model is installed in the service | 6 |

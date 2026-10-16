# IEN metodoloji ve sonuç raporu (taslak)

**Durum: taslak.** Model seçimi kesin (rastgele orman); simülasyon varsayımları ve 15 dk bekleme sınırı geçici onaylıdır, akademik gerekçe ve kaynak sonra eklenecek. Kararlar `docs/KARAR_LISTESI.md` ve `docs/decisions.json` dosyalarındadır; sayılar `docs/MODEL_KARSILASTIRMA.md`, `docs/IEN_DENEY_SONUCLARI.md` ve `docs/SONUC_OZETI.md` dosyalarından alınmıştır (komutla yeniden üretilir). Aşağıdaki rakamlar **iki model dalında da birbirine çok yakındır**; kesin değer için seçilen dalın `SONUC_OZETI.md` dosyasına bakın. `[ONAY]` etiketli yerler ekibin ya da hocanın kararını bekler. Kaynakça bölümü eksiktir ve doğrulanmadan kullanılmamalıdır.

## 1. Özet

Poliklinik randevularında hastaların yaklaşık %20'si gelmiyor ve muayene kapasitesi boş kalıyor. Çalışmada her randevu için bir gelmeme olasılığı tahmin edildi, olasılığı yüksek randevulara seçici olarak ek hasta yazıldı (overbooking) ve sonuç, sabit aralıklı randevuyla karşılaştırıldı. Karşılaştırma gerçek randevu kayıtları üzerinde SimPy ile yapılan bir simülasyonla yapıldı.

Ana bulgular:

1. Tahmin gücü sınırlıdır: rastgele orman test kümesinde ROC-AUC 0,729'a (%95 aralık 0,721–0,736), 4 seviyeli karar ağacı 0,720'ye, lojistik regresyon 0,658'e ulaşır.
2. Karar ayarı (eşik %30, günlük ek randevu sınırı 4, hasta başına ortalama 7,5 dk muayene, 15 dk slot) oturum başına görülen hastayı yaklaşık 12,8'den 15,6'ya (**+%22**) çıkarır, boşta kalmayı yaklaşık %14 azaltır ve doluluğu %40'tan %49'a çıkarır. Bedeli küçüktür: ortalama bekleme yaklaşık 0,2 dk'dan 1,1 dk'ya, mesai aşımı yaklaşık 0,2 dk artar. Kabul edilen en uzun ortalama bekleme 15 dk'dır; karar ayarı bu sınırın çok altındadır.
3. Rastgele orman ile karar ağacı simülasyon sonuçlarında neredeyse aynıdır; modeller arasındaki küçük AUC farkı klinik sonuca yansımıyor (rakamlar `docs/SONUC_OZETI.md` dosyasındadır).
4. Ortalama bekleme küçük olsa da dağılım uzun kuyrukludur: kuralda hastaların %9,5'i 5 dk'dan, %2,8'i 10 dk'dan, %0,8'i 15 dk'dan uzun bekler; %95'inci yüzdelik 7,7 dk'dır ve uzun bekleyenler çoğunlukla ek randevulu slotlardadır (bölüm 4.7).
5. Sonuç yönü tüm duyarlılık senaryolarında aynıdır; büyüklüğü muayene süresine ve gelmeme oranına bağlıdır.

## 2. Veri

Kaggle "Medical Appointment No Shows" veri seti, 110.527 satır; temizlikten sonra 110.521 randevu, 27 gün (29 Nisan – 8 Haziran 2016). Temizlik adımları `ml/data/clean_data.py` içindedir. Hedef değişken: randevuya gelmeme. `SMS_received` randevudan sonra oluştuğu için model özelliği olarak kullanılmaz (`docs/features.md`). Hasta geçmişi özellikleri yalnızca randevunun alındığı günden önceki randevulardan hesaplanır.

Veri setinde randevu saati ve hekim kimliği yoktur; sistem tek departmandır (General Practice, `Department` sütunu). Bu yüzden saat, muayene odası (oturum) ve slot bilgisi simülasyonda üretilir.

## 3. Yöntem

### 3.1 Tahmin modeli

- **Protokol:** randevu gününe göre zaman ayrımı (ilk %80 eğitim: 88.535 randevu, son %20 test: 21.986 randevu); test kümesi doğal dağılımını korur; ölçekleme yalnızca eğitimde öğrenilir; yeniden örnekleme yoktur.
- **Hiperparametre:** eğitim dönemi tarihe göre 5 bloğa bölünür, genişleyen pencereyle 4 doğrulama katı; seçim ölçütü log-loss.
- **Karşılaştırılan modeller:** lojistik regresyon, rastgele orman, karar ağacı; referans olarak kural R4 (`docs/formulas/rules.md`) ve sabit oran.
- **Eşik:** F1'i en yükseğe çıkaran eşik eğitimin katlama dışı tahminlerinden seçilir.
- **Teslim:** seçilen model tüm günlerle eğitilir, servisin kabul kontrollerinden geçirilir ve `ml/models/` altına yazılır (`ml/apply_decisions.py`).
- Ayrıntı ve tüm tablolar: `docs/MODEL_KARSILASTIRMA.md`.

### 3.2 Overbooking kuralı

Bir slota ikinci hasta, slottaki her hastanın gelmeme riski eşiğin üstündeyse ve günlük ek randevu sınırı dolmadıysa yazılır. Bu kural `overbooking-service` içindeki `rules.decide` ile aynı kararı verir (`simulation/parity_check.py`: 20.000 rastgele slotta fark yok). Teslim edilen kural yalnızca eşik kuralıdır; maliyet bazlı kural (R5-A), beklenen değer kuralı (R5-B, havayolu mantığı) ve literatürdeki politika karşılaştırma olarak raporlanır (`docs/formulas/overbooking.md`).

### 3.3 Simülasyon

SimPy ayrık olay simülasyonu: departmanın bir muayene odası (oturum); 16 slot x 15 dk (4 saat); 20 randevu isteği (slot sayısı + 4); log-normal muayene süresi (ortalama 7,5 dk, aralık 5–10 dk, değişkenlik 0,5); hasta gecikmesi (sapma 4 dk). Muayene süresi, Türkiye'deki devlet hastanesi polikliniklerinde hasta başına 5–10 dk ayrıldığı bilgisine, 15 dk slot ise Türkiye'de randevu aralığının genel olarak 15 dk olmasına dayanır (ekip bilgisi; kaynakları eklenecek `[ONAY]`); gecikme ve talep varsayımdır. Risk ve gelme/gelmeme bilgisi gerçek tahminlerden ve gerçek sonuçlardan çekilir. Tüm politikalar **aynı rastgele oturumları** görür (ortak rastgele sayılar), farklar eşleştirilmiş olarak güven aralığı ve etki büyüklüğüyle verilir. "Tek bölüm, tek doktor" kuralı uygulanmamıştır (karar listesi 5); günün randevuları departmanın muayene odası oturumlarına dağıtılır, sonuçlar oturum başınadır. KPI tanımları ve uygulamayla farkları: `docs/KPI_VE_VARSAYIM_KARSILASTIRMASI.md`.

## 4. Bulgular

### 4.1 Model

| Model | ROC-AUC | PR-AUC | Brier | Kalibrasyon eğimi |
|---|---|---|---|---|
| Rastgele orman | 0,729 | 0,339 | 0,136 | 1,10 |
| Karar ağacı (derinlik 4) | 0,720 | 0,305 | 0,138 | 1,06 |
| Lojistik regresyon | 0,658 | 0,295 | 0,145 | 0,90 |
| Kural R4 | 0,577 | 0,234 | 0,150 | 0,68 |

- Rastgele orman 0,30 eşiğinde precision 0,33, recall 0,48 (hastaların %27'si işaretlenir); 0,40 eşiğinde yalnızca %3,8 işaretlenir ve recall 0,08'dir. Yüksek eşikler az hastayı kapsar.
- Kalibrasyon: eğitim ve test arasında gelmeme oranı %20,6'dan %18,5'e düştüğünden tahminler test kümesinde biraz yüksektir (kesişim −0,14).
- **Alt gruplar (rastgele orman).** Test kümesindeki hastaların %54'ü yeni (geçmişi yok), %46'sı tekrar gelen hastadır. Ayırt etme gücü iki grupta da yakındır (AUC 0,721 ve 0,737): model yeni hastalarda da yaş ve randevuya kalan gün gibi özelliklerle anlamlı ayrım yapar, geçmişi olanlarda biraz daha iyidir. Her iki grupta ortalama tahmin gerçek orandan biraz yüksektir (yeni: %22,3 tahmin, %19,6 gerçek; tekrar gelen: %18,3 ve %17,2); fazlalık yeni hastalarda daha büyüktür. Kalibrasyon eğimi iki grupta da 1,12'dir (tahminler gerçek farkları biraz az gösterir). **Operasyonel sonuç:** 0,30 eşiğinde yeni hastaların %34'ü, tekrar gelenlerin %17,5'i yüksek riskli sayılır; yani kural, ek randevuyu çoğunlukla yeni hastaların slotlarında açar. İşaretlenenlerin isabet oranı iki grupta benzerdir (0,32 ve 0,35). Bu bir adalet ve güvenilirlik notudur: yeni hastaların tahmini daha belirsiz olduğundan hasta geçmişi biriktikçe model yeniden kalibre edilmelidir (`docs/MODEL_KARSILASTIRMA.md` bölüm 5).
- Literatürdeki %95 doğruluk (Batool ve ark., 2020), değerlendirmeden önce tüm veri setinin dengelenmesinden gelir; sızıntısız protokolle sonuç bizimkine (AUC ≈ 0,72) denktir (`docs/LITERATUR_INCELEMESI.md`).

### 4.2 Politikalar (oturum başına, sabit aralığa göre fark; aralıklar `IEN_DENEY_SONUCLARI.md`'de)

Sabit aralık: 12,8 hasta, 0,2 dk bekleme, 144 dk boşta, 0,25 dk mesai aşımı, doluluk %40.

| Politika | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +2,8 | +0,9 | −20 | +0,2 |
| Eşik %20 | +3,2 | +1,2 | −24 | +0,1 |
| Eşik %40 | +0,4 | +0,1 | −3 | +0,0 |
| Maliyet kuralı r=0,5 | +2,1 | +0,7 | −15 | +0,3 |
| Havayolu kuralı | +3,2 | +1,6 | −24 | +0,1 |

Maliyet kuralı r=1,0 neredeyse hiç tetiklenmez (+0,02 hasta): modelin en yüksek riski yaklaşık %50 olduğundan bu kural işe yaramaz. Hasta kazancı eşik %30'dan %20'ye inerken yalnızca +2,8'den +3,2'ye çıkar; kazanç talep tavanıyla sınırlıdır (20 istek, 16 slot).

### 4.3 Şablonlar ve kısa slot

20 slot x 12 dk (kısa slot), tek başına görülen hastayı +3,2 artırır ve boşta kalmayı 24 dk azaltır; bekleme +0,4 dk ve mesai aşımı +0,6 dk artar. Kısa slota karar ayarı eklenirse hasta sayısı daha fazla artmaz (+3,2) ve bekleme +1,7 dk'ya çıkar: kısa slot ile overbooking birbirinin yerine geçer, birlikte ek kazanç yoktur. Slot kaydırma (0,5) bekleme artışını küçültür (+0,9 → +0,7 dk) ama mesai aşımını artırır (+0,2 → +0,5 dk). Ayrıntı: `IEN_DENEY_SONUCLARI.md` bölüm 3.

### 4.4 Eşik ve günlük sınır

Izgara (`IEN_DENEY_SONUCLARI.md` bölüm 2) eşik %15–%20 ve sınır 4–6 ayarlarında ulaşılabilir en yüksek hasta sayısına (≈ 15,9) ulaşır; karar ayarı (eşik %30, sınır 4) bunun yaklaşık %97'sini 1,1 dk beklemeyle verir. Eşik %20'ye inmek yaklaşık +0,4 hasta daha getirir ve beklemeyi +0,3 dk artırır; yani 15 dk'lık bekleme sınırı hiçbir ayarda bağlayıcı değildir ve eşik seçimi bekleme sınırından çok "kaç ek hasta kabul ediyoruz" sorusudur.

### 4.5 Duyarlılık

Karar ayarının sabit aralığa göre bekleme farkı: muayene 5 dk iken +0,4 dk, 10 dk iken +2,2 dk (mesai aşımı 0,0 ve +1,1 dk). Talep slot sayısına yakınsa (16 istek, 16 slot) kural hiçbir kazanç sağlamaz. Gelmeme oranı x0,7 olursa kazanç neredeyse yok (+0,1 hasta); x1,3'te +2,9 hasta. 10 dk'lık slotla (24 slot) +3,1 hasta, +1,7 dk bekleme.

### 4.6 Hatırlatma senaryosu (varsayımsal)

Hatırlatma etkisi %0'dan %30'a çıkarsa sabit aralıkta görülen hasta 12,9'dan 13,3'e çıkar; karar ayarıyla 15,6'dan 15,2'ye düşer. Yani hatırlatma etkili olursa overbooking'in **ek** kazancı küçülür (2,8 → 1,9 hasta); iki yöntem birbirinin yerine kısmen geçer. Gerçek etki A/B testiyle ölçülmelidir.

### 4.7 Bekleme dağılımı (tek tek hastalar)

3.000 eşleştirilmiş oturumda her hastanın beklemesi incelendi (`docs/BEKLEME_DAGILIMI.md`).

| | Sabit aralık | Karar ayarı | Ek randevulu slottaki hastalar |
|---|---|---|---|
| Ortalama (dk) | 0,22 | 1,14 | 2,48 |
| %95'inci yüzdelik (dk) | 0,73 | 7,71 | 10,87 |
| %99'uncu yüzdelik (dk) | 6,25 | 14,16 | 17,45 |
| 5 dk'dan uzun bekleyen | %1,5 | %9,5 | %21,5 |
| 15 dk'dan uzun bekleyen | %0,1 | %0,8 | %1,8 |
| En uzun (dk) | 39 | 68 | 68 |

Bir oturumda en az bir hastanın 15 dk'dan uzun beklemesi sabit aralıkta %1,0, kuralda %8,7 oturumda görülür. Ortalamanın 15 dk sınırının çok altında olması, tek tek hastaların bu sınırı aşmadığı anlamına gelmez; yönetim sınırı **hasta başına** (ör. %95'inci yüzdelik) tanımlamak isteyebilir.

### 4.8 Fayda ve maliyet birlikte

Kural oturum başına **+2,79 hasta** görür (+%22) ve muayene odasının boş kalmasını 20 dk azaltır (doluluk %40 → %49). Bedeli: toplam **+15 hasta-dakika** ek bekleme ve **+0,21 dk** mesai aşımı; yani ek hasta başına yaklaşık **5,4 dk** toplam bekleme ve 0,07 dk mesai aşımı. Bekleme yükünün çoğunu ek randevulu slotlardaki hastalar taşır. Fayda, kapasitenin zaten bol olduğu bir ortamda (doluluk %40) elde edilir; muayene süresi 10 dk'ya çıkarsa bedel belirgin büyür (bekleme artışı +2,2 dk, mesai +1,1 dk). Hasta sayısı, bekleme, boşta kalma ve mesai aşımı birlikte ele alındığında karar ayarı (eşik %30, sınır 4) makul bir dengedir; eşik %20 yalnızca +0,4 hasta daha getirir, bekleme ve uzun bekleyen oranını artırır.

## 5. Yorum: neden daha çok hasta görülürken bekleme artıyor?

Ek hasta, yalnızca ilk hasta gelmezse "bedava" olur. İlk hastanın riski yüksek olsa bile gelme ihtimali %50–70'tir; ikisi de gelirse (bu sık olur) muayene odası aynı slotta iki hastaya bakar ve ikinci hasta bekler; bu bekleme sonraki slotlara taşınır. Boşta kalma azalır çünkü gelmeyen hastaların boşluğu dolar. Muayene ortalaması 7,5 dk iken 15 dk'lık bir slotta iki hastayı görmek mümkündür; bu yüzden bekleme küçük kalır (yaklaşık +1 dk). Muayene 10 dk'ya yaklaştıkça iki hasta slota sığmaz ve bekleme ile mesai aşımı artar (+2,2 ve +1,1 dk). Bu yüzden iyileşme ve bedel her zaman birlikte raporlanmalıdır. Not: ortalama muayene slotun yarısı kadar olduğundan oda, kural olmadan da zamanın yaklaşık %60'ında boştur (doluluk %40); kuralın asıl işi bu kapasiteyi kullanmaktır.

## 6. Sınırlılıklar

1. Tek bir zaman bölmesi ve 27 gün (simülasyon riskleri dönüşümlü katlarla üretilir; ileri doğru pencere karşılaştırması farkı küçük buldu); mevsimsellik ve haftalık kalıplar değerlendirilemez.
2. Randevu saati, hekim kimliği ve gerçek talep verisi yok; simülasyon yapısı varsayımlara dayanır. Slot (15 dk x 16) Türkiye'de yaygın randevu aralığına dayanır, ekip bilgisidir `[ONAY]`.
3. Hekim yoktur, sistem tek departmandır; sonuçlar muayene odası oturumu başınadır ve oda sayısı varsayımdır.
4. Tahmin gücü sınırlı (AUC ≈ 0,73); model riski en çok %50 civarına çıkarır, bu yüzden yüksek eşikler hiç tetiklenmez.
5. Hatırlatma etkisi ölçülmedi; senaryo analizi varsayımsaldır, `SMS_received` rastgele deney değildir.
6. Ortalama bekleme 15 dk sınırının çok altında, ancak dağılım uzun kuyrukludur (bölüm 4.7): hastaların %0,8'i 15 dk'dan uzun bekler. Slot süresi (15 dk) için kaynak bulunamadı; devlet hastanelerinde randevu aralığının 5–10 dk olduğuna dair haberler var (`docs/KAYNAK_ARASTIRMASI.md`).
7. Simülasyon ve uygulama KPI'ları aynı tanımı farklı hesaplar (`KPI_VE_VARSAYIM_KARSILASTIRMASI.md`).

## 7. Sonuç ve öneri `[ONAY]`

- Model: **rastgele orman seçildi** (ekip kararı, 17 Ekim 2026; #7). Karar ağacıyla klinik sonuç aynıdır (ağaç yorumlanabilir ve birkaç KB, orman yaklaşık 15 MB); ağaç karşılaştırma için tutulur.
- Kural: eşik %30 ve günlük sınır 4 ulaşılabilir hasta kazancının yaklaşık %97'sini verir ve 15 dk sınırının çok altında kalır; eşik %20 biraz daha fazla hasta getirir, bekleme yine küçük kalır. Serviste günlük sınır 2 ve muayene süresi 12 dk'dır; bu iki değer karar listesine göre güncellenmelidir (PR #64).
- Hatırlatma: etkisi canlı A/B testiyle ölçülmelidir.

## 8. Yeniden üretim

```bash
python ml/data/clean_data.py
python ml/build_reports.py
python ml/evaluate_models.py          # docs/MODEL_KARSILASTIRMA.md
python ml/apply_decisions.py          # karar listesine göre model + sonuçlar
python simulation/parity_check.py     # servis ile kural uyumu
python ml/leakage_check.py            # zamansal sızıntı kontrolü
```

**Temiz ortam kontrolü (17 Ekim 2026).** Depo kopyası, `requirements` dosyalarıyla kurulan yeni bir sanal ortamda (Python 3.11, pandas 3.0.6, numpy 2.4.6, scikit-learn 1.9.1, scipy 1.17.1, simpy 4.1.2) baştan sona çalıştırıldı: `clean_data.py`, `build_reports.py`, `evaluate_models.py`, `apply_decisions.py` (model, deneyler, bekleme dağılımı, servis kabul kontrolleri, kural uyumu) ve `leakage_check.py`. Hepsi hatasız bitti. `docs/SONUC_OZETI.md` ve `docs/BEKLEME_DAGILIMI.md` bayt bayt aynı çıktı; `MODEL_KARSILASTIRMA.md` yalnızca üçüncü ondalıkta (ör. kalibrasyon eğimi 1,103 → 1,102), `IEN_DENEY_SONUCLARI.md` ise yalnızca eşit değerli ızgara satırlarının sırasında farklıdır; sonuçlar ve yorumlar değişmez. Rapordaki sayılar Python 3.11.2 / pandas 2.0.1 / scikit-learn 1.2.2 ortamından gelir.

**Servis uyumu.** Seçili model ve karar ayarları servisin kendi testlerinde ve HTTP API'sinde denendi (`docs/SERVIS_UYUM_RAPORU.md`). **Zamansal sızıntı.** Simülasyonun 27 günlük riskleri dönüşümlü katlarla üretilir; yalnızca geçmişle eğitilen model karşılaştırması AUC'de ve simülasyon sonucunda pratikte fark vermedi (`docs/ZAMANSAL_SIZINTI_KONTROLU.md`: 0,731 ve 0,729).

## 9. Kaynakça (eksik, doğrulanacak)

- Batool T., Abuelnoor M., El Boutari O., Aloul F., Sagahyroon A. (2020). *Predicting Hospital No-Shows Using Machine Learning.* 2020 IEEE International Conference on Internet of Things and Intelligence System (IoTaIS), s. 142–148. DOI: 10.1109/IoTaIS50849.2021.9359692.
- Veri seti: Kaggle, "Medical Appointment No Shows" (KaggleV2-May-2016). Bağlantı ve erişim tarihi eklenecek.
- Muayene süresi (hasta başına 5–10 dk), slot (15 dk) ve bekleme sınırı için kaynak taraması: `docs/KAYNAK_ARASTIRMASI.md` (haber ve TBMM belgeleri; hakemli kaynak değil, elle doğrulanmalı; slot için kaynak bulunamadı) `[ONAY]`.
- Ders notlarındaki formül kaynakları ve overbooking literatürü eklenecek `[ONAY]`: her kaynak elle doğrulanmalıdır.

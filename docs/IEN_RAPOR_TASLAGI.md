# IEN metodoloji ve sonuç raporu (taslak)

**Durum: taslak.** Kararlar `docs/KARAR_LISTESI.md` ve `docs/decisions.json` dosyalarındadır; sayılar `docs/MODEL_KARSILASTIRMA.md`, `docs/IEN_DENEY_SONUCLARI.md` ve `docs/SONUC_OZETI.md` dosyalarından alınmıştır (komutla yeniden üretilir). Aşağıdaki rakamlar **iki model dalında da birbirine çok yakındır**; kesin değer için seçilen dalın `SONUC_OZETI.md` dosyasına bakın. `[ONAY]` etiketli yerler ekibin ya da hocanın kararını bekler. Kaynakça bölümü eksiktir ve doğrulanmadan kullanılmamalıdır.

## 1. Özet

Poliklinik randevularında hastaların yaklaşık %20'si gelmiyor ve doktor boş kalıyor. Çalışmada her randevu için bir gelmeme olasılığı tahmin edildi, olasılığı yüksek randevulara seçici olarak ek hasta yazıldı (overbooking) ve sonuç, sabit aralıklı randevuyla karşılaştırıldı. Karşılaştırma gerçek randevu kayıtları üzerinde SimPy ile yapılan bir simülasyonla yapıldı.

Ana bulgular:

1. Tahmin gücü sınırlıdır: rastgele orman test kümesinde ROC-AUC 0,729'a (%95 aralık 0,721–0,736), 4 seviyeli karar ağacı 0,720'ye, lojistik regresyon 0,658'e ulaşır.
2. Karar ayarı (eşik %30, günlük ek randevu sınırı 4, hasta başına 7,5 dk muayene, 10 dk slot) oturum başına görülen hastayı yaklaşık 19,2'den 22,3'e (**+%16**) çıkarır ve boşta kalmayı yaklaşık %23–24 azaltır, doluluğu %60'tan %70'e çıkarır. Bedeli: ortalama bekleme yaklaşık 1,3 dk'dan 3 dk'ya çıkar, mesai aşımı yaklaşık 0,3 dk artar. Kabul edilen en uzun ortalama bekleme 15 dk'dır; karar ayarı bu sınırın çok altındadır.
3. Rastgele orman ile karar ağacı simülasyon sonuçlarında neredeyse aynıdır (görülen hasta 22,3 ve 22,3; bekleme 3,0 ve 2,9 dk): modeller arasındaki küçük AUC farkı klinik sonuca yansımıyor.
4. Sonuç yönü tüm duyarlılık senaryolarında aynıdır; büyüklüğü muayene süresine ve gelmeme oranına bağlıdır.

## 2. Veri

Kaggle "Medical Appointment No Shows" veri seti, 110.527 satır; temizlikten sonra 110.521 randevu, 27 gün (29 Nisan – 8 Haziran 2016). Temizlik adımları `ml/data/clean_data.py` içindedir. Hedef değişken: randevuya gelmeme. `SMS_received` randevudan sonra oluştuğu için model özelliği olarak kullanılmaz (`docs/features.md`). Hasta geçmişi özellikleri yalnızca randevunun alındığı günden önceki randevulardan hesaplanır.

Veri setinde randevu saati ve doktor kimliği yoktur. Bu yüzden saat, doktor ve slot bilgisi simülasyonda üretilir.

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

SimPy ayrık olay simülasyonu: bir doktor; 24 slot x 10 dk (4 saat); 28 randevu isteği; log-normal muayene süresi (ortalama 7,5 dk, aralık 5–10 dk, değişkenlik 0,5); hasta gecikmesi (sapma 4 dk). Muayene süresi, Türkiye'deki devlet hastanesi polikliniklerinde hasta başına 5–10 dk ayrıldığı bilgisine dayanır (kaynağı eklenecek `[ONAY]`); slot, gecikme ve talep varsayımdır. Risk ve gelme/gelmeme bilgisi gerçek tahminlerden ve gerçek sonuçlardan çekilir. Tüm politikalar **aynı rastgele oturumları** görür (ortak rastgele sayılar), farklar eşleştirilmiş olarak güven aralığı ve etki büyüklüğüyle verilir. "Tek bölüm, tek doktor" kuralı uygulanmamıştır (karar listesi 5); günün randevuları doktor oturumlarına dağıtılır, sonuçlar oturum başınadır. KPI tanımları ve uygulamayla farkları: `docs/KPI_VE_VARSAYIM_KARSILASTIRMASI.md`.

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
- Yeni hasta (geçmişi yok) AUC 0,721, tekrar gelen hasta 0,737.
- Literatürdeki %95 doğruluk (Batool ve ark., 2020), değerlendirmeden önce tüm veri setinin dengelenmesinden gelir; sızıntısız protokolle sonuç bizimkine (AUC ≈ 0,72) denktir (`docs/LITERATUR_INCELEMESI.md`).

### 4.2 Politikalar (oturum başına, sabit aralığa göre fark; aralıklar `IEN_DENEY_SONUCLARI.md`'de)

Sabit aralık: 19,2 hasta, 1,3 dk bekleme, 98 dk boşta, 1,9 dk mesai aşımı.

| Politika | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| Karar ayarı (eşik %30, sınır 4) | +3,1 | +1,8 | −23 | +0,3 |
| Eşik %20 | +3,2 | +2,3 | −24 | −0,1 |
| Eşik %40 | +0,6 | +0,3 | −4 | +0,3 |
| Maliyet kuralı r=0,5 | +2,7 | +1,4 | −20 | +0,7 |
| Havayolu kuralı | +3,2 | +2,9 | −24 | −0,1 |

Maliyet kuralı r=1,0 neredeyse hiç tetiklenmez (+0,03 hasta): modelin en yüksek riski yaklaşık %50 olduğundan bu kural işe yaramaz. Hasta kazancı eşik %30'dan %20'ye inerken artmaz (+3,1 → +3,2) ama bekleme artar; kazanç talep tavanıyla sınırlıdır (28 istek, 24 slot).

### 4.3 Şablonlar ve kısa slot

30 slot x 8 dk (kısa slot), tek başına görülen hastayı +3,1 artırır, boşta kalmayı 25 dk azaltır ve mesai aşımını 1,1 dk düşürür. Kısa slota karar ayarı eklenirse bekleme +5,9 dk'ya çıkar ve hasta sayısı daha fazla artmaz: kısa slot ile overbooking birbirinin yerine geçer, birlikte kazanç getirmez. Slot kaydırma (0,5) belirgin bir fark yaratmadı. Ayrıntı: `IEN_DENEY_SONUCLARI.md` bölüm 3.

### 4.4 Eşik ve günlük sınır

Izgara (`IEN_DENEY_SONUCLARI.md` bölüm 2) eşik %15–%30 ve sınır 4–8 aralığında ulaşılabilir en yüksek hasta sayısının (≈ 22,3) tavan olduğunu gösterir; karar ayarı (eşik %30, sınır 4) bu tavanın %99,7'sini 3,1 dk beklemeyle verir. Daha gevşek ayarlar (daha düşük eşik, daha yüksek sınır) hasta sayısını artırmaz, yalnızca beklemeyi artırır. 15 dk'lık bekleme sınırı bağlayıcı değildir.

### 4.5 Duyarlılık

Karar ayarının sabit aralığa göre bekleme farkı: muayene 5 dk iken +0,4 dk, 10 dk iken +6,9 dk (mesai aşımı +0,2 ve +6,7 dk). Talep slot sayısına eşitse (24 istek) kural hiçbir kazanç sağlamaz. Gelmeme oranı x0,7 olursa kazanç neredeyse yok (+0,2 hasta); x1,3'te +2,9 hasta. 15 dk'lık slotla +2,8 hasta, +1,0 dk bekleme.

### 4.6 Hatırlatma senaryosu (varsayımsal)

Hatırlatma etkisi %0'dan %30'a çıkarsa sabit aralıkta görülen hasta 19,3'ten 20,0'a çıkar; karar ayarıyla 22,4'ten 22,5'e. Yani hatırlatma etkili olursa overbooking'in **ek** kazancı küçülür (3,1 → 2,6 hasta). İki yöntem birbirinin yerine kısmen geçer. Gerçek etki A/B testiyle ölçülmelidir.

## 5. Yorum: neden daha çok hasta görülürken bekleme artıyor?

Ek hasta, yalnızca ilk hasta gelmezse "bedava" olur. İlk hastanın riski yüksek olsa bile gelme ihtimali %50–70'tir; ikisi de gelirse (bu sık olur) doktor aynı slotta iki hastaya bakar ve ikinci hasta bekler; bu bekleme sonraki slotlara taşınır. Boşta kalma azalır çünkü gelmeyen hastaların boşluğu dolar. Muayene süresi kısaldıkça (5–10 dk) iki hastayı aynı slotta görmek kolaylaşır ve bekleme küçük kalır; 10 dk'ya yaklaştıkça bekleme ve mesai aşımı belirgin biçimde artar. Bu yüzden iyileşme ve bedel her zaman birlikte raporlanmalıdır.

## 6. Sınırlılıklar

1. Tek bir zaman bölmesi ve 27 gün; mevsimsellik ve haftalık kalıplar değerlendirilemez.
2. Randevu saati, doktor kimliği ve gerçek talep verisi yok; simülasyon yapısı varsayımlara dayanır. Slot (10 dk x 24) karar listesinden **türetilmiştir** `[ONAY]`.
3. "Tek hekim" kuralı uygulanmadı; sonuçlar doktor oturumu başınadır.
4. Tahmin gücü sınırlı (AUC ≈ 0,73); model riski en çok %50 civarına çıkarır, bu yüzden yüksek eşikler hiç tetiklenmez.
5. Hatırlatma etkisi ölçülmedi; senaryo analizi varsayımsaldır, `SMS_received` rastgele deney değildir.
6. Ortalama bekleme 15 dk sınırının çok altında; ama bekleme dağılımı (en uzun bekleyen hastalar) ayrıca raporlanmadı.
7. Simülasyon ve uygulama KPI'ları aynı tanımı farklı hesaplar (`KPI_VE_VARSAYIM_KARSILASTIRMASI.md`).

## 7. Sonuç ve öneri `[ONAY]`

- Model: rastgele orman ile karar ağacı klinik sonuçta aynı; ağaç yorumlanabilir ve çok küçüktür (birkaç KB, ormanın yaklaşık 15 MB'ına karşı). Seçim ekibe aittir (#7); şimdilik rastgele orman seçili, karar ağacı aday olarak hazırdır.
- Kural: eşik %30 ve günlük sınır 4 hasta kazancının neredeyse tamamını verir ve 15 dk sınırının çok altında kalır. Serviste günlük sınır 2 ve muayene süresi 12 dk'dır; bu iki değer karar listesine göre güncellenmelidir (CEN).
- Hatırlatma: etkisi canlı A/B testiyle ölçülmelidir.

## 8. Yeniden üretim

```bash
python ml/data/clean_data.py
python ml/build_reports.py
python ml/evaluate_models.py          # docs/MODEL_KARSILASTIRMA.md
python ml/apply_decisions.py          # karar listesine göre model + sonuçlar
python simulation/parity_check.py     # servis ile kural uyumu
```

**Temiz ortam kontrolü (16 Ekim 2026).** Depo kopyası, `requirements` dosyalarıyla kurulan yeni bir sanal ortamda (Python 3.11, pandas 3.0.6, numpy 2.4.6, scikit-learn 1.9.1, scipy 1.17.1, simpy 4.1.2) çalıştırıldı: `clean_data.py`, `build_reports.py`, `evaluate_models.py --quick`, `experiments.py --quick`, `parity_check.py` ve `export_candidate.py` hatasız bitti. Test AUC'leri eski ortamla aynı çıktı (lojistik 0,658, rastgele orman 0,730). Tam deney koşuları bu ortamda yeniden çalıştırılmadı; rapordaki sayılar Python 3.11.2 / pandas 2.0.1 / scikit-learn 1.2.2 ortamından gelir.

## 9. Kaynakça (eksik, doğrulanacak)

- Batool T., Abuelnoor M., El Boutari O., Aloul F., Sagahyroon A. (2020). *Predicting Hospital No-Shows Using Machine Learning.* 2020 IEEE International Conference on Internet of Things and Intelligence System (IoTaIS), s. 142–148. DOI: 10.1109/IoTaIS50849.2021.9359692.
- Veri seti: Kaggle, "Medical Appointment No Shows" (KaggleV2-May-2016). Bağlantı ve erişim tarihi eklenecek.
- Muayene süresi (hasta başına 5–10 dk, Türkiye devlet hastaneleri): kaynak eklenecek `[ONAY]`.
- Ders notlarındaki formül kaynakları ve overbooking literatürü eklenecek `[ONAY]`: her kaynak elle doğrulanmalıdır.

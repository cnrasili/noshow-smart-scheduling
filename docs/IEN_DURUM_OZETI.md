# IEN Durum Özeti

Bu dosya, IEN tarafında şu ana kadar ne yaptığımızı, neyi çözdüğümüzü ve nelerin eksik kaldığını basit bir dille anlatır. Branch: `IEN`. Tarih: 2 Ekim 2026.

## 1. Proje ne yapmaya çalışıyor?

Hastaların bir kısmı randevuya gelmiyor. Gelmeyen hasta, doktorun boş durması demek. Bunu azaltmak için üç şey yapıyoruz:

1. Her hasta için **"gelmeme ihtimali"ni tahmin eden bir model** kuruyoruz.
2. İhtimali yüksek olan randevulara **fazladan bir hasta yazıyoruz** (buna overbooking diyoruz).
3. Bunun işe yarayıp yaramadığını **bilgisayarda simüle ederek** ölçüyoruz.

## 2. Neler yaptık?

| Konu | Ne yaptık | Nerede? |
|---|---|---|
| Ders formülleri | Tahmin, olasılık, istatistik ve kalite kontrol derslerinden projede işe yarayan formülleri topladık. Her birinin projede nerede kullanılacağını yazdık. | `docs/formulas/` |
| Kurallar | Gelme ihtimalini hesaplayan 4 kural yazdık: hasta geçmişine göre, bölüme (veride yok, yerine cinsiyet denendi), yaşa göre ve bunların birleşimi (hiç geçmişi olmayan yeni hasta için). | `docs/formulas/rules.md` |
| Overbooking kuralı | Havayollarının mantığını kliniğe uyarladık: "fazladan hasta eklemenin getireceği faydayla zararı karşılaştır." | `docs/formulas/overbooking.md` |
| Veri temizliği | Kaggle verisini temizledik (110.527 satır, 6'sı hatalı çıktı) ve Excel'e yazdık. | `ml/data/clean_data.py` |
| Modeller | Lojistik regresyon ve random forest kurduk. AUC ve kalibrasyonu ölçtük, üç Excel dosyası hazırladık. | `ml/build_reports.py` |
| Simülasyon | Python SimPy ile bir klinik günü simüle ettik (Arena yerine, hoca izin verdi). | `simulation/clinic_sim.py` |
| Grafikler ve dashboard | KPI kartlı bir sayfa ve üç grafik hazırladık. | `simulation/dashboard.py`, `simulation/plots.py`, `simulation/value_ladder.py` |
| Tüm gün simülasyonu | Test haftasının her gününün **tüm gerçek randevu kayıtları** (günde 4.000+) yaklaşık 220 klinik oturumuna dağıtılıp simüle edilir. Gün toplamları, dakika dakika animasyon ve tüm kayıtların tablosu (her kayıt için model, lojistik regresyon ve R4 riski, gerçek sonuç, simülasyon sonucu). `python real_days.py --source r4` ile kararı R4 kuralının riskiyle de verdirebilirsiniz. | `simulation/real_days.py` |
| Canlı simülasyon | Bir klinik gününü animasyonla izleyebileceğiniz sayfa ve terminalde SimPy olay kaydı. Tek komutla her şey: `python simulation/main.py`. | `simulation/live_day.py`, `simulation/main.py` |
| Randevu şablonları | 3 farklı şablon tasarlayıp test ettik, kazananı ayrı klasöre kaydettik. Karşılaştırma artık verinin **27 gününün tüm gerçek randevuları** (110.521 kayıt) üzerinden yapılıyor. Sayfanın üstünde "Overall" kartları (kazanan şablon ve hiçbir kural yokken, sayı ve yüzde olarak), altında her gün için açılır tablolar var: görülen hasta, gelmeyen, boş slot bulamayan, bekleme, boş zaman, mesai aşımı. | `simulation/templates/` (`day_by_day.py`) |

## 3. Bulduklarımız (en önemli sonuçlar)

**Veri**
- 6 haftalık veri var (29 Nisan – 8 Haziran 2016). Gelmeme oranı **%20**.
- Hastaların sadece **%28'inin** daha önce randevusu var. Yani çoğu hasta "yeni".
- Gelmemeyi en çok **randevunun ne kadar önce alındığı** belirliyor: 15 gün ve üstü %34, 2 gün ve altı %9.
- Gelmeme oranı gençlerde (%23) yaşlılardan (%16) fazla. Cinsiyetin etkisi çok küçük (0,6 puan).

**Model**

| Yöntem | Başarı (AUC, 0,5 = şans, 1 = mükemmel) |
|---|---|
| Random forest | 0,73 |
| Lojistik regresyon | 0,66 |
| Sadece kurallarımız | 0,58 |

Random forest en iyisi. Lojistik regresyon, randevu süresi arttıkça düz bir çizgi varsaydığı için geride kalıyor. Aralıklara bölersek 0,72'ye çıkıyor (henüz yapmadık).

**Overbooking simülasyonu** (bir oturumda, hiç overbooking yapmayana göre):

| | Fark |
|---|---|
| Görülen hasta | **+2 hasta** |
| Doktorun boş kaldığı süre | **−24 dakika** |
| Hastanın ortalama bekleme süresi | **+3 dakika** (kötü) |
| Doktorun mesai aşımı | **+2 dakika** (kötü) |

Yani overbooking hasta sayısını artırıyor ve boş zamanı azaltıyor, ama beklemeyi de artırıyor. **Projenin ilk iddiası olan "hem bekleme hem boş zaman iyileşir" bu varsayımlarla çıkmıyor.**

Tahmin modelinin katkısı: Fazladan her hasta için yaşanan bekleme, rastgele overbooking'de 2,5 dakika, modelle hedefli overbooking'de 1,6 dakika. Yani model bedeli azaltıyor ama sıfırlamıyor.

**Randevu şablonları**
- **Kısa slotlar (12 dk):** En çok hastayı görüyor (+3) ama mesai aşımı yüksek (8,8 dk).
- **Kaydırılmış overbooking:** Seçtiğimiz sınırlara göre kazanan bu, ama kazancı çok küçük (+0,3 hasta).
- **Tampon slot:** İşe yaramadı, hasta sayısı bile düştü.

## 4. Çözdüğümüz sorunlar ve düzelttiğimiz hatalar

- Kaggle verisinde bölüm bilgisi yok. Bu yüzden bölüm kuralını veride kullanmadık; cinsiyet testi yaptık, etkisi önemsiz çıktı.
- Simülasyonda **negatif bekleme süresi** çıkıyordu (erken gelen hasta randevu saatinden önce muayene ediliyordu). Düzelttik. Düzeltmeden önceki bekleme rakamları yanlıştı.
- Excel raporundaki karşılaştırma değeri yanlış hesaplanmıştı, düzelttik.
- Yeni hastalar (hiç geçmişi olmayanlar) için de ihtimal hesaplayabiliyoruz (4. kural).
- Overbooking kuralının formülünü kendimiz türettik ve küçük bir bilgisayar hesabıyla doğruladık.

## 5. Eksik kalanlar ve bakılması gerekenler

Önemliden önemsize doğru:

1. **Simülasyonun sayıları varsayım.** Slot süresi (15 dk), muayene süresi (ortalama 12 dk) ve hastaların ne kadar geç kaldığı bizim tahminimiz. Gerçek değerler lazım. En çok **muayene süresinin ne kadar değiştiği** önemli: değişkenlik artarsa sabit randevuda bekleme 2 dakikadan 8 dakikaya çıkıyor.
2. **Başarı ölçütünü belirlemek lazım.** "Bekleme ve mesai aşımı en fazla 5 dakika olsun" dedik ama bunu biz seçtik. Hoca ya da proje yöneticisiyle konuşulmalı. Kazanan şablon bu sınıra göre değişiyor.
3. **Kısa slot + overbooking birlikte denenmedi.** Muhtemelen hocanın ilk soracağı soru: "Overbooking yerine slotu kısaltsak olmaz mı?"
4. **Modeli servise bağlamak.** Hazır model dosyası henüz `overbooking-service`'e verilmedi. Servisteki kural (`rules.py`) ile bizim yazdığımız kural da aynı değil, birine karar verilmeli.
5. **Hatırlatmanın etkisi simülasyonda yok.** Hatırlatma mesajı gelmeme oranını düşürür. Bunu simülasyona eklemek lazım. Kaggle'daki SMS verisinden etkiyi çıkarmayın, yanıltıcı (SMS zaten riskli hastalara gönderilmiş).
6. **Gelmeme oranı kayıyor.** Eğitimde %20,6, son haftada %18,5. Model bu yüzden hafif fazla risk veriyor. Canlıda düzenli izleme ve yeniden kalibrasyon gerekecek (`quality-control.md`).
7. **Küçük modelleme işleri:** Lojistik regresyonda randevu süresini aralıklara bölmek; Winters formülünü ders slaytlarından kontrol etmek; kalite kontrol çarpan tabloları PDF'te resim olduğu için okunamadı, elle girilmeli.
8. **Excel formülleri açılıp bakılmadı.** Raporlardaki ROC ve kalibrasyon tabloları Excel formülü, ama bu bilgisayarda Excel olmadığı için açıp çalıştıramadık. Python ile aynı sonucu verdiğini ayrıca kontrol ettik. Excel'de bir kez açıp bakın.
9. **Yapılan işin ne kadarının web/veritabanı/servis tarafıyla uyduğunu kontrol etmedik.** O tarafı CEN arkadaşlarımız yazdı, biz sadece okuduk.

**Tüm gün simülasyonunda dikkat:** Kaggle'da doktor bilgisi yok. Bir günün randevuları doktorlara *rastgele* dağıtılıyor (oturum başına 20 randevu isteği, 16 slot). Oturum başına 4 fazla istek bizim varsayımımız ve "slotsuz kalan randevular" ile overbooking'in kazancını doğrudan etkiliyor. Gerçek doktor sayısı ve talep bilinmeden bu sayılar kesin sonuç değildir.

## 6. Nasıl çalıştırırım?

Bazı dosyalar herkese açık repoya girmesin diye GitHub'da yok (ders notları, ham veri, model Excel'leri). Bunları kendi bilgisayarınızda şöyle üretirsiniz:

1. Kaggle'dan [Medical Appointment No Shows](https://www.kaggle.com/datasets/joniarroba/noshowappointments) verisini indirin. Dosyayı `ml/data/raw/` içine koyun ve adını `noshow-smart-scheduling-veriseti.csv` yapın.
2. Kütüphaneleri kurun:

```bash
pip install -r ml/requirements.txt -r simulation/requirements.txt
```

3. Veriyi temizleyin:

```bash
python ml/data/clean_data.py
```

4. Modelleri kurun, Excel raporlarını ve simülasyon için risk dosyasını üretin:

```bash
cd ml
python build_reports.py
```

5. Simülasyonu çalıştırın. **Tek komut yeter** (yaklaşık 30 saniye): VS Code'da `simulation/main.py` dosyasını açıp çalıştırın ya da terminalde:

```bash
cd ../simulation
python main.py
```

Bu komut 5 adımı sırayla çalıştırır, son adımda SimPy'ın olay kaydını terminale yazar (kim ne zaman geldi, doktor ne zaman başladı) ve sonuçları toplayan `simulation/output/index.html` sayfasını tarayıcıda açar. Sayfadaki **Whole days** bağlantısı bir günün tüm kayıtlarını gösterir. **Live simulation** bağlantısı bir klinik gününü animasyonla oynatır: bekleme odası, doktor, gelmeyen hastalar; yanda sabit randevu ve overbooking aynı gün üzerinde karşılaştırılır. Animasyondaki hastalar **gerçek randevu kayıtları**: test haftasının (2–8 Haziran 2016) gerçek günlerinden, hastaların gerçek randevu alma sırasıyla, modelin verdiği riskle ve gerçekten gelip gelmediğiyle çalışır. Muayene süresi ve geç kalma Kaggle verisinde olmadığı için simüle edilir. Hızlı deneme için `python main.py --quick`. İsterseniz adımları tek tek de çalıştırabilirsiniz:

```bash
python clinic_sim.py
python plots.py
python value_ladder.py --risks ../ml/data/processed/risks_random_forest.csv
python dashboard.py --risks ../ml/data/processed/risks_random_forest.csv
python templates/compare_templates.py
```

Dashboard `simulation/output/dashboard.html` olarak çıkar, tarayıcıda açın. Şablon sonuçları `simulation/templates/results/` ve kazanan `simulation/templates/winner/` içinde.

## 7. Dosya haritası

```
docs/formulas/      formüller ve kurallar (forecast, probability, statistics,
                    quality-control, rules, overbooking)
docs/IEN_DURUM_OZETI.md   bu dosya
ml/data/clean_data.py     veri temizleme
ml/build_reports.py       modeller + Excel raporları
simulation/               SimPy simülasyonu, grafikler, dashboard
simulation/templates/     3 randevu şablonu, karşılaştırma, kazanan
```

## 8. Dikkat edilecek üç şey

- Sonuçlar **bu veriyle ve bu varsayımlarla** geçerli. Veri tek şehirden ve 6 haftalık. Raporda bunu söylemeyi unutmayın.
- Simülasyondaki rakamları "kesin sonuç" diye sunmayın. Gerçek muayene süresi gelince yeniden çalıştırmak gerekir.
- Hastanın cinsiyetine göre farklı muamele etmek hem adil değil hem de veride işe yaramıyor. Kurallarda kullanmadık.

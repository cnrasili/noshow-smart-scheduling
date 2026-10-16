# Literatür İncelemesi

Bu dosya, projemizle doğrudan ilgili bir makaleyi özetler, iddialarını kendi verimizde sınar ve bizim çalışmamız için çıkardığımız dersleri listeler. Yeni makale okundukça aynı biçimde alt bölüm olarak eklenebilir.

**Okunan makale:** Batool T., Abuelnoor M., El Boutari O., Aloul F., Sagahyroon A. (2020). *Predicting Hospital No-Shows Using Machine Learning.* 2020 IEEE International Conference on Internet of Things and Intelligence System (IoTaIS), s. 142–148. DOI: 10.1109/IoTaIS50849.2021.9359692.

## 1. Makale ne yapıyor?

- **Amaç:** Hastanın randevuya gelmeme (no-show) riskini tahmin etmek ve gelmeyeceği öngörülen slotları fazladan randevuya açmak. Bunun için "ASIM" adlı bir randevu sistemi (mobil uygulama, web uygulaması, sunucular, veritabanı ve sınıflandırıcı) tasarlıyorlar.
- **Veri:** Bizimle **aynı Kaggle verisi** (Brezilya, 110.527 kayıt, %20,19 gelmeme).
- **Ön işleme:** Cinsiyet 0/1, mahalle numaraya çevrildi, randevu alınan gün ile randevu günü arasındaki fark "lead time" özelliği olarak eklendi. Sınıf dengesizliği, `Instance Hardness Threshold` (IHT) adlı yöntemle çoğunluk sınıfı (gelenler) azaltılarak giderildi.
- **Modeller:** Karar ağacı (DT), Naive Bayes (NB), KNN, doğrusal SVM, doğrusal olmayan SVM. Hepsi grid search ile ayarlandı. Veri 10 kez rastgele %80/%20 bölündü, ortalamalar raporlandı, ayrıca 5 katlı çapraz doğrulama yapıldı. Özellik azaltma (SelectKBest, SelectPercentile, PCA) denendi.
- **Sonuç tablosu (makalenin Tablo VII'si):**

| Model | Doğruluk | Precision | Recall | F1 |
|---|---|---|---|---|
| Karar ağacı | %94,5 | %95 | %95 | %95 |
| Naive Bayes | %85 | %80 | %85 | %85 |
| KNN | %92,5 | %90,5 | %90,5 | %90,5 |
| SVM (doğrusal) | %92 | %90,5 | %88 | %88 |
| SVM (doğrusal olmayan) | %94,5 | %95 | %95 | %95 |

  Zaman karmaşıklığı düşük olduğu için karar ağacı seçildi.
- **Özellik azaltma:** Tek bir özellik (K=1) bile %95,4 doğruluk verdi. Lead time'ı çıkarınca doğruluk %95,28'den %59,24'e düştü (Tablo IX). Makale bunu, lead time'ın en bilgi verici özellik olduğunu gösteren kanıt olarak sunuyor.
- **Overbooking:** Sadece tek cümleyle: "sınıflandırıcının gelmeyecek dediği slotlar overbooking'e açılır ve görevliye bildirilir". Overbooking'in bekleme, boş zaman ya da mesai üzerindeki etkisi **ölçülmemiş**.

## 2. Makalenin aktardığı literatür

Makale şu çalışmaları özetliyor (rakamlar makalenin aktardığı biçimiyle, aslına bakılmadı):

| Çalışma | Bulgu |
|---|---|
| Norris ve ark.; Triemstra ve Lowery; McMullen ve Netland | Lead time ile gelmeme arasında ilişki var |
| Mohammadi ve ark. | Lojistik regresyon %73, yapay sinir ağı %71, Naive Bayes %82 doğruluk; lead time önemli |
| Levy | %65 doğruluk |
| Alaeddini ve ark. | Lojistik regresyon + Naive Bayes karması, %80 doğruluk; tatil yakınlığı ve klinik türü gelmemeyle ilişkili |
| Cao ve Tang; Chen | Overbooking stratejileri |
| Walji ve Zhang | Hatırlatma mesajlarının insan-bilgisayar etkileşimi tasarımı |
| Percac-Lima ve ark. | Aranarak hatırlatılan grupta gelmeme oranı kontrol grubundan **%7,3 daha düşük** |
| Kaplan-Lewis ve Percac-Lima | Gelmeme nedenleri: **unutkanlık** ve **yanlış iletişim** (tarih/saatin yanlış bilinmesi, randevunun iptal sanılması) |

## 3. Eleştirel değerlendirme: %95 neden gerçek değil?

Makalenin en iddialı sonucunu (%95 doğruluk, tek özellikle %95) `ml/paper_replication.py` ile kendi temizlenmiş verimizde yeniden ürettik. Betik, makaledeki protokolü ve hatasız bir protokolü yan yana çalıştırır.

**Makalenin protokolü:** Önce **bütün veri** IHT ile dengeleniyor, sonra rastgele bölünüyor, test de bu dengelenmiş kümeden yapılıyor.

**Hatasız protokol:** Önce gerçek veri bölünüyor, dengeleme sadece eğitim kısmına uygulanıyor, test gerçek dağılımda (%20 gelmeme) yapılıyor.

| | Makale protokolü | Hatasız protokol |
|---|---|---|
| Karar ağacı, 10 özellik, doğruluk | %93,8 (makale: %94,5) | **%51,9** |
| Tek özellik (yalnız lead time), doğruluk | %93,8 (makale: %95,4) | %51,9 |
| AUC | 0,967 | **0,716** |
| "Gelmeyecek" işaretlenen hasta oranı | — | %65 (gerçek oran %20) |
| Ortalama tahmin edilen risk | — | 0,65 (gerçek oran 0,20) |
| "Herkes gelir" diyen kuralın doğruluğu | %79,8 | %79,8 |

**Sebepler:**

1. **IHT, 64.394 "gelen" kaydı sildi** (verinin %58'i, hepsi çoğunluk sınıfından). Silinenler modelin ayıramadığı, yani zor örnekler. Geriye kalan %48 gelmeyen içeren kolay bir küme. Test de aynı kümeden yapıldığı için doğruluk şişiyor.
2. **Doğruluk dengesiz veride yanıltıcı bir ölçü.** Hatasız protokolde doğruluk %51,9: "herkes gelir" diyen kuraldan (%79,8) bile kötü.
3. **Olasılıklar kalibre değil.** Dengelenmiş eğitimle model ortalama %65 risk veriyor, oysa gerçek oran %20. Bu olasılıklar overbooking kararında kullanılamaz.
4. **Rastgele bölme.** Aynı hasta hem eğitimde hem testte olabilir. Makale, bu konuda önlem aldığını söylemiyor.
5. **Gerçek ayırt etme gücü:** AUC 0,72. Bizim modelimizin AUC'si 0,73 (random forest). Yani iki çalışma aynı gerçek performansta, fark sadece ölçüm yönteminde.
6. **Makalede AUC ve kalibrasyon yok.** Precision/recall dengelenmiş küme üzerinde.

Not: Makalenin "önceki çalışmalar %65–82 doğruluk verdi, biz %95 verdik" karşılaştırması bu yüzden geçersizdir: farklı veri ve farklı protokollerin doğrulukları karşılaştırılamaz. **Makaleyi rakamı için kaynak göstermeyin**; konunun literatürünü ve lead time bulgusunu desteklemek için kullanın.

## 4. Makalenin doğruladıkları

| Konu | Makale | Bizim kontrolümüz |
|---|---|---|
| Lead time en önemli özellik | Evet | Çıkarınca random forest AUC'si 0,735'ten **0,627**'ye düşüyor |
| Mahalle bilgisi | Özellik olarak kullanmışlar | Ekleyince AUC 0,7300'den 0,7308'e: kazanç sıfır, dışarıda bırakmamız doğru |
| `SMS_received` | Özellik olarak kullanmışlar | Randevu anında bilinmiyor, bizde kullanılmıyor (doğru) |
| Gelmeme oranı | %20,19 | Bizde %20,2 (temizlenmiş veri) |

## 5. Makalenin politikası simülasyonumuzda

Makalenin overbooking mantığını ("sınıflandırıcı gelmeyecek dediği her slotu fazla randevuya aç, üst sınır yok") simülasyona **karşılaştırma politikası** olarak ekledik (`simulation/templates/day_by_day.py`). İki hâli var; sonuçlar 27 günün tüm gerçek randevuları için:

| | Görülen hasta | Ortalama bekleme | Doktor boş zamanı |
|---|---|---|---|
| Kural yok (sabit aralık) | 67.276 | 2,0 dk | 9.062 saat |
| Makale politikası, **kalibre** modelimizle (p ≥ 0,5) | 67.281 (+%0,0) | 2,0 dk | 9.061 saat |
| Makale politikası, **dengelenmiş eğitimli** sınıflandırıcıyla | 88.169 (**+%31,1**) | **14,7 dk (+%640)** | 4.732 saat (−%47,8) |
| Bizim eşik kuralı 0,30 | 84.547 (+%25,7) | 6,1 dk (+%205) | 5.718 saat (−%36,9) |
| Kısa slotlar (Şablon 1) | 88.207 (+%31,1) | 5,9 dk (+%198) | 5.664 saat (−%37,5) |

Okuma:

- **Kalibre modelle makale politikası neredeyse hiç çalışmaz.** En yüksek riskimiz 0,54, hastaların yalnızca %0,01'i p ≥ 0,5. Kural hiç tetiklenmiyor.
- **Dengelenmiş sınıflandırıcıyla** hastaların %57,5'i "gelmeyecek" işaretleniyor. Aynı kadar hasta görülüyor (+%31, kısa slotlarla eşit) ama bekleme **14,7 dakikaya** çıkıyor, bizim yöntemlerimizin 2,5 katı. Yani makalenin yaklaşımı, hasta sayısını artırmanın en pahalı yolu.
- **Bizim yaklaşımın avantajı** tek bir şey: olasılığı kalibre ediyor ve kararı maliyete bağlıyor (R5-A), sınıflandırıcının 0/1 çıktısına değil.

## 6. Bizim eksiklerimiz ve yapılacaklar

1. **Hiperparametre ayarı yok.** Makale grid search kullanmış. Bizde `min_samples_leaf=50` ve `C=1` sabit. Zamana göre çapraz doğrulamayla ayar yapılmalı.
2. **Doğruluk, precision, recall raporlanmadı.** Jüri bunları soracaktır. Raporda "herkes gelir" tabanı (%79,8) ve seçilen eşikte (örneğin 0,30) precision/recall verilmeli. Makaleyle karşılaştırırken protokol farkı açıkça yazılmalı.
3. **Model çeşitliliği az.** Sadece lojistik regresyon ve random forest var. Lead time'ı aralıklara bölen lojistik regresyon (AUC ≈ 0,72) ve bir gradyan artırma modeli denenmeli.
4. **Yeni modelin dengelenmemesi şart.** Ekibin modeli henüz repoda değil (`ml/models` boş). Eğitimde dengeleme ya da `class_weight='balanced'` kullanılırsa olasılıklar şişer (ortalama 0,20 yerine ~0,45–0,65) ve overbooking kuralı bozulur (5. bölüm). Model dengelemesiz eğitilmeli, kalibrasyonu kontrol edilmeli.
5. **Yeni hastalar için ayrı performans ölçülmedi.** Hastaların %72'sinin önceki randevusu yok. AUC bu alt grup için ayrıca raporlanmalı (R4 kuralının hedefi bu).
6. **Hasta bazlı ayırma yok.** Eğitim ve test bölmeleri hasta bazında değil (günlere göre). Aynı hastalar iki tarafta olabilir. Bu, sınırlılıklar bölümünde yazılmalı.
7. **Hatırlatma etkisi simülasyonda yok.** Makalenin aktardığı çalışmada aranarak hatırlatma gelmeme oranını %7,3 azaltmış. Bu rakam, simülasyona hatırlatma etkisini eklerken (açıkça varsayım diye işaretleyerek) dayanak olabilir. Dikkat: Kaggle'daki SMS verisi bu etkiyi ölçmek için kullanılamaz (SMS riskli hastalara gönderilmiş).
8. **Tatil ve klinik türü yok.** Literatür bunları önemli buluyor. Verimiz 6 haftalık ve klinik bilgisi yok; bunları test edemeyiz, sınırlılık olarak yazılmalı.

## 7. Yeniden üretim

`ml/paper_replication.py` yukarıdaki 3. ve 4. bölümlerdeki tüm rakamları üretir. `imbalanced-learn` yüklemesi `numpy` ve `scikit-learn` sürümlerini yükseltir ve projenin ortamını bozabilir, bu yüzden betik ayrı bir sanal ortamda çalıştırılmalı (kurulum adımları betiğin başında yazıyor). Simülasyon sonuçları için `python simulation/main.py` çalıştırılır; makale politikaları `simulation/templates/results/comparison.html` içinde "Literature" satırları olarak görünür.

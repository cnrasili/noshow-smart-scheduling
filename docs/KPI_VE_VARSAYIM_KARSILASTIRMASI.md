# KPI ve varsayım karşılaştırması

Bu belge iki soruyu yanıtlar: (1) simülasyondaki KPI'lar uygulamadaki KPI ekranıyla aynı şeyi mi ölçüyor, (2) simülasyonda hangi değerler **ölçülmüş**, hangileri **karar**, hangileri **varsayım**. Kararlar `docs/KARAR_LISTESI.md` ve `docs/decisions.json` dosyalarındadır; sayılar `docs/IEN_DENEY_SONUCLARI.md` ve `docs/SONUC_OZETI.md` dosyalarından gelir.

## 1. KPI tanımları: simülasyon ve uygulama

Tanımlar `docs/kpi-definitions.md`'deki gibidir ve ikisinde de aynıdır. Hesaplama biçimi farklıdır:

| KPI | Simülasyon (`simulation/clinic_sim.py`) | Uygulama (`GET /kpi`, `docs/api-contract.md`) | Fark ne yapar? |
|---|---|---|---|
| Bekleme | Muayene başlangıcı − max(randevu saati, hastanın gelişi); geliş saati gerçek gecikmeyle dağılır | Hastaların **zamanında geldiği** varsayılır; muayene başlangıç ve bitişi kayıtlı değildir | Uygulama yalnızca sıra kaynaklı beklemeyi görür; simülasyondaki geç kalma etkisi görünmez |
| Muayene süresi | Log-normal, ortalama 7,5 dk (aralık 5–10 dk), değişkenlik 0,5 | Sabit süre, `kpi.service_minutes` (serviste şu an 12, karar 7,5) | Değişkenlik bekleme ve mesai aşımını artırır; sabit süre bunları küçük gösterir |
| Boşta kalma | Oturum içinde hastasız dakikalar | Aynı tanım, sabit süreli hastalarla | Benzer; fark muayene süresinden gelir |
| Mesai aşımı | Son muayene bitişi − oturum sonu | Aynı tanım, sabit süreli hastalarla | Aynı |
| Doluluk | Meşgul süre ÷ oturum süresi | Aynı tanım | Aynı |
| Oturum süresi | 16 slot x 15 dk = 240 dk | İlk slot başı – son slot sonu ya da çalışma saatleri (`kpi.session`) | Slot şablonu seçimine bağlı |

**Sonuç.** İki taraf aynı tanımı kullanıyor ama uygulama daha iyimser bir ölçüm yapar (zamanında gelen hasta, sabit süre). Raporda simülasyon ve uygulama sayıları yan yana verilecekse bu fark yazılmalıdır. "Ölçülen" değerler yalnızca uygulamada kayıtlı `attended` bilgisinden gelen hasta sayısı ve gelmeme oranıdır; bekleme, boşta kalma ve mesai aşımı iki tarafta da **model çıktısıdır**, doğrudan ölçüm değildir.

## 2. Ölçülen, karar ve varsayım

| Değer | Durum | Kaynak | Not |
|---|---|---|---|
| No-show riski | **Ölçülmüş** (modelin görmediği 27 günde tahmin) | `ml/data/processed/` | Zamana göre ayrılmış değerlendirme (`docs/MODEL_KARSILASTIRMA.md`) |
| Gelme / gelmeme | **Ölçülmüş** (110.521 gerçek randevu) | Kaggle verisi | — |
| Muayene süresi 5–10 dk, ortalama 7,5 dk | **Karar** (ekip) | Türkiye devlet hastanesi poliklinik uygulaması | Kaynak eklenecek `[ONAY]` |
| Eşik %30, günlük sınır 4 | **Karar** (ekip) | `decisions.json` | — |
| En uzun ortalama bekleme 15 dk | **Karar** (ekip) | `decisions.json` | — |
| Slot 15 dk, 16 slot (4 saat) | **Karar** (ekip; Türkiye'de randevu aralığı genel olarak 15 dk) | `decisions.json` | Kaynak eklenecek `[ONAY]`; 10 dk slot için duyarlılık satırı var |
| Muayene değişkenliği 0,5 | Varsayım | `SessionConfig` | Süreler sağa çarpıktır; kaynak gerekli |
| Geç kalma sapması 4 dk | Varsayım | `SessionConfig` | Veri setinde geliş saati yok; ölçülemez |
| Talep: slot sayısı + 4 istek (20) | Varsayım | `SessionConfig` | Veride saat bilgisi olmadığından günlük talep slota oranlanamaz |
| Muayene odası (oturum) sayısı | Karar: tek hekim kuralı **uygulanmaz**; sistem tek departman (General Practice) | #61 | Günün randevuları departmanın muayene odası oturumlarına dağıtılır; sonuçlar oturum başına, oda sayısı varsayım |
| Hatırlatma etkisi | **Ölçülmemiş**; yalnızca senaryo | `experiments.py` | Gerçek A/B testi gerekir; `SMS_received` rastgele deney değildir |

## 3. Servis ve simülasyon ayarları

`simulation/parity_check.py`, servisin `rules.decide` fonksiyonuyla simülasyonun eşik kuralının 20.000 rastgele slotta **aynı kararı** verdiğini gösterir (fark 0). Karar listesinden sonra ayarlar şöyle ayrışır; farkları komut yazdırır:

| Ayar | Servis (`config.yaml`) | Karar |
|---|---|---|
| Eşik | 0,30 | 0,30 (aynı) |
| Günlük ek randevu sınırı | **2** | **4** |
| Muayene süresi (`kpi.service_minutes`) | **12 dk** | **7,5 dk** |

Servis tarafındaki iki değer ve bunları sınayan testler CEN tarafından güncellenmelidir (`docs/KARAR_LISTESI.md` bölüm 5).

## 4. Duyarlılık: hangi varsayım sonucu ne kadar değiştirir?

Güncel tablo `docs/IEN_DENEY_SONUCLARI.md` bölüm 4'tedir (karar ayarının sabit aralığa göre farkı). Rastgele orman ile (600 oturum, eşleştirilmiş):

| Varsayım | Görülen | Bekleme (dk) | Boşta (dk) | Mesai aşımı (dk) |
|---|---|---|---|---|
| Taban (7,5 dk, 15 dk slot) | +2,76 | +0,95 | −20,7 | +0,27 |
| Muayene 5 dk | +2,76 | +0,41 | −14,3 | 0,00 |
| Muayene 10 dk | +2,76 | +2,18 | −26,7 | +1,14 |
| Değişkenlik 0,3 | +2,76 | +0,78 | −20,7 | +0,10 |
| Değişkenlik 0,8 | +2,76 | +1,37 | −20,8 | +0,63 |
| Talep 16 istek (= slot sayısı) | +0,00 | +0,96 | −0,4 | −0,36 |
| Talep 24 istek | +2,76 | +0,91 | −21,0 | +0,24 |
| Geç kalma sapması 8 dk | +2,76 | +0,90 | −20,5 | +0,55 |
| 10 dk slot, 24 slot | +3,12 | +1,71 | −22,8 | +0,68 |
| No-show oranı x0,7 | +0,11 | +0,05 | −0,9 | −0,01 |
| No-show oranı x1,3 | +2,91 | +0,97 | −21,4 | +0,13 |

**Okuma.**

- **Güvenle söylenebilen:** kural hasta sayısını artırır ve boşta kalmayı azaltır; bunun bedeli bekleme ve çoğu durumda mesai aşımıdır. Yön hiçbir duyarlılık senaryosunda değişmez.
- **Varsayıma bağlı olan:** bedelin büyüklüğü. Muayene 5 dk iken bekleme artışı yalnızca +0,4 dk, 10 dk iken +2,2 dk'dır; mesai aşımı artışı 0,0 ile 1,1 dk arasında oynar. Muayene süresinin üst sınırı (10 dk) bekleme ve mesai aşımı için kritiktir.
- **Kuralın değeri no-show oranına bağlıdır:** gelmeme oranı %30 düşerse kural neredeyse hiç tetiklenmez (+0,11 hasta); %30 artarsa kazanç büyür (+2,9). Veride gelmeme oranı yaklaşık %20'dir.
- **Talep kapasiteyi aşmıyorsa** (16 istek, 16 slot) kural işe yaramaz: önce yeterli talep olmalıdır.

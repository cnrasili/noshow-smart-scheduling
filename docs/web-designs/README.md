# Web arayüzü için 3 örnek tasarım (IEN tarafı)

Üç tasarım da tek dosyalık HTML'dir; çift tıklayıp tarayıcıda açılır, sunucu gerekmez.
Sayılar gerçek randevu kayıtlarından ve SimPy simülasyonundan gelir. Simülasyon parametreleri
(slot 10 dk x 24, muayene ortalama 7,5 dk, gecikme 4 dk, oturum başına 4 ek talep; `docs/decisions.json`) karar listesine göre geçici onaylıdır, akademik gerekçe sonra eklenecek.

| Dosya | Hasta | Personel | Yönetim |
|---|---|---|---|
| `design1.html` (kurumsal portal) | Aylık takvimde gün seç, saat seç, randevu al; randevularım ve mesajlar | Bugünkü program: saat çizelgesi, Geldi/Gelmedi, sıradaki hasta | Özet (KPI, kural karşılaştırması), randevu kararları (risk, ek randevu), mesajlar ve A/B |
| `design2.html` (haftalık takvim) | Haftalık takvim ızgarasında saat seç | Pano: Bekleyen / Geldi / Gelmedi sütunları | Eşik ve günlük limit kaydırıcıları, "Bu karar neden verildi?" paneli, karar günlüğü, KPI, mesajlar ve A/B |

**Departman bazlı:** Sistem tek departmandır (`General Practice`, hekim yok; 17 Ekim 2026 kapsamı). Hasta departmanın takviminden saat alır; personel (poliklinik) ekranı o günün listesini görür; yönetim ekranında oturumlar "Oturum n" olarak anılır (simülasyonun muayene odası oturumu).

Üç rol ayrı portal gibi davranır (ayrı renk, ayrı menü). Üstteki şeritten giriş türü seçilir (demo).

**Gizlilik kuralı:** Eşik kuralı, overbooking, gelmeme riski ve A/B grubu **yalnızca yönetim** ekranında görünür. Hasta takvimde sadece "müsait / dolu" görür; personel yalnızca kendi programını (saat, randevu no, yaş) görür. **Demo günü ve veri günleri:** "Bugün" 9 Haziran 2016'dır ve program boştur. Hasta panelinden (üstteki seçimle 3 demo hasta arasında geçilir) alınan randevular hekimin o günkü programına düşer ve yönetim ekranındaki karar kaydında nedeniyle görünür. Aynı saate ikinci hasta, ilk hastanın riski %30 ve üstündeyse ve günlük 4 ek randevu dolmadıysa yazılır. Hekim "Geldi / Gelmedi" işaretini yalnızca bugün için yapar. Veri setindeki 27 günün (29 Nisan – 8 Haziran) her birinde o günün **tüm gerçek randevuları** (110.521 kayıt; randevu no, yaş, gerçek sonuç) salt okunur görünür; veri setinde randevu saati olmadığından saat gösterilmez. Doktor ekranında takvimle ileri-geri gezilir, listeler kendi içinde kaydırılır ve 200–300 kayıtlık parçalarla yüklenir. Yönetim ekranında her gün için gerçek gelmeme oranı, ortalama risk ve eşik üstü payı tablo halinde gösterilir. Gerçek kayıtlar `records.js` dosyasındadır (iki sayfa aynı klasörden okur, dosyaları birlikte tutun).

**Yönetimde gün seçimi:** Randevu kararları (tasarım 1) ve takvim/karar günlüğü (tasarım 2) ekranlarında 27 veri gününden biri seçilir; her gün için o günün bir muayene odası oturumu (20 randevu isteği, gerçek kayıtlardan simülasyonla slotlara dağıtılmış) risk ve ek randevu kararlarıyla gösterilir.

**Demo sınırı:** Risk modelinin API'si bağlı olmadığından yeni randevuların riski gerçek risk dağılımından örneklenir ("örnek" diye etiketlidir).

Üçünde de bulunanlar (Excel'deki görevlere göre; yönetim ekranında):
- **KPI kartları:** doluluk, boşta kalma, mesai aşımı, ortalama bekleme, görülen hasta; her kart "kural yok" ile karşılaştırılır.
- **Onay ve hatırlatma mesajları:** örnek metinler, gönderim zamanı (onay 1 dk içinde, hatırlatma 24 saat önce), durum. Kontrol grubu yalnızca onay alır (`docs/api-contract.md`).
- **Hatırlatma A/B tablosu:** `GET /ab/summary` yanıtıyla aynı alanlar. **Bu gerçek bir deney değildir:** veri setindeki `SMS_received` alanından hesaplanır, gruplar rastgele değildir; SMS alanların gelmeme oranı daha yüksektir, fark nedensel okunamaz. Gerçek test başlayınca aynı tablo canlı veriyle dolar.

Sayfalar canlı API'ye değil, `data.json` içindeki dondurulmuş sonuçlara bağlıdır.

## Yeniden üretme

```bash
python simulation/web_designs/build.py           # veriyi yeniden hesaplar ve sayfaları yazar
python simulation/web_designs/build.py --reuse   # data.json'dan yalnızca sayfaları yeniler
```

Şablonlar ve ortak kod `simulation/web_designs/` içindedir (`design*.html`, `common.js`); `build.py` ayrıca `records.js` üretir; `/*__DATA__*/null` yerine veri gömülür.

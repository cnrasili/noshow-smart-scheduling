# IEN tarafı teslim notu (CEN ekibi için)

IEN tarafında yapılacak iş kalmadı. Aşağıda ne yapıldığı, nerede olduğu ve sizden beklenenler var.

## 1. Kararlar (hepsi `docs/decisions.json` ve `docs/KARAR_LISTESI.md` içinde)

| Konu | Karar |
|---|---|
| Model | Random Forest (`random_forest-v1`, AUC 0,729). Karar ağacı alternatif olarak ayrı dalda duruyor. |
| Overbooking eşiği | 0,30 |
| Günlük ek randevu sınırı | 4 |
| Aynı saate en fazla | 2 hasta |
| Bekleme sınırı | 15 dk |
| Muayene süresi | ortalama 7,5 dk (5–10 dk arası) |
| Slot süresi | 15 dk, günde 16 slot (Türkiye'de genel uygulama; kaynakla doğrulanmadı) |
| Kapsam | Hekim bazlı değil, **departman bazlı**: `Department = General Practice` |
| Tek doktor kuralı | uygulanmayacak |
| Teslim tarihi | 16 Aralık 2026 |

Karar değişirse `docs/decisions.json` güncellenir, `python ml/apply_decisions.py` ile model, simülasyon ve belgeler yeniden üretilir.

## 2. Ne yapıldı

- **Veri:** `ml/data/clean_data.py` temiz veriye `Department` sütununu ekler. Zamansal sızıntı kontrolü yapıldı (`docs/ZAMANSAL_SIZINTI_KONTROLU.md`).
- **Modeller:** Lojistik regresyon, Random Forest, karar ağacı karşılaştırıldı (`docs/MODEL_KARSILASTIRMA.md`). Zamana göre %80/%20 bölme, AUC, kalibrasyon, alt grup analizi var.
- **Servis modeli:** `ml/models/` altında, servisin scikit-learn 1.9.1 sürümüyle üretildi. Main'de kurulu.
- **Simülasyon:** `simulation/` altında SimPy modeli. Sonuçlar (2.000 oturum, kural yok → kural var): görülen hasta 12,81 → 15,60 (+%22), doluluk 0,40 → 0,49, ortalama bekleme 0,22 → 1,13 dk. Özet: `docs/SONUC_OZETI.md`, ayrıntı: `docs/IEN_DENEY_SONUCLARI.md`, bekleme dağılımı: `docs/BEKLEME_DAGILIMI.md`.
- **Servis ayarları (PR #64):** `overbooking-service/config.yaml` içinde sınır 4, muayene süresi 7,5 dk.
- **Web tasarımları:** `docs/web-designs/design1.html` ve `design2.html`. Giriş sayfası var: Randevu Oluştur (hasta), Doktor Girişi (departman), Yönetici Girişi (tüm sayfalar). Demo hesaplar: doktor `doktor` / `doktor123` / `DR-001`; yönetici kodu `YON-2026`. Risk, eşik ve overbooking yalnızca yönetim ekranında görünür. KPI kartları gerçek veriden ve `decisions.json`'dan beslenir.
- **Hasta kayıtları:** `python simulation/web_designs/serve.py` çalışırken hasta bilgileri ve randevular ayrı `output/web_randevulari.xlsx` dosyasına yazılır (ana veri dosyasına dokunmaz).
- **Belgeler:** `docs/Anlatım.md` (baştan sona anlatım), `docs/TEKRAR_URETIM.md` (tekrar üretim), `docs/HOCAYA_SORULACAKLAR.md`, `docs/DEMO_VE_JURI_HAZIRLIGI.md`, `docs/IEN_RAPOR_TASLAGI.md`.

## 3. PR'lar ve dallar

- **PR #62** (`IEN`): ana IEN işi. **PR #64** (`IEN-service-settings`): servis ayarları. İkisinin de CI'ı geçiyor, birleştirilebilir, maintainer onayı bekliyor.
- `IEN-RandomForest` ve `IEN-DecisionTree` dalları model alternatifleri için referans olarak duruyor.

## 4. Sizden beklenenler

1. **Web uygulamasında slot süresi 20 dk → 15 dk** olmalı (karar 15 dk).
2. **Model API bağlantısı** (CEN-2): servis `random_forest-v1` modelini yükleyip riski döndürecek. Kural `POST /booking-decision` ile aynı mantıkta: slot doluysa ve her hastanın riski ≥ 0,30 ise, günlük sınır (4) aşılmadıysa ek randevuya izin.
3. **PR #62 ve #64 incelemesi ve birleştirilmesi.** Sonrasında #6, #8, #9, #61 issue'ları kapatılabilir.
4. **Hocadan cevap bekleyenler:** muayene süresi, slot süresi, `AppointmentDay` sütunundaki saatlerin (hepsi 00:00) girilip girilmeyeceği. Cevaplara göre sayılar tek komutla yeniden üretilir.

## 5. Dikkat edilecekler

- Web tasarımlarındaki giriş ve hesaplar yalnızca demo. Gerçek kimlik doğrulama sunucuda yapılmalı.
- Web tasarımlarının KPI kartları (doluluk %38,0 → %47,8) gerçek randevu sırasıyla hesaplanır; `SONUC_OZETI.md` rastgele oturumlarla hesaplanır (%40 → %49). Fark yöntemden gelir, ayrıntısı `docs/web-designs/README.md` içinde.
- Modeli yeniden eğitirken scikit-learn sürümü servisle aynı (1.9.1) olmalı.

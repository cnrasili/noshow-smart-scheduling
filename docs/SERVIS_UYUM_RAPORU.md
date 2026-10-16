# Servis uyum raporu (IEN modeli ve kararları, overbooking servisi)

**Amaç:** `IEN` dalındaki modelin ve karar ayarlarının overbooking servisiyle çalıştığını, hangi servis testlerinin güncellenmesi gerektiğini göstermek. **Sınır:** Bu kontrol IEN tarafında, servisin bir **kopyası** üzerinde yapıldı; servis dosyalarına dokunulmadı. CEN'in gerçek ortamında (Docker, PostgreSQL, Python 3.12) doğrulanmadı; CEN bu raporun komutlarını kendi ortamında tekrarlamalıdır.

## 1. Nasıl denendi

- Servis (`overbooking-service/`), veritabanı paketi (`db/`) ve `ml/export_model.py` geçici bir klasöre kopyalandı.
- Ortam: Python 3.11, scikit-learn 1.9.1, pandas 3.0.6, pytest; servisin kendi testleri (bellek içi SQLite, sahte hasta ve slot kaynakları).
- Modelin yeri `MODEL_DIR` ortam değişkeniyle verildi (`overbooking_service/config.py` → `model_dir`).

```bash
# servis klasöründe (CEN ortamında)
MODEL_DIR=../ml/models pytest
```

## 2. Sonuçlar

| Durum | Sonuç |
|---|---|
| Değişmemiş servis, `dummy-v0` modeli | 150 test geçti (ortam sağlıklı) |
| Seçili rastgele orman (`ml/models/`) | 148 geçti, 2 başarısız: `test_predict_api.py::test_returns_probability_and_version` ve `::test_prediction_is_logged` yalnızca `model_version == "dummy-v0"` bekliyor; API artık `random_forest-v1` döndürüyor |
| Karar ağacı adayı (`ml/models/candidates/decision_tree/`) | Aynı: 148 geçti, aynı 2 test `dummy-v0` yüzünden başarısız |
| `config.yaml` karar değerleriyle (`daily_overbook_limit: 4`, `service_minutes: 7.5`) ve rastgele orman | 144 geçti, 6 başarısız (aşağıdaki liste) |

Modelin kabul testleri (`test_model_acceptance.py`: özellik şeması, olasılık aralığı, sıralama) iki modelde de **geçti**.

## 3. CEN'in güncellemesi gereken testler

Hepsi, testlerde sabit yazılı eski değerlerden geliyor:

| Test | Neden başarısız | Yapılacak |
|---|---|---|
| `test_predict_api.py::test_returns_probability_and_version` | `dummy-v0` bekliyor | Beklenen sürümü yeni modelin sürümüyle (`random_forest-v1`) ya da `predictor.version` ile değiştirin |
| `test_predict_api.py::test_prediction_is_logged` | Aynı | Aynı |
| `test_booking_api.py::test_default_rule_comes_from_config` | `daily_overbook_limit == 2` bekliyor | 4 |
| `test_kpi.py::test_default_settings_come_from_config` | `service_minutes == 12` bekliyor | 7,5 |
| `test_kpi.py::test_kpi_endpoint` | Muayene süresi 12 dk varsayımıyla hesaplanmış beklenen değerler | 7,5 dk ile yeniden hesaplayın |
| `test_kpi.py::test_day_without_working_hours_falls_back_to_slots` | Aynı | Aynı |

Servis kodu (`rules.py`, `predictor.py`) değişmeden çalışıyor; yalnızca `config.yaml` (iki değer) ve bu testler güncellenir.

**Güncelleme (17 Ekim 2026).** Karar ayarları ve ilgili 4 test (`test_booking_api`, `test_kpi`) `IEN-service-settings` dalında güncellendi (`config.yaml`, servis `README.md`); `dummy-v0` modeliyle servisin 150 testi geçiyor. Kalan 2 test (`test_predict_api.py`) model kurulunca (`install_model`) güncellenir, çünkü model sürümü modelle birlikte değişir.

## 4. Gerçek model ve kural, HTTP API üzerinden

Gerçek model ve `config.yaml` kuralı (eşik 0,30, günlük sınır 4), `/predict` ve `/booking-decision` uçlarından çağrıldı. Hasta ve slot verisi sahteydi; model ve kural gerçekti.

| Çağrı | Rastgele orman | Karar ağacı |
|---|---|---|
| `/predict`: genç, 3 gelmeme geçmişi, 40 gün önce alınmış | p = 0,358 | p = 0,370 |
| `/predict`: yaşlı, 5 gelen randevu, 1 gün önce alınmış | p = 0,118 | p = 0,186 |
| `/predict`: yeni hasta | p = 0,346 | p = 0,370 |
| `/booking-decision`: boş slot | izin, normal | izin, normal |
| `/booking-decision`: slottaki hasta yüksek riskli (0,36 / 0,37 ≥ 0,30) | izin, **overbook**, "daily overbooks 0/4" | aynı |
| `/booking-decision`: slottaki hasta düşük riskli (0,12 / 0,19 < 0,30) | **ret** | **ret** |

Yani `dummy-v0` devreden çıkıyor (yanıttaki `model_version` yeni modelin adı), risk hastaya göre değişiyor ve karar riske göre değişiyor.

## 5. Bu kontrolün kapsamadığı

- Gerçek veritabanı (PostgreSQL), Docker imajı ve Python 3.12.
- Web uygulamasından çağrı (CEN-1) ve KPI ekranı (admin servis) ile zincirin tamamı.
- Model dosyasının servisin kendi `install_model` komutuyla kurulumu: IEN tarafında kabul kontrolleri çalıştırıldı (`ml/apply_decisions.py`); kurulum adımı CEN'de yapılmalı.

Bu yüzden uçtan uca doğrulama (tahmin → karar → randevu → KPI) CEN ile birlikte yapılacak iş olarak açık kalır.

**Güncelleme (17 Ekim 2026, sonra).** Rastgele orman modeli `main`'e alındı ve serviste kuruldu (PR #65, `94f9c93`); `dummy-v0` ve `make_dummy_model.py` kaldırıldı, `test_predict_api.py` yeni sürümü bekleyecek biçimde güncellendi. Bu rapordaki 2 başarısız test bu yüzden artık geçerli değil. Servis ayarları (limit 4, 7,5 dk) PR #64'te bekliyor.

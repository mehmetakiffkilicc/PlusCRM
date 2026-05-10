---
title: churn-view — Churn Analizi
tags: [source, backend, analytics]
source: backend/api/analytics/churn_view.py
date: 2026-05-04
status: stable
---

# churn-view — Churn Analizi

**Özet:** Müşteri kaybı (churn) analizini hesaplayan endpoint. Seçilen tarih filtresine göre referans tarihi belirler ve bu tarihe göre churn oranlarını hesaplar; gelecek tarihlerde yanlış hesaplama yapmamak için akıllı tarih düzeltme mantığı içerir.
**Kütüphaneler:** DRF, `db_engine` (SQLite/Postgres abstraction)
**Bağlantılar:** [[entities/analytics-churn-view]], [[concepts/churn]]

## Önemli Mimari Detaylar

### Referans Tarihi Mantığı
- `end_date_param` varsa → kullanıcı seçimi referans alınır.
- `year_param` + `month_param` varsa → ayın son günü hesaplanır.
- **Kritik**: Seçilen tarih gelecekte ise (örn. 2026 yılı seçildi ama bugün Ocak) → `datetime.now()` kullanılır. Bu olmadan tüm müşteriler churn görünür.
- `db_engine.ph()` ile SQL parametresi abstraction (`?` SQLite, `%s` Postgres).

### Filtreler
`year`, `month`, `end_date`, `customer_type`, `approval_status`, `region` — tümü GET parametresiyle alınır.

## Issues
- Gelecek tarihe gelince "herkesi churn saymak" problemi yakalanmış ve düzeltilmiş. Benzer mantık diğer analytics view'larda da uygulandı mı kontrol edilmeli.

## Sources
- `backend/api/analytics/churn_view.py`

## Related
- [[concepts/churn]] — churn kavramı ve hesaplama yöntemi
- [[entities/analytics-churn-view]] — entity sayfası
- [[sources/code-modules/2026-05-04-rfm-view]] — benzer mimari pattern (rfm)

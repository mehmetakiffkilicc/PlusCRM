---
title: Analytics — Churn View
tags: [backend, analytics]
source: backend/api/analytics/churn_view.py
date: 2026-05-04
status: stable
---

# Analytics — Churn View

**Özet:** Müşteri kaybı oranını ve riskli müşterileri tespit eden endpoint. Gelecek tarihlerde yanlış hesaplama yapmamak için akıllı referans tarihi mantığı içerir.
**Kütüphaneler:** DRF, `db_engine`
**Bağlantılar:** [[concepts/churn]], [[entities/datasource-modeli]], [[sources/code-modules/2026-05-04-churn-view]]

## Endpoint
`GET /api/veri-kaynaklari/<data_source_id>/churn-analizi/`

## Parametre Grubu
`year`, `month`, `end_date`, `customer_type`, `approval_status`, `region`

## Önemli Davranış
Seçilen dönem ilerideyse `datetime.now()` referans alınır — tüm müşterileri yanlışlıkla churn saymayı engeller.

## Sources
- `backend/api/analytics/churn_view.py`
- `backend/api/urls.py` satır 115

## Related
- [[concepts/churn]] — kavram sayfası
- [[entities/page-churn-analysis]] — frontend

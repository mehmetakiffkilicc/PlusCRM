---
title: Analytics — Segmentasyon View
tags: [backend, analytics]
source: backend/api/analytics/segmentation_view.py
date: 2026-05-04
status: stable
---

# Analytics — Segmentasyon View

**Özet:** Müşteri segment dağılımını ve segment geçiş matrisini döndüren endpoint. Database tipi datasource'lar için SQL aggregate optimize edilmiştir.
**Kütüphaneler:** DRF, `analytics.base` TTL cache
**Bağlantılar:** [[concepts/segmentasyon]], [[entities/analytics-rfm-view]], [[sources/code-modules/2026-05-04-segmentation-view]]

## Endpoint'ler
- `GET /api/veri-kaynaklari/<id>/segmentasyon/`
- `GET /api/veri-kaynaklari/<id>/segmentasyon/detay/`
- `GET /api/veri-kaynaklari/<id>/segment-gecis-matrisi/`

## Optimizasyon
Database datasource → SQL aggregate. CSV/JSON datasource → Python hesaplama.

## Sources
- `backend/api/analytics/segmentation_view.py`
- `backend/api/urls.py` satır 121-122, 135

## Related
- [[concepts/segmentasyon]] — metodoloji
- [[entities/analytics-rfm-view]] — RFM segmentleriyle örtüşür
- [[entities/page-segmentation]] — frontend

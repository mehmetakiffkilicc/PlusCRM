---
title: Analytics — CLV View
tags: [backend, analytics]
source: backend/api/analytics/clv_view.py
date: 2026-05-04
status: stable
---

# Analytics — CLV View

**Özet:** Müşteri yaşam boyu değerini Platinum/Gold/Silver/Bronze segmentlerinde hesaplar; drill-down tutarlılığı için 5 dakikalık dahili cache kullanır.
**Kütüphaneler:** DRF, Python in-process cache
**Bağlantılar:** [[concepts/clv]], [[entities/datasource-modeli]], [[sources/code-modules/2026-05-04-clv-view]]

## Endpoint'ler
- `GET /api/veri-kaynaklari/<id>/clv-analizi/` — özet
- `GET /api/veri-kaynaklari/<id>/clv-analizi/detaylar/` — segment drill-down

## Dahili Cache
`_clv_internal_cache` dict, 5dk TTL. Özet ve detay aynı cache'i paylaşır.

## Sources
- `backend/api/analytics/clv_view.py`
- `backend/api/urls.py` satır 116-117

## Related
- [[concepts/clv]] — metodoloji
- [[entities/page-clv]] — frontend

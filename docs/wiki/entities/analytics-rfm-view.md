---
title: Analytics — RFM View
tags: [backend, analytics]
source: backend/api/analytics/rfm_view.py
date: 2026-05-04
status: stable
---

# Analytics — RFM View

**Özet:** Müşterileri 11 segmente ayıran RFM (Recency/Frequency/Monetary) analizi endpoint'i. Segment tanımları, renkleri ve önerilen aksiyonları döndürür.
**Kütüphaneler:** DRF, SQLite3, `analytics.base`
**Bağlantılar:** [[concepts/rfm-analizi]], [[entities/datasource-modeli]], [[entities/analytics-segmentation-view]], [[sources/code-modules/2026-05-04-rfm-view]]

## Endpoint
`GET /api/veri-kaynaklari/<data_source_id>/rfm-analizi/`

## 11 Segment (Özet)
Şampiyonlar → Potansiyel Şampiyonlar → Sadık → Sadık Olmaya Adaylar → Yeni → Tekrar Kazanılanlar → Yüksek Harcama → İlgi Bekleyenler → Risk Altındakiler → Uyuyanlar → Kayıp Müşteriler.

## Cache
`base.get_cached_data` / `base.set_cached_data` ile TTL'li in-process cache.

## Sources
- `backend/api/analytics/rfm_view.py`
- `backend/api/urls.py` satır 114 (`rfm-analizi/`)

## Related
- [[concepts/rfm-analizi]] — metodoloji
- [[entities/page-rfm-analysis]] — frontend sayfası
- [[entities/analytics-segmentation-view]] — segmentasyon (genel dağılım)

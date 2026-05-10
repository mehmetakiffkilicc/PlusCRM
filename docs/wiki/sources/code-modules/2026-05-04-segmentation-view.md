---
title: segmentation-view — Müşteri Segmentasyonu
tags: [source, backend, analytics]
source: backend/api/analytics/segmentation_view.py
date: 2026-05-04
status: stable
---

# segmentation-view — Müşteri Segmentasyonu

**Özet:** Müşterileri segment dağılımına göre raporlar; database tipindeki veri kaynaklarında doğrudan SQL optimizasyonu kullanır. `base.py`'deki TTL-cache altyapısıyla tekrarlı sorguları önler.
**Kütüphaneler:** DRF, `analytics.base` cache altyapısı
**Bağlantılar:** [[entities/analytics-segmentation-view]], [[concepts/segmentasyon]], [[entities/datasource-modeli]]

## Cache Altyapısı
- `_build_filter_cache_key()`: kullanıcı ID + request parametrelerinden anahtar üretir.
- `_get_ttl_cache()` / `_set_ttl_cache()`: 5 dakika TTL.
- `_segmentation_filter_cache_max_entries`: önbellek büyüklüğü sınırı.

## Database Optimizasyonu
Datasource tipi `database` ise veya isim `sal/sat` içeriyorsa `db_engine` ile SQL aggregate sorgusu çalıştırır — Python'da hesaplama yerine.

## `_segment_detail_cache`
Segment detay görünümü için ayrı 5 dk. cache; segment drill-down sorgularını hızlandırır.

## Sources
- `backend/api/analytics/segmentation_view.py`

## Related
- [[concepts/segmentasyon]] — segmentasyon metodolojisi
- [[sources/code-modules/2026-05-04-rfm-view]] — segmentler RFM skorlarına dayalı

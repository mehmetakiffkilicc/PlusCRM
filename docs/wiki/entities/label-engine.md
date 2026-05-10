---
title: Label Engine
tags: [backend, domain]
source: backend/label_engine.py
date: 2026-05-04
status: stable
---

# Label Engine

**Özet:** Feature tablolarından 60+ boolean davranış etiketi ve skor kolonu hesaplayarak `musterietiketler` tablosunu güncelleyen toplu SQL motorudur. Her çalışmada tüm etiketler sıfırlanır, sonra yeniden hesaplanır.
**Kütüphaneler:** `db_engine`, Python logging
**Bağlantılar:** [[concepts/musteri-etiketleri]], [[entities/sync-worker]], [[sources/code-modules/2026-05-04-label-engine]]

## Çalışma Şartı
`feature_core_builder.py` önce tamamlanmış olmalı (feature tabloları hazır).

## Etiket Grupları (Özet)
Zaman deseni, sepet deseni, fiyat davranışı, kategori odak, risk/kayıp, hane tipi skoru, churn skoru.

## `build_labels(cursor)` + `capture_etiket_snapshot()`
`build_labels` güncel etiketleri hesaplar; `capture_etiket_snapshot` tarihsel kayıt tutar.

## Sources
- `backend/label_engine.py`

## Related
- [[concepts/musteri-etiketleri]] — etiket metodolojisi
- [[entities/sync-worker]] — label_engine'i tetikler
- [[entities/analytics-rfm-view]] — RFM + etiket birlikte kullanılır

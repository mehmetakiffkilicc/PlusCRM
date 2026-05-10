---
title: label-engine — Müşteri Etiket Motoru
tags: [source, backend, domain]
source: backend/label_engine.py
date: 2026-05-04
status: stable
---

# label-engine — Müşteri Etiket Motoru

**Özet:** Feature tablolarından 60+ boolean davranış etiketi ve skor kolonu hesaplayarak `musterietiketler` tablosunu güncelleyen toplu SQL motorudur. Önce tüm etiketleri sıfırlar (ADIM 0), ardından tek tek hesaplar.
**Kütüphaneler:** `db_engine` (PostgreSQL/SQLite abstraction), Python logging
**Bağlantılar:** [[entities/label-engine]], [[concepts/musteri-etiketleri]], [[entities/sync-worker]]

## Çalışma Akışı

```
build_labels(cursor)
  ADIM 0: musterietiketler → tüm bool = FALSE, tüm skor = 0
  ADIM 1: run_label_update() × N etiket
          Her etiket için: SQL UPDATE + rowcount + süre log
```

## Etiket Kategorileri
| Kategori | Örnekler |
|---|---|
| Zaman deseni | `sabah_alisveriscisi`, `hafta_sonu_alisveriscisi`, `aylik_duzenli_alici` |
| Sepet deseni | `buyuk_sepet`, `kucuk_sepet`, `stokcu_alici` |
| Fiyat davranışı | `indirim_avcisi`, `fiyata_duyarsiz`, `promosyon_bagimli` |
| Kategori odak | `kasap_odakli`, `manav_odakli`, `saglikli_yasam_egilimli` |
| Risk/kayıp | `winback_adayi`, `kaybedilme_riski_yuksek`, `tamamen_kaybedilmis` |
| Hane skoru | `hane_bekar_skoru`, `hane_aile_skoru`, `hane_cocuklu_skoru` |
| Churn skoru | `churn_skoru` (sayısal 0-100) |

## Bağımlılık
`feature_core_builder.py` önce çalışmış olmalıdır (feature tabloları hazır olmalı).

## Sources
- `backend/label_engine.py`

## Related
- [[concepts/musteri-etiketleri]] — etiket metodolojisi
- [[entities/sync-worker]] — sync_worker label_engine'i tetikler
- [[entities/analytics-rfm-view]] — RFM segmentleri etiketlerle birlikte kullanılır

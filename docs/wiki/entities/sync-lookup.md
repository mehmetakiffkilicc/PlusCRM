---
title: Sync Lookup
tags: [infra, etl]
source: sync_worker/sync_lookup.py
date: 2026-05-04
status: stable
---

# Sync Lookup

**Özet:** MSSQL'den marka, ürün, kategori, mağaza, kampanya ve müşteri lookup tablolarını çekip PostgreSQL'e yazar. Kendi sürücü öncelik listesiyle ODBC bağlantısı kurar.
**Kütüphaneler:** pyodbc, `decouple`, `sync_lock`
**Bağlantılar:** [[entities/sync-worker]], [[concepts/etl-pipeline]], [[sources/code-modules/2026-05-04-sync-lookup]]

## Senkronize Edilen Tablolar
markalar, urunler, kategoriler, magazalar, kampanyalar, musteriler

## SQL Abstraction
`_ph()`, `_insert_ignore()`, `_insert_replace()` → SQLite ve PostgreSQL için aynı kod.

## Issues
- Default credentials kaynak kodda gözüküyor. Railway secrets mutlaka set edilmeli.

## Sources
- `sync_worker/sync_lookup.py`

## Related
- [[entities/sync-worker]] — orkestratör
- [[concepts/etl-pipeline]] — genel ETL akışı

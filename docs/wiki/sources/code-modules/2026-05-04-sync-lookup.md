---
title: sync-lookup — Lookup Tablo Senkronizasyonu
tags: [source, infra, etl]
source: sync_worker/sync_lookup.py
date: 2026-05-04
status: stable
---

# sync-lookup — Lookup Tablo Senkronizasyonu

**Özet:** Kaynak MSSQL veritabanındaki marka, ürün, kategori, mağaza, kampanya ve müşteri lookup tablolarını pyodbc + ODBC üzerinden çeker ve PostgreSQL/SQLite hedef veritabanına yazar.
**Kütüphaneler:** `pyodbc`, `sqlite3`, `decouple`, `sync_lock`, `models`
**Bağlantılar:** [[entities/sync-lookup]], [[concepts/etl-pipeline]], [[entities/sync-worker]]

## Bağlantı Konfigürasyonu
```python
SQL_SERVER_CONFIG = {
    'server': config('SQL_SERVER', ...),  # Tailscale IP: 100.109.143.127
    'port': '14330',
    'database': 'DerinSISShow',
    'username': 'sa',
    'password': config('SQL_PASSWORD', ...)
}
```
ODBC driver öncelik sırası: Driver 18 → Driver 17 → Native Client 11 → SQL Server.

## Veritabanı Abstraction
- `_ph()`: SQLite `?` vs PostgreSQL `%s` parametresi
- `_insert_ignore()`: `OR IGNORE` (SQLite) vs `ON CONFLICT DO NOTHING` (PostgreSQL)
- `_insert_replace()`: SQLite için `OR REPLACE`, PostgreSQL için custom conflict handling

## Railway Tailscale Bridge
Railway ortamında SOCKS5 bridge (`127.0.0.1:14330`) üzerinden MSSQL bağlantısı kurulur.

## Issues
- Kimlik bilgileri `.env` üzerinden alınıyor (`decouple.config`), ancak default değerler kaynak kodda gözüküyor — Railway environment secrets zorunlu.

## Sources
- `sync_worker/sync_lookup.py`

## Related
- [[entities/sync-worker]] — orkestratör
- [[sources/code-modules/2026-05-04-run-sync]] — lookup bu dosyayı çağırır
- [[concepts/etl-pipeline]] — ETL metodolojisi

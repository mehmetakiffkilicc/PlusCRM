---
title: Sync Worker
tags: [infra, etl]
source: sync_worker/run_sync.py
date: 2026-05-04
status: stable
---

# Sync Worker

**Özet:** MSSQL kaynak veritabanından PostgreSQL hedef veritabanına lookup ve satış verilerini aktaran ETL servisidir. Railway'de bağımsız bir servis olarak çalışır; docker-compose'a dahil değildir.
**Kütüphaneler:** pyodbc, psycopg2, APScheduler, pandas, redis
**Bağlantılar:** [[entities/sync-lookup]], [[concepts/etl-pipeline]], [[decisions/karar-sync-worker-ayri]], [[sources/code-modules/2026-05-04-run-sync]]

## Bileşenler

| Dosya | Amaç |
|---|---|
| `run_sync.py` | Ana orkestratör (lookup → sales sırası) |
| `sync_lookup.py` | Marka, Ürün, Kategori, Mağaza, Kampanya, Müşteri |
| `sync_sales.py` | Aylık satış hareketleri |
| `sync_summary.py` | Özet tablo hesabı |
| `scheduler_service.py` | APScheduler periyodik tetikleme |
| `sync_lock.py` | Eşzamanlı sync engelleme |
| `tcp_bridge.py` + `start-tailscale.sh` | Tailscale SOCKS5 köprüsü |

## Railway Bağlantı Stratejisi
Tailscale VPN üzerinden SOCKS5 köprü (`127.0.0.1:14330`) ile MSSQL'e bağlanır.

## Sources
- `sync_worker/run_sync.py`
- `sync_worker/sync_lookup.py`

## Related
- [[entities/label-engine]] — sync sonrası label_engine çalışır
- [[concepts/etl-pipeline]] — veri akışı metodolojisi
- [[syntheses/etl-veri-akisi]] — uçtan uca akış

---
title: docker-compose — Servis Orkestrasyonu
tags: [source, infra]
source: docker-compose.yml
date: 2026-05-04
status: stable
---

# docker-compose — Servis Orkestrasyonu

**Özet:** Üç servisi (postgres, backend, frontend) `powerbi_network` üzerinde çalıştıran Docker Compose tanımıdır. Postgres bellek parametreleri özel olarak ayarlanmış; backend 3G bellek limiti ile sınırlandırılmış; sync_worker bu compose'da yer almaz (ayrı Railway servisi).
**Kütüphaneler:** Docker Compose v3.8, PostgreSQL 16 Alpine
**Bağlantılar:** [[entities/docker-compose]], [[entities/sync-worker]], [[issues/sorun-healthcheck-timeout]], [[issues/sorun-postgres-ram]]

## Servisler

| Servis | Image | Port | Bellek | Not |
|---|---|---|---|---|
| postgres | postgres:16-alpine | 5432 | — | shared_buffers=512MB, work_mem=32MB, max_connections=50 |
| backend | ./backend Dockerfile | 5000 | 3G limit | healthcheck'e bağımlı |
| frontend | ./frontend Dockerfile | 3000 | — | hot-reload volume mount |

## Postgres Tuning
`shared_buffers=512MB`, `work_mem=32MB`, `effective_cache_size=2GB`, `max_connections=50`, `random_page_cost=1.1` (SSD için).

## Decisions
- [[decisions/karar-gunicorn-no-preload]]: Backend başlarken Railway healthcheck timeout sorunu nedeniyle `--preload` kaldırıldı.
- [[decisions/karar-sync-worker-ayri]]: sync_worker bu compose'da yer almaz, kendi Railway servisi olarak deploy edilir.

## Issues
- [[issues/sorun-healthcheck-timeout]]: Gunicorn preload + healthcheck çakışması.
- [[issues/sorun-postgres-ram]]: Railway RAM baskısı; `work_mem` ve `shared_buffers` düşürüldü.

## Sources
- `docker-compose.yml` (tümü)

## Related
- [[entities/docker-compose]] — entity sayfası
- [[entities/sync-worker]] — ayrı deploy edilen ETL servisi

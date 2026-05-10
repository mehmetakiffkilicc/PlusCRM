---
title: Docker Compose
tags: [infra]
source: docker-compose.yml
date: 2026-05-04
status: stable
---

# Docker Compose

**Özet:** postgres, backend ve frontend servislerini `powerbi_network` üzerinde tanımlayan orkestrasyon dosyası. Postgres bellek parametreleri Railway RAM bütçesine göre ayarlanmış; sync_worker ayrı deploy edilir.
**Kütüphaneler:** Docker Compose 3.8, PostgreSQL 16 Alpine
**Bağlantılar:** [[entities/sync-worker]], [[issues/sorun-healthcheck-timeout]], [[issues/sorun-postgres-ram]], [[sources/code-modules/2026-05-04-docker-compose]]

## Servis Özeti
- **postgres**: port 5432, shared_buffers=512MB, max_connections=50
- **backend**: port 5000, mem limit 3G, healthcheck bağımlı
- **frontend**: port 3000, hot-reload

## Sources
- `docker-compose.yml`

## Related
- [[entities/sync-worker]] — bu compose'da yok
- [[decisions/karar-gunicorn-no-preload]] — backend startup optimizasyonu

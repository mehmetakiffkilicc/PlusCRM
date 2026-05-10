---
title: API Client
tags: [frontend]
source: frontend/src/api/client.ts
date: 2026-05-04
status: stable
---

# API Client

**Özet:** Tüm REST çağrılarını kapsayan tekil Axios istemcisi. In-flight GET dedupe, 120s seçici cache, 401 otomatik redirect ve trailing-slash interceptor içerir. Singleton export — `import apiClient from './api/client'`.
**Kütüphaneler:** Axios, TypeScript
**Bağlantılar:** [[entities/store-auth]], [[entities/api-ai-client]], [[decisions/karar-axios-cache-120s]], [[sources/code-modules/2026-05-04-api-client]]

## Cache Kuralı
Analytics (CLV/RFM/Churn) cache'lenmez. Portal detayları, kategori, dashboard-sqlite 120s cache'lenir.

## Endpoint Kapsam
Auth, DataSources, Dashboard, Widget, CRM Analytics, Kampanya, AI Asistan, Bildirimler, Scheduled Campaigns, AI Dashboards.

## Sources
- `frontend/src/api/client.ts`

## Related
- [[entities/api-ai-client]] — AI streaming için ayrı istemci
- [[decisions/karar-axios-cache-120s]] — cache kararı
- [[decisions/karar-jwt-localstorage]] — token storage

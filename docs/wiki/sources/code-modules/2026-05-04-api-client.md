---
title: api-client — Axios İstemcisi ve Cache Katmanı
tags: [source, frontend]
source: frontend/src/api/client.ts
date: 2026-05-04
status: stable
---

# api-client — Axios İstemcisi ve Cache Katmanı

**Özet:** Tüm REST endpoint çağrılarını kapsayan tekil monolitik Axios istemcisidir. In-flight GET dedupe, 120 saniyelik seçici response cache, 401 otomatik redirect ve trailing-slash ekleme interceptor'ları içerir.
**Kütüphaneler:** Axios, TypeScript
**Bağlantılar:** [[entities/api-client]], [[decisions/karar-axios-cache-120s]], [[decisions/karar-jwt-localstorage]]

## Cache Stratejisi (`shouldCacheGet`)

**Cache'lenmeyenler (her zaman taze)**:
- `/auth/` endpoint'leri
- `/clv`, `/rfm`, `/churn` — analytics sayfaları
- `/veri-kaynaklari/` list endpoint'i

**Cache'lenenler (120s TTL)**:
- `/urun-portali/`, `/marka-portali/`, `/customers/`
- `/analiz/`, `/urunler/`, `/kategori-raporu/`
- `/datasources/`, `/dashboard-sqlite`, `/dashboard/`

## In-flight Dedupe
Aynı GET isteği uçuştayken gelen ikinci istek beklenir — yeni HTTP isteği açılmaz.

## Interceptor'lar
1. **Request**: `Bearer <token>` header ekle; trailing slash ekle.
2. **Response**: 401 → `localStorage` temizle → `/giris`'e yönlendir.

## Token Yönetimi
`localStorage.getItem('auth_token')` ile başlatılır; `setToken`/`clearToken` metodları cache + inFlight haritalarını temizler.

## Decisions
- [[decisions/karar-axios-cache-120s]]: Analytics verisi sık değişmediğinden 2dk cache performansı artırır.
- [[decisions/karar-jwt-localstorage]]: Token localStorage'da saklanır (XSS riski mevcut — HttpOnly cookie tercih edilebilir).

## Sources
- `frontend/src/api/client.ts`

## Related
- [[entities/api-client]] — entity sayfası
- [[entities/api-ai-client]] — AI streaming için ayrı istemci
- [[entities/store-auth]] — token'ı yöneten store

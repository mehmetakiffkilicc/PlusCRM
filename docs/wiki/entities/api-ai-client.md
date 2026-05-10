---
title: API AI Client
tags: [frontend, llm]
source: frontend/src/api/aiClient.ts
date: 2026-05-04
status: stable
---

# API AI Client

**Özet:** AI sohbet isteklerini yöneten `fetch` tabanlı ayrı istemci. Server-Sent Events (SSE) streaming yanıtları işler; `ApiClient`'dan bağımsız olarak `/ai/sohbet/` endpoint'lerini çağırır.
**Kütüphaneler:** Browser Fetch API, TypeScript
**Bağlantılar:** [[entities/api-client]], [[concepts/streaming-chat]], [[entities/store-chat]]

## Neden Ayrı İstemci?
Axios streaming'i iyi desteklemez. SSE/streaming yanıtlar için `fetch` + `ReadableStream` gerekir.

## Hata Yönetimi ve Zaman Aşımı
- `streamChat` metodu 90 saniyelik timeout mekanizması içerir. Backend yanıt vermezse `AbortController` ile istek iptal edilir ve `onError` çağrılır.
- HTTP hataları (non-2xx) hemen `onError` ile bildirilir.
- `AbortError` hariç tüm hatalar `onError` üzerinden UI'a iletilir.

## Sources
- `frontend/src/api/aiClient.ts`

## Related
- [[entities/api-client]] — REST için ana istemci
- [[concepts/streaming-chat]] — SSE streaming metodolojisi
- [[entities/store-chat]] — AI mesaj geçmişi state

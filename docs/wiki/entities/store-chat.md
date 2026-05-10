---
title: Store — Chat
tags: [frontend, store, llm]
source: frontend/src/stores/chatStore.ts
date: 2026-05-04
status: draft
---

# Store — Chat

**Özet:** AI asistan sohbet oturumunu ve mesaj geçmişini yöneten Zustand store'u. `localStorage`'da `chat-storage` anahtarıyla persist edilir; `logout()` çağrısında temizlenir.
**Kütüphaneler:** Zustand 4, TypeScript
**Bağlantılar:** [[entities/store-auth]], [[entities/api-ai-client]], [[concepts/streaming-chat]]

## State
- `activeSessionId`: Aktif oturum ID'si. Yoksa mesaj gönderilmez, hata gösterilir.
- `messages`: Mesaj geçmişi (user/assistant).
- `isStreaming`: Streaming durumu. Zaman aşımı (90sn) ile korunur.
- `streamingContent`: Gelen token'lar.
- `toolCall`: Aktif araç çağrısı durumu (`start` | `running` | `result`).
- `cancelFn`: Stream iptal fonksiyonu.

## Hata Yönetimi
- Session yoksa `sendMessage` hata mesajı ekler, session oluşturulamazsa `startNewSession` hata fırlatır.
- Stream 90 saniye içinde yanıt vermezse `aiClient.streamChat` zaman aşımı hatası verir.

## Sources
- `frontend/src/stores/chatStore.ts`

## Related
- [[entities/api-ai-client]] — sohbet isteklerini gönderir
- [[entities/store-auth]] — logout'ta bu store temizlenir

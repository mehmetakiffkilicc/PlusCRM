---
title: Store — Auth
tags: [frontend, store]
source: frontend/src/stores/authStore.ts
date: 2026-05-04
status: stable
---

# Store — Auth

**Özet:** Zustand ile yönetilen minimal kimlik doğrulama state'i. JWT token ve kullanıcı bilgisini tutar; logout tüm store persist anahtarlarını temizler.
**Kütüphaneler:** Zustand 4, TypeScript
**Bağlantılar:** [[entities/api-client]], [[entities/app-router]], [[concepts/jwt-akisi]], [[sources/code-modules/2026-05-04-auth-store]]

## State
```typescript
{ user: {id, email} | null, token: string | null, isAuthenticated: boolean }
```

## `logout()` Yan Etkisi
`auth_token`, `chat-storage`, `dashboard-storage`, `notification-storage` — tüm localStorage anahtarları temizlenir.

## Başlangıç Durumu
`isAuthenticated = !!localStorage.getItem('auth_token')` — sayfa yenilemesinde oturum korunur.

## Sources
- `frontend/src/stores/authStore.ts`

## Related
- [[entities/api-client]] — Bearer token için store'dan okur
- [[concepts/jwt-akisi]] — JWT akışı uçtan uca
- [[decisions/karar-jwt-localstorage]] — token saklama yeri kararı

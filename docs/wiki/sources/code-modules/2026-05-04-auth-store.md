---
title: auth-store — JWT Kimlik Doğrulama Store
tags: [source, frontend]
source: frontend/src/stores/authStore.ts
date: 2026-05-04
status: stable
---

# auth-store — JWT Kimlik Doğrulama Store

**Özet:** Zustand ile yönetilen minimal kimlik doğrulama state'i. `user`, `token`, `isAuthenticated` alanlarını tutar; `logout()` hem auth hem de diğer store'ların localStorage anahtarlarını temizler.
**Kütüphaneler:** Zustand 4, TypeScript
**Bağlantılar:** [[entities/store-auth]], [[concepts/jwt-akisi]], [[decisions/karar-jwt-localstorage]]

## State Yapısı
```typescript
{ user: User | null, token: string | null, isAuthenticated: boolean }
```
`isAuthenticated` başlangıçta `!!localStorage.getItem('auth_token')` ile belirlenir → sayfa yenilemesinde oturum korunur.

## `logout()` Temizliği
```typescript
localStorage.removeItem('auth_token')
localStorage.removeItem('chat-storage')
localStorage.removeItem('dashboard-storage')
localStorage.removeItem('notification-storage')
```
Diğer store'ların persist key'lerini de temizler — tam oturum sıfırlama.

## Decisions
- [[decisions/karar-jwt-localstorage]]: Token localStorage'da. XSS riski açısından HttpOnly cookie değerlendirilebilir.

## Sources
- `frontend/src/stores/authStore.ts`

## Related
- [[entities/store-auth]] — entity sayfası
- [[concepts/jwt-akisi]] — JWT akışı uçtan uca
- [[entities/api-client]] — Bearer token eklemek için bu store'a bağlı

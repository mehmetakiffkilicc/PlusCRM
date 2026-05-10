---
title: App Router
tags: [frontend]
source: frontend/src/App.tsx
date: 2026-05-04
status: stable
---

# App Router

**Özet:** React Router v6 ile tüm uygulama sayfalarını yönlendiren kök bileşen. 22 sayfa lazy yüklenir; auth durumuna göre DashboardLayout altında nested route veya /giris yönlendirmesi yapılır.
**Kütüphaneler:** React Router v6, React 18 lazy/Suspense, Zustand
**Bağlantılar:** [[entities/store-auth]], [[entities/dashboard-layout]], [[sources/code-modules/2026-05-04-app-tsx]]

## Public Route'lar
`/giris`, `/kayit`

## Authenticated Route'lar (DashboardLayout içinde)
`/`, `/rfm-analizi`, `/churn-analizi`, `/clv-analizi`, `/segmentasyon`, `/kampanyalar`, `/musteri-portali`, `/kohort-analizi`, `/ai-takvim`, `/ai-paneller`, `/ai-paneller/:id`, + 10 daha

## Preload Optimizasyonu
Auth durumu bilinince ilk sayfa chunk'ı önceden yüklenir → soğuk cache'de ilk navigasyonu hızlandırır.

## Sources
- `frontend/src/App.tsx`

## Related
- [[entities/store-auth]] — `isAuthenticated` state
- [[entities/dashboard-layout]] — auth kabuk

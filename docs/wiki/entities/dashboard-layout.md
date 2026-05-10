---
title: Dashboard Layout
tags: [frontend]
source: frontend/src/layouts/DashboardLayout.tsx
date: 2026-05-04
status: stable
---

# Dashboard Layout

**Özet:** Kimlik doğrulaması gerektiren tüm sayfaları saran kabuk bileşeni. Sidebar navigasyonu ve React Router `<Outlet>` içerir; auth olmayan kullanıcılar `/giris`'e yönlendirilir.
**Kütüphaneler:** React, React Router v6, Mantine
**Bağlantılar:** [[entities/app-router]], [[entities/store-auth]], [[entities/store-ui]]

## Sources
- `frontend/src/layouts/DashboardLayout.tsx`

## Related
- [[entities/app-router]] — DashboardLayout tüm auth route'ları sarar
- [[entities/store-ui]] — sidebar açık/kapalı state

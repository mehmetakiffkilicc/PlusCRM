---
title: Dashboard Modeli
tags: [backend, domain, model]
source: backend/api/models.py
date: 2026-05-04
status: stable
---

# Dashboard Modeli

**Özet:** Kullanıcıya ait widget panellerinin konteyneri. Kullanıcı başına birden fazla panel oluşturulabilir; her panel `Widget` nesneleri içerir.
**Kütüphaneler:** Django ORM
**Bağlantılar:** [[entities/widget-modeli]], [[entities/aidashboard-modeli]], [[sources/code-modules/2026-05-04-models]]

## Alanlar

| Alan | Tip | Notlar |
|---|---|---|
| user | FK → User | CASCADE, db_index |
| name | CharField(255) | db_index |
| description | TextField | opsiyonel |
| created_at | DateTimeField | auto_now_add, db_index |
| updated_at | DateTimeField | auto_now, db_index |

## Composite İndeks
- `(user, updated_at)` — son güncellenen önce listele

## Sources
- `backend/api/models.py` satır 31-45

## Related
- [[entities/widget-modeli]] — `related_name='widgets'` ile bağlı
- [[entities/aidashboard-modeli]] — AI tarafından üretilen panel modeli (farklı)
- [[entities/page-dashboard-home]] — frontend panel listesi

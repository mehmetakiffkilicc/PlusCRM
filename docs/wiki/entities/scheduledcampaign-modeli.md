---
title: ScheduledCampaign Modeli
tags: [backend, domain, model]
source: backend/api/models.py
date: 2026-05-04
status: stable
---

# ScheduledCampaign Modeli

**Özet:** AI asistan tarafından veya kullanıcı tarafından planlanan SMS/e-posta/anlık bildirim kampanyalarını zamanlı olarak kayıt altına alır.
**Kütüphaneler:** Django ORM
**Bağlantılar:** [[entities/ainotification-modeli]], [[entities/page-ai-dashboards]], [[sources/code-modules/2026-05-04-models]]

## Alanlar

| Alan | Tip | Seçenekler |
|---|---|---|
| user | FK → User | CASCADE |
| title | CharField(255) | — |
| segment | CharField(255) | hedef segment adı |
| channel | CharField(20) | sms / email / push |
| scheduled_at | DateTimeField | db_index |
| status | CharField(20) | pending / completed / cancelled |

## Composite İndeks
- `(user, status, scheduled_at)` — takvim görünümü sorgusu

## Sources
- `backend/api/models.py` satır 148-173

## Related
- [[entities/page-ai-dashboards]] — frontend AI takvim sayfası (`/ai-takvim`)
- [[concepts/streaming-chat]] — AI asistan kampanya planlama aracı üretir

---
title: AIDashboard Modeli
tags: [backend, domain, model, llm]
source: backend/api/models.py
date: 2026-05-04
status: stable
---

# AIDashboard Modeli

**Özet:** AI asistanın konuşma sırasında ürettiği dinamik panel konfigürasyonlarını kalıcı olarak saklar. `config` JSONField panel bileşenlerini ve ayarlarını içerir.
**Kütüphaneler:** Django ORM
**Bağlantılar:** [[entities/dashboard-modeli]], [[entities/page-ai-dashboards]], [[sources/code-modules/2026-05-04-models]]

## Alanlar

| Alan | Tip | Notlar |
|---|---|---|
| user | FK → User | CASCADE |
| name | CharField(255) | — |
| config | JSONField | panel bileşenleri + ayarları |
| is_favorite | BooleanField | default=False |

## Dashboard vs AIDashboard
`Dashboard` modeli kullanıcı tarafından manuel oluşturulur; `AIDashboard` AI asistan tarafından otomatik oluşturulur ve `config` JSONField'ında serbest yapılandırma taşır.

## Sources
- `backend/api/models.py` satır 175-191

## Related
- [[entities/page-ai-dashboards]] — frontend listesi `/ai-paneller`
- [[decisions/karar-llm-dual-provider]] — AI paneller Anthropic/Gemini üretir

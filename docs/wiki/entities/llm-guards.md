---
title: LLM — Guards
tags: [backend, llm, security]
source: backend/api/analytics/llm/guards.py
date: 2026-05-04
status: draft
---

# LLM — Guards

**Özet:** AI araç çağrıları ve sohbet istekleri için güvenlik ve uygunluk filtresi. Zararlı veya kapsam dışı istekleri `tool_executor` çalışmadan önce engeller.
**Kütüphaneler:** Python stdlib
**Bağlantılar:** [[entities/llm-tool-executor]], [[entities/llm-cost-tracker]]

## Beklenen Davranış
- Yasak araç adı veya parametresi varsa → red
- Uygunsuz içerik tespiti → hata yanıtı
- Kapsam dışı istek → loglama + red

## Sources
- `backend/api/analytics/llm/guards.py`

## Related
- [[entities/llm-tool-executor]] — guards.py'den sonra çalışır
- [[concepts/tool-use-pattern]] — araç çağrısı güvenlik katmanı

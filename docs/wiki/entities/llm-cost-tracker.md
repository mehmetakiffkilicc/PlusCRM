---
title: LLM — Cost Tracker
tags: [backend, llm]
source: backend/api/analytics/llm/cost_tracker.py
date: 2026-05-04
status: draft
---

# LLM — Cost Tracker

**Özet:** Her AI araç çağrısı ve sohbet isteğinin token sayısını ve USD maliyetini hesaplayıp `AISession.total_cost` ve `AIMessage.input/output_tokens` alanlarını günceller.
**Kütüphaneler:** Python stdlib, Django ORM
**Bağlantılar:** [[entities/aisession-modeli]], [[entities/aimessage-modeli]], [[entities/llm-tool-executor]]

## Beklenen Davranış
- Model başına birim fiyat tablosu (Anthropic Claude, Gemini fiyatları)
- Her yanıtta token sayısı → maliyet → AISession.total_cost güncelleme

## Sources
- `backend/api/analytics/llm/cost_tracker.py`

## Related
- [[entities/aisession-modeli]] — `total_cost` alanı
- [[decisions/karar-llm-dual-provider]] — iki provider farklı fiyatlandırma

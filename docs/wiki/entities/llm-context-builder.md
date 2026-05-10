---
title: LLM — Context Builder
tags: [backend, llm]
source: backend/api/analytics/llm/context_builder.py
date: 2026-05-04
status: stable
---

# LLM — Context Builder

**Özet:** AI sohbet isteklerindeki prompt bağlamını 3 katmanda oluşturur: cacheable glossary, dinamik sayfa bağlamı, araç sonuçları. Prompt caching için bilinçli ayrım yapılmıştır.
**Kütüphaneler:** Python stdlib, `prompt_templates.GLOSSARY`
**Bağlantılar:** [[entities/llm-tool-executor]], [[entities/llm-prompt-templates]], [[concepts/tool-use-pattern]], [[sources/code-modules/2026-05-04-context-builder]]

## API
- `build_static_context()` → glossary string (cacheable)
- `build_dynamic_context(page_context)` → sayfa + filtreler
- `build_full_context(page_context)` → static + dynamic birleşimi

## `data_source_id` Sessiz Taşıma
`page_context['data_source_id']` değeri dinamik context metnine eklenmez; doğrudan `tool_executor.execute_tool` tarafından Smart-Injection ile kullanılır.

## Sources
- `backend/api/analytics/llm/context_builder.py`

## Related
- [[entities/llm-tool-executor]] — context'i alarak araç çalıştırır
- [[syntheses/ai-sohbet-akisi]] — bütünsel AI akışı

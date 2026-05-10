---
title: context-builder — LLM Bağlam Oluşturucu
tags: [source, backend, llm]
source: backend/api/analytics/llm/context_builder.py
date: 2026-05-04
status: stable
---

# context-builder — LLM Bağlam Oluşturucu

**Özet:** AI sohbet isteklerindeki LLM prompt bağlamını 3 katmanda inşa eder: statik glossary (prompt caching için uygun), dinamik sayfa bağlamı (aktif sayfa + filtreler), ve araç sonuçları. Bu ayrım Anthropic prompt caching'ini optimize etmek için bilinçli olarak yapılmıştır.
**Kütüphaneler:** Python standart kütüphane, `prompt_templates.GLOSSARY`
**Bağlantılar:** [[entities/llm-context-builder]], [[concepts/tool-use-pattern]], [[entities/llm-tool-executor]]

## 3 Katman Mimarisi

```
build_full_context()
  ├── build_static_context()   → GLOSSARY (segment tanımları) — CACHEABLE
  ├── build_dynamic_context()  → Aktif sayfa + filtreler + özet veri
  └── [tool sonuçları]         → execute_tool() sonrası eklenir
```

### Statik Katman
`GLOSSARY` dict'i `prompt_templates.py`'den alınır. Segment açıklamalarını içerir. Prompt caching ile her istek tekrar göndermez.

### Dinamik Katman
`page_context` dict:
```python
{
  "page": "churn_analysis",
  "data_source_id": 1,       # sessizce iletilir, metne eklenmez
  "filters": {"period": "son_6_ay"},
  "summary_data": {...}      # max 2000 karakter
}
```

## Decisions
- `data_source_id` dinamik context'e metin olarak **eklenmez** — `tool_executor` sessizce yönetir.
- `summary_data` 2000 karakterle kırpılır (token limiti kontrolü).

## Sources
- `backend/api/analytics/llm/context_builder.py`
- `backend/api/analytics/llm/prompt_templates.py` (GLOSSARY)

## Related
- [[entities/llm-context-builder]] — entity sayfası
- [[entities/llm-tool-executor]] — araç yürütme, smart injection
- [[concepts/tool-use-pattern]] — LLM araç çağrısı deseni
- [[syntheses/ai-sohbet-akisi]] — bütünsel AI akışı

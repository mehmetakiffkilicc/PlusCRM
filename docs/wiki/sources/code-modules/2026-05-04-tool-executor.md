---
title: tool-executor — LLM Araç Yürütme Motoru
tags: [source, backend, llm]
source: backend/api/analytics/llm/tool_executor.py
date: 2026-05-04
status: stable
---

# tool-executor — LLM Araç Yürütme Motoru

**Özet:** LLM'nin istediği araçları `tools.py`'deki fonksiyonlara yönlendiren ve yürüten modüldür. Akıllı parametre enjeksiyonu (Smart-Injection), 30 saniyelik timeout ve thread izolasyonu içerir.
**Kütüphaneler:** `concurrent.futures`, Python `inspect`
**Bağlantılar:** [[entities/llm-tool-executor]], [[entities/llm-context-builder]], [[concepts/tool-use-pattern]]

## `execute_tool()` İşleyişi

```
execute_tool(tool_name, parameters, user, context)
  1. Smart-Injection: data_source_id eksikse context'ten al
     → Fallback: varsayılan data_source_id = 1 (Sessiz Enjeksiyon)
  2. getattr(tools, tool_name) ile fonksiyonu bul
  3. inspect.signature ile geçerli parametreleri filtrele
  4. ThreadPoolExecutor(max_workers=1) + 30s timeout ile çalıştır
  5. Timeout/hata → JSON error response
```

## Smart-Injection (Sessiz Enjeksiyon)
`data_source_id` parametresi eksikse:
- `context` dict ise → `context.get('data_source_id')`
- `context` string ise → regex ile `"data_source_id": <n>` ara
- Bulunamazsa → `1` enjekte et (tek datasource varsayımı)

## Decisions
- `max_workers=1`: Araç başına tek thread. LLM paralel araç çağrısı yapsa da seri yürütülür.
- Varsayılan `data_source_id=1`: Üretim ortamında tek ana datasource bulunduğu varsayımı.

## Issues
- Tek datasource varsayımı (`= 1`) — birden fazla tenant/datasource senaryosunda kırılabilir.

## Sources
- `backend/api/analytics/llm/tool_executor.py`

## Related
- [[entities/llm-tool-executor]] — entity sayfası
- [[entities/llm-guards]] — araç çağrısı öncesi güvenlik katmanı
- [[concepts/tool-use-pattern]] — genel LLM araç deseni

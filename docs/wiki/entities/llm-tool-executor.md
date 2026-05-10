---
title: LLM — Tool Executor
tags: [backend, llm]
source: backend/api/analytics/llm/tool_executor.py
date: 2026-05-04
status: stable
---

# LLM — Tool Executor

**Özet:** LLM'nin istediği araç adını `tools.py`'deki fonksiyona yönlendirip, 30 saniyelik timeout ve thread izolasyonuyla yürüten modüldür. Eksik `data_source_id` parametresini context'ten otomatik enjekte eder.
**Kütüphaneler:** `concurrent.futures`, Python `inspect`
**Bağlantılar:** [[entities/llm-context-builder]], [[entities/llm-guards]], [[concepts/tool-use-pattern]], [[sources/code-modules/2026-05-04-tool-executor]]

## `execute_tool(tool_name, parameters, user, context)`

1. Smart-Injection: `data_source_id` eksikse context'ten al (fallback: `1`)
2. `getattr(tools, tool_name)` ile fonksiyon bul
3. `inspect.signature` ile geçerli parametreleri filtrele
4. `ThreadPoolExecutor(1)` + `future.result(timeout=30)` ile çalıştır
5. Timeout / hata → JSON `{status: "error", ...}`

## Issues
- Varsayılan `data_source_id=1` — çok kiracılı (multi-tenant) ortamda kırılır.

## Sources
- `backend/api/analytics/llm/tool_executor.py`

## Related
- [[entities/llm-context-builder]] — context'i üretir
- [[entities/llm-guards]] — araç çağrısı öncesi güvenlik

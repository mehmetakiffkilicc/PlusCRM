---
title: AISession Modeli
tags: [backend, domain, model, llm]
source: backend/api/models.py
date: 2026-05-04
status: stable
---

# AISession Modeli

**Özet:** Bir kullanıcının AI asistan ile başlattığı sohbet oturumunu temsil eder. Token sayısı ve maliyet oturum düzeyinde takip edilir.
**Kütüphaneler:** Django ORM
**Bağlantılar:** [[entities/aimessage-modeli]], [[entities/aiauditlog-modeli]], [[concepts/streaming-chat]], [[sources/code-modules/2026-05-04-models]]

## Alanlar

| Alan | Tip | Notlar |
|---|---|---|
| user | FK → User | CASCADE, db_index |
| title | CharField(255) | default='Yeni Sohbet' |
| model_name | CharField(100) | default='gemini-2.0-flash' |
| total_tokens | IntegerField | kümülatif |
| total_cost | DecimalField(10,6) | USD maliyet |

## ÇELİŞKİ
`model_name` varsayılanı `gemini-2.0-flash` ama `context_builder.py` ve `decisions/karar-llm-dual-provider.md` Anthropic'in de aktif kullanıldığını gösteriyor. Hangi model varsayılan olmalı belirsiz.

## Sources
- `backend/api/models.py` satır 99-107

## Related
- [[entities/aimessage-modeli]] — `related_name='messages'`
- [[decisions/karar-llm-dual-provider]] — çift provider kararı
- [[concepts/streaming-chat]] — oturum kullanım senaryosu

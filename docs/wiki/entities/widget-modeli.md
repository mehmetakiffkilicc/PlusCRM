---
title: Widget Modeli
tags: [backend, domain, model]
source: backend/api/models.py
date: 2026-05-04
status: stable
---

# Widget Modeli

**Özet:** Bir Dashboard içindeki tek bir grafik bileşenidir. Veri kaynağı, grafik tipi, eksen tanımları ve aggregasyon türü burada tanımlanır.
**Kütüphaneler:** Django ORM
**Bağlantılar:** [[entities/dashboard-modeli]], [[entities/datasource-modeli]], [[sources/code-modules/2026-05-04-models]]

## Alanlar

| Alan | Tip | Seçenekler |
|---|---|---|
| dashboard | FK → Dashboard | CASCADE, related_name='widgets' |
| data_source | FK → DataSource | CASCADE |
| type | CharField(20) | line / bar / pie / scatter / heatmap |
| title | CharField(255) | — |
| x_axis | CharField(255) | opsiyonel |
| y_axis | CharField(255) | opsiyonel |
| aggregation | CharField(20) | sum / average / count / min / max |
| filters | JSONField | default=dict |

## Sources
- `backend/api/models.py` satır 48-82

## Related
- [[entities/dashboard-modeli]] — parent
- [[entities/datasource-modeli]] — veri kaynağı FK

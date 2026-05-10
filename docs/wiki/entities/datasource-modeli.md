---
title: DataSource Modeli
tags: [backend, domain, model]
source: backend/api/models.py
date: 2026-05-04
status: stable
---

# DataSource Modeli

**Özet:** Kullanıcının yüklediği veri kaynağını temsil eden ana varlık modelidir. CSV, JSON veya doğrudan veritabanı (MSSQL) bağlantısı desteklenir; verinin kendisi `data` JSONField'ında saklanır.
**Kütüphaneler:** Django ORM, PostgreSQL JSONField
**Bağlantılar:** [[entities/dashboard-modeli]], [[entities/widget-modeli]], [[entities/serializers]], [[sources/code-modules/2026-05-04-models]]

## Alanlar

| Alan | Tip | Notlar |
|---|---|---|
| user | FK → User | CASCADE, db_index |
| name | CharField(255) | db_index |
| type | CharField(20) | csv / json / database |
| data | JSONField | default=list — satır listesi |
| column_mapping | JSONField | default=dict — sütun eşleştirme |
| connection_info | JSONField | database tipi için MSSQL config |
| uploaded_at | DateTimeField | auto_now_add, db_index |

## Composite İndeksler
- `(user, uploaded_at)` — kullanıcı veri kaynağı listesi
- `(user, type)` — tipe göre filtreleme

## Kritik Davranış
`type='database'` datasource'lar `data` alanı kullanmaz; analytics view'lar `connection_info`'yu `db_engine` ile canlı sorgu için kullanır.

## Sources
- `backend/api/models.py` satır 5-28

## Related
- [[entities/widget-modeli]] — Widget.data_source FK
- [[entities/analytics-rfm-view]] — DataSource üzerinden RFM hesaplar
- [[concepts/etl-pipeline]] — database tipi datasource → sync_worker ile beslenir

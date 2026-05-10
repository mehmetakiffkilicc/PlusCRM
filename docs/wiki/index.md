---
title: Index
tags: [meta]
date: 2026-05-04
status: stable
---

# BackendFronend Wiki — İçerik Kataloğu

> Bu dosya her INGEST sonrası otomatik güncellenir. Tüm sayfaların haritası burada.

---

## Kaynaklar (`sources/`)

### code-modules
- [[sources/code-modules/2026-05-04-models]] — Django ana veri modelleri
- [[sources/code-modules/2026-05-04-urls]] — Tüm API endpoint'leri
- [[sources/code-modules/2026-05-04-rfm-view]] — RFM segmentasyon analizi view
- [[sources/code-modules/2026-05-04-churn-view]] — Churn analizi view
- [[sources/code-modules/2026-05-04-clv-view]] — CLV (Customer Lifetime Value) view
- [[sources/code-modules/2026-05-04-segmentation-view]] — Segmentasyon view
- [[sources/code-modules/2026-05-04-context-builder]] — LLM bağlam oluşturma modülü
- [[sources/code-modules/2026-05-04-tool-executor]] — LLM araç yürütme motoru
- [[sources/code-modules/2026-05-04-label-engine]] — Müşteri etiket motoru
- [[sources/code-modules/2026-05-04-run-sync]] — ETL orkestratörü
- [[sources/code-modules/2026-05-04-sync-lookup]] — Lookup tabloları senkronizasyonu
- [[sources/code-modules/2026-05-04-app-tsx]] — React router ve uygulama iskeleti
- [[sources/code-modules/2026-05-04-api-client]] — Axios istemcisi ve cache katmanı
- [[sources/code-modules/2026-05-04-auth-store]] — JWT kimlik doğrulama store'u
- [[sources/code-modules/2026-05-04-docker-compose]] — Servis tanımları

---

## Varlıklar (`entities/`)

### Backend — Modeller
- [[entities/datasource-modeli]] — Yüklenen veri kaynağı (CSV/JSON)
- [[entities/dashboard-modeli]] — Kullanıcı paneli
- [[entities/widget-modeli]] — Panel grafik bileşeni
- [[entities/aisession-modeli]] — AI sohbet oturumu
- [[entities/aimessage-modeli]] — AI mesajı (token/maliyet takibi)
- [[entities/aiauditlog-modeli]] — AI araç çağrı audit kaydı
- [[entities/ainotification-modeli]] — Kullanıcı bildirimleri
- [[entities/scheduledcampaign-modeli]] — Zamanlanmış kampanya
- [[entities/aidashboard-modeli]] — AI üretimli panel konfigürasyonu
- [[entities/systemsetting-modeli]] — Sistem ayarları

### Backend — Analytics Views
- [[entities/analytics-rfm-view]] — RFM segmentasyon endpoint
- [[entities/analytics-churn-view]] — Churn analizi endpoint
- [[entities/analytics-clv-view]] — CLV hesaplama endpoint
- [[entities/analytics-segmentation-view]] — Segment ve geçiş matrisi
- [[entities/analytics-campaign-view]] — Kampanya önerileri
- [[entities/analytics-category-report]] — Kategori raporu
- [[entities/analytics-customer-portal]] — Müşteri 360 portal
- [[entities/analytics-product-portal]] — Ürün portalı
- [[entities/analytics-kohort-view]] — Kohort analizi
- [[entities/analytics-sprint4-view]] — Birliktelik, sadakat, enflasyon, rakip, hane

### Backend — LLM Alt-Sistemi
- [[entities/llm-context-builder]] — Bağlam oluşturma
- [[entities/llm-tool-executor]] — Araç yürütme
- [[entities/llm-guards]] — Güvenlik/uygunluk katmanı
- [[entities/llm-cost-tracker]] — Token maliyeti takibi
- [[entities/llm-session-store]] — Oturum yönetimi
- [[entities/llm-prompt-templates]] — Prompt şablonları

### Backend — Diğer
- [[entities/label-engine]] — Müşteri etiket motoru
- [[entities/auth-views]] — Register/Login/Profile endpoint'leri
- [[entities/crm-urls]] — CRM alt-endpoint'leri
- [[entities/serializers]] — DRF serializer'ları
- [[entities/django-core]] — Settings, URL router, middleware

### Frontend — Sayfalar
- [[entities/page-login]] — Giriş ekranı
- [[entities/page-dashboard-home]] — Ana özet panosu
- [[entities/page-rfm-analysis]] — RFM analizi sayfası
- [[entities/page-churn-analysis]] — Churn analizi sayfası
- [[entities/page-clv]] — CLV analizi sayfası
- [[entities/page-segmentation]] — Segmentasyon sayfası
- [[entities/page-campaigns]] — Kampanya listesi
- [[entities/page-customer-portal]] — Müşteri 360 portal sayfası
- [[entities/page-brand-report]] — Marka raporu
- [[entities/page-category-report]] — Kategori raporu
- [[entities/page-kohort]] — Kohort analizi sayfası
- [[entities/page-ai-dashboards]] — AI panel listesi

### Frontend — Store'lar
- [[entities/store-auth]] — Kimlik doğrulama durumu (JWT)
- [[entities/store-dashboard]] — Dashboard/widget durumu
- [[entities/store-chat]] — AI sohbet oturumu
- [[entities/store-notification]] — Bildirimler
- [[entities/store-ui]] — UI genel durumu

### Frontend — API & Bileşenler
- [[entities/api-client]] — Axios istemcisi (cache + dedupe)
- [[entities/api-ai-client]] — AI streaming istemcisi
- [[entities/app-router]] — React Router yapılandırması
- [[entities/dashboard-layout]] — Auth kabuk bileşeni
- [[entities/components-ai]] — AI widget kataloğu
- [[entities/components-portal]] — Portal bileşenleri

### Altyapı
- [[entities/docker-compose]] — Servis orkestrasyonu
- [[entities/sync-worker]] — ETL orkestratörü
- [[entities/sync-lookup]] — Lookup senkronizasyonu
- [[entities/sync-sales]] — Satış verisi senkronizasyonu
- [[entities/sync-scheduler]] — Periyodik tetikleme (APScheduler)
- [[entities/playwright-mcp]] — Playwright MCP E2E test altyapısı

---

## Kavramlar (`concepts/`)

- [[concepts/rfm-analizi]] — Recency/Frequency/Monetary segmentasyon
- [[concepts/churn]] — Müşteri kaybı tahmini ve analizi
- [[concepts/clv]] — Customer Lifetime Value hesabı
- [[concepts/kohort-analizi]] — Kohort tabanlı davranış analizi
- [[concepts/market-basket]] — Ürün birliktelik analizi
- [[concepts/musteri-etiketleri]] — Günlük hesaplanan davranış etiketleri
- [[concepts/etl-pipeline]] — MSSQL→Postgres veri akışı
- [[concepts/jwt-akisi]] — JWT tabanlı kimlik doğrulama akışı
- [[concepts/streaming-chat]] — Server-Sent Events ile AI yanıt akışı
- [[concepts/tool-use-pattern]] — LLM araç çağrısı deseni
- [[concepts/kpi-cache]] — SQLite tabanlı KPI önbelleği
- [[concepts/segmentasyon]] — Müşteri segmentleme yöntemleri

---

## Kararlar (`decisions/`)

- [[decisions/karar-sqlite-direct-kpi]] — KPI endpoint'leri için SQLite direct sorgu
- [[decisions/karar-jwt-localstorage]] — JWT'yi localStorage'da saklama
- [[decisions/karar-axios-cache-120s]] — 120 saniyelik GET yanıt önbelleği
- [[decisions/karar-llm-dual-provider]] — Anthropic + Gemini çift-provider stratejisi
- [[decisions/karar-sync-worker-ayri]] — sync_worker'ı ayrı Railway servisi olarak deploy
- [[decisions/karar-gunicorn-no-preload]] — Preload kaldırma (healthcheck timeout fix)

---

## Sorunlar (`issues/`)

- [[issues/sorun-healthcheck-timeout]] — Gunicorn preload + Railway healthcheck çakışması
- [[issues/sorun-collectstatic-startup]] — collectstatic'in startup'a eklenmesi ve düzeltme
- [[issues/sorun-postgres-ram]] — Postgres bellek ayarı ve optimizasyon
- [[issues/sorun-syntax-error-llm-view]] — llm_view.py SyntaxError (düzeltildi)

---

## Sentezler (`syntheses/`)

- [[syntheses/mimari-genel-bakis]] — Tüm sistem tek sayfada
- [[syntheses/analytics-istek-akisi]] — Analytics sorgu yaşam döngüsü
- [[syntheses/ai-sohbet-akisi]] — AI sohbet end-to-end akışı
- [[syntheses/etl-veri-akisi]] — ETL pipeline veri akışı
- [[syntheses/kimlik-dogrulama-akisi]] — Auth akışı uçtan uca
- [[syntheses/modul-haritasi]] — Tüm modüllerin hızlı dizini

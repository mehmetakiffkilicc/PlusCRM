# PLUS CRM — AUDIT LOG

Bu dosya, tüm test süreçlerindeki bulguları ve bug durumlarını merkezi olarak takip etmek için kullanılır.

| ID | Sayfa | Tür | Severity | Özet | Durum |
|----|-------|-----|----------|------|-------|
| BUG-DSH-001 | Dashboard | API Hatası | CRITICAL | Yıl filtresi uygulandığında 500 hatası (SQL Ambiguity) | Açık |
| BUG-DSH-002 | Dashboard | UI Hatası | MEDIUM | API 500 hatası durumunda kullanıcıya uyarı gösterilmiyor | Açık |
| BUG-DSH-003 | Dashboard | Veri Hatası | LOW | Yıllık ciro toplamları ile ana ciro kartı arasında %1.2 fark var | Açık |
| BUG-CUS-001 | Müşteri Portalı | UI Hatası | CRITICAL | Arama kutusu listeyi filtrelemiyor (API isteği atılmıyor) | Açık |
| BUG-CUS-002 | Müşteri Portalı | AI Hatası | MEDIUM | Segment AI özeti (/ai/ozet) ERR_ABORTED ile başarısız oluyor | Açık |
| BUG-AI-001 | AI Asistan | UI Hatası | LOW | Model ismi "gemini-2.5-flash" (typo), 2.0 olmalı | Açık |
| BUG-RFM-001 | RFM Analizi | Veri Hatası | MEDIUM | Şampiyonlar kartı 0 görünüyor (Veri mismatch) | Açık |

# API Güvenlik Test Raporu
**Tarih:** 2026-04-29  
**Test Yöntemi:** HTTP istekleri (browser evaluate ile)

---

## Katman 1 — Kimlik Doğrulama ✅

| Test | Beklenen | Gerçekleşen | Sonuç |
|------|---------|-------------|-------|
| Auth başlığı olmadan istek | 401 | 401 | ✅ |
| Geçersiz token (`Bearer invalid_token_xyz`) | 401 | 401 | ✅ |
| Auth olmadan SQL injection denemesi | 401 | 401 | ✅ |

---

## Katman 2 — Yetkilendirme

### BUG-SEC-001 — veri-kaynaklari ID doğrulaması yok
**Severity:** LOW (tek-tenant ortam — gerçek veri izolasyon riski düşük, ama prensipte sorunlu)  
**Tür:** Güvenlik / Yetkilendirme Eksikliği  
**Tetikleyici:** `GET /api/veri-kaynaklari/999/musteriler/` (kullanıcının yalnızca ID=1 kaynağı var)  
**Beklenen:** 403 veya 404  
**Gerçekleşen:** 200 + 199.383 müşteri verisi dönüyor  
**Ek Detay:** ID 0, 2, 3, 5, 10, 100, 999 — hepsi aynı veriyi döndürüyor. Backend `veri_kaynagi_id` parametresini filtreleme için kullanmıyor; sahibi olan kullanıcının tek kaynağına düşüyor  
**Risk Analizi:** Şu an tek-tenant (her kullanıcı sadece kendi verisini görüyor). Ancak ID doğrulaması olmadığı için çok-tenant senaryo eklenmesi halinde ciddi izolasyon açığına dönüşür  
**Düzeltme Önerisi:** View'larda `get_object_or_404(VeriKaynagi, id=pk, user=request.user)` şeklinde sahiplik kontrolü ekle

---

## Katman 3 — SQL Injection

| Test | Payload | Sonuç |
|------|---------|-------|
| Search alanı injection | `' OR '1'='1` | 200 + **boş liste** → ORM parametrized query koruyor ✅ |
| Path injection | `/1 OR 1=1/musteriler/` | 404 → URL router reddetti ✅ |
| UNION injection (query param) | `customer_id=1 UNION SELECT...` | 200 → param yok sayıldı, veri sızmadı ✅ |

**Django ORM parametrized query kullandığı için SQL injection koruması aktif.** ✅

---

## Katman 4 — Güvenlik Header'ları

`fetch()` üzerinden CORS politikası bazı headerları maskeler. Django `settings.py` incelemesine göre:

| Header | settings.py | Durum |
|--------|-------------|-------|
| `X-Content-Type-Options: nosniff` | `SECURE_CONTENT_TYPE_NOSNIFF = True` | ✅ Tanımlı |
| `X-Frame-Options: DENY` | `X_FRAME_OPTIONS = 'DENY'` | ✅ Tanımlı |
| `HSTS` | `SECURE_HSTS_SECONDS = 31536000` (prod) | ✅ Tanımlı |
| `Session Cookie Secure` | `SESSION_COOKIE_SECURE = True` (prod) | ✅ Tanımlı |
| `CSRF Cookie Secure` | `CSRF_COOKIE_SECURE = True` (prod) | ✅ Tanımlı |
| `Content-Security-Policy` | Tanımlı değil | ⚠️ Eksik |

### BUG-SEC-002 — Content-Security-Policy header yok
**Severity:** LOW  
**Tür:** Güvenlik / Header Eksikliği  
**Gerçekleşen:** `settings.py`'da CSP header tanımlı değil  
**Risk:** XSS saldırılarına karşı ek katman eksik  
**Düzeltme Önerisi:** `django-csp` paketi ekle veya `SECURE_CROSS_ORIGIN_OPENER_POLICY` ayarlarını genişlet

---

## Katman 5 — Rate Limiting ✅

`settings.py` incelemesinden:
- Anonim: 100/saat
- Kullanıcı: 1.000/saat  
- Login: 5/dakika (brute-force koruması)

---

## Özet

| Kategori | Durum |
|----------|-------|
| Auth olmadan erişim | ✅ 401 |
| Geçersiz token | ✅ 401 |
| SQL injection | ✅ ORM koruyor |
| ID doğrulaması | ⚠️ BUG-SEC-001 |
| Güvenlik header'ları | ⚠️ CSP eksik (BUG-SEC-002) |
| Rate limiting | ✅ Tanımlı |

**Bug Sayısı:** 1 LOW + 1 LOW  
**Genel Durum:** Geçti (2 low-severity güvenlik iyileştirmesi önerildi)

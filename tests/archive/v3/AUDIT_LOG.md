# MarketFlow CRM — Test Audit Logu v3
**Test Tarihi:** 2026-04-29  
**Test Metodolojisi:** Oracle-in-the-Loop + Filtre Oracle Protokolü + UI Seviyesi Doğrulama  
**Tur:** v3 — Tüm sayfalar tarandı, header filtresi her sayfada UI üzerinden test edildi

---

## Bug Matrisi (Tümü)

| ID | Sayfa | Tür | Severity | Özet | Durum |
|----|-------|-----|----------|------|-------|
| BUG-DSH-004 | Dashboard | API Crash | **CRITICAL** | Bölge filtresi uygulandığında PostgreSQL type hatasıyla çöküyor | Açık |
| BUG-DSH-001 | Dashboard | Veri / Mantık | **HIGH** | Bireysel filtresiyle `totalReceipts` = 3.629.227 (toplam 554.142'nin **6.5 katı**) | Açık |
| BUG-DSH-002 | Dashboard | Sahte Filtre | **HIGH** | `/panel/trend/` `customer_type` parametresini yok sayıyor | Açık |
| BUG-DSH-003 | Dashboard | Sahte Filtre | **HIGH** | `/panel/karsilastirma/` `customer_type` parametresini yok sayıyor | Açık |
| BUG-DSH-005 | Dashboard | Sahte Filtre | **HIGH** | `/panel/kpiler/?year=2024` yıl filtresini yok sayıyor | Açık |
| BUG-DSH-008 | Dashboard | Veri / UI | **HIGH** | Bireysel filtresiyle Yıllık Ciro/Fiş bölümleri filtresiz veri gösteriyor | Açık |
| BUG-DSH-009 | Dashboard | Veri / UI | **HIGH** | Bireysel filtresiyle Onay Durumu kartı filtresiz toplam gösteriyor (199.310) | Açık |
| BUG-AI-001 | AI Asistan | UI / Mantık | **HIGH** | "Yeni Sohbet Başlat" butonu chat penceresini açmıyor (`setChatOpened` çağrılmıyor) | Açık |
| BUG-RFM-002 | RFM | Sahte Filtre | **HIGH** | `customer_type` filtresi RFM analizine hiç uygulanmıyor (UI + API doğrulandı) | Açık |
| BUG-RFM-003 | RFM | Sahte Filtre | **HIGH** | `year` filtresi RFM analizine hiç uygulanmıyor | Açık |
| BUG-CHU-004 | Churn | Sahte Filtre | **HIGH** | `customer_type` filtresi churn analizine hiç uygulanmıyor (UI + API doğrulandı) | Açık |
| BUG-MSA-001 | Marka Sadakati | Sahte Filtre | **HIGH** | `customer_type` filtresi marka sadakati analizine uygulanmıyor | Açık |
| BUG-KOH-001 | Kohort Analizi | Sahte Filtre | **HIGH** | `customer_type` filtresi kohort analizine uygulanmıyor | Açık |
| BUG-URN-001 | Ürün Birliktelik | Sahte Filtre | **HIGH** | `customer_type` filtresi ürün birlikteliğine uygulanmıyor | Açık |
| BUG-RAK-001 | Rakip Riski | Sahte Filtre | **HIGH** | `customer_type` filtresi rakip riski analizine uygulanmıyor | Açık |
| BUG-HAN-001 | Hane Analizi | Sahte Filtre | **HIGH** | `customer_type` filtresi hane analizine uygulanmıyor | Açık |
| BUG-KAT-001 | Kategori Raporu | Sahte Filtre | **HIGH** | `customer_type` filtresi kategori raporu endpoint'lerine uygulanmıyor | Açık |
| BUG-DSH-006 | Dashboard | Sahte Filtre | MEDIUM | `/panel/segmentler/` `customer_type` parametresini yok sayıyor | Açık |
| BUG-MUS-001 | Müşteri Portalı | Veri | MEDIUM | Detaylı Analiz marka tablosunda Miktar her zaman "0 Adet" | Açık |
| BUG-MUS-003 | Müşteri Portalı | Filtre Kök Neden | MEDIUM | `approval_status` filtresi ASCII "i" ile gönderilince 0 döner; UI doğru `Onaylı` gönderiyor (API çalışıyor) | Kapatıldı |
| BUG-MUS-005 | Müşteri Portalı | UI / Filtre | MEDIUM | Sayfa ilk yüklenirken `customer_type` parametresi gönderilmiyor (Zustand→API gecikmesi) | Açık |
| BUG-CHU-001 | Churn | Veri | MEDIUM | `churnByMonth` boş — aylık trend grafiği veri göstermiyor | Açık |
| BUG-CHU-003 | Churn | Veri | MEDIUM | `atRiskCustomers` boş — risk listesine drilldown yapılamıyor | Açık |
| BUG-RFM-001 | RFM | Veri | MEDIUM | 3.983 müşteri (%2) hiçbir RFM segmentine dahil değil | Açık |
| BUG-SEG-001 | Segmentasyon | Sahte Filtre | MEDIUM | `customer_type` filtresi etiket özetine uygulanmıyor (UI + API doğrulandı) | Açık |
| BUG-ENF-001 | Enflasyon Profili | 404 | MEDIUM | `/enflasyon-profili` sayfası 404 — sidebar'da görünüyor ama implement edilmemiş | Açık |
| BUG-URN-002 | Ürün Analizi | 404 | MEDIUM | `/urun-analizi` sayfası 404 — implement edilmemiş | Açık |
| BUG-MUS-002 | Müşteri Portalı | UI | LOW | Ürün miktarları floating point hatalı: `720.7289999999999 ADET` | Açık |
| BUG-CHU-002 | Churn | Veri | LOW | `riskFactors` boş — risk faktörü analizi gösterilemiyor | Açık |
| BUG-MUS-004 | Müşteri Portalı | Veri Bütünlüğü | LOW | 3.983 müşterinin tipi tanımsız — filtrelerden düşüyor | Açık |
| BUG-MSA-002 | Marka Sadakati | UI / Filtre | LOW | Sayfa yüklemede header filtresi iletilmiyor (parametresiz API çağrısı) | Açık |
| BUG-AKL-001 | Akıllı Sorgulama | 404 | LOW | `/akilli-sorgulama` sayfası 404 — implement edilmemiş | Açık |
| BUG-SEC-001 | API Güvenlik | Güvenlik | LOW | `veri-kaynaklari` ID doğrulaması yok — her ID aynı veriyi döndürüyor | Açık |
| BUG-SEC-002 | API Güvenlik | Güvenlik | LOW | Content-Security-Policy header tanımlı değil | Açık |

---

## Severity Özeti

| Severity | Sayı |
|----------|------|
| CRITICAL | 1 |
| HIGH | 16 |
| MEDIUM | 10 |
| LOW | 7 |
| **TOPLAM** | **34** |

---

## Sahte Filtre Haritası (Güncel — v3)

Filtre parametresi gönderilip SQL'e uygulanmayan endpoint'ler:

| Endpoint | Sahte Filtre Parametreleri | Bug |
|----------|---------------------------|-----|
| `GET /panel/kpiler/` | `year`, `region` (crash) | DSH-005, DSH-004 |
| `GET /panel/trend/` | `customer_type`, `region`, `approval_status` | DSH-002 |
| `GET /panel/karsilastirma/` | `customer_type`, `region`, `approval_status` | DSH-003 |
| `GET /panel/segmentler/` | `customer_type`, `region`, `approval_status` | DSH-006 |
| `GET /veri-kaynaklari/1/rfm-analizi/` | `customer_type`, `region`, `approval_status`, `year` | RFM-002, RFM-003 |
| `GET /veri-kaynaklari/1/churn-analizi/` | `customer_type`, `region`, `approval_status` | CHU-004 |
| `GET /veri-kaynaklari/1/musteri-etiket-ozeti/` | `customer_type`, `region`, `approval_status` | SEG-001 |
| `GET /veri-kaynaklari/1/marka-sadakati/` | `customer_type`, `region`, `approval_status` | MSA-001 |
| `GET /veri-kaynaklari/1/kohort-analizi/` | `customer_type`, `region`, `approval_status` | KOH-001 |
| `GET /veri-kaynaklari/1/urun-birliktelik/` | `customer_type`, `region`, `approval_status` | URN-001 |
| `GET /veri-kaynaklari/1/rakip-riski/` | `customer_type`, `region`, `approval_status` | RAK-001 |
| `GET /veri-kaynaklari/1/hane-analizi/` | `customer_type`, `region`, `approval_status` | HAN-001 |
| `GET /veri-kaynaklari/1/kategori-raporu/agac/` | `customer_type`, `region`, `approval_status` | KAT-001 |
| `GET /veri-kaynaklari/1/kategori-terk-by-kategori/` | `customer_type`, `region`, `approval_status` | KAT-001 |

**Çalışan filtreler:**
- `GET /veri-kaynaklari/1/musteriler/` → `customer_type` ✅
- `GET /veri-kaynaklari/1/churn-analizi/` → `year` ✅
- `GET /veri-kaynaklari/1/clv-analizi/` → `customer_type` ✅
- `GET /veri-kaynaklari/1/yeni-musteriler/` → `customer_type` ✅
- `GET /veri-kaynaklari/1/markalar/` → `customer_type`, `approval_status` ✅
- `GET /panel/kpiler/` → `customer_type` (ciro/müşteri doğru, sadece fiş patlıyor) ✅/⚠️

---

## UI Seviyesi Filtre Doğrulaması (v3 — YENİ)

Header filtresi "Bireysel" seçilip network isteği yakalandığında:

| Sayfa | API Parametresi | UI→API İletimi |
|-------|----------------|----------------|
| Dashboard | `customer_type=Bireysel` gönderiliyor | ✅ |
| RFM Analizi | `customer_type` YOK (parametresiz) | ❌ BUG |
| Churn Analizi | `customer_type` YOK (parametresiz) | ❌ BUG |
| Segmentasyon | `customer_type` YOK (parametresiz) | ❌ BUG |
| Müşteri Portalı | İlk yüklemede `customer_type` YOK | ❌ BUG-MUS-005 |
| CLV Analizi | `customer_type=Bireysel` gönderiliyor | ✅ |
| Yeni Müşteriler | `customer_type=Bireysel` gönderiliyor | ✅ |
| Marka Raporu | `customer_type=Bireysel` gönderiliyor | ✅ |
| Marka Sadakati | `customer_type` YOK (parametresiz) | ❌ BUG-MSA-002 |
| Kohort Analizi | `customer_type` YOK (parametresiz) | ❌ BUG |
| Hane Analizi | `customer_type` YOK (parametresiz) | ❌ BUG |

---

## Sayfa Bazlı Sonuçlar v3

| Sayfa | URL | Durum | Yeni Bug |
|-------|-----|-------|----------|
| Dashboard | `/` | 🔴 1 CRITICAL + 6 HIGH + 1 MED | DSH-008, DSH-009 |
| Müşteri Portalı | `/musteri-portali` | ⚠️ 2 MED + 2 LOW | MUS-005 |
| Kampanya Önerileri | `/kampanya-onerileri` | ✅ Geçti | — |
| AI Takvim | `/ai-takvim` | ✅ Geçti | — |
| AI Asistan | `/ai-asistan` | ⚠️ 1 HIGH | — |
| RFM Analizi | `/rfm-analizi` | 🔴 2 HIGH + 1 MED | — |
| Churn Analizi | `/churn-analizi` | ⚠️ 1 HIGH + 2 MED | — |
| Segmentasyon | `/segmentasyon` | ⚠️ 1 MED | — |
| CLV Analizi | `/clv-analizi` | ✅ Geçti | — |
| Yeni Müşteriler | `/yeni-musteriler` | ✅ Geçti | — |
| Marka Sadakati | `/marka-sadakati` | 🔴 1 HIGH + 1 MED | MSA-001, MSA-002 |
| Kohort Analizi | `/kohort-analizi` | 🔴 1 HIGH | KOH-001 |
| Ürün Birliktelik | `/urun-birliktelik` | 🔴 1 HIGH | URN-001 |
| Enflasyon Profili | `/enflasyon-profili` | ❌ 404 | ENF-001 |
| Rakip Riski | `/rakip-riski` | 🔴 1 HIGH | RAK-001 |
| Hane Analizi | `/hane-analizi` | 🔴 1 HIGH | HAN-001 |
| Kategori Raporu | `/kategori-raporu` | 🔴 1 HIGH | KAT-001 |
| Marka Raporu | `/marka-raporu` | ✅ Geçti | — |
| Ürün Analizi | `/urun-analizi` | ❌ 404 | URN-002 |
| Akıllı Sorgulama | `/akilli-sorgulama` | ❌ 404 | AKL-001 |
| API Güvenlik | — | ⚠️ 2 LOW | — |

---

## Öncelikli Düzeltme Sırası (v3)

### 1. BUG-DSH-004 — CRITICAL — Bölge Filtresi Backend Crash
**Etki:** Bölge filtresi uygulandığında sistem çöküyor  
**Kök Neden:** `kpiler` view'ında `kayit_magazasi` TEXT alanı INTEGER ile karşılaştırılıyor  
**Düzeltme:** `CAST(kayit_magazasi AS INTEGER)` veya tip uyumu

### 2. BUG-DSH-001 — HIGH — Bireysel Fiş Patlaması
**Kök Neden:** `COUNT(DISTINCT fis_no)` yerine satır sayısı kullanılıyor  
**Düzeltme:** `COUNT(DISTINCT fis_no)` kullan

### 3. Toplu Sahte Filtre Düzeltmesi — HIGH (13 endpoint)
**Etkilenen dosyalar:**
- `dashboard_view.py` → trend, karsilastirma, kpiler (year), segmentler
- `rfm_view.py` → rfm-analizi
- `churn_view.py` → churn-analizi
- `segmentation_view.py` → musteri-etiket-ozeti
- `marka_sadakat_view.py` → marka-sadakati
- `kohort_view.py` → kohort-analizi
- `urun_birliktelik_view.py` → urun-birliktelik
- `rakip_riski_view.py` → rakip-riski
- `hane_analizi_view.py` → hane-analizi
- `kategori_raporu_view.py` → kategori-raporu/agac, kategori-terk-by-kategori

### 4. UI→API Filtre İletimi — MEDIUM
**Etkilenen sayfalar:** RFM, Churn, Segmentasyon, Marka Sadakati, Kohort, Hane
**Kök Neden:** Frontend useEffect ya store bağımlılığı eksik, ya da filtre store'u bu sayfalara bağlanmamış

### 5. 404 Sayfalar — MEDIUM
**Enflasyon Profili, Ürün Analizi, Akıllı Sorgulama** — implement edilmemiş

### 6. BUG-AI-001 — HIGH — Yeni Sohbet Açılmıyor
**Düzeltme:** `AIAssistant.tsx:76` onClick'e `useUIStore.getState().setChatOpened(true)` ekle

### 7. Dashboard UI Tutarsızlıkları — HIGH
**DSH-008:** Yıllık Ciro/Fiş bölümleri filtresiz veri gösteriyor (trend/karsilastirma endpoint'i sahte filtre yüzünden)  
**DSH-009:** Onay Durumu kartı filtresiz toplam gösteriyor (199.310 vs filtreli 140.869)

---

## Doğrulanan İşlevler (Geçen)

- ✅ Tüm sayfa yüklemeleri başarılı (404 olanlar hariç)
- ✅ Kampanya → AI Takvim akışı uçtan uca çalışıyor
- ✅ AI Sohbet SSE streaming, tool use çalışıyor
- ✅ Auth koruması (401), SQL injection direnci (ORM)
- ✅ Müşteri listesi `customer_type` filtresi doğru çalışıyor
- ✅ Churn `year` filtresi çalışıyor
- ✅ Sayfalama + filtre değişimi → page=1 reset
- ✅ CLV Analizi tüm filtreler çalışıyor
- ✅ Yeni Müşteriler `customer_type` filtresi çalışıyor
- ✅ Marka Raporu `customer_type` + `approval_status` filtreleri çalışıyor
- ✅ `approval_status=Onaylı` (doğru UTF-8 encoding) API'de çalışıyor → 140.869 müşteri

---

**CRITICAL Bug Sayısı: 1**  
**HIGH Bug Sayısı: 16**  
**Toplam Bug: 34**  
**Genel Durum: ❌ Filtre sistemi büyük çoğunlukla sahte — 14 endpoint'te sahte filtre, 3 sayfa 404**


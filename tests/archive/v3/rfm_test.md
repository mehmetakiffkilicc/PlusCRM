# RFM Analizi Test Raporu v2 (Filtre Odaklı)
**Tarih:** 2026-04-29  
**URL:** https://show.xpluscrm.com/rfm-analizi

---

## Katman 1 — Erişim & Yükleme ✅
- [x] Sayfa yüklendi
- [x] `/api/veri-kaynaklari/1/rfm-analizi/` → 200
- [x] 11 segment görünüyor

---

## Katman 2 — Veri Doğruluğu ⚠️
- API `totalCustomers`: 199.383
- Segment toplamı: 195.400
- **BUG-RFM-001: 3.983 müşteri segmentsiz** (önceki)

---

## Katman 4 — FİLTRE TESTLERİ (Oracle Protokolü)

### TEST RFM-F01: Müşteri Tipi filtresi — Sahte Filtre Tespiti

```
Filtresiz  → segment toplamı: 195.400, totalCustomers: 199.383
Bireysel   → segment toplamı: 195.400, totalCustomers: 199.383
Kurumsal   → segment toplamı: 195.400, totalCustomers: 199.383
sahte_filtre_Bireysel = TRUE
sahte_filtre_Kurumsal = TRUE
```

**→ BUG-RFM-002 (YENİ): `customer_type` filtresi RFM analizine hiç uygulanmıyor**

---

### TEST RFM-F02: Yıl filtresi — Sahte Filtre Tespiti

```
Filtresiz  → segment toplamı: 195.400, totalCustomers: 199.383
Yıl 2024   → segment toplamı: 195.400, totalCustomers: 199.383
sahte_filtre_yil = TRUE
```

**→ BUG-RFM-003 (YENİ): `year` filtresi de RFM analizine uygulanmıyor**

---

## Bug Listesi (Bu Sayfa)

### BUG-RFM-001 — 3.983 müşteri segmentsiz (ÖNCEKİ)
**Severity:** MEDIUM  
**Kanıt:** totalCustomers(199.383) - segment_toplamı(195.400) = 3.983

### BUG-RFM-002 — customer_type filtresi sahte (YENİ)
**Severity:** HIGH  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /veri-kaynaklari/1/rfm-analizi/?customer_type=Bireysel`  
**Beklenen:** Yalnızca bireysel müşterilerin RFM segmentleri  
**Gerçekleşen:** Tüm müşterilerin segmentleri (filtresiz ile aynı)  
**Kanıt:** sahte_filtre = TRUE — tüm segment sayıları birebir aynı  
**Düzeltme Önerisi:** `rfm_view.py` → `get_rfm_analysis()` fonksiyonunda `customer_type` parametresi alınıp SQL WHERE'e eklenmeli

### BUG-RFM-003 — year filtresi sahte (YENİ)
**Severity:** HIGH  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /veri-kaynaklari/1/rfm-analizi/?year=2024`  
**Beklenen:** 2024 alışverişlerine göre hesaplanmış RFM segmentleri  
**Gerçekleşen:** Tüm zamanların segmentleri (filtresiz ile aynı)  
**Kanıt:** sahte_filtre = TRUE  
**Düzeltme Önerisi:** `rfm_view.py` → tarih filtresi satış sorgusuna uygulanmıyor

---

## Özet

| Kategori | Durum |
|----------|-------|
| Yükleme | ✅ OK |
| Filtresiz veri | ✅ OK |
| customer_type filtresi | ❌ BUG-RFM-002 (Sahte) |
| year filtresi | ❌ BUG-RFM-003 (Sahte) |
| Segmentsiz müşteri | ⚠️ BUG-RFM-001 |

**Bug Sayısı:** 2 HIGH + 1 MEDIUM  
**Genel Durum:** ❌ Tüm filtreler sahte

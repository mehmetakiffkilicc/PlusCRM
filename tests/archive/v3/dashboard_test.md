# Dashboard Test Raporu v2 (Filtre Odaklı)
**Tarih:** 2026-04-29  
**Test URL:** https://show.MarketFlow.com/  
**Test Hesabı:** makif4596@gmail.com

---

## Katman 1 — Erişim & Yükleme ✅
- [x] Sayfa 3 saniye içinde yükleniyor
- [x] Console'da 0 JS error (hata yok)
- [x] Tüm API istekleri 200 dönüyor
- [x] Spinner → veri geçişi düzgün

---

## Katman 2 — Veri Doğruluğu ✅

| KPI | Ekranda | API'den | Eşleşme |
|-----|---------|---------|---------|
| Toplam Ciro | ₺441.611.381 | ₺441.611.381 | ✅ |
| Toplam Fiş | 554.142 | 554.142 | ✅ |
| Toplam Kayıtlı Müşteri | 199.310 | 199.310 | ✅ |
| Churn Oranı | %46.5 | %46.5 | ✅ |

---

## Katman 4 — FİLTRE TESTLERİ (Oracle Protokolü)

### TEST DSH-F01: Bireysel filtresi → KPI

| Değer | Filtresiz | Bireysel | Kurumsal | Beklenen |
|-------|-----------|----------|----------|---------|
| Ciro | ₺441.611.381 | ₺398.894.795 | ₺44.820.864 | Bireysel < Toplam ✅ |
| Fiş | 554.142 | **3.629.227** | 135.243 | Bireysel < Toplam ❌ |
| Müşteri | 199.310 | 194.504 | 896 | Bireysel < Toplam ✅ |

**→ BUG-DSH-001 (önceden bilinen): Bireysel fiş sayısı 6.5x şişiyor**

**Yeni Bulgu — Müşteri tipi tutarsızlığı:**
- Bireysel: 194.504 + Kurumsal: 896 = **195.400**
- Toplam: **199.383** (Müşteri Portalı API)
- **Fark: 3.983 müşterinin tipi tanımsız** — bu müşteriler filtreden düşüyor

---

### TEST DSH-F02: Trend grafiği — Sahte Filtre Tespiti

```
Filtresiz  API: salesByMonth[0] = { month: "2024-01", sales: 2.350.087 }
Bireysel   API: salesByMonth[0] = { month: "2024-01", sales: 2.350.087 }
sahte_filtre = TRUE
```

**→ BUG-DSH-002 (YENİ): `/panel/trend/` endpoint'i `customer_type` parametresini yok sayıyor**

---

### TEST DSH-F03: Karşılaştırma grafiği — Sahte Filtre Tespiti

```
Filtresiz  API: 2024 Ocak ciro = 2.350.087
Bireysel   API: 2024 Ocak ciro = 2.350.087
sahte_filtre = TRUE
```

**→ BUG-DSH-003 (YENİ): `/panel/karsilastirma/` endpoint'i `customer_type` parametresini yok sayıyor**

---

### TEST DSH-F04: Bölge filtresi → CRASH

```
GET /panel/kpiler/?region=Ankara
Response: {"error": "operator does not exist: text = integer\nLINE 1: ... cnt FROM musteriler WHERE 1=1 AND kayit_magazasi IN (SELECT..."}
```

**→ BUG-DSH-004 (YENİ — CRITICAL): Bölge filtresi uygulandığında backend PostgreSQL hatası ile çöküyor**

---

### TEST DSH-F05: Yıl 2024 filtresi → KPI Sahte Filtre

```
Filtresiz API: totalRevenue = 441.611.381, totalReceipts = 554.142
Yıl 2024  API: totalRevenue = 441.611.381, totalReceipts = 554.142
sahte_filtre = TRUE
```

**→ BUG-DSH-005 (YENİ): `/panel/kpiler/?year=2024` yıl filtresini yok sayıyor — tüm yılları döndürüyor**

---

### TEST DSH-F06: Segment dağılımı — Sahte Filtre

```
Filtresiz: Şampiyonlar: 268, Potansiyel Şampiyonlar: 5.736...
Bireysel:  Şampiyonlar: 268, Potansiyel Şampiyonlar: 5.736...
sahte_filtre = TRUE
```

**→ BUG-DSH-006 (YENİ): `/panel/segmentler/` endpoint'i `customer_type` parametresini yok sayıyor**

---

### TEST DSH-F07: Filtre sıfırlama

- [x] UI'da filtre kaldırılınca parametresiz API isteği gönderiliyor ✅
- [x] KPI'lar orijinal değere dönüyor ✅

---

## Bug Listesi (Bu Sayfa)

### BUG-DSH-001 — Bireysel filtresiyle fiş patlaması (ÖNCEKİ)
**Severity:** HIGH  
**Tür:** Veri Hatası / Mantık Hatası  
**Tetikleyici:** `GET /panel/kpiler/?customer_type=Bireysel`  
**Beklenen:** totalReceipts < 554.142  
**Gerçekleşen:** totalReceipts = 3.629.227 (6.5x şişiyor)  
**Kanıt:** Filtresiz: 554.142 → Bireysel: 3.629.227  
**Düzeltme Önerisi:** `kpiler` view'ında satış satırları değil `COUNT(DISTINCT fis_no)` kullan

### BUG-DSH-002 — Trend grafiği customer_type filtresi yok sayılıyor (YENİ)
**Severity:** HIGH  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /panel/trend/?customer_type=Bireysel`  
**Beklenen:** Yalnızca bireysel müşteri satışları  
**Gerçekleşen:** Tüm müşteri satışları (filtresiz ile aynı)  
**Kanıt:** sahte_filtre = TRUE, her iki response byte-by-byte aynı  
**Düzeltme Önerisi:** `dashboard_view.py` → `get_dashboard_trend()` fonksiyonuna `customer_type` WHERE koşulu ekle

### BUG-DSH-003 — Karşılaştırma grafiği customer_type filtresi yok sayılıyor (YENİ)
**Severity:** HIGH  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /panel/karsilastirma/?customer_type=Bireysel`  
**Beklenen:** Yalnızca bireysel müşteri 3 yıllık karşılaştırması  
**Gerçekleşen:** Tüm müşteri verisi (filtresiz ile aynı)  
**Kanıt:** sahte_filtre = TRUE  
**Düzeltme Önerisi:** `get_dashboard_comparison()` fonksiyonuna filtre parametreleri ekle; hardcoded tarih kaldırılmalı

### BUG-DSH-004 — Bölge filtresi backend crash (YENİ — CRITICAL)
**Severity:** CRITICAL  
**Tür:** API Hatası / PostgreSQL Hatası  
**Tetikleyici:** `GET /panel/kpiler/?region=Ankara`  
**Beklenen:** Ankara mağazalarına ait KPI  
**Gerçekleşen:** `{"error": "operator does not exist: text = integer ... kayit_magazasi IN (SELECT..."}`  
**Kanıt:** HTTP 500 benzeri hata response (JSON error body)  
**Düzeltme Önerisi:** `kpiler` view'ında region/mağaza JOIN sorgusunda tip uyuşmazlığı var — `kayit_magazasi` TEXT, JOIN kolonları INTEGER — `CAST` ekle

### BUG-DSH-005 — KPI yıl filtresi yok sayılıyor (YENİ)
**Severity:** HIGH  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /panel/kpiler/?year=2024`  
**Beklenen:** Yalnızca 2024 yılı KPI'ları (ciro < 441M)  
**Gerçekleşen:** totalRevenue = 441.611.381 (tüm yıllar — filtresiz ile aynı)  
**Kanıt:** sahte_filtre = TRUE  
**Düzeltme Önerisi:** `kpiler` view'ında `year` parametresi SQL `WHERE YEAR(tarih) = ?` olarak uygulanmıyor

### BUG-DSH-006 — Segment dağılımı customer_type filtresi yok sayılıyor (YENİ)
**Severity:** MEDIUM  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /panel/segmentler/?customer_type=Bireysel`  
**Beklenen:** Bireysel müşterilerin segment dağılımı  
**Gerçekleşen:** Tüm müşterilerin segment dağılımı  
**Kanıt:** sahte_filtre = TRUE  
**Düzeltme Önerisi:** `get_dashboard_segments()` fonksiyonuna `customer_type` filtresi ekle

---

## Özet

| Kategori | Durum |
|----------|-------|
| Yükleme | ✅ OK |
| KPI Doğruluğu (filtresiz) | ✅ OK |
| Bireysel filtresi → KPI ciro/müşteri | ✅ Azalıyor |
| Bireysel filtresi → KPI fiş | ❌ BUG-DSH-001 |
| Trend filtresi | ❌ BUG-DSH-002 |
| Karşılaştırma filtresi | ❌ BUG-DSH-003 |
| Bölge filtresi | 🔴 BUG-DSH-004 (CRASH) |
| Yıl filtresi → KPI | ❌ BUG-DSH-005 |
| Segment filtresi | ❌ BUG-DSH-006 |
| Filtre sıfırlama | ✅ OK |

**Bug Sayısı:** 1 CRITICAL + 3 HIGH + 1 MEDIUM + 1 HIGH (önceki) = **1 CRITICAL + 4 HIGH + 1 MEDIUM**  
**Genel Durum:** ❌ Kritik sorunlar var


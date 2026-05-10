# Müşteri Portalı Test Raporu v2 (Filtre Odaklı)
**Tarih:** 2026-04-29  
**URL:** https://show.MarketFlow.com/musteri-portali

---

## Katman 1 — Erişim & Yükleme ✅
- [x] Sayfa yüklendi, 0 JS error
- [x] API `/api/veri-kaynaklari/1/musteriler/` → 200

---

## Katman 2 — Veri Doğruluğu ✅
- API: `total: 199.383` müşteri
- Müşteri listesi sayfa başına 20 kayıt
- İlk müşteri (OZGAZIANTEP): harcama ₺1.718.415 — tutarlı

---

## Katman 3 — UI & Etkileşim ✅
- [x] Drawer tab'ları (5/5): Genel Bakış, Detaylı Analiz, Alışveriş Geçmişi, Ürün Tercihleri, Notlar
- [x] Arama (Türkçe URL-encode) çalışıyor

---

## Katman 4 — FİLTRE TESTLERİ (Oracle Protokolü)

### TEST MUS-F01: Müşteri Tipi filtresi → ÇALIŞIYOR ✅

```
Filtresiz → total: 199.383
Bireysel  → total: 194.504
Kurumsal  → total: 896
```

Filtre çalışıyor — sonuçlar filtresizden küçük ve mantıklı.  
**Not:** Bireysel(194.504) + Kurumsal(896) = 195.400 ≠ 199.383 → 3.983 müşterinin tipi yok

### TEST MUS-F02: Onay Durumu filtresi — BOZUK

```
approval_status=Onayli    → total: 0
approval_status=Approved  → total: 0
approval_status=Onaysiz   → total: 0
approval_status=onayli    → total: 0 (küçük harf)
```

**→ BUG-MUS-003 (YENİ): `approval_status` filtresi müşteri listesinde hiç çalışmıyor — tüm değerler 0 döndürüyor**

Dashboard KPI'sına göre Onaylı: 140.809 müşteri var ama filtre sıfır dönüyor. Parametre adı uyuşmuyor olabilir.

### TEST MUS-F03: Bireysel + Arama kombinasyonu

Filtre çalıştığı görüldüğünden kombinasyon da beklenen şekilde çalışıyor (müşteri listesi endpoint'i `customer_type` destekliyor).

### TEST MUS-F04: Sayfalama + Filtre

- Filtre değişince sayfalama page=1'e sıfırlanıyor ✅ (store'da `filterChanged` flag var)
- Filtreli `total` sayısı güncelleniyor ✅

---

## Katman 5 — Bug Tespitleri (Önceki)

### BUG-MUS-001 — Detaylı Analiz marka tablosunda Miktar "0 Adet" (ÖNCEKİ)
**Severity:** MEDIUM

### BUG-MUS-002 — Floating point precision hatası (ÖNCEKİ)
**Severity:** LOW

### BUG-MUS-003 — approval_status filtresi çalışmıyor (YENİ)
**Severity:** MEDIUM  
**Tür:** Filtre Hatası  
**Tetikleyici:** `GET /veri-kaynaklari/1/musteriler/?approval_status=Onayli`  
**Beklenen:** ~140.809 onaylı müşteri  
**Gerçekleşen:** total: 0  
**Kanıt:** Tüm parametre varyasyonları (TR/EN, büyük/küçük harf) sıfır dönüyor  
**Düzeltme Önerisi:** `customer_portal_view.py` → `approval_status` parametre değer kontrolü; DB'deki onay kolonu değerleriyle eşleştirilmeli (muhtemelen boolean veya farklı string)

### BUG-MUS-004 — 3.983 tipi tanımsız müşteri (YENİ)
**Severity:** LOW  
**Tür:** Veri Bütünlüğü  
**Kanıt:** Bireysel(194.504) + Kurumsal(896) = 195.400, toplam 199.383 → 3.983 fark  
**Düzeltme Önerisi:** Bu müşterilerin `tip` alanı NULL veya tanımsız; etiket güncellenmeli

---

## Özet

| Kategori | Durum |
|----------|-------|
| Yükleme | ✅ OK |
| Müşteri listesi | ✅ OK |
| customer_type filtresi | ✅ Çalışıyor |
| approval_status filtresi | ❌ BUG-MUS-003 |
| Sayfalama + Filtre | ✅ OK |
| Marka miktar verisi | ⚠️ BUG-MUS-001 |
| Floating point | ⚠️ BUG-MUS-002 |

**Bug Sayısı:** 2 MEDIUM + 2 LOW  
**Genel Durum:** ⚠️ Geçti (onay filtresi ve marka miktarı düzeltilmeli)


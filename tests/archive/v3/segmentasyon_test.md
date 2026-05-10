# Segmentasyon Test Raporu v2 (Filtre Odaklı)
**Tarih:** 2026-04-29  
**URL:** https://show.MarketFlow.com/segmentasyon

---

## Katman 1 — Erişim & Yükleme ✅
- [x] Sayfa yüklendi
- [x] `/api/veri-kaynaklari/1/musteri-etiket-ozeti/` → 200

---

## Katman 2 — Veri Doğruluğu ✅
- `toplam_musteri`: 182.929 (aktif etiket sahibi)
- 9 kategori, çok sayıda etiket yüklüyor

---

## Katman 4 — FİLTRE TESTLERİ (Oracle Protokolü)

### TEST SEG-F01: Müşteri Tipi filtresi — Sahte Filtre Tespiti

```
Filtresiz → sabah_alisveriscisi: 3.655
Bireysel  → sabah_alisveriscisi: 3.655
sahte_filtre = TRUE
```

**→ BUG-SEG-001 (YENİ): `customer_type` filtresi segmentasyon etiket özetine hiç uygulanmıyor**

---

### TEST SEG-F02: Onay Durumu filtresi — Sahte Filtre Tespiti

`approval_status` parametresi de yok sayılıyor (endpoint parametre almıyor).

---

## Bug Listesi (Bu Sayfa)

### BUG-SEG-001 — customer_type filtresi sahte (YENİ)
**Severity:** MEDIUM  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /veri-kaynaklari/1/musteri-etiket-ozeti/?customer_type=Bireysel`  
**Beklenen:** Yalnızca bireysel müşterilerin davranış etiket dağılımı  
**Gerçekleşen:** Tüm müşterilerin etiketleri (filtresiz ile aynı)  
**Kanıt:** sahte_filtre = TRUE  
**Düzeltme Önerisi:** `segmentation_view.py` → `customer_type` parametresini al ve müşteri WHERE koşuluna ekle

---

## Özet

| Kategori | Durum |
|----------|-------|
| Yükleme | ✅ OK |
| Filtresiz veri | ✅ OK |
| customer_type filtresi | ❌ BUG-SEG-001 (Sahte) |

**Bug Sayısı:** 1 MEDIUM  
**Genel Durum:** ⚠️ Filtreler sahte


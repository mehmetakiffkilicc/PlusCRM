# Raporlar Sayfaları Test Raporu
**Tarih:** 2026-04-29  
**URL'ler:** /urun-analizi, /kategori-raporu, /marka-raporu

---

## Ürün Analizi (/urun-analizi)

### Katman 1 — Erişim ❌
- Sayfa 404 veriyor — sidebar'da görünüyor ama implement edilmemiş
- API çağrısı yok

**→ BUG-URN-002 (YENİ — MEDIUM): `/urun-analizi` sayfası 404**

---

## Kategori Raporu (/kategori-raporu)

### Katman 1 — Erişim ✅
- `/api/veri-kaynaklari/1/kategori-raporu/agac/` → 200
- `/api/veri-kaynaklari/1/kategori-terk-by-kategori/` → 200

### Filtre Testi — Sahte Filtre

```
Filtresiz agac[0]: "Et & Balık & Kümes Hayvanları", revenue: 92.859.500
Bireysel  agac[0]: "Et & Balık & Kümes Hayvanları", revenue: 92.859.500 (birebir aynı)
sahte_filtre_agac = TRUE
sahte_filtre_terk = TRUE
```

**→ BUG-KAT-001 (YENİ — HIGH): `customer_type` filtresi kategori raporu endpoint'lerine uygulanmıyor**  
**Etkilenen:** `kategori-raporu/agac/` ve `kategori-terk-by-kategori/`  
**Düzeltme:** `kategori_raporu_view.py` → her iki sorguya `customer_type` WHERE koşulu ekle

---

## Marka Raporu (/marka-raporu)

### Katman 1 — Erişim ✅
- `/api/veri-kaynaklari/1/markalar/?customer_type=Bireysel&approval_status=Onayli&page=1&limit=10` → 200

### Filtre Testi ✅

```
Filtresiz → top_marka: KIRMIZI ET, sales: 74.610.454
Bireysel  → top_marka: MANAV, sales: 64.219.396
sahte_filtre = FALSE ✅
```

**Marka raporu filtresi düzgün çalışıyor ve UI parametreleri doğru gönderiyor.**

---

## Akıllı Sorgulama (/akilli-sorgulama)

### Katman 1 — Erişim ❌
- Sayfa 404 veriyor — sidebar'da görünüyor ama implement edilmemiş

**→ BUG-AKL-001 (YENİ — LOW): `/akilli-sorgulama` sayfası 404**

---

## Özet

| Sayfa | Erişim | Filtre |
|-------|--------|--------|
| Ürün Analizi | ❌ 404 (BUG-URN-002) | — |
| Kategori Raporu | ✅ | ❌ Sahte (BUG-KAT-001) |
| Marka Raporu | ✅ | ✅ Çalışıyor |
| Akıllı Sorgulama | ❌ 404 (BUG-AKL-001) | — |

**Bug Sayısı:** 1 HIGH + 2 MEDIUM/LOW  
**Genel Durum:** ⚠️ Marka raporu çalışıyor, kategori filtresiz, 2 sayfa eksik

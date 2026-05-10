# Stratejik Analiz Sayfaları Test Raporu
**Tarih:** 2026-04-29  
**URL'ler:** /kohort-analizi, /urun-birliktelik, /enflasyon-profili, /rakip-riski, /hane-analizi

---

## Kohort Analizi (/kohort-analizi)

### Katman 1 — Erişim ✅
- `/api/veri-kaynaklari/1/kohort-analizi/?max_ay=12` → 200

### Filtre Testi — Sahte Filtre

```
Filtresiz → kohort_ay: 2024-05, retention[0]: 100%
Bireysel  → kohort_ay: 2024-05, retention[0]: 100%  (birebir aynı)
sahte_filtre = TRUE
```

**→ BUG-KOH-001 (YENİ — HIGH): `customer_type` filtresi kohort analizine uygulanmıyor**  
**Düzeltme:** `kohort_view.py` → `customer_type` parametresini müşteri filtresine ekle

---

## Ürün Birliktelik (/urun-birliktelik)

### Katman 1 — Erişim ✅
- `/api/veri-kaynaklari/1/urun-birliktelik/?min_lift=1.0&sort_by=lift&limit=200` → 200

### Filtre Testi — Sahte Filtre

```
Filtresiz → birliktelikler[0]: S.OGLU BAL PIKNIK
Bireysel  → birliktelikler[0]: S.OGLU BAL PIKNIK  (birebir aynı)
sahte_filtre = TRUE
```

**→ BUG-URN-001 (YENİ — HIGH): `customer_type` filtresi ürün birlikteliğine uygulanmıyor**  
**Düzeltme:** `urun_birliktelik_view.py` → transaction filtresi müşteri tipine göre daraltılmalı

---

## Enflasyon Profili (/enflasyon-profili)

### Katman 1 — Erişim ❌
- Sayfa 404 veriyor
- Sidebar'da görünüyor ama route/component implement edilmemiş

**→ BUG-ENF-001 (YENİ — MEDIUM): `/enflasyon-profili` sayfası 404 — implement edilmemiş**

---

## Rakip Riski (/rakip-riski)

### Katman 1 — Erişim ✅
- `/api/veri-kaynaklari/1/rakip-riski/` → 200

### Filtre Testi — Sahte Filtre

```
Filtresiz → dagilim: {orta: 16668, dusuk: 646, toplam: 18233, yuksek: 919}
Bireysel  → dagilim: {orta: 16668, dusuk: 646, toplam: 18233, yuksek: 919}
sahte_filtre = TRUE
```

**→ BUG-RAK-001 (YENİ — HIGH): `customer_type` filtresi rakip riski analizine uygulanmıyor**  
**Düzeltme:** `rakip_riski_view.py` → müşteri tipi filtresini satış sorgusuna ekle

---

## Hane Analizi (/hane-analizi)

### Katman 1 — Erişim ✅
- `/api/veri-kaynaklari/1/hane-analizi/` → 200 (parametresiz — UI filtre iletmiyor)

### Filtre Testi — Sahte Filtre

```
Filtresiz → hane_dagilim[0]: Bekar, musteri_sayisi: 182.929
Bireysel  → hane_dagilim[0]: Bekar, musteri_sayisi: 182.929
sahte_filtre = TRUE
```

**→ BUG-HAN-001 (YENİ — HIGH): `customer_type` filtresi hane analizine uygulanmıyor**  
**Düzeltme:** `hane_analizi_view.py` → müşteri tipi filtresi etikete dayalı sorguya eklenmeli

---

## Özet

| Sayfa | Erişim | Filtre |
|-------|--------|--------|
| Kohort Analizi | ✅ | ❌ Sahte (BUG-KOH-001) |
| Ürün Birliktelik | ✅ | ❌ Sahte (BUG-URN-001) |
| Enflasyon Profili | ❌ 404 (BUG-ENF-001) | — |
| Rakip Riski | ✅ | ❌ Sahte (BUG-RAK-001) |
| Hane Analizi | ✅ | ❌ Sahte (BUG-HAN-001) |

**Bug Sayısı:** 4 HIGH + 1 MEDIUM  
**Genel Durum:** ❌ Sahte filtreler yaygın, bir sayfa eksik

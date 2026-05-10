# Churn Analizi Test Raporu v2 (Filtre Odaklı)
**Tarih:** 2026-04-29  
**URL:** https://show.xpluscrm.com/churn-analizi

---

## Katman 1 — Erişim & Yükleme ✅
- [x] Sayfa yüklendi
- [x] `/api/veri-kaynaklari/1/churn-analizi/` → 200

---

## Katman 2 — Veri Doğruluğu ✅
| KPI | API | UI | Eşleşme |
|-----|-----|----|---------|
| Churn Oranı | %46.5 | %46.5 | ✅ |
| Churn Müşteri | 92.668 | 92.668 | ✅ |
| Risk Altında | 38.100 | 38.100 | ✅ |

---

## Katman 4 — FİLTRE TESTLERİ (Oracle Protokolü)

### TEST CHU-F01: Müşteri Tipi filtresi — Sahte Filtre Tespiti

```
Filtresiz → churnRate: 46.5, churnedCustomers: 92.668
Bireysel  → churnRate: 46.5, churnedCustomers: 92.668
sahte_filtre_Bireysel = TRUE
```

**→ BUG-CHU-004 (YENİ): `customer_type` filtresi churn analizine hiç uygulanmıyor**

---

### TEST CHU-F02: Yıl filtresi — ÇALIŞIYOR (kısmen)

```
Filtresiz → churnRate: 46.5
Yıl 2024  → churnRate: 52.9
sahte_filtre_yil = FALSE ✅
```

Yıl filtresi churn rate'i değiştiriyor — bu endpoint'in en azından `year` parametresini uyguladığı anlaşılıyor.  
**Ancak:** `churnByMonth` yıl filtresiyle bile boş geliyor (BUG-CHU-001 devam ediyor).

---

### TEST CHU-F03: Risk müşteri listesi araştırması

```
filtresiz → atRiskCustomers.length: 0
Bireysel  → atRiskCustomers.length: 0
```

KPI 38.100 risk müşterisi gösteriyor ama liste her koşulda boş.

**→ BUG-CHU-003 (önceki): atRiskCustomers API'den hiç gelmiyor**

---

## Bug Listesi (Bu Sayfa)

### BUG-CHU-001 — Aylık churn trendi boş (ÖNCEKİ)
**Severity:** MEDIUM  
**Kanıt:** `churnByMonth: []` — yıl filtresiyle de değişmiyor

### BUG-CHU-002 — Risk faktörleri boş (ÖNCEKİ)
**Severity:** LOW  
**Kanıt:** `riskFactors: []`

### BUG-CHU-003 — Risk müşteri listesi boş (ÖNCEKİ)
**Severity:** MEDIUM  
**Kanıt:** KPI 38.100 gösteriyor ama `atRiskCustomers: []`

### BUG-CHU-004 — customer_type filtresi sahte (YENİ)
**Severity:** HIGH  
**Tür:** Sahte Filtre  
**Tetikleyici:** `GET /veri-kaynaklari/1/churn-analizi/?customer_type=Bireysel`  
**Beklenen:** Yalnızca bireysel müşterilerin churn analizi  
**Gerçekleşen:** Tüm müşterilerin analizi (filtresiz ile birebir aynı)  
**Kanıt:** `sahte_filtre_Bireysel = TRUE`  
**Düzeltme Önerisi:** `churn_view.py` → `customer_type` parametresi alınıp SQL WHERE'e eklenmeli

---

## Özet

| Kategori | Durum |
|----------|-------|
| Yükleme | ✅ OK |
| KPI doğruluğu (filtresiz) | ✅ OK |
| Yıl filtresi | ✅ Çalışıyor |
| customer_type filtresi | ❌ BUG-CHU-004 (Sahte) |
| Aylık trend | ❌ BUG-CHU-001 |
| Risk listesi | ❌ BUG-CHU-003 |

**Bug Sayısı:** 1 HIGH + 2 MEDIUM + 1 LOW  
**Genel Durum:** ⚠️ Yıl filtresi çalışıyor, diğerleri sahte veya boş

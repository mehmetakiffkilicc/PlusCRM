# PLUS CRM — Diğer Raporlar Test Raporu

**Test Tarihi:** 30 Nisan 2026
**Test Eden:** Oracle Agent (Antigravity)
**Durum:** Beklemede

## Kontrol Listesi

### Churn Analizi (/churn-analizi)
- [x] Sayfa yükleniyor (Hızlı)
- [x] Grafik ve KPI kartları render ediliyor
- [x] Riskli müşteri metrikleri (%66.5 Churn) dolu ve tutarlı

### Segmentasyon (/segmentasyon)
- [x] Segment kartları (Şampiyonlar, Sadık, vb.) görünüyor
- [x] Etiket bazlı (Ziyaret, Sepet, Fiyat) kırılımlar dolu
- [x] AI ile Yorumla butonu mevcut

### RFM Analizi (/rfm-analizi)
- [x] RFM Grid ve Segment kartları render ediliyor
- [ ] **BUG-RFM-001:** Üst kartta "Şampiyonlar" 0 görünüyor (Veride olmasına rağmen)

### Ürün Birliktelik (/urun-birliktelik)
- [x] 5.000 kural başarıyla listeleniyor
- [x] Lift, Confidence ve Ortak Fiş metrikleri doğru

---

## Bulgular (Buglar)
- **🟡 BUG-RFM-001 (MEDIUM): RFM Kart Hatası**
    - **Açıklama:** RFM Analizi sayfasında üstteki "Şampiyonlar" kartı 0 değerini gösteriyor. Ancak alt listede Şampiyon segmentine ait müşteriler olduğu biliniyor.
    - **Kanıt:** Screenshot `page-2026-04-30T20-20-36-805Z.png`

---

## Kanıtlar (Screenshots)
- ![Churn](.playwright-mcp\page-2026-04-30T20-19-53-061Z.png)
- ![Segmentasyon](.playwright-mcp\page-2026-04-30T20-20-13-682Z.png)
- ![RFM](.playwright-mcp\page-2026-04-30T20-20-36-805Z.png)
- ![Ürün Birliktelik](.playwright-mcp\page-2026-04-30T20-21-00-549Z.png)

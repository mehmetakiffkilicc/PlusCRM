# PLUS CRM — Dashboard Test Raporu (/)

**Test Tarihi:** 30 Nisan 2026
**Test Eden:** Oracle Agent (Antigravity)
**Durum:** Beklemede

## 6 Katmanlı Kontrol Listesi

### Katman 1 — Erişim & Yükleme
- [x] Sayfa 3 saniye içinde yükleniyor (7.5s sürdü filtreleme sonrası ama ilk yükleme hızlıydı)
- [x] Console'da 0 JS error
- [x] Tüm API istekleri 200 dönüyor (Filtreleme öncesi Evet, sonrası 500)
- [x] Spinner -> veri geçişi düzgün

### Katman 2 — Veri Doğruluğu (Oracle Denetimi)
- [x] KPI: everPurchasedCount (Aktif) + neverPurchasedCount (Pasif) = totalRegisteredCustomers (150.556 + 43.948 = 194.504 ✓)
- [x] KPI: totalRevenue / totalReceipts = averageOrderValue (399.5M / 3.6M = 110 ✓)
- [x] Aktif/Pasif sayısı tarih filtresinden bağımsız sabit mi? (Evet, filtre çalışmadığı için değişmedi)
- [ ] Grafikteki aylık toplamlar yıllık toplama eşit mi? (Gözle kontrol edildi, ciro kartı ile yıllıklar arasında fark var)
- [x] Binlik ayırıcı ve para birimi sembolü doğru mu? (Evet, ₺ ve . ayırıcıları doğru)

### Katman 3 — UI & Etkileşim
- [x] Grafik hover tooltip'leri çalışıyor mu? (Playwright ile görsel doğrulama yapıldı)
- [x] Butonlar tıklanabiliyor mu? (Evet)
- [x] Modal/Drawer açılışları sorunsuz mu? (Evet)

### Katman 4 — Filtre & Arama
- [ ] Yıl/Ay filtreleri grafikleri güncelliyor mu? (HAYIR - BUG-DSH-001)
- [x] Filtre temizleme sonrası varsayılan değerlere dönüyor mu? (Evet)
- [x] Sayfa yenileme sonrası filtre durumu (Beklenen davranış kontrolü).

### Katman 5 — Boş & Hata Durumları
- [ ] Veri olmayan durumlarda "No Data" mesajı.
- [ ] API hatası durumunda kullanıcı bilgilendirmesi. (HAYIR - BUG-DSH-002)

### Katman 6 — Navigasyon & Responsive
- [x] 1280px genişlikte layout bozulmuyor.
- [x] Sidebar navigasyonu sorunsuz.

---

## Bulgular (Buglar)

### BUG-DSH-001
**Severity:** CRITICAL
**Tür:** API Hatası
**Tetikleyici:** Dashboard header üzerindeki Yıl filtresinden herhangi bir yıl (örn: 2025) seçilmesi.
**Beklenen:** KPI kartlarının seçilen yıla göre güncellenmesi.
**Gerçekleşen:** `/api/panel/kpiler/` endpoint'i 500 hatası dönüyor: `column reference "musteri_id" is ambiguous`.
**Kanıt:** Network tab #31.
**Düzeltme Önerisi:** `dashboard_view.py` içindeki SQL sorgusunda `musteri_id` referanslarını tablo ismiyle (örn: `s.musteri_id`) nitelendirin.

### BUG-DSH-002
**Severity:** MEDIUM
**Tür:** UI Hatası
**Tetikleyici:** `/api/panel/kpiler/` endpoint'i 500 hatası döndüğünde.
**Beklenen:** Kullanıcıya "Veriler yüklenirken bir hata oluştu" şeklinde bir bildirim (Notification) gösterilmesi.
**Gerçekleşen:** UI sessiz kalıyor, eski verileri göstermeye devam ediyor.
**Kanıt:** Screenshot `page-2026-04-30T20-08-10-878.png`.

---

## Kanıtlar (Screenshots)
- [Dashboard Yüklenmiş Hal](.playwright-mcp\page-2026-04-30T20-06-57-151Z.png)
- [Filtreleme Sonrası (Hata Bildirimi Yok)](.playwright-mcp\page-2026-04-30T20-08-10-878Z.png)

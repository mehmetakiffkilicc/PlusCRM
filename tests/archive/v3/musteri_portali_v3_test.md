# Müşteri Portalı — Test Planı v3 (Derinlemesine, Çok Müşteri)

## Context

**Kaynak:** Ekran görüntüsünde "Harcama ve Ziyaret Trendi" grafiği boş, "AI Profil Özeti" spinner gösteriyor.
**Görev:** Tüm sekmeler, kartlar, butonlar, modal'lar uçtan uca test edilecek. Birden fazla müşteri (farklı segment, harcama, tip) test edilecek.
**URL:** https://backendofxplus.up.railway.app → Müşteri Portalı

---

## Test Felsefesi — Filtre Oracle Protokolü (v2 standardı)

```
1. UYGULA    → UI'da filtre/buton/sekme
2. YAKALA    → browser_network_requests ile API isteği
3. DOĞRULA   → evaluate() ile direkt API'ye istek at
4. KARŞILAŞTIR → UI değeri == API değeri mi?
```

**Boş veri tespiti:** Grafik/kart boşsa → API response'a bak → `[]` mı geliyor yoksa dolu ama UI mu göstermiyor?

---

## Test Müşterileri (Çeşitli Segment)

Her sekmede en az 2-3 farklı müşteri test edilecek:

| Müşteri Seti | Arama Yöntemi | Beklenen Profil |
|-------------|--------------|----------------|
| SET-A | En yüksek harcama → sort_by=total_spend | Şampiyon segment, dolu profil |
| SET-B | En düşük harcama → sort_by=total_spend asc | Kayıp/Uyuyan segment |
| SET-C | "Bireysel" filtresi → ilk müşteri | Bireysel tip |
| SET-D | "Kurumsal" filtresi → ilk müşteri | Kurumsal tip |
| SET-E | Çok yüksek ziyaret → sort_by=total_visits | Sadık müşteri |

---

## Bug Rapor Formatı

```
### BUG-MUS-[NNN]
**Severity:** CRITICAL | HIGH | MEDIUM | LOW
**Tür:** Boş Veri | Sahte Filtre | UI Hatası | API Hatası | Mantık Hatası
**Müşteri:** [ID veya hangi set]
**Sekme/Kart:** [Genel Bakış / Detaylı Analiz / ...]
**Tetikleyici:** [Adım adım]
**Beklenen:** [Ne görmeli]
**Gerçekleşen:** [Ne gördük — boş mu, hata mı, yanlış veri mi]
**Kanıt:** [API response veya screenshot]
**Düzeltme:** [Backend dosya + ne yapılmalı]
```

---

## KATMAN 0 — Sayfa Erişimi & Liste

### MUS-L01: Sayfa Yükleme
- [ ] /musteri-portali 3 saniyede yükleniyor
- [ ] Console 0 JS error
- [ ] API `/veri-kaynaklari/1/musteriler/` → 200 dönüyor
- [ ] Toplam müşteri sayısı görünüyor ("X müşteri")

### MUS-L02: Liste Filtreleri Çalışıyor mu?

```
TEST: Müşteri Tipi = Bireysel
  UYGULA → dropdown'dan Bireysel seç
  YAKALA → network request'te customer_type=Bireysel gidiyor mu?
  API → /musteriler/?customer_type=Bireysel → kaç kayıt?
  KARŞILAŞTIR → UI toplam sayısı == API total?
  KONTROL → total < 199.383 (filtresiz) olmalı
```

```
TEST: Segment Filtresi = Şampiyonlar
  UYGULA → Segment dropdown'dan "01-) Şampiyonlar" seç
  API → /musteriler/?segments=01-)%20Şampiyonlar
  KARŞILAŞTIR → toplam ~268 mi?
```

```
TEST: Harcama filtresi = min 100.000
  UYGULA → Min Harcama kutusuna 100000 yaz
  API → /musteriler/?min_spend=100000
  KONTROL → dönen müşterilerin total_spend hepsi >= 100000 mı?
```

```
TEST: Arama + Müşteri Tipi kombinasyonu
  UYGULA → Bireysel seç + arama kutusuna isim yaz
  KONTROL → Sonuçlar hem Bireysel hem arama ile filtreli mi?
```

### MUS-L03: Sıralama
- [ ] "Toplam Harcama" sıralama → sayılar azalan mı artan mı doğru?
- [ ] "Son Alışveriş" sıralama → tarihler doğru sırada mı?
- [ ] Sayfa 2'ye git → sıralama bozulmadı mı?

### MUS-L04: Sayfalama + Filtre Sıfırlanma
```
ADIM: Listeyi scroll ile 3. sayfaya getir (infinite scroll)
ADIM: Müşteri Tipi filtresini değiştir
KONTROL: page=1'e döndü mü? (API isteğinde page=1 olmalı)
KONTROL: Toplam müşteri sayısı güncellendi mi?
```

---

## KATMAN 1 — Müşteri Detay Modal Açılışı

Her SET için yapılacak:

### MUS-D01: Modal Açılıyor mu?
```
ADIM: SET-A müşterisine tıkla
KONTROL: Modal açılıyor mu?
KONTROL: Yükleme spinner'ı görünüyor mu?
KONTROL: API /musteriler/{id}/ → 200 dönüyor mu?
KONTROL: Başlıkta "Müşteri Analiz Portalı" yazıyor mu?
KONTROL: Sağ üstte Activity Badge ve Trend Badge görünüyor mu?
```

### MUS-D02: Header Kartı (Müşteri Kimliği)
```
KONTROL: Avatar baş harfi doğru mu?
KONTROL: Ad Soyad görünüyor mu?
KONTROL: ID numarası görünüyor mu?
KONTROL: Telefon numarası veya "Tel Yok" yazıyor mu?
KONTROL: Müşteri Tipi (Bireysel/Kurumsal) görünüyor mu?
KONTROL: RFM Segment badge mavi dolu badge olarak görünüyor mu?
KONTROL: Etiket badge'leri (gri noktalı) görünüyor mu?
  → SET-B (düşük harcama) → hiç etiket yoksa [] boş → badge alanı çökmüyor mu?
KONTROL: AI NBA Widget yükleniyor mu? (sağ üst köşe)
```

---

## KATMAN 2 — Genel Bakış Sekmesi

### MUS-OV01: CLV Kartı (Yaşam Boyu Değer)
```
SET-A ve SET-B için:
KONTROL: "₺X.XXX.XXX" formatında toplam harcama görünüyor mu?
  → 0 gelirse "₺0" mı gösteriyor, yoksa boş mu?
KONTROL: Ziyaret sayısı görünüyor (rakam)
KONTROL: Ortalama Sepet "₺X.XXX" formatında görünüyor
KONTROL: detail.kpis.total_spend == API response kpis.total_spend?
```

### MUS-OV02: Harcama ve Ziyaret Trendi Grafiği ← EKRAN GÖRÜNTÜSÜNDE BOŞ
```
SET-A ve SET-B için:
ADIM: Modal aç
YAKALA: API /musteriler/{id}/ response'unda spending_trend key var mı?
KONTROL: spending_trend → [] (boş array) mı geliyor?
  → EVET boş ise: Backend sorgu son 90 günü filtreliyor
              → Müşteri son 90 günde alışveriş yapmamışsa boş gelir
              → BUG ADAYI: SET-A (şampiyon) bile boşsa backend sorgu problemi var
KONTROL: spending_trend dolu geliyorsa ama grafik boşsa:
  → spendingTrendOption week_start formatı sorunsuz mu? (slice(5) yapıyor)
KONTROL: "Arşive Git" butonu tıklanabilir mi ve işlev var mı?
  → Şu an onClick={() => {}} boş → BUG: İşlevsiz buton
API DOĞRULAMA:
  evaluate() → fetch('/api/veri-kaynaklari/1/musteriler/{id}/').then(r=>r.json())
  → spending_trend alanını kontrol et
```

### MUS-OV03: CustomerNarrativeSection (AI)
```
KONTROL: Bileşen render oluyor mu?
KONTROL: Loading durumunda spinner görünüyor mu?
KONTROL: AI yanıtı geliyor mu yoksa hata mı?
```

### MUS-OV04: AI Profil Özeti Kartı ← EKRANDA SPINNER GÖRÜNMESİ NORMAL
```
KONTROL: "Yükle" butonuna tıkla
KONTROL: Spinner görünüyor mu?
KONTROL: AI yanıtı geldi mi? (API /api/ai/... veya stream)
KONTROL: Hata varsa kullanıcıya mesaj gösteriliyor mu?
SET-B (düşük harcama) için de aynı test
```

### MUS-OV05: Gün Bazlı Davranış Grafiği
```
SET-A ve SET-B için:
KONTROL: Grafik yükleniyor mu?
  → detail.day_distribution → 7 gün için veri var mı?
  → Bazı günler 0 ziyaret → bar yüksekliği 0 mı (kaybolmuyor mu)?
KONTROL: X ekseni 7 gün adı doğru mu? (Pazartesi'den Pazar'a)
KONTROL: Y ekseni sol = Ziyaret, sağ = Harcama
KONTROL: Tooltip'e hover yapılınca bilgi geliyor mu?
```

---

## KATMAN 3 — Detaylı Analiz Sekmesi

### MUS-AN01: Kategori Dağılımı (Donut Chart)
```
SET-A ve SET-C için:
ADIM: Detaylı Analiz sekmesine tıkla
KONTROL: Grafik yükleniyor mu?
  → detail.fav_categories → [] boşsa chart boş → boş durum mesajı var mı?
KONTROL: Kategori isimleri Türkçe mi?
KONTROL: Tooltip'te "₺X ({d}%)" formatında görünüyor mu?
KONTROL: Dilim sayısı mantıklı mı? (1-10 arası)
```

### MUS-AN02: En Çok Tercih Edilen Markalar Tablosu
```
SET-A, SET-B, SET-D için:
KONTROL: Tablo görünüyor mu?
KONTROL: Marka adı, Harcama (₺X.XXX), Miktar (X Adet) sütunları dolu mu?
  → SET-B (düşük harcama) → az marka, az satır → tablo hiç yoksa "Veri yok" mu gösteriyor?
KONTROL: Grafik ikonu butonuna (mavi, sağ taraf) tıkla
  → Marka Analizi modal açılıyor mu?
```

### MUS-AN03: Marka Analizi Modal
```
ADIM: Bir markanın grafik ikonuna tıkla
KONTROL: Modal açılıyor mu?
KONTROL: Marka adı ve toplam harcama görünüyor mu?
KONTROL: "TOP ÜRÜNLER" listesi var mı?
  → Ürün adına tıklanınca ProductPortal açılıyor mu?
  → total_revenue ve adet gösteriliyor mu?
SET-B için: top_products boş ise → modal sadece başlık + harcama + boş liste → çökmüyor mu?
```

---

## KATMAN 4 — Alışveriş Geçmişi Sekmesi

### MUS-HIS01: Fiş Listesi Yüklenmesi
```
SET-A ve SET-E için:
ADIM: Alışveriş Geçmişi sekmesine tıkla
KONTROL: Loading spinner görünüyor mu?
KONTROL: API /musteriler/{id}/?mode=fis_listesi&page=1&page_size=50 → 200?
KONTROL: Tablo görünüyor mu?
KONTROL: Sütunlar: Tarih | Fiş No | Mağaza | Miktar | Toplam | [Detay butonu]
KONTROL: Tarih formatı "GG.AA.YYYY SS:DD" mi?
KONTROL: Fiş No bold mu?
KONTROL: Toplam ₺ ile formatlanmış mı?
KONTROL: has_more=true ise "Daha Fazla..." butonu görünüyor mu?
SET-B için: çok az fişi var → has_more=false → buton görünmüyor mu?
```

### MUS-HIS02: Daha Fazla Yükle (Sayfalama)
```
SET-A (çok fişi var):
ADIM: "Daha Fazla..." butonuna tıkla
KONTROL: page=2 ile yeni istek gidiyor mu?
KONTROL: Yeni fişler listenin altına ekleniyor mu (üzerine yazılmıyor)?
KONTROL: Toplam fiş sayısı (fisListesiTotal) doğru mu?
```

### MUS-HIS03: Sepet Detay Modal
```
SET-A'nın herhangi bir fişi:
ADIM: "Detay" butonuna tıkla
KONTROL: Modal açılıyor mu?
KONTROL: API /musteriler/{id}/?fis_no={FIS_NO} → 200?
KONTROL: Modal'da Fiş No ve Toplam görünüyor mu?
KONTROL: Ürün tablosu: Ürün adı | Adet | Tutar dolu mu?
KONTROL: Ürün adına tıklayınca ProductPortal açılıyor mu?
KONTROL: Tutar formatı ₺X.XXX mi?
SET-B fişi için de test et (az kalem olabilir)
```

### MUS-HIS04: Alışveriş Geçmişi Modali (historyOpened)
```
ADIM: Trend grafiğindeki bir noktaya tıkla (spendingTrend click handler)
KONTROL: "Alışveriş Geçmişi" başlıklı ayrı modal açılıyor mu?
  → Şu an modal içi sadece <Text>Geçmiş detayları...</Text> → BUG: İçerik boş!
  → SEVERITY: MEDIUM — placeholder modal, hiç içerik yok
```

---

## KATMAN 5 — Ürün Tercihleri Sekmesi

### MUS-PROD01: Sekme Yüklenmesi
```
SET-A ve SET-C için:
ADIM: Ürün Tercihleri sekmesine tıkla
KONTROL: Loading spinner görünüyor mu?
KONTROL: API /musteriler/{id}/?mode=urun_analizi → 200?
KONTROL: Response'da tekrar_alim veya top_products var mı?
```

### MUS-PROD02: En Çok Alınan Ürünler Listesi
```
KONTROL: Ürün adları listesi görünüyor mu?
KONTROL: Her ürünün sağında "X Adet" badge var mı?
KONTROL: Ürün adına tıklayınca ProductPortal açılıyor mu?
  → ppProductId ve ppProductName doğru set ediliyor mu?
SET-B (düşük harcama): ürün listesi boşsa → loading bitti mi ama liste gösterilmiyor mu?
  → urunAnalizi dolu ama tekrar_alim/top_products boşsa → hiç gösterim yok → BUG ADAYI
```

### MUS-PROD03: Ürün Bazlı Öneriler (AI)
```
KONTROL: AI Insight Card yükleniyor mu?
KONTROL: Yükle butonuna tıkla → spinner → yanıt geliyor mu?
```

---

## KATMAN 6 — Zaman Tüneli Sekmesi

### MUS-TIM01: Timeline Yüklenmesi
```
SET-A ve SET-E için:
ADIM: Zaman Tüneli sekmesine tıkla
KONTROL: Loading spinner görünüyor mu?
KONTROL: API /musteriler/{id}/zaman-cizelgesi/ → 200?
KONTROL: Response yapısı: {aylik_ozet: [...]} veya doğrudan array?
  → Kod: Array.isArray(zamanCizelgesi) ? zamanCizelgesi : zamanCizelgesi?.aylik_ozet ?? []
  → Backend hangi format dönüyor? Kontrol et
```

### MUS-TIM02: Timeline İçeriği
```
KONTROL: Timeline item'lar görünüyor mu?
KONTROL: Her item'da "Ay" bilgisi var mı? (item.ay)
KONTROL: Ziyaret sayısı görünüyor mu? (item.ziyaret_sayisi)
KONTROL: Toplam tutar ₺X.XXX formatında mı?
KONTROL: RFM segment bilgisi (item.rfm_segment) gri küçük yazıyla görünüyor mu?
SET-B: çok az ay verisi → 1-2 item → çökmüyor mu?
```

### MUS-TIM03: Zaman Tüneli Boş Durum
```
SET-B (yeni kayıp müşteri):
KONTROL: API [] boş array dönerse → UI ne gösteriyor?
  → Kod: zamanCizelgesi && (...) — zamanCizelgesi null değil ama aylik_ozet [] ise
  → Timeline bileşeni boş render mi ediyor, yoksa "Veri yok" mesajı var mı?
  → BUG ADAYI: Boş state için kullanıcıya mesaj yok
```

---

## KATMAN 7 — Notlar & CRM Sekmesi

### MUS-NOT01: Notlar Sekmesi Yüklenmesi
```
SET-A için:
ADIM: Notlar & CRM sekmesine tıkla
KONTROL: API /musteriler/{id}/notlar/ → 200?
KONTROL: Not ekleme formu görünüyor mu? (TextInput + Select + Ekle butonu)
```

### MUS-NOT02: Not Ekleme
```
ADIM: Metin kutusuna not yaz: "Test notu — QA"
ADIM: Önem = "yuksek" seç
ADIM: Ekle butonuna tıkla
KONTROL: Loading spinner görünüyor mu?
KONTROL: POST /musteriler/{id}/notlar/ → 201 veya 200?
KONTROL: Not listesinde yeni not görünüyor mu?
KONTROL: Ekledikten sonra TextInput temizlendi mi?
KONTROL: Önem badge rengi: normal=mavi, yuksek=mavi, kritik=kırmızı mı?
KONTROL: Tarih formatı doğru mu?
```

### MUS-NOT03: Not Silme
```
ADIM: Az önce eklenen notu sil (X butonu)
KONTROL: DELETE /musteriler/{id}/notlar/{not_id}/ → 204?
KONTROL: Notlar listesinden siliniyor mu (UI anında güncelleniyor mu)?
```

### MUS-NOT04: Boş Not Ekleme Engeli
```
ADIM: TextInput boşken Ekle butonuna tıkla
KONTROL: İstek gönderilmiyor mu? (yeniNot.trim() === '' koşulu)
KONTROL: Kullanıcıya hata mesajı gösteriliyor mu? (gösterilmiyor olabilir — BUG ADAYI)
```

### MUS-NOT05: İkinci Müşteri (SET-B) Notlar
```
KONTROL: SET-B müşterisini aç → Notlar sekmesine git
KONTROL: Notlar boş ise liste boş görünüyor mu, çökmüyor mu?
KONTROL: Not ekle → başarılı mı?
```

---

## KATMAN 8 — Sub-Modal'lar ve Cross-Navigation

### MUS-SUB01: ProductPortal Açılışı
```
ADIM: Detaylı Analiz → Marka Analizi → Ürün adına tıkla
KONTROL: ProductPortal modal açılıyor mu?
KONTROL: Doğru ürün adı başlıkta görünüyor mu?
KONTROL: Ürün detayları yükleniyor mu?
KONTROL: ProductPortal kapatınca CustomerDetailPortal hala açık mı?
```

### MUS-SUB02: Modal Kapatma ve Yeniden Açma
```
ADIM: SET-A müşterisini aç → Notlar sekmesine git → modal kapat
ADIM: SET-B müşterisini aç
KONTROL: Notlar state'i sıfırlandı mı? (SET-A'nın notları SET-B'de görünmüyor)
KONTROL: fisListesi sıfırlandı mı? (önceki müşterinin fişleri yok)
KONTROL: urunAnalizi sıfırlandı mı?
```

### MUS-SUB03: Kategori Analizi Modal (Açılış Yolu Yok!)
```
KONTROL: Detaylı Analiz sekmesinde Kategori Dağılımı chart'ındaki dilimlere tıklanabilir mi?
  → Kod'da categoryModalOpened state ve openCategoryModal var
  → AMA: categoryChartOption'da onClick handler YOK
  → Marka tablosunda icon butonu var (openBrandModal) ama kategori chart'ında tıklama yok
  → BUG ADAYI: Kategori Analizi Modal açılabilir ama açma yolu yok
```

---

## KATMAN 9 — Farklı Müşteri Tipleri Çapraz Karşılaştırma

### MUS-CROSS01: Şampiyon vs Kayıp Müşteri Karşılaştırması
```
SET-A (Şampiyon):
  → spending_trend: dolu (son 90 gün aktif)
  → fav_brands: 10 marka
  → fav_categories: 8 kategori
  → day_distribution: 7 günün çoğunda veri var
  → Beklenen: HİÇBİR KAR BOŞLUK OLMAMALI

SET-B (Kayıp/Uyuyan):
  → spending_trend: BOŞ (son 90 günde alışveriş yok → NORMAL DAVRANIŞ)
  → fav_brands: az, belki 2-3 marka
  → fav_categories: az
  → day_distribution: büyük ihtimalle dolu (tarihsiz aggregate)
  → Beklenen: Boş grafik için "Son 90 günde veri yok" mesajı
```

### MUS-CROSS02: Bireysel vs Kurumsal Müşteri
```
SET-C (Bireysel):
  → Müşteri tipi badge: "Bireysel"
  → Etiketler farklı (ev tipi etiketler)

SET-D (Kurumsal):
  → Müşteri tipi badge: "Kurumsal"
  → Alışveriş geçmişi → faturalı alışveriş fişleri mi?
  KONTROL: Kurumsal müşteri için fis_listesi dönüyor mu?
```

---

## KATMAN 10 — Railway Memory Limit

### MUS-PERF01: Çok Müşteri Ardışık Açma
```
ADIM: 5 farklı müşteri ardışık aç/kapat
KONTROL: Her açılışta API isteği tamamlanıyor (200) mu?
KONTROL: Console'da memory error var mı?
KONTROL: 5. müşteride yavaşlama var mı?
```

### MUS-PERF02: Büyük Fiş Listesi
```
SET-E (çok ziyaretli müşteri):
ADIM: Alışveriş Geçmişi → "Daha Fazla" × 5 kez
KONTROL: Her page_size=50 istek başarılı mı?
KONTROL: 250+ fiş yüklendikten sonra UI donmuyor mu?
```

---

## Beklenen Bug Listesi (Keşiften)

| Aday ID | Severity | Sekme | Şüphe |
|---------|----------|-------|-------|
| BUG-MUS-HIS04 | MEDIUM | Alışveriş | historyOpened modal içeriği boş ("Geçmiş detayları...") |
| BUG-MUS-OV02a | HIGH | Genel Bakış | spending_trend boş → boş grafik → "Veri yok" mesajı yok |
| BUG-MUS-OV02b | MEDIUM | Genel Bakış | "Arşive Git" butonu tıklanamaz (onClick boş) |
| BUG-MUS-SUB03 | MEDIUM | Detaylı Analiz | Kategori donut chart tıklanınca modal açılmıyor |
| BUG-MUS-NOT04 | LOW | Notlar | Boş not eklenince hata mesajı yok |
| BUG-MUS-TIM03 | LOW | Zaman Tüneli | Boş timeline için kullanıcıya mesaj yok |
| BUG-MUS-PROD02 | HIGH | Ürün Tercihleri | urunAnalizi dolu ama top_products [] ise hiç render yok |

---

## Test Yürütme Sırası

1. **KATMAN 0** → Liste ve filtreler (SET-A, SET-B bul)
2. **KATMAN 1** → SET-A modal aç → header doğrula
3. **KATMAN 2** → Genel Bakış (SET-A ve SET-B karşılaştır)
4. **KATMAN 3** → Detaylı Analiz (SET-A → tüm markaları test et)
5. **KATMAN 4** → Alışveriş Geçmişi (SET-A: fiş + sepet detay)
6. **KATMAN 5** → Ürün Tercihleri (SET-A ve SET-B)
7. **KATMAN 6** → Zaman Tüneli (SET-A ve SET-B)
8. **KATMAN 7** → Notlar (SET-A: ekle/sil, SET-B: not yok)
9. **KATMAN 8** → Sub-modal'lar ve cross-navigation
10. **KATMAN 9** → SET-C ve SET-D ile karşılaştırma
11. **KATMAN 10** → Performance kontrol

---

## Sonuç Formatı

Her testten sonra AUDIT_LOG.md güncellenir. Bulunan bug'lar dosyaya eklenir.

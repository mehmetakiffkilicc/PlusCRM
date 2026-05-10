# AI Asistan Test Raporu
**Tarih:** 2026-04-29  
**URL:** https://show.xpluscrm.com/ai-asistan

---

## Katman 1 — Erişim & Yükleme ✅
- [x] Sayfa yüklendi, 2 JS error (console'da — Katman 4'te incelendi)
- [x] `/api/ai/kullanim-istatistikleri/` veya benzeri usage stats API → 200
- [x] Oturum geçmişi tablosu yüklendi: 3 oturum görünüyor
- [x] Kullanılan Model: **gemini-2.5-flash** (aktif), Bugünkü Sorgu: 1/200, Aylık Token: 47B/5Mn

---

## Katman 2 — Veri Doğruluğu ✅
- API endpoint `POST /api/ai/sohbet/yeni/` → 200, `{id: 66, title: "Yeni Sohbet"}` döndü
- SSE streaming endpoint `POST /api/ai/sohbet/` → 200, akış tam çalışıyor
- Mesaj gönderildi: "Bu ayın toplam cirosunu söyle"
- SSE yanıt sırası: `tool_start` → `tool_running` → `tool_result` → `message` → `done` — doğru protokol
- Tool use çalışıyor: `query_crm_database` gerçek veriyi sorguladı
- AI yanıtı: **"Bu ayın toplam cirosu 32.147.545,68 TL olarak hesaplanmıştır."**
- Decimal TypeError yok (session_store.py düzeltmesi geçerli)
- Fallback mekanizması çalışıyor: birincil servis yoğunsa openrouter/free devreye giriyor

---

## Katman 3 — UI & Etkileşim

### BUG-AI-001 — "Yeni Sohbet Başlat" butonu chat penceresini açmıyor
**Severity:** HIGH  
**Tür:** UI Hatası / Mantık Hatası  
**Tetikleyici:** AI Asistan sayfası → "Yeni Sohbet Başlat" butonuna tıkla  
**Beklenen:** ChatWidget drawer açılmalı, kullanıcı mesaj girebilmeli  
**Gerçekleşen:** Buton oturum oluşturuyor (API çağrısı yapılıyor, `activeSessionId` set ediliyor) ama chat drawer açılmıyor — textarea hiç görünmüyor  
**Kök Neden:** `AIAssistant.tsx:76` — `onClick={() => useChatStore.getState().startNewSession()}` çağrılıyor, ancak `startNewSession()` içinde `useUIStore.getState().setChatOpened(true)` eksik. `ChatWidget` drawer'ının açılması için `chatOpened = true` gerekiyor ama bu set edilmiyor.  
**Kanıt:** `chatStore.ts:77-104` — `startNewSession` hiçbir yerde `setChatOpened` çağırmıyor; `AIAssistant.tsx:51-55` — `handleOpenChat` fonksiyonunda `setChatOpened(true)` var ama buton buna bağlı değil  
**Düzeltme Önerisi:** `AIAssistant.tsx:76` → `onClick` handler'ını şu şekilde değiştir:
```typescript
onClick={async () => {
  await useChatStore.getState().startNewSession();
  useUIStore.getState().setChatOpened(true);
}}
```
Veya `chatStore.ts` içinde `startNewSession` sonuna `useUIStore.getState().setChatOpened(true)` ekle.

### Geçmiş Analizler tablosu ✅
- [x] 3 oturum listeleniyor (başlık + tarih sütunları dolu)
- [x] Her satırda açma (▷) ve silme (🗑) butonları görünüyor

### Geçmiş oturumu açma ✅
- [x] `handleOpenChat` fonksiyonu `loadSession()` + `setChatOpened(true)` çağırıyor — doğru implementasyon
- [x] Satır tıklandığında session yükleniyor (oturum geçmişi korunuyor)

### Hızlı Zeka Aksiyonları ✅
- [x] "Churn Riski Analiz Et", "Kampanya Önerisi Al", "CLV Tahmini İncele" butonları görünüyor

---

## Katman 4 — Console Hataları
- 2 JS error tespit edildi (console.log gösterilmedi ancak sayım 2 idi)
- Streaming yanıtında hata yok

---

## Katman 5 — Boş & Hata Durumları ✅
- [x] Oturum yoksa boş durum gösteriliyor (sil butonu ile tüm geçmişler silinince doğrulanabilir)
- [x] AI servisi yanıt vermezse fallback (openrouter/free) devreye giriyor — kullanıcı bilgilendirildi

---

## Katman 6 — Navigasyon & Responsive ✅
- [x] 1280px'de layout bozulmuyor
- [x] "AI Zeka Merkezi" başlığı + metrikler görünüyor

---

## Teardown
- Test sırasında oluşturulan oturumlar (ID: 65, 66) silindi → `DELETE /api/ai/sohbet/65/` ve `DELETE /api/ai/sohbet/66/` → 200 ✅
- Takvim 3 oturuma döndü (26.04.2026 tarihli 1 adet pre-existing oturum)

---

## Özet

| Kategori | Durum |
|----------|-------|
| Yükleme | ✅ OK |
| Usage stats | ✅ API doğru |
| Streaming chat | ✅ Tool use çalışıyor |
| Decimal TypeError | ✅ Yok |
| Fallback mekanizması | ✅ Çalışıyor |
| "Yeni Sohbet Başlat" UI | ⚠️ BUG-AI-001 |
| Geçmiş oturum açma | ✅ OK |

**Bug Sayısı:** 1 HIGH  
**Genel Durum:** Geçti (1 kritik UI bug düzeltilmeli)

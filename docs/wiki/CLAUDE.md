# BackendFronend Wiki — Vault Şeması (Anayasa)

## Amaç

Bu vault, **BackendFronend** projesinin — analytics + CRM portal, RFM/Churn/CLV/Kohort analizleri, Anthropic + Gemini destekli AI asistan, MSSQL→Postgres ETL pipeline, React+Mantine frontend — kalıcı bilgi arşividir.

**Kullanım kuralı**: Yeni bir özellik veya modül planlanırken **önce wiki**, sonra kod okunur. Cevap wiki'de bulunmazsa INGEST ile kaynaktan çıkarılır ve wikiye dosyalanır.

---

## Klasör Yapısı

```
docs/wiki/
├── CLAUDE.md          # bu dosya — vault şeması
├── index.md           # içerik kataloğu (her sayfaya link)
├── log.md             # zamansal append-only kayıt
├── lint-report.md     # son lint pass bulgular
├── raw/               # DOKUNULMAZ — sadece oku, asla yazma
│   ├── code-modules/  # kaynak kod referans noktaları (.path.txt veya symlink)
│   └── docs/          # harici dokümanlar, transcriptler
├── sources/           # her kaynak için özetlenmiş sayfa
│   └── code-modules/  # 2026-05-04-<slug>.md formatında
├── entities/          # somut varlıklar (modeller, view'lar, sayfalar, servisler)
├── concepts/          # soyut kavramlar (RFM, Churn, JWT, Streaming…)
├── decisions/         # mimari kararlar (ADR benzeri)
├── issues/            # sorunlar, riskler, anti-pattern'ler
├── syntheses/         # üst düzey sentez ve akış diyagramları
└── archive/           # silinmiş/eski sayfalar (silme yok — archive)
```

---

## Sayfa Formatı (ZORUNLU)

Her wiki sayfasının başında şu frontmatter bloğu **mutlaka** yer alır:

```yaml
---
title: Sayfa Başlığı
tags: [backend|frontend|infra|domain|concept|decision|issue|synthesis]
source: backend/api/analytics/rfm_view.py
date: 2026-05-04
status: draft|stable|stale
---
```

Frontmatter'dan sonra **zorunlu bölümler**:

```markdown
# Başlık

**Özet:** Maksimum 3 cümle. Ne yaptığını, neden var olduğunu, kime/neye hizmet ettiğini anlat.
**Kütüphaneler:** Kullanılan teknolojiler (Django, DRF, Zustand, Mantine…)
**Bağlantılar:** [[ilgili-sayfa-1]], [[ilgili-sayfa-2]]

## Detay
...

## Sources
- `backend/api/...` (satır referansı opsiyonel ama önerilir)

## Related
- [[diger-sayfa]] — kısa ilişki açıklaması
```

---

## Naming Konvansiyonu

- **kebab-case**: `analytics-rfm.md`, `dashboard-modeli.md`, `karar-jwt-localstorage.md`
- **Varlık sayfaları**: modül/dosya adına yakın (`rfm-view.md`, `auth-store.md`, `app-router.md`)
- **Karar sayfaları**: `karar-<konu>.md` (örn. `karar-sqlite-direct-kpi.md`)
- **Sorun sayfaları**: `sorun-<konu>.md` (örn. `sorun-n-plus-1-sorgu.md`)
- **Kavram sayfaları**: kısaltma değil tam ad (`rfm-analizi.md`, `kohort-analizi.md`)

---

## INGEST Workflow

Yeni bir kaynak (kod modülü, transcript, belge) eklendiğinde sırayla:

1. Kaynağı oku; anahtar çıkarımları, kararları, sorunları tespit et.
2. `sources/code-modules/2026-MM-DD-<slug>.md` sayfası yaz:
   - Goal, What-was-done, Files, Decisions, Issues, Open-threads, Sources, Related
3. Bahsedilen her **entity** için `entities/` sayfası yarat veya güncelle. Çift yönlü link kur.
4. Her **mimari/teknik karar** için `decisions/karar-<konu>.md` atomik sayfa.
5. Her **sorun/risk** için `issues/sorun-<konu>.md`.
6. Her **soyut kavram** için `concepts/<kavram>.md` sayfası yarat veya güncelle.
7. `log.md`'ye: `## [YYYY-MM-DD] ingest | <slug>` + dokunulan dosyalar listesi.
8. `index.md`'yi güncelle — yeni sayfalar ilgili kategoriye eklenir.

---

## QUERY Workflow

1. `index.md`'yi oku — ilgili kategorileri belirle.
2. İlgili sayfaları oku (`entities/`, `concepts/`, `syntheses/`).
3. Cevabı sentezle. İddia başına kaynak referansı ver.
4. Değerli bir keşifse atomik sayfa olarak `syntheses/` veya `concepts/`'e dosyala (tek fikir = tek sayfa).
5. `log.md`'ye: `## [YYYY-MM-DD] query | "soru" → filed: <path>` (sadece dosyalanan sorgular).

---

## LINT Workflow

`lint-report.md` yazar, otomatik düzeltme yapmaz:

- **Çelişkiler**: `## ÇELİŞKİ` başlıklı sayfalar
- **Orphan sayfalar**: hiçbir yerden gelen `[[link]]` olmayan sayfalar
- **Tek yönlü linkler**: A→B var ama B→A yok
- **Kendi sayfası olmayan kavramlar**: metinde geçen ama `concepts/`'te bulunmayan terimler
- **Stale claim'ler**: `status: stale` işaretli sayfalar
- **Veri boşlukları**: doldurulabilecek eksik bilgiler

---

## Hard Rules

1. **`raw/` IMMUTABLE.** Hiçbir zaman `raw/` içine içerik yazma. Sadece oku. Sembolik link veya `.path.txt` referansı koy — orijinal dosyaya dokunma.
2. **Kaynaksız iddia yasak.** Her önemli cümle hangi `raw/` kaynağından geldiğini `## Sources` bölümünde belirtir.
3. **Çelişki silinmez, işaretlenir.** Kaynak A ile Kaynak B çeliştiğinde ilgili sayfaya `## ÇELİŞKİ` bölümü ekle, ileride çöz.
4. **Çift yönlü link zorunlu.** A sayfasına `[[B]]` eklediysen B sayfasına da `[[A]]` ekle.
5. **Her ingest/query log'lanır.** `log.md`'ye zaman damgalı giriş.
6. **Sayfa silinmez, archive edilir.** Eski/hatalı sayfa `archive/` altına taşınır, index güncellenir.
7. **Atomic filed-back.** Sentezi tek "session özeti" değil ayrık atomik sayfalar olarak dosyala.
8. **Şema birlikte evrilir.** Kural çalışmıyorsa bu dosyayı güncelle. Sonraki oturumda yeni kural geçerli.

---

## Bu Projeye Özel Kurallar

- Backend kaynak referansları `backend/` ile başlar (örn. `backend/api/analytics/rfm_view.py`).
- Frontend kaynak referansları `frontend/src/` ile başlar (örn. `frontend/src/pages/RFMAnalysis.tsx`).
- Her endpoint sayfası `backend/api/urls.py` satır referansı içerir.
- Her React sayfası `frontend/src/App.tsx` route kaydına ve ilgili Zustand store'una link verir.
- AI subsistem sayfaları `backend/api/analytics/llm/` ve `frontend/src/components/ai/` çift taraflı referans eder.
- sync_worker sayfaları, hangi Postgres tablolarını yazdığını açıklar.

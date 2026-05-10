---
title: Playwright MCP Entegrasyonu
tags: [infra, testing, frontend]
source: .mcp.json, playwright.config.ts
date: 2026-05-06
status: stable
---

# Playwright MCP Entegrasyonu

**Özet:** Tarayıcı tabanlı E2E (end-to-end) testleri için Playwright kuruldu. MCP (Model Context Protocol) üzerinden ajanlar testleri otonom olarak çalıştırabilir. Headless Chromium varsayılan tarayıcıdır.

**Kütüphaneler:** @playwright/test@1.59.1, @playwright/mcp@0.0.73
**Bağlantılar:** [[entities/docker-compose]], [[concepts/streaming-chat]]

## Kurulum

```bash
cd frontend
npm install -D @playwright/test playwright @playwright/mcp
npx playwright install chromium
```

## MCP Yapılandırması (`.mcp.json`)

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless"],
      "env": { "PLAYWRIGHT_BROWSERS_PATH": "0" }
    }
  }
}
```

## npm Script'leri

| Komut | Açıklama |
|--------|------------|
| `npm run e2e` | Headless test çalıştır |
| `npm run e2e:ui` | UI modunda test çalıştır |

## Test Yapısı

- `e2e/` dizini: Test dosyaları
- `playwright.config.ts`: Base URL `https://show.xpluscrm.com` (Canlı sunucu)
- `headless: false`: Tarayıcı görünür modda açılır, manuel giriş yapılabilir

## AI Test Senaryoları

1. **Session oluşturma:** `startNewSession` API çağrısı ve timeout kontrolü
2. **Streaming hatası:** 90sn timeout sonrası hata mesajı gösterimi
3. **UI state triad:** Boş/loading/error durumlarının kontrolü
4. **Manuel giriş:** `manual-login.spec.ts` ile tarayıcı açılır, kullanıcı giriş yapar, sonra test devam eder

## Sources
- `.mcp.json`
- `frontend/playwright.config.ts`
- `frontend/package.json` (e2e script'leri)

## Related
- [[concepts/streaming-chat]] — SSE streaming testleri
- [[entities/store-chat]] — Chat store test senaryoları

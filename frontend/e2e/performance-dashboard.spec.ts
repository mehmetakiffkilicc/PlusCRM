import { test, expect, Page } from '@playwright/test'

interface ApiTiming {
  url: string
  method: string
  startTime: number
  endTime: number
  duration: number
  status: number
}

async function login(page: Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  const emailInput = page.locator('input[type="email"], input[name="email"]').first()
  if (await emailInput.isVisible({ timeout: 5000 }).catch(() => false)) {
    await emailInput.fill('makif4596@gmail.com')
    await page.locator('input[type="password"], input[name="password"]').first().fill('Test1234')
    await page.locator('button[type="submit"], button:has-text("Giriş")').first().click()
    await page.waitForTimeout(3000)
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})
  }
}

test('Anasayfa yüklenme performansı ölçümü', async ({ page }) => {
  const apiTimings: ApiTiming[] = []

  // API çağrılarını yakala
  await page.route('**/api/**', async (route) => {
    const url = route.request().url()
    const method = route.request().method()
    const startTime = Date.now()
    try {
      const response = await route.fetch()
      const duration = Date.now() - startTime
      apiTimings.push({ url, method, startTime, endTime: Date.now(), duration, status: response.status() })
      return await route.fulfill({ response })
    } catch (e) {
      apiTimings.push({ url, method, startTime, endTime: Date.now(), duration: Date.now() - startTime, status: 0 })
      await route.continue()
    }
  })

  // Login
  console.log('\n=== PERFORMANS TESTİ BAŞLADI ===')
  const loginStart = Date.now()
  await login(page)
  const loginDuration = Date.now() - loginStart
  console.log(`⏱ Giriş süresi: ${loginDuration}ms`)

  // Sayfa yükleme sürelerini ölç
  const loadStart = Date.now()

  // KPI kartlarının görünmesini bekle
  const kpiStart = Date.now()
  const kpiCard = page.locator('[class*="KpiCard"], .kpi-card, [class*="kpi"]').first()
  await kpiCard.waitFor({ state: 'visible', timeout: 30000 }).catch(() => {})
  const kpiDuration = Date.now() - kpiStart
  console.log(`⏱ İlk KPI kartı görünene kadar: ${kpiDuration}ms (toplam: ${Date.now() - loadStart}ms)`)

  // Sayfanın tam yüklenmesini bekle
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {})
  const networkIdleDuration = Date.now() - loadStart
  console.log(`⏱ Network idle: ${networkIdleDuration}ms`)

  // Tüm API çağrıları bitsin diye ek bekleme
  await page.waitForTimeout(2000)

  const totalDuration = Date.now() - loadStart
  console.log(`⏱ Toplam yükleme süresi: ${totalDuration}ms`)

  // API çağrılarını analiz et
  console.log(`\n📡 API Çağrıları (${apiTimings.length} adet):`)
  const slowCalls = apiTimings.filter(t => t.duration > 1000).sort((a, b) => b.duration - a.duration)
  
  for (const call of apiTimings.sort((a, b) => b.duration - a.duration)) {
    const urlShort = call.url.length > 80 ? call.url.substring(0, 80) + '...' : call.url
    const status = call.status || 'FAILED'
    console.log(`   ${call.method} ${status} ${call.duration}ms → ${urlShort}`)
  }

  if (slowCalls.length > 0) {
    console.log(`\n🐌 YAVAŞ API ÇAĞRILARI (>1s):`)
    for (const call of slowCalls) {
      console.log(`   ⚠ ${call.method} ${call.duration}ms → ${call.url}`)
    }
  }

  // Sayfanın görsel durumunu kontrol et
  const hasKpi = await kpiCard.isVisible().catch(() => false)
  const hasChart = await page.locator('canvas, .recharts-wrapper, [class*="chart"], [class*="Chart"]').first().isVisible().catch(() => false)

  console.log(`\n📊 GÖRSELLER:`)
  console.log(`   KPI Kartları: ${hasKpi ? '✓' : '✗'}`)
  console.log(`   Grafikler: ${hasChart ? '✓' : '✗'}`)
  console.log(`   API Çağrıları: ${apiTimings.length} adet`)
  console.log(`   Yavaş Çağrılar: ${slowCalls.length} adet (${slowCalls.filter(t => t.duration > 3000).length} adet >3s)`)

  // Test başarısız olmasın, sadece raporla
  expect(true).toBe(true)
})

test('Anasayfa statik kaynak yükleme süresi', async ({ page }) => {
  const resourceTimings: { name: string; duration: number }[] = []

  page.on('requestfinished', (request) => {
    const url = request.url()
    if (url.endsWith('.js') || url.endsWith('.css') || url.endsWith('.png') || url.endsWith('.jpg') || url.endsWith('.svg')) {
      const timing = request.timing()
      if (timing) {
        const duration = (timing.responseEnd || 0) - (timing.requestStart || 0)
        if (duration > 0) {
          resourceTimings.push({ name: url.split('/').pop() || url, duration })
        }
      }
    }
  })

  await login(page)
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})

  console.log(`\n=== STATİK KAYNAK YÜKLEME ===`)
  const slowResources = resourceTimings.filter(r => r.duration > 500).sort((a, b) => b.duration - a.duration)
  
  if (slowResources.length > 0) {
    console.log(`Yavaş kaynaklar (>500ms):`)
    for (const r of slowResources) {
      console.log(`   ⚠ ${r.duration}ms → ${r.name}`)
    }
  }

  console.log(`\nToplam statik kaynak: ${resourceTimings.length} adet`)
  console.log(`Yavaş kaynaklar: ${slowResources.length} adet`)

  expect(true).toBe(true)
})

import { test, expect, Page } from '@playwright/test'

const BASE = 'http://127.0.0.1:3099'

async function bypassAuth(page: Page) {
  // Set localStorage BEFORE navigating so the app sees auth_token
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'test-bypass-token')
    localStorage.setItem('theme-store', JSON.stringify({
      state: { activeTheme: 'default', colorScheme: 'light' }
    }))
  })
}

async function logThemeState(page: Page, label: string) {
  const dataTheme = await page.evaluate(() =>
    document.documentElement.getAttribute('data-theme')
  )
  console.log(`[${label}] data-theme = "${dataTheme}"`)
  return dataTheme
}

async function captureConsole(page: Page) {
  const logs: string[] = []
  page.on('console', (msg) => logs.push(`[${msg.type().toUpperCase()}] ${msg.text()}`))
  page.on('pageerror', (err) => logs.push(`[PAGE_ERROR] ${err.message}`))
  return logs
}

test('Theme Switching: Varsayilan -> MarketCRM', async ({ page }) => {
  const consoleLogs: string[] = []
  page.on('console', (msg) => consoleLogs.push(`[${msg.type().toUpperCase()}] ${msg.text()}`))
  page.on('pageerror', (err) => consoleLogs.push(`[PAGE_ERROR] ${err.message}`))

  // Intercept ALL API calls to return empty/fake data so the app doesn't crash
  await page.route('**/api/**', (route) => {
    const url = route.request().url()
    if (url.includes('/api/auth/') || url.includes('/api/login')) {
      // Let auth calls go through
      route.continue()
    } else if (url.includes('/ayarlar') || url.includes('/settings')) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          localization: { currency: 'TRY', language: 'tr' },
          appearance: { primary_color: '#4f46e5' }
        })
      })
    } else if (url.includes('/profile')) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1, email: 'test@test.com',
          first_name: 'Test', last_name: 'User'
        })
      })
    } else if (url.includes('/dashboard') || url.includes('/kpi') || url.includes('/trend') || url.includes('/segment')) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({})
      })
    } else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({})
      })
    }
  })

  // Step 1: Set auth bypass
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'test-bypass-token')
    localStorage.setItem('theme-store', JSON.stringify({
      state: { activeTheme: 'default', colorScheme: 'light' }
    }))
  })

  console.log('--- STEP 1: Navigate to Dashboard (default theme) ---')
  await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 30000 })
  // Wait for React to render
  await page.waitForTimeout(2000)
  const theme1 = await logThemeState(page, 'Dashboard - Initial')
  console.log(`Page title: ${await page.title()}`)

  // Step 2: Navigate to Settings
  console.log('\n--- STEP 2: Navigate to /ayarlar (Settings) ---')
  await page.goto(BASE + '/ayarlar', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)
  const theme2 = await logThemeState(page, 'Settings - Before Click')

  // Step 3: Click the MarketCRM theme card
  console.log('\n--- STEP 3: Click MarketCRM (Teal) theme card ---')
  // Try multiple selectors for the theme card
  try {
    const marketCrmCard = page.locator('.theme-card').last()
    await expect(marketCrmCard).toBeVisible({ timeout: 5000 })
    console.log('Found MarketCRM theme card, clicking...')
    await marketCrmCard.click()
    await page.waitForTimeout(1000)
  } catch (e) {
    console.log('theme-card selector failed, trying text-based selector...')
    try {
      const marketCrmCard = page.locator('text=MarketCRM').first()
      await expect(marketCrmCard).toBeVisible({ timeout: 5000 })
      await marketCrmCard.click()
      await page.waitForTimeout(1000)
    } catch (e2) {
      console.log('Text selector also failed:', e2.message)
    }
  }
  const theme3 = await logThemeState(page, 'Settings - After Click')

  // Step 4: Navigate back to Dashboard and screenshot
  console.log('\n--- STEP 4: Navigate back to Dashboard ---')
  await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2000)
  const theme4 = await logThemeState(page, 'Dashboard - After Theme Switch')
  await page.screenshot({ path: 'test-results/dashboard-marketCRM.png', fullPage: true })
  console.log('Screenshot saved: dashboard-marketCRM.png')

  // Step 5: Check computed styles of kpi-card
  console.log('\n--- STEP 5: Check .kpi-card computed styles ---')
  const kpiCard = page.locator('.kpi-card').first()
  try {
    await expect(kpiCard).toBeVisible({ timeout: 5000 })
    const styles = await kpiCard.evaluate((el) => {
      const cs = getComputedStyle(el)
      return {
        borderLeftColor: cs.borderLeftColor,
        borderRadius: cs.borderRadius,
        boxShadow: cs.boxShadow,
        borderLeftWidth: cs.borderLeftWidth,
      }
    })
    console.log('KPI Card computed styles (MarketCRM):')
    console.log(`  border-left-color: ${styles.borderLeftColor}`)
    console.log(`  border-radius: ${styles.borderRadius}`)
    console.log(`  box-shadow: ${styles.boxShadow}`)
    console.log(`  border-left-width: ${styles.borderLeftWidth}`)
  } catch (e) {
    console.log('Could not find .kpi-card element:', e.message)
  }

  // Step 6: Switch back to default theme
  console.log('\n--- STEP 6: Switch back to Default theme ---')
  await page.goto(BASE + '/ayarlar', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)
  try {
    const defaultCard = page.locator('.theme-card').first()
    await expect(defaultCard).toBeVisible({ timeout: 5000 })
    await defaultCard.click()
    await page.waitForTimeout(1000)
  } catch (e) {
    console.log('Default theme card click failed:', e.message)
  }
  const theme5 = await logThemeState(page, 'Settings - Back to Default')

  // Final Report
  console.log('\n========== FINAL REPORT ==========')
  console.log(`Theme sequence: ${theme1} -> ${theme2} -> ${theme3} -> ${theme4} -> ${theme5}`)
  console.log('\nConsole errors:')
  const errors = consoleLogs.filter(l => l.startsWith('[ERROR]') || l.startsWith('[PAGE_ERROR]'))
  errors.forEach(e => console.log(`  ${e}`))
  console.log(`\nTotal console messages: ${consoleLogs.length}`)
  console.log('==================================')
})

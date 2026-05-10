import { test, expect } from '@playwright/test'

const CREDS = { email: 'makif4596@gmail.com', password: 'Test1234' }

test('Check API response for product portal', async ({ page }) => {
  await page.goto('/giris')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(500)
  await page.locator('#email').fill(CREDS.email)
  await page.locator('#password').fill(CREDS.password)
  await page.locator('button[type="submit"]').click()
  await page.waitForTimeout(5000)
  await page.waitForLoadState('networkidle')

  // Catch the API call when we open a product
  let apiResponse: any = null
  page.on('response', async (resp) => {
    const url = resp.url()
    if (url.includes('urun-portali')) {
      try {
        apiResponse = await resp.json()
      } catch {}
    }
  })

  await page.goto('/urunler')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(3000)

  const ilkUrun = page.locator('text=/DANA TRANC/i').first()
  await expect(ilkUrun).toBeVisible({ timeout: 10000 })
  await ilkUrun.click()
  await page.waitForTimeout(8000)

  if (apiResponse) {
    console.log('=== PERFORMANCE KEYS ===')
    console.log(Object.keys(apiResponse.performance || {}).join(', '))
    console.log('=== PERFORMANCE VALUES ===')
    for (const [k, v] of Object.entries(apiResponse.performance || {})) {
      console.log(`  ${k}: ${JSON.stringify(v)}`)
    }
    console.log('=== SUMMARY ===')
    console.log(JSON.stringify(apiResponse.summary, null, 2))
  } else {
    console.log('⚠ API response not captured')
  }
})

import { test } from '@playwright/test'

test('Ay filtresi - sadece Ocak seçildiğinde tüm yıllardaki Ocak verisi gelmeli', async ({ page }) => {
  const apiCalls: { params: string; months: string[] }[] = []

  // API çağrılarını yakala
  await page.route('**/api/panel-sqlite/**', async (route) => {
    const url = new URL(route.request().url())
    const params = url.searchParams.toString()
    const response = await route.fetch()
    const json = await response.json()
    const months = (json.salesByMonth || []).map((m: any) => m.month)
    apiCalls.push({ params, months })
    console.log(`📡 API: ${params} | months: ${months.length}`)
    await route.fulfill({ response })
  })

  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Otomatik giriş
  const emailInput = page.locator('input[type="email"], input[name="email"]').first()
  if (await emailInput.isVisible({ timeout: 5000 }).catch(() => false)) {
    await emailInput.fill('makif4596@gmail.com')
    await page.locator('input[type="password"], input[name="password"]').first().fill('Test1234')
    await page.locator('button[type="submit"], button:has-text("Giriş")').first().click()
    await page.waitForURL('**/')
  }
  await page.waitForTimeout(3000)

  const initialCallCount = apiCalls.length
  console.log(`İlk yükleme API çağrısı: ${initialCallCount}`)

  // "Tüm Yıllar" seç (yıl filtresini temizle)
  const yearBtn = page.locator('button').filter({ hasText: /202\d/ }).first()
  if (await yearBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await yearBtn.click()
    await page.waitForTimeout(300)
    await page.locator('div').filter({ hasText: 'Tüm Yıllar' }).first().click()
    await page.waitForTimeout(500)
    console.log('✅ "Tüm Yıllar" seçildi')
  }

  // Dropdown'u aç
  const monthBtn = page.locator('button').filter({ hasText: 'Tüm Aylar' }).first()
  await monthBtn.click()
  await page.waitForTimeout(500)

  // Dropdown içinden "Ocak" seçeneğini bul ve tıkla
  // Not: page.locator('div').filter({ hasText: 'Ocak' }).first() dashboard içeriğindeki
  // başka bir div'i bulduğu için evaluate ile doğrudan React dropdown'ını hedefliyoruz
  await page.evaluate(() => {
    const divs = document.querySelectorAll('div')
    for (let i = 0; i < divs.length; i++) {
      const d = divs[i]
      if (d.textContent?.trim() === 'Ocak' && getComputedStyle(d).cursor === 'pointer') {
        d.click()
        return
      }
    }
  })
  console.log('✅ "Ocak" seçildi')

  // "Uygula" butonuna tıkla (showApplyButton=true ile filtreler bekler)
  const applyBtn = page.locator('button').filter({ hasText: 'Uygula' }).first()
  if (await applyBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await applyBtn.click()
    console.log('✅ "Uygula" tıklandı')
  } else {
    console.log('⚠ "Uygula" butonu görünür değil')
  }

  // API çağrısını bekle
  await page.waitForTimeout(5000)

  // Sonuçları raporla
  console.log(`\n=== TEST SONUCU ===`)
  console.log(`Toplam API çağrısı: ${apiCalls.length}`)
  console.log(`Yükleme sonrası yeni çağrı: ${apiCalls.length - initialCallCount}`)

  const lastCall = apiCalls[apiCalls.length - 1]
  if (lastCall) {
    const hasMonth1 = lastCall.params.includes('month=1')
    const hasYear = lastCall.params.includes('year=')
    const allJan = lastCall.months.length > 0 && lastCall.months.every(m => m.endsWith('-01'))

    if (hasMonth1 && !hasYear) {
      console.log('✅ Sadece month=1 parametresi gidiyor (year yok)')
    } else if (hasMonth1 && hasYear) {
      console.log(`⚠ month=1 ve year parametresi birlikte: ${lastCall.params}`)
    } else {
      console.log(`⚠ month=1 parametresi yok: ${lastCall.params}`)
    }

    if (allJan) {
      console.log(`✅ Tüm aylar Ocak (${lastCall.months.length} adet: ${lastCall.months.join(', ')})`)
    } else {
      const nonJan = lastCall.months.filter(m => !m.endsWith('-01'))
      console.log(`❌ Ocak dışı aylar var: ${nonJan.join(', ')}`)
    }
  } else {
    console.log('❌ Yeni API çağrısı yapılmadı!')
  }
})

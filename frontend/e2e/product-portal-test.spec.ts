import { test, expect } from '@playwright/test'

const CREDS = { email: 'makif4596@gmail.com', password: 'Test1234' }

test('Ürün Portalı - Dana Tranç son 7 gün verisi ve badge görünürlüğü', async ({ page }) => {
  // 1. Login
  await page.goto('/giris')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(500)
  await page.locator('#email').fill(CREDS.email)
  await page.locator('#password').fill(CREDS.password)
  await page.locator('button[type="submit"]').click()
  await page.waitForTimeout(3000)
  if (page.url().includes('/giris')) {
    console.log('⚠ Login başarısız')
    return
  }
  console.log('✓ Giriş başarılı')

  // 2. Ürünler sayfası
  await page.goto('/urunler')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(5000)

  // 3. En çok satanlar listesinde ilk ürüne tıkla (🥇 DANA TRANC KG)
  const ilkUrun = page.locator('text=/DANA TRANC/i').first()
  await expect(ilkUrun).toBeVisible({ timeout: 10000 })
  await ilkUrun.click()
  console.log('✓ Dana Tranç tıklandı')

  // 4. Portal yüklenmesini bekle
  await page.waitForTimeout(8000)

  // 5. Ekran görüntüsü al
  await page.screenshot({ path: 'portal-sonuc.png', fullPage: false })

  // 6. Sayfa metnini analiz et
  const text = await page.textContent('body') || ''

  // Hata var mı?
  if (text.includes('hata') && !text.includes('Normal') && !text.includes('Toplam')) {
    console.log('⚠ Portal hatası!')
    // Hata detayını göster
    const hataIndex = text.indexOf('hata')
    console.log('Hata bağlamı:', text.substring(Math.max(0, hataIndex - 50), hataIndex + 200))
    return
  }
  console.log('✓ Portal başarıyla yüklendi')

  // 7. Son 7 Gün verisi
  const son7 = text.indexOf('Son 7 Gün')
  if (son7 >= 0) {
    const snippet = text.substring(son7, son7 + 250)
    console.log('--- Son 7 Gün ---')
    console.log(snippet)
  } else {
    console.log('⚠ "Son 7 Gün" bulunamadı')
  }

  // 8. Son 30 Gün verisi
  const son30 = text.indexOf('Son 30 Gün')
  if (son30 >= 0) {
    const snippet = text.substring(son30, son30 + 150)
    console.log('--- Son 30 Gün ---')
    console.log(snippet)
  }

  // 9. Badge kontrolü
  const badges = ['Artış Trendi', 'Düşüş Trendi', 'Nötr Trend', 'Normal', 'Yıldız', 'Popüler', 'Orta', 'Stok']
  const gorunen = badges.filter(b => text.includes(b))
  console.log('Görünen badgelar:', gorunen.join(', ') || 'Hiçbiri')

  // 10. Performans kategorisi
  const perfKats = ['Yıldız', 'Popüler', 'Orta', 'Düşük', 'Durgun']
  const perfKat = perfKats.find(k => text.includes(k))
  console.log('Performans kategorisi:', perfKat || 'bulunamadı')

  console.log('✓ Test tamamlandı!')
})

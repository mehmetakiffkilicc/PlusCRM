import { test, expect } from '@playwright/test';

test.describe('AI Asistan Sorun Giderimi - Temel Kontrol', () => {
  test('Sayfa yüklenebiliyor mu?', async ({ page }) => {
    // Vite dev server'ın çalıştığından emin olun (npm run dev)
    await page.goto('/');
    
    // Login sayfası mı kontrol et
    await expect(page).toHaveURL(/giris|login/);
    console.log('✓ Sayfa başarıyla yüklendi');
  });

  test('Login yapıp dashboard\'a erişim', async ({ page }) => {
    await page.goto('/giris');
    
    // Email ve şifre alanlarını doldur
    await page.fill('input[type="email"], input[name="email"]', 'test@example.com');
    await page.fill('input[type="password"], input[name="password"]', 'testpassword');
    
    // Giriş yap butonuna tıkla
    await page.click('button[type="submit"]');
    
    // Dashboard'a yönlendirildiğini kontrol et (en fazla 10sn bekle)
    await page.waitForURL('/', { timeout: 10000 });
    console.log('✓ Giriş başarılı, dashboard\'a yönlendirildi');
    
    // AI Widget'ının sayfada olduğunu kontrol et
    const aiWidget = page.locator('[class*="chat"], [class*="ChatWidget"], button[aria-label*="sohbet"], button[aria-label*="chat"]').first();
    await expect(aiWidget).toBeVisible({ timeout: 5000 });
    console.log('✓ AI Widget bulundu');
  });
});

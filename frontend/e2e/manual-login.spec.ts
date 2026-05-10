import { test, expect } from '@playwright/test';

test('Manuel Giriş ve AI Testi', async ({ page }) => {
  // Show.xpluscrm.com'a git
  await page.goto('/');
  
  // Sayfanın yüklendiğini bekle
  await page.waitForLoadState('networkidle');
  console.log('✓ Sayfa yüklendi, lütfen giriş yapın...');
  
  // Kullanıcının manuel giriş yapması için bekle (60 saniye)
  await page.waitForTimeout(60000);
  
  // Giriş sonrası dashboard'a yönlendirildiğini kontrol et
  const currentURL = page.url();
  console.log('Mevcut URL:', currentURL);
  
  if (currentURL.includes('/giris') || currentURL.includes('/login')) {
    console.log('⚠ Giriş yapılmadı, test duruyor...');
    return;
  }
  
  console.log('✓ Giriş başarılı!');
  
  // Önce sidebar'ın açık olduğundan emin ol (mobil değilse)
  const viewport = page.viewportSize();
  if (viewport && viewport.width > 1024) {
    console.log('Masaüstü modu: Sidebar tetikleyicisi aranıyor...');
    
    // AI Zeka Asistanı butonunu ara (sidebar'da)
    const aiTrigger = page.locator('[class*="ai-sidebar-trigger"]').first();
    
    try {
      await expect(aiTrigger).toBeVisible({ timeout: 5000 });
      console.log('✓ AI Sidebar tetikleyicisi bulundu');
      
      // ChatWidget'ı aç
      await aiTrigger.click();
      console.log('✓ AI Widget açılıyor...');
      
      // Modal'ın açılmasını bekle
      await page.waitForTimeout(1500);
      
    } catch (e) {
      console.log('⚠ Sidebar tetikleyicisi bulunamadı, alternatif yöntem deneniyor...');
    }
  }
  
  // Chat Modal'ının açık olduğunu kontrol et
  const chatModal = page.locator('[role="dialog"]:has-text("AI Strateji Asistanı"), [class*="ChatWidget"]').first();
  
  try {
    // Chat input'unu ara (Modal içinde)
    const input = page.locator('input[placeholder*="sor"], textarea[placeholder*="sor"], [class*="ChatWidget"] input').first();
    await expect(input).toBeVisible({ timeout: 10000 });
    console.log('✓ Chat input bulundu');
    
    // Test mesajı gönder
    await input.fill('Merhaba, test mesajı');
    await page.keyboard.press('Enter');
    console.log('✓ Test mesajı gönderildi, yanıt bekleniyor...');
    
    // Yanıtı bekle (30 saniye)
    await page.waitForTimeout(30000);
    console.log('✓ Test tamamlandı');
    
  } catch (e) {
    console.log('⚠ Chat input bulunamadı:', e.message);
    // Ekran görüntüsü al
    await page.screenshot({ path: 'login-debug.png', fullPage: true });
    console.log('Ekran görüntüsü: login-debug.png');
    
    // Sayfa HTML'ini kaydet (debug için)
    const html = await page.content();
    require('fs').writeFileSync('page-content.html', html);
    console.log('Sayfa içeriği: page-content.html');
  }
});

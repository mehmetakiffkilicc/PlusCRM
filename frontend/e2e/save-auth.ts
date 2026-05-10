import { chromium } from '@playwright/test';

async function saveAuthState() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('Tarayıcı açıldı. Lütfen giriş yapın...');
  await page.goto('https://show.MarketFlow.com');

  // Kullanıcının giriş yapmasını bekle (dashboard sayfasına yönlendirilene kadar)
  await page.waitForURL('**/dashboard**', { timeout: 300000 });

  console.log('Giriş başarılı! Oturum kaydediliyor...');

  // Auth state'i kaydet
  await context.storageState({ path: 'test-results/auth-state.json' });

  console.log('Oturum kaydedildi: test-results/auth-state.json');
  await browser.close();
}

saveAuthState().catch(console.error);


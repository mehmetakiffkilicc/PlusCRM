import { test, Page, BrowserContext } from '@playwright/test';
import * as fs from 'fs';

const BASE_URL = 'https://show.xpluscrm.com';
const AUTH_STATE_PATH = 'test-results/auth-state.json';

async function openChat(page: Page) {
  // Sağ alttaki FAB butonunu bul (genelde son button)
  const fab = page.locator('button').last();
  await fab.click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1500);

  // Textarea veya input görünene kadar bekle
  await page.waitForSelector('textarea, input[type="text"]', { timeout: 10000 });
}

async function sendCommand(page: Page, command: string) {
  const input = page.locator('textarea, input[type="text"]').first();
  await input.fill(command);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(2000);
}

async function waitForPanel(page: Page) {
  // Panel oluşturuldu mesajını bekle
  await page.waitForSelector('text=/panel.*oluşturuldu|başarılı|tamamlandı/i', { timeout: 60000 });
  await page.waitForTimeout(2000);
}

async function clickViewLink(page: Page) {
  const link = page.locator('text=/görüntüle/i').first();
  await link.click({ timeout: 10000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);
}

test.describe('AI Panel Testleri', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    
    // Login
    await page.goto(BASE_URL + '/login');
    await page.fill('input[name="email"]', 'makif4596@gmail.com');
    await page.fill('input[name="password"]', 'Test1234');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 30000 });
    
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test.afterAll(async () => {
    await page?.close();
    await context?.close();
  });

  test('1. Coğrafi Satış Dağılımı', async () => {
    await openChat(page);
    await sendCommand(page, 'Bana iller bazında satış dağılımını gösteren panel oluştur');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/1-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/1-panel.png' });
  });

  test('2. Sezonsal Trend', async () => {
    await openChat(page);
    await sendCommand(page, 'Son 3 yılın aylık satış trendini gösteren panel yap');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/2-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/2-panel.png' });
  });

  test('3. Ödeme Yöntemi', async () => {
    await openChat(page);
    await sendCommand(page, 'Ödeme yöntemlerine göre satış dağılımını gösteren panel oluştur');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/3-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/3-panel.png' });
  });

  test('4. Müşteri Yaşam Döngüsü', async () => {
    await openChat(page);
    await sendCommand(page, 'Müşteri yaşam döngüsünü gösteren lifecycle panel oluştur');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/4-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/4-panel.png' });
  });

  test('5. Ürün Kar Marjı', async () => {
    await openChat(page);
    await sendCommand(page, 'Kategori bazında kar marjı gösteren panel yap');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/5-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/5-panel.png' });
  });

  test('6. Sepet Analizi', async () => {
    await openChat(page);
    await sendCommand(page, 'Ortalama sepet tutarını gösteren panel oluştur');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/6-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/6-panel.png' });
  });

  test('7. Hane ve Çalışan', async () => {
    await openChat(page);
    await sendCommand(page, 'Hane büyüklüğü ve çalışan sayısına göre analiz paneli oluştur');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/7-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/7-panel.png' });
  });

  test('8. Kampanya Etkililiği', async () => {
    await openChat(page);
    await sendCommand(page, 'Kampanya ROI ve dönüşüm oranlarını gösteren panel yap');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/8-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/8-panel.png' });
  });

  test('9. Envanter Stok', async () => {
    await openChat(page);
    await sendCommand(page, 'Stok devir hızını gösteren envanter paneli oluştur');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/9-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/9-panel.png' });
  });

  test('10. Sadakat Skoru', async () => {
    await openChat(page);
    await sendCommand(page, 'Müşteri sadakat skoru dağılımını gösteren panel oluştur');
    await waitForPanel(page);
    await page.screenshot({ path: 'test-results/10-created.png' });
    await clickViewLink(page);
    await page.screenshot({ path: 'test-results/10-panel.png' });
  });
});

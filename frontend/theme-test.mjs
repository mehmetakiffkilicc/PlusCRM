import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  
  // Collect console errors
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

  // 1. Login
  await page.goto('https://show.MarketFlow.com/giris');
  await page.waitForTimeout(2000);
  await page.fill('input[type="email"], input[name="email"], input[placeholder*="mail"]', 'makif4596@gmail.com');
  await page.fill('input[type="password"], input[name="password"]', 'Test1234');
  await page.click('button[type="submit"], button:has-text("Giriş")');
  await page.waitForTimeout(3000);
  
  // 2. Dashboard - BEFORE theme switch
  await page.goto('https://show.MarketFlow.com/');
  await page.waitForTimeout(3000);
  
  // Get data-theme
  const dataThemeBefore = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  console.log('=== BEFORE ===');
  console.log('data-theme:', dataThemeBefore);
  
  // KPI card styles
  const kpiStyles = await page.evaluate(() => {
    const el = document.querySelector('.kpi-card');
    if (!el) return { error: 'no kpi-card found' };
    const cs = getComputedStyle(el);
    return {
      borderTopColor: cs.borderTopColor,
      borderLeftColor: cs.borderLeftColor,
      borderRadius: cs.borderRadius,
      boxShadow: cs.boxShadow,
      background: cs.background,
      hasBefore: getComputedStyle(el, '::before').content !== 'none',
      borderWidth: cs.borderTopWidth,
    };
  });
  console.log('KPI styles:', JSON.stringify(kpiStyles, null, 2));
  
  // Chart card styles
  const chartStyles = await page.evaluate(() => {
    const el = document.querySelector('.chart-card');
    if (!el) return { error: 'no chart-card found' };
    const cs = getComputedStyle(el);
    return {
      borderTopColor: cs.borderTopColor,
      borderRadius: cs.borderRadius,
      boxShadow: cs.boxShadow,
      hasBefore: getComputedStyle(el, '::before').content !== 'none',
      borderWidth: cs.borderTopWidth,
    };
  });
  console.log('Chart styles:', JSON.stringify(chartStyles, null, 2));
  
  // 3. Go to Settings and switch theme
  await page.goto('https://show.MarketFlow.com/ayarlar');
  await page.waitForTimeout(2000);
  
  // Click MarketCRM theme card
  await page.click('text=MarketCRM');
  await page.waitForTimeout(2000);
  
  // Verify data-theme changed
  const dataThemeAfter = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  console.log('=== AFTER SWITCH ===');
  console.log('data-theme:', dataThemeAfter);
  
  // 4. Back to Dashboard
  await page.goto('https://show.MarketFlow.com/');
  await page.waitForTimeout(3000);
  
  // Get KPI styles again
  const kpiStylesAfter = await page.evaluate(() => {
    const el = document.querySelector('.kpi-card');
    if (!el) return { error: 'no kpi-card found' };
    const cs = getComputedStyle(el);
    return {
      borderTopColor: cs.borderTopColor,
      borderRadius: cs.borderRadius,
      boxShadow: cs.boxShadow,
      background: cs.background,
      hasBefore: getComputedStyle(el, '::before').content !== 'none',
      borderWidth: cs.borderTopWidth,
    };
  });
  console.log('KPI styles after:', JSON.stringify(kpiStylesAfter, null, 2));
  
  // Chart styles after
  const chartStylesAfter = await page.evaluate(() => {
    const el = document.querySelector('.chart-card');
    if (!el) return { error: 'no chart-card found' };
    const cs = getComputedStyle(el);
    return {
      borderTopColor: cs.borderTopColor,
      borderRadius: cs.borderRadius,
      boxShadow: cs.boxShadow,
      hasBefore: getComputedStyle(el, '::before').content !== 'none',
      borderWidth: cs.borderTopWidth,
    };
  });
  console.log('Chart styles after:', JSON.stringify(chartStylesAfter, null, 2));
  
  console.log('=== ERRORS ===');
  console.log(errors);
  
  // Screenshots
  await page.screenshot({ path: 'screenshot-after.png' });
  
  await browser.close();
})();


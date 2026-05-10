import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

  // Login
  await page.goto('https://show.MarketFlow.com/giris');
  await page.waitForTimeout(2000);
  await page.fill('input[type="email"], input[name="email"], input[placeholder*="mail"]', 'makif4596@gmail.com');
  await page.fill('input[type="password"], input[name="password"]', 'Test1234');
  await page.click('button[type="submit"], button:has-text("Giriş")');
  await page.waitForTimeout(3000);

  // Go to Settings
  await page.goto('https://show.MarketFlow.com/ayarlar');
  await page.waitForTimeout(4000);

  // Debug: list theme elements
  const debugInfo = await page.evaluate(() => {
    const themes = document.querySelectorAll('[data-theme-name], [data-theme], .theme-card, .theme-item');
    const results = [];
    themes.forEach((el, i) => {
      results.push({
        index: i,
        tag: el.tagName,
        text: el.textContent?.trim().substring(0, 80),
        visible: el.offsetParent !== null,
        rect: el.getBoundingClientRect(),
        attrs: Array.from(el.attributes).map(a => `${a.name}=${a.value}`),
      });
    });
    return results;
  });
  console.log('Theme elements:', JSON.stringify(debugInfo, null, 2));

  // Also dump all text containing "MarketCRM"
  const marketTexts = await page.evaluate(() => {
    const results = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while (node = walker.nextNode()) {
      if (node.textContent.includes('MarketCRM')) {
        const parent = node.parentElement;
        results.push({
          text: node.textContent.trim(),
          tag: parent?.tagName,
          parentClasses: Array.from(parent?.classList || []),
          parentRect: parent?.getBoundingClientRect(),
          parentVisible: parent?.offsetParent !== null,
        });
      }
    }
    return results;
  });
  console.log('MarketCRM texts:', JSON.stringify(marketTexts, null, 2));

  // Screenshot for analysis
  await page.screenshot({ path: 'settings-debug.png' });

  console.log('=== ERRORS ===');
  console.log(errors);
  
  await browser.close();
})();


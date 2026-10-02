// Снимает сайты из scripts/shots.txt: <ключ>1.jpg (верх, 1400×875), <ключ>2.jpg (ниже по странице), <ключ>-m.jpg (телефон).
const { chromium } = require('playwright');
const fs = require('fs');

const list = fs.readFileSync('scripts/shots.txt', 'utf8').split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#')).map(l => l.split(/\s+/));
fs.mkdirSync('shots-out', { recursive: true });

async function open(browser, url, opts) {
  const page = await browser.newPage(opts);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  // прокрутка, чтобы подгрузились ленивые картинки и анимации появления
  const h = await page.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < Math.min(h, 8000); y += 500) { await page.evaluate(v => window.scrollTo(0, v), y); await page.waitForTimeout(120); }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(2500);
  return page;
}

(async () => {
  const browser = await chromium.launch();
  for (const [key, url] of list) {
    const d = await open(browser, url, { viewport: { width: 1400, height: 875 } });
    await d.screenshot({ path: `shots-out/${key}1.jpg`, quality: 90 });
    await d.evaluate(() => window.scrollTo(0, Math.min(window.innerHeight * 1.1, document.body.scrollHeight - window.innerHeight)));
    await d.waitForTimeout(1500);
    await d.screenshot({ path: `shots-out/${key}2.jpg`, quality: 90 });
    await d.close();
    const m = await open(browser, url, { viewport: { width: 350, height: 758 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    await m.screenshot({ path: `shots-out/${key}-m.jpg`, quality: 90 });
    await m.close();
    console.log('готово', key, url);
  }
  await browser.close();
})();

// Картинки превью ссылок (Telegram, Facebook, WhatsApp): site/assets/img/og-{hy,ru,en}.png, 1200×630.
// Запуск: node scripts/og_images.cjs  (нужен Playwright с Chromium). Тексты ниже, по одному набору на язык.
const path = require('path');
let pw; try { pw = require('playwright'); } catch (e) { pw = require('/opt/node22/lib/node_modules/playwright'); }
const SITE = path.resolve(__dirname, '../site');
const T = {
  hy: { title: 'Կայքեր և համակարգեր բիզնեսի համար', sub: 'Ռեստորաններ · Հյուրանոցներ · Խանութներ', price: '150 000 ֏-ից', langs: 'Հայ · Рус · Eng' },
  ru: { title: 'Сайты и системы для бизнеса в Армении', sub: 'Рестораны · Отели · Магазины', price: 'от 150 000 ֏', langs: 'Հայ · Рус · Eng' },
  en: { title: 'Websites and systems for business in Armenia', sub: 'Restaurants · Hotels · Shops', price: 'from 150,000 ֏', langs: 'Հայ · Рус · Eng' },
};
const LOGO = '<svg viewBox="0 0 40 40"><path d="M14.5 11.5 15.6 5.8l3 3.2L20 5l1.4 4 3-3.2 1.1 5.7Z" fill="#8f2a2e"/><circle cx="20" cy="23" r="13" fill="#b8373a"/><path d="M15.2 19 11.4 23l3.8 4M24.8 19l3.8 4-3.8 4M21.6 18.2l-3.2 9.6" fill="none" stroke="#fff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const TG = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.9 4.3 18.8 19c-.2 1-.9 1.3-1.7.8l-4.6-3.4-2.2 2.1c-.3.3-.5.5-1 .5l.3-4.7 8.6-7.8c.4-.3-.1-.5-.6-.2L6.9 13 2.4 11.6c-1-.3-1-1 .2-1.5L20.5 3.2c.8-.3 1.6.2 1.4 1.1Z"/></svg>';
const page = (t, lang) => `<!doctype html><html lang="${lang}"><head><meta charset="utf-8">
<link rel="stylesheet" href="assets/fonts/fonts.css"><style>
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;overflow:hidden;background:radial-gradient(circle at 85% 20%,#24403d 0,#14201f 55%);color:#fff;font-family:"Noto Sans","Noto Sans Armenian",sans-serif;position:relative}
.l{position:absolute;left:72px;top:64px;width:560px;height:502px;display:flex;flex-direction:column}
.logo{display:flex;align-items:center;gap:16px;font:700 54px "Noto Serif","Noto Serif Armenian",serif}.logo svg{width:72px;height:72px}.logo b{color:#e0575a}
h1{font:700 ${lang === 'ru' ? 52 : 48}px/1.12 "Noto Serif","Noto Serif Armenian",serif;margin-top:40px}
.sub{font-size:${lang === "hy" ? 24 : 27}px;color:#aebbba;margin-top:18px}
.row{margin-top:auto;display:flex;gap:12px;align-items:center}
.chip{border-radius:99px;padding:10px 20px;font-size:24px;font-weight:600}
.price{background:#c9964f;color:#14201f}.lang{border:2px solid #3a5754;color:#dfe7e6}
.tg{position:absolute;left:72px;bottom:28px;display:none}
.shot{position:absolute;left:680px;top:70px;width:640px;border-radius:16px;box-shadow:0 30px 80px rgba(0,0,0,.5);transform:rotate(-4deg)}
.ph{position:absolute;left:640px;top:330px;width:190px;border-radius:20px;border:4px solid #fff;box-shadow:0 20px 50px rgba(0,0,0,.5);transform:rotate(-4deg)}
.site{position:absolute;right:48px;bottom:34px;display:flex;align-items:center;gap:10px;background:#2aa3df;border-radius:99px;padding:10px 20px 10px 14px;font-size:24px;font-weight:600}.site svg{width:26px;height:26px}
</style></head><body>
<div class="l"><div class="logo">${LOGO}<span>Evn<b>Web</b></span></div><h1>${t.title}</h1><div class="sub">${t.sub}</div>
<div class="row"><span class="chip price">${t.price}</span><span class="chip lang">${t.langs}</span></div></div>
<img class="shot" src="assets/img/hotel-1.webp"><img class="ph" src="assets/img/restaurant-4-t.webp">
<div class="site">${TG}evnweb.am</div></body></html>`;
(async () => {
  const fs = require('fs');
  const b = await pw.chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  for (const [lang, t] of Object.entries(T)) {
    const tmp = path.join(SITE, `_og-${lang}.html`);
    fs.writeFileSync(tmp, page(t, lang));
    await p.goto('file://' + tmp); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(SITE, `assets/img/og-${lang}.png`) });
    fs.unlinkSync(tmp); console.log('og-' + lang + '.png');
  }
  await b.close();
})();

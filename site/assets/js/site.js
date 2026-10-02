// Карусель проектов: копия карточек в конце ленты, чтобы она крутилась бесконечно (до привязки лайтбокса — клики работают и у копий)
(function () {
  var track = document.querySelector('.projects');
  if (!track) return;
  Array.prototype.slice.call(track.children).forEach(function (c) {
    var k = c.cloneNode(true);
    k.setAttribute('aria-hidden', 'true'); k.classList.add('pj--clone');
    k.querySelectorAll('a,button').forEach(function (el) { el.setAttribute('tabindex', '-1'); });
    track.appendChild(k);
  });
})();
(function () {
  var lb = document.getElementById('lb'), img = lb.querySelector('img'), cap = lb.querySelector('figcaption');
  var list = [], idx = 0;
  function show(i) {
    idx = (i + list.length) % list.length;
    img.src = list[idx].dataset.full; img.alt = list[idx].dataset.cap; cap.textContent = list[idx].dataset.cap;
  }
  document.querySelectorAll('[data-g]').forEach(function (g) {
    var btns = Array.prototype.slice.call(g.querySelectorAll('button'));
    btns.forEach(function (b, i) {
      b.addEventListener('click', function () { list = btns; show(i); lb.classList.add('open'); document.body.style.overflow = 'hidden'; });
    });
  });
  function close() { lb.classList.remove('open'); document.body.style.overflow = ''; }
  lb.querySelector('.x').onclick = close;
  lb.querySelector('.pv').onclick = function (e) { e.stopPropagation(); show(idx - 1); };
  lb.querySelector('.nx').onclick = function (e) { e.stopPropagation(); show(idx + 1); };
  lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
  document.addEventListener('keydown', function (e) {
    if (!lb.classList.contains('open')) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') show(idx - 1);
    if (e.key === 'ArrowRight') show(idx + 1);
  });
  // Цели Метрики: клик по способу связи (telegram, whatsapp, viber, phone, email)
  const goals = [['t.me/', 'telegram'], ['wa.me/', 'whatsapp'], ['viber:', 'viber'], ['tel:', 'phone'], ['mailto:', 'email']];
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a || typeof window.ym !== 'function') return;
    const g = goals.find(([part]) => a.getAttribute('href').includes(part));
    if (g) window.ym(113109354, 'reachGoal', g[1]);
  });
  // Запоминаем выбранный язык: с главной армянской страницы человек потом сразу попадает на свой язык
  document.querySelectorAll('.lang a').forEach(function (a) {
    a.addEventListener('click', function () { try { localStorage.setItem('lang', a.dataset.lang); } catch (e) {} });
  });
  document.getElementById('y').textContent = new Date().getFullYear();
})();
// Карусель проектов: едет сама по кругу, стоит при наведении, касании и открытом лайтбоксе; стрелки и палец тоже листают
(function () {
  var track = document.querySelector('.projects'), lb = document.getElementById('lb');
  if (!track) return;
  var cards = track.children, n = cards.length / 2, pos = 0, last = 0, hold = 0, hover = false, SPEED = 45;
  var still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function half() { return cards[n].offsetLeft - cards[0].offsetLeft; }
  function step() { return cards[1].offsetLeft - cards[0].offsetLeft; }
  function wrap() {
    var h = half(), x = track.scrollLeft;
    if (x >= h) x -= h; else if (x < 1) x += h; else return;
    track.scrollLeft = x;
  }
  function pause(ms) { hold = Math.max(hold, performance.now() + ms); }
  function tick(t) {
    var dt = Math.min(64, t - (last || t)); last = t;
    if (!still && !hover && t > hold && !(lb && lb.classList.contains('open'))) {
      if (Math.abs(track.scrollLeft - pos) > 2) pos = track.scrollLeft;
      pos += SPEED * dt / 1000;
      var h = half(); if (pos >= h) pos -= h;
      track.scrollLeft = pos;
    } else pos = track.scrollLeft;
    requestAnimationFrame(tick);
  }
  track.addEventListener('mouseenter', function () { hover = true; });
  track.addEventListener('mouseleave', function () { hover = false; });
  track.addEventListener('touchstart', function () { pause(4000); }, { passive: true });
  track.addEventListener('touchend', function () { pause(2500); }, { passive: true });
  track.addEventListener('focusin', function () { pause(6000); });
  var t; track.addEventListener('scroll', function () { clearTimeout(t); t = setTimeout(function () { if (performance.now() < hold || hover) wrap(); pos = track.scrollLeft; }, 120); });
  document.querySelectorAll('.carousel-nav__btn').forEach(function (b) {
    b.addEventListener('click', function () {
      pause(3500);
      if (+b.dataset.dir < 0 && track.scrollLeft < step()) track.scrollLeft += half();
      track.scrollBy({ left: step() * +b.dataset.dir, behavior: 'smooth' });
    });
  });
  track.scrollLeft = 1; pos = 1;
  requestAnimationFrame(tick);
})();
// Первый экран: три сцены сменяют друг друга; на узком экране сцена уменьшается под ширину
(function () {
  var stage = document.querySelector('.stage');
  if (!stage) return;
  var scenes = stage.querySelectorAll('.scene'), dots = stage.querySelectorAll('.scenes__dots button'), i = 0, timer;
  function fit() { stage.style.setProperty('--k', Math.min(1, stage.clientWidth / 600)); }
  function show(n) {
    i = (n + scenes.length) % scenes.length;
    scenes.forEach(function (s, k) { s.classList.toggle('on', k === i); });
    dots.forEach(function (d, k) { d.classList.toggle('on', k === i); });
  }
  function play() {
    clearInterval(timer);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    timer = setInterval(function () { if (!document.hidden) show(i + 1); }, 5500);
  }
  dots.forEach(function (d, k) { d.addEventListener('click', function () { show(k); play(); }); });
  stage.addEventListener('mouseenter', function () { clearInterval(timer); });
  stage.addEventListener('mouseleave', play);
  window.addEventListener('resize', fit);
  fit(); play();
})();

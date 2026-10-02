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
// Карусель проектов: стрелки и точки, на телефоне листается пальцем (CSS scroll-snap)
(function () {
  var nav = document.querySelector('.carousel-nav'), track = document.querySelector('.projects');
  if (!nav || !track) return;
  var cards = track.children, dotsBox = nav.querySelector('.carousel-nav__dots'), btns = nav.querySelectorAll('.carousel-nav__btn');
  function step() { return cards.length > 1 ? cards[1].offsetLeft - cards[0].offsetLeft : track.clientWidth; }
  function pages() { return Math.max(1, Math.round((track.scrollWidth - track.clientWidth) / step()) + 1); }
  function current() { return Math.round(track.scrollLeft / step()); }
  function build() {
    dotsBox.innerHTML = '';
    for (var i = 0; i < pages(); i++) {
      var d = document.createElement('button'); d.type = 'button'; d.setAttribute('aria-label', String(i + 1));
      d.addEventListener('click', (function (n) { return function () { track.scrollTo({ left: n * step() }); }; })(i));
      dotsBox.appendChild(d);
    }
    update();
  }
  function update() {
    var c = current(), n = pages();
    Array.prototype.forEach.call(dotsBox.children, function (d, i) { d.classList.toggle('on', i === Math.min(c, n - 1)); });
    btns[0].disabled = track.scrollLeft < 4;
    btns[1].disabled = track.scrollLeft > track.scrollWidth - track.clientWidth - 4;
  }
  btns.forEach(function (b) { b.addEventListener('click', function () { track.scrollBy({ left: step() * +b.dataset.dir }); }); });
  var t; track.addEventListener('scroll', function () { clearTimeout(t); t = setTimeout(update, 60); });
  window.addEventListener('resize', build);
  build();
})();

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

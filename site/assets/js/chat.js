// Live chat EVNWEB: сообщения уходят Азату в Telegram через бота на Cloudflare (bot/worker.js),
// его ответы (reply в Telegram) приходят в окно сразу по WebSocket, опрос остаётся запасным путём.
// История хранится у бота, id разговора в localStorage.
(function () {
  var API = 'https://evnweb-bot.vip-azatazat.workers.dev/chat/';
  var WS = API.replace('https://', 'wss://') + 'ws?sid=';
  var AV_BOT = '/assets/img/logo-180.png', AV_AZAT = '/assets/img/azat.webp';
  var lang = (document.documentElement.lang || 'hy').slice(0, 2);
  var T = {
    hy: { title: 'Գրեք Ազատին', hi: 'Բարև Ձեզ։ Ես Ազատն եմ, EVNWEB։ Գրեք ձեր հարցը, կպատասխանեմ այստեղ աշխատանքային օրվա ընթացքում։ Կարող եք թողնել նաև հեռախոսահամար կամ Telegram։', ph: 'Ձեր հաղորդագրությունը…', send: 'Ուղարկել', open: 'Չատ', err: 'Չհաջողվեց ուղարկել, փորձեք նորից', slow: 'Մի քիչ սպասեք և ուղարկեք նորից', tg: 'Կամ գրեք Telegram-ով', name: 'Ազատ', on: 'առցանց', sub: 'EVNWEB', nw: 'Նոր հաղորդագրություն' },
    ru: { title: 'Написать Азату', hi: 'Здравствуйте! Я Азат, EVNWEB. Напишите ваш вопрос, отвечу здесь в течение рабочего дня. Можно оставить телефон или Telegram.', ph: 'Ваше сообщение…', send: 'Отправить', open: 'Чат', err: 'Не удалось отправить, попробуйте ещё раз', slow: 'Подождите немного и отправьте снова', tg: 'Или напишите в Telegram', name: 'Азат', on: 'онлайн', sub: 'EVNWEB', nw: 'Новое сообщение' },
    en: { title: 'Message Azat', hi: 'Hi! I’m Azat from EVNWEB. Type your question and I’ll reply here during the working day. You can also leave your phone or Telegram.', ph: 'Your message…', send: 'Send', open: 'Chat', err: 'Couldn’t send, please try again', slow: 'Please wait a moment and send again', tg: 'Or message me on Telegram', name: 'Azat', on: 'online', sub: 'EVNWEB', nw: 'New message' },
  }[lang] || null;
  if (!T) return;

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  var sid = store('evn_chat_sid');
  var seen = Number(store('evn_chat_seen')) || 0;
  var n = 0, msgs = [], timer = null, lastActive = Date.now(), open = false, ws = null, wsTry = 0;
  var ready = false, baseTitle = document.title, blink = null, audio = null;

  var css = '.evc-btn{position:fixed;right:18px;bottom:18px;z-index:31;height:56px;padding:0 20px 0 16px;border-radius:28px;border:0;background:var(--accent,#1f5f5b);color:#fff;font:600 1rem var(--sans,system-ui);display:flex;align-items:center;gap:8px;box-shadow:0 10px 30px rgba(0,0,0,.2);cursor:pointer}' +
    '.evc-btn svg{width:24px;height:24px}.evc-live{position:absolute;left:30px;bottom:12px;width:12px;height:12px;border-radius:50%;background:#2ecc71;border:2px solid var(--accent,#1f5f5b);display:none}.evc-btn.live .evc-live{display:block}.evc-dot{position:absolute;top:6px;right:8px;width:12px;height:12px;border-radius:50%;background:#e0575a;border:2px solid #fff;display:none}' +
    '.fab{bottom:86px !important}' +
    '.evc{position:fixed;right:18px;bottom:86px;z-index:40;width:min(360px,calc(100vw - 32px));height:min(520px,calc(100vh - 120px));background:#fff;border-radius:18px;box-shadow:0 20px 60px rgba(0,0,0,.25);display:none;flex-direction:column;overflow:hidden;font:15px/1.45 var(--sans,system-ui);color:#1b2124}' +
    '.evc.open{display:flex}.evc-h{background:var(--accent,#1f5f5b);color:#fff;padding:12px 16px;display:flex;align-items:center;gap:10px}.evc-t{flex:1;display:flex;flex-direction:column;line-height:1.25}.evc-t b{font-size:1.02rem}.evc-t small{opacity:.8;font-size:.8rem}' +
    '.evc-av{position:relative;width:40px;height:40px;flex:none}.evc-av img{width:40px;height:40px;border-radius:50%;object-fit:cover;background:#fff;display:block}.evc-on{position:absolute;right:0;bottom:0;width:12px;height:12px;border-radius:50%;background:#2ecc71;border:2px solid var(--accent,#1f5f5b);display:none}.evc.live .evc-on{display:block}.evc-h button{background:none;border:0;color:#fff;font-size:1.5rem;line-height:1;cursor:pointer;padding:0 4px}' +
    '.evc-l{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:#f6f4ef}' +
    '.evc-m{max-width:85%;padding:9px 12px;border-radius:14px;white-space:pre-wrap;word-wrap:break-word}.evc-a{background:#fff;align-self:flex-start;border-bottom-left-radius:4px}.evc-v{background:var(--accent,#1f5f5b);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}' +
    '.evc-e{font-size:.85rem;color:#b8373a;text-align:center}.evc-tg{font-size:.85rem;text-align:center;padding:6px 0 0}.evc-tg a{color:var(--accent,#1f5f5b)}' +
    '.evc-f{display:flex;gap:8px;padding:10px;border-top:1px solid #e4dfd5}.evc-f textarea{flex:1;resize:none;border:1px solid #e4dfd5;border-radius:12px;padding:9px 11px;font:inherit;height:44px;max-height:120px}.evc-f button{border:0;border-radius:12px;background:var(--accent,#1f5f5b);color:#fff;font:600 .95rem var(--sans,system-ui);padding:0 14px;cursor:pointer}.evc-f button:disabled{opacity:.5}' +
    // На телефоне окно на весь экран; шрифт поля 16px, иначе iPhone увеличивает страницу при вводе и окно «уезжает»
    '@media (max-width:520px){.evc{left:8px;right:8px;top:8px;bottom:auto;width:auto;height:calc(100vh - 16px);height:calc(100dvh - 16px);border-radius:14px}' +
    '.evc-f textarea{font-size:16px}.evc-btn span{display:none}.evc-btn{padding:0 16px}.evc-open .evc-btn,.evc-open .fab{display:none}}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  var btn = document.createElement('button');
  btn.className = 'evc-btn'; btn.type = 'button'; btn.setAttribute('aria-label', T.title);
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/></svg><span>' + T.open + '</span><i class="evc-dot"></i><i class="evc-live"></i>';
  var box = document.createElement('div');
  box.className = 'evc'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', T.title);
  box.innerHTML = '<div class="evc-h"><div class="evc-av"><img alt="" width="40" height="40"><i class="evc-on"></i></div><div class="evc-t"><b></b><small></small></div><button type="button" aria-label="×">×</button></div><div class="evc-l"></div>' +
    '<form class="evc-f"><textarea rows="1" maxlength="1500"></textarea><button type="submit"></button></form>';
  var avImg = box.querySelector('.evc-av img'), hTitle = box.querySelector('.evc-t b'), hSub = box.querySelector('.evc-t small');
  var list = box.querySelector('.evc-l'), form = box.querySelector('form'), ta = box.querySelector('textarea'), sendBtn = form.querySelector('button');
  ta.placeholder = T.ph; sendBtn.textContent = T.send;
  document.body.appendChild(box); document.body.appendChild(btn);

  function bubble(text, who, cls) {
    var d = document.createElement('div'); d.className = cls || ('evc-m evc-' + who); d.textContent = text; list.appendChild(d);
    list.scrollTop = list.scrollHeight; return d;
  }
  // Пока Азат не ответил, в шапке аватар бота; после его первого ответа его фото и зелёная точка «онлайн»
  function header() {
    var live = msgs.some(function (m) { return m.f === 'a'; });
    box.classList.toggle('live', live); btn.classList.toggle('live', live);
    var src = live ? AV_AZAT : AV_BOT;
    if (avImg.getAttribute('src') !== src) avImg.src = src;
    hTitle.textContent = live ? T.name : T.title;
    hSub.textContent = live ? T.on : T.sub;
  }
  function render() {
    header();
    list.innerHTML = '';
    bubble(T.hi, 'a');
    msgs.forEach(function (m) { bubble(m.t, m.f === 'v' ? 'v' : 'a'); });
    var tg = document.createElement('div'); tg.className = 'evc-tg';
    tg.innerHTML = '<a href="https://t.me/+37493401179" target="_blank" rel="noopener"></a>'; tg.firstChild.textContent = T.tg;
    list.appendChild(tg); list.scrollTop = list.scrollHeight;
  }
  function dot() {
    var unread = msgs.filter(function (m) { return m.f === 'a'; }).length > seen && !open;
    btn.querySelector('.evc-dot').style.display = unread ? 'block' : 'none';
  }
  function markSeen() { seen = msgs.filter(function (m) { return m.f === 'a'; }).length; store('evn_chat_seen', String(seen)); dot(); }

  // Новый ответ Азата: короткий звук и мигающий заголовок вкладки, пока посетитель не посмотрит
  function beep() {
    try {
      var C = window.AudioContext || window.webkitAudioContext; if (!C) return;
      audio = audio || new C(); if (audio.state === 'suspended') audio.resume();
      [[880, 0], [1320, 0.12]].forEach(function (f) {
        var o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime + f[1];
        o.type = 'sine'; o.frequency.value = f[0]; o.connect(g); g.connect(audio.destination);
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.25, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.25);
        o.start(t); o.stop(t + 0.3);
      });
    } catch (e) {}
  }
  function stopBlink() { if (blink) { clearInterval(blink); blink = null; document.title = baseTitle; } }
  function startBlink() {
    if (blink) return; var on = false;
    blink = setInterval(function () { on = !on; document.title = on ? '💬 ' + T.nw : baseTitle; }, 1000);
  }
  function notify(fresh) {
    if (!fresh.length) return;
    beep();
    if (document.hidden || !open) startBlink();
  }
  // AudioContext разрешён только после действия посетителя: готовим его при первом клике или вводе
  ['click', 'keydown', 'touchstart'].forEach(function (ev) {
    document.addEventListener(ev, function () { try { var C = window.AudioContext || window.webkitAudioContext; if (C && !audio) audio = new C(); if (audio && audio.state === 'suspended') audio.resume(); } catch (e) {} }, { once: true, passive: true });
  });
  window.addEventListener('focus', function () { if (open) stopBlink(); });

  function add(j) {
    if (j.msgs && j.msgs.length && j.n > n && j.n - n <= j.msgs.length) {
      var got = j.msgs.slice(j.msgs.length - (j.n - n));
      msgs = msgs.concat(got); n = j.n;
      render(); if (open) markSeen(); else dot(); lastActive = Date.now();
      if (ready) notify(got.filter(function (m) { return m.f === 'a'; }));
    } else if (j.n > n) poll();   // что-то пропустили, пока не было связи
  }
  function poll() {
    if (!sid) return;
    // первый ответ после загрузки страницы — это история, по ней не звеним
    fetch(API + 'poll?sid=' + sid + '&after=' + n).then(function (r) { return r.json(); }).then(add).catch(function () {}).then(function () { ready = true; schedule(); });
  }
  function schedule() {
    clearTimeout(timer);
    if (!sid) return;
    var idle = Date.now() - lastActive;
    if (idle > 30 * 60 * 1000) { if (ws) ws.close(); return; }   // полчаса тишины: перестаём спрашивать
    connect();
    // при живом WebSocket опрос редкий, только на всякий случай
    var live = ws && ws.readyState === 1;
    timer = setTimeout(poll, live ? 60000 : open ? (idle > 5 * 60 * 1000 ? 12000 : 4000) : 20000);
  }
  function connect() {
    if (!sid || !window.WebSocket || (ws && ws.readyState < 2)) return;
    try { ws = new WebSocket(WS + sid); } catch (e) { ws = null; return; }
    ws.onopen = function () { wsTry = 0; };
    ws.onmessage = function (e) { try { add(JSON.parse(e.data)); } catch (x) {} };
    ws.onclose = function () {
      ws = null;
      if (Date.now() - lastActive < 30 * 60 * 1000) setTimeout(connect, Math.min(60000, 2000 * Math.pow(2, wsTry++)));
    };
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden && open) stopBlink(); if (!document.hidden && sid) { lastActive = Date.now(); poll(); } });

  var phone = window.matchMedia('(max-width:520px)');
  // Когда на телефоне открыта клавиатура, окно подстраивается под видимую часть экрана
  function fit() {
    var vv = window.visualViewport;
    if (!open || !phone.matches || !vv) { box.style.top = box.style.height = ''; return; }
    box.style.top = (vv.offsetTop + 8) + 'px'; box.style.height = (vv.height - 16) + 'px';
    list.scrollTop = list.scrollHeight;
  }
  if (window.visualViewport) { visualViewport.addEventListener('resize', fit); visualViewport.addEventListener('scroll', fit); }

  function toggle(v) {
    open = v; box.classList.toggle('open', v);
    document.documentElement.classList.toggle('evc-open', v);
    document.body.style.overflow = v && phone.matches ? 'hidden' : '';
    fit();
    if (v) { stopBlink(); render(); markSeen(); lastActive = Date.now(); poll(); if (!phone.matches) setTimeout(function () { ta.focus(); }, 50); }
  }
  btn.addEventListener('click', function () { toggle(!open); });
  box.querySelector('.evc-h button').addEventListener('click', function () { toggle(false); });
  ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit')); } });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var text = ta.value.trim(); if (!text) return;
    if (!sid) { sid = ''; var a = new Uint8Array(12); (window.crypto || window.msCrypto).getRandomValues(a); for (var i = 0; i < a.length; i++) sid += ('0' + a[i].toString(16)).slice(-2); store('evn_chat_sid', sid); }
    sendBtn.disabled = true;
    fetch(API + 'send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sid: sid, text: text, page: location.pathname }) })
      .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
      .then(function (r) {
        if (r.s !== 200) throw r.s;
        ta.value = ''; if (n < r.j.n) { msgs.push({ f: 'v', t: text }); n = r.j.n; } render(); lastActive = Date.now(); schedule();
        if (window.ym) try { ym(113109354, 'reachGoal', 'chat'); } catch (x) {}
      })
      .catch(function (s) { bubble(s === 429 ? T.slow : T.err, '', 'evc-e'); })
      .then(function () { sendBtn.disabled = false; });
  });

  // вернувшийся посетитель: подтянуть историю и новые ответы
  header();
  if (sid) poll(); else ready = true;
})();

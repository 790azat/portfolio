// Live chat EVNWEB: сообщения уходят Азату в Telegram через бота на Cloudflare (bot/worker.js),
// его ответы (reply в Telegram) окно забирает опросом. История хранится у бота, id разговора в localStorage.
(function () {
  var API = 'https://evnweb-bot.vip-azatazat.workers.dev/chat/';
  var lang = (document.documentElement.lang || 'hy').slice(0, 2);
  var T = {
    hy: { title: 'Գրեք Ազատին', hi: 'Բարև Ձեզ։ Ես Ազատն եմ, EVNWEB։ Գրեք ձեր հարցը, կպատասխանեմ այստեղ աշխատանքային օրվա ընթացքում։ Կարող եք թողնել նաև հեռախոսահամար կամ Telegram։', ph: 'Ձեր հաղորդագրությունը…', send: 'Ուղարկել', open: 'Չատ', err: 'Չհաջողվեց ուղարկել, փորձեք նորից', slow: 'Մի քիչ սպասեք և ուղարկեք նորից', tg: 'Կամ գրեք Telegram-ով' },
    ru: { title: 'Написать Азату', hi: 'Здравствуйте! Я Азат, EVNWEB. Напишите ваш вопрос, отвечу здесь в течение рабочего дня. Можно оставить телефон или Telegram.', ph: 'Ваше сообщение…', send: 'Отправить', open: 'Чат', err: 'Не удалось отправить, попробуйте ещё раз', slow: 'Подождите немного и отправьте снова', tg: 'Или напишите в Telegram' },
    en: { title: 'Message Azat', hi: 'Hi! I’m Azat from EVNWEB. Type your question and I’ll reply here during the working day. You can also leave your phone or Telegram.', ph: 'Your message…', send: 'Send', open: 'Chat', err: 'Couldn’t send, please try again', slow: 'Please wait a moment and send again', tg: 'Or message me on Telegram' },
  }[lang] || null;
  if (!T) return;

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  var sid = store('evn_chat_sid');
  var seen = Number(store('evn_chat_seen')) || 0;
  var n = 0, msgs = [], timer = null, lastActive = Date.now(), open = false;

  var css = '.evc-btn{position:fixed;right:18px;bottom:18px;z-index:31;height:56px;padding:0 20px 0 16px;border-radius:28px;border:0;background:var(--accent,#1f5f5b);color:#fff;font:600 1rem var(--sans,system-ui);display:flex;align-items:center;gap:8px;box-shadow:0 10px 30px rgba(0,0,0,.2);cursor:pointer}' +
    '.evc-btn svg{width:24px;height:24px}.evc-dot{position:absolute;top:6px;right:8px;width:12px;height:12px;border-radius:50%;background:#e0575a;border:2px solid #fff;display:none}' +
    '.fab{bottom:86px !important}' +
    '.evc{position:fixed;right:18px;bottom:86px;z-index:40;width:min(360px,calc(100vw - 32px));height:min(520px,calc(100vh - 120px));background:#fff;border-radius:18px;box-shadow:0 20px 60px rgba(0,0,0,.25);display:none;flex-direction:column;overflow:hidden;font:15px/1.45 var(--sans,system-ui);color:#1b2124}' +
    '.evc.open{display:flex}.evc-h{background:var(--accent,#1f5f5b);color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px}.evc-h b{flex:1;font-size:1.02rem}.evc-h button{background:none;border:0;color:#fff;font-size:1.5rem;line-height:1;cursor:pointer;padding:0 4px}' +
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
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/></svg><span>' + T.open + '</span><i class="evc-dot"></i>';
  var box = document.createElement('div');
  box.className = 'evc'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', T.title);
  box.innerHTML = '<div class="evc-h"><b></b><button type="button" aria-label="×">×</button></div><div class="evc-l"></div>' +
    '<form class="evc-f"><textarea rows="1" maxlength="1500"></textarea><button type="submit"></button></form>';
  box.querySelector('b').textContent = T.title;
  var list = box.querySelector('.evc-l'), form = box.querySelector('form'), ta = box.querySelector('textarea'), sendBtn = form.querySelector('button');
  ta.placeholder = T.ph; sendBtn.textContent = T.send;
  document.body.appendChild(box); document.body.appendChild(btn);

  function bubble(text, who, cls) {
    var d = document.createElement('div'); d.className = cls || ('evc-m evc-' + who); d.textContent = text; list.appendChild(d);
    list.scrollTop = list.scrollHeight; return d;
  }
  function render() {
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

  function poll() {
    if (!sid) return;
    fetch(API + 'poll?sid=' + sid + '&after=' + n).then(function (r) { return r.json(); }).then(function (j) {
      if (j.msgs && j.msgs.length && j.n > n) { msgs = msgs.concat(j.msgs); n = j.n; render(); if (open) markSeen(); else dot(); lastActive = Date.now(); }
    }).catch(function () {}).then(schedule);
  }
  function schedule() {
    clearTimeout(timer);
    if (!sid) return;
    var idle = Date.now() - lastActive;
    if (idle > 30 * 60 * 1000) return;                 // полчаса тишины: перестаём спрашивать
    timer = setTimeout(poll, open ? (idle > 5 * 60 * 1000 ? 12000 : 4000) : 20000);
  }

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
    if (v) { render(); markSeen(); lastActive = Date.now(); poll(); if (!phone.matches) setTimeout(function () { ta.focus(); }, 50); }
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
        ta.value = ''; msgs.push({ f: 'v', t: text }); n = r.j.n; render(); lastActive = Date.now(); schedule();
        if (window.ym) try { ym(113109354, 'reachGoal', 'chat'); } catch (x) {}
      })
      .catch(function (s) { bubble(s === 429 ? T.slow : T.err, '', 'evc-e'); })
      .then(function () { sendBtn.disabled = false; });
  });

  // вернувшийся посетитель: подтянуть историю и новые ответы
  if (sid) poll();
})();

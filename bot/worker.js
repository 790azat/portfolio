// Telegram-бот EVNWEB на Cloudflare Workers (хостинг SmartApe не пропускает Telegram).
// Отвечает тем, кто написал сам: меню ниш, пример (видео/фото), заявка с номером, всё пересылается Азату.
// Ответ Азата (reply на пересланное) уходит клиенту. Получатель заявок: кто отправит /admin и свой номер ADMIN_PHONE.
// Переменные окружения: TG_TOKEN (секрет), TG_SECRET (секрет заголовка webhook), KV-привязка BOT, Durable Object CHAT (ChatRoom).
// Выкладка: .github/workflows/bot.yml

const PHONE = '+374 93 40-11-79';
const TG_LINK = 'https://t.me/+37493401179';
const ADMIN_PHONE = '37493401179';
const MEDIA = 'https://raw.githubusercontent.com/790azat/portfolio/main/site';

const NICHES = {
  restoran: ['🍽 Ռեստորան / Ресторан, кафе', 'm/2026-10-nedelya-1/06-reel-restoran/reel.mp4', null,
    'Ռեստորանի կայք՝ մենյու լուսանկարներով 3 լեզվով, սեղանի ամրագրում, ադմին, որտեղ գները փոխում եք ինքներդ։ 280 000 ֏-ից։\n\nСайт ресторана: меню с фото на 3 языках, бронь столов, админка, где цены меняете сами. От 280 000 ֏.'],
  otel: ['🏨 Հյուրանոց / Отель, гостевой дом', 'm/2026-10-nedelya-1/07-reel-otel/reel.mp4', 'docs/predlozhenie-otel.pdf',
    'Հյուրանոցի կայք՝ ուղիղ ամրագրում առանց Booking-ի միջնորդավճարի, զբաղվածության օրացույց, ադմին։ 450 000 ֏-ից։\n\nСайт отеля: прямая бронь без комиссии Booking, календарь занятости, админка. От 450 000 ֏.'],
  magazin: ['🛒 Խանութ / Магазин', null, 'docs/predlozhenie-supermarket.pdf',
    'Առցանց խանութ՝ 400 000 ֏-ից, մնացորդների և ժամկետների հաշվառում՝ 650 000 ֏-ից։\n\nОнлайн-магазин от 400 000 ֏, учёт остатков и сроков годности от 650 000 ֏.'],
  salon: ['💇 Սրահ / Салон, барбершоп', 'm/2026-10-segmenty/01-karusel-salon/2.jpg', null,
    'Կայք առցանց գրանցումով՝ հաճախորդն ինքն է ընտրում վարպետին և ժամը։ 150 000 ֏-ից։\n\nСайт с онлайн-записью: клиент сам выбирает мастера и время. От 150 000 ֏.'],
  klinika: ['🦷 Կլինիկա / Клиника', 'm/2026-10-segmenty/02-post-stomatologiya/1.jpg', null,
    'Կլինիկայի կայք՝ բժիշկներ, գներ, առցանց գրանցում։ 280 000 ֏-ից։\n\nСайт клиники: врачи, цены, онлайн-запись. От 280 000 ֏.'],
  avto: ['🚗 Ավտոսերվիս / Автосервис', 'm/2026-10-segmenty/03-post-avtoservis/1.jpg', null,
    'Ավտոսերվիսի կայք առցանց գրանցումով։ 150 000 ֏-ից։\n\nСайт автосервиса с онлайн-записью. От 150 000 ֏.'],
  drugoe: ['➕ Այլ / Другое', null, null,
    'Լենդինգ՝ 150 000 ֏-ից։ Գրեք, թե ինչով եք զբաղվում, կառաջարկեմ լուծում։\n\nЛендинг от 150 000 ֏. Напишите, чем вы занимаетесь, предложу решение.'],
};

// Live chat на сайте: окно chat.js пишет сюда, сообщение уходит Азату в Telegram,
// его reply кладётся в историю разговора, окно забирает её опросом.
const ORIGINS = ['https://evnweb.am', 'https://www.evnweb.am', 'https://s18113211.smrtp.ru'];
const CHAT_TTL = 60 * 60 * 24 * 30;

function tg(env) {
  return async (m, p) => {
    const r = await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/${m}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p),
    });
    const j = await r.json().catch(() => ({}));
    if (!j.ok) console.log(m, JSON.stringify(j));
    return j.result;
  };
}

async function chat(req, env, url) {
  const origin = req.headers.get('Origin') || '';
  const allowed = ORIGINS.includes(origin) || origin.startsWith('http://localhost');
  const cors = {
    'Access-Control-Allow-Origin': allowed ? origin : ORIGINS[0],
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store',
  };
  const res = (v, status = 200) => new Response(JSON.stringify(v), { status, headers: cors });
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
  const q = req.method === 'POST' ? await req.json().catch(() => ({})) : Object.fromEntries(url.searchParams);
  const sid = String(q.sid || '');
  if (!/^[a-z0-9]{16,40}$/.test(sid)) return res({ error: 'sid' }, 400);
  const room = env.CHAT.get(env.CHAT.idFromName(sid));
  // WebSocket: ответ Азата приходит в окно сразу, без опроса
  if (url.pathname === '/chat/ws') {
    if (!allowed || req.headers.get('Upgrade') !== 'websocket') return new Response('no', { status: 400 });
    return room.fetch(new Request(`https://room/ws?sid=${sid}`, req));
  }
  if (url.pathname === '/chat/poll') {
    const r = await room.fetch(`https://room/poll?sid=${sid}&after=${Number(q.after) || 0}`);
    return res(await r.json());
  }
  if (url.pathname !== '/chat/send' || req.method !== 'POST') return res({ error: 'not found' }, 404);
  const text = String(q.text || '').trim().slice(0, 1500);
  if (!text) return res({ error: 'empty' }, 400);
  const r = await room.fetch(`https://room/add?sid=${sid}`, { method: 'POST', body: JSON.stringify({ f: 'v', t: text, page: String(q.page || '').slice(0, 200) }) });
  const j = await r.json();
  if (r.status !== 200) return res(j, r.status);
  const head = j.first ? `🌐 Чат на сайте, новый посетитель${j.page ? ` (${j.page})` : ''}` : '🌐 Чат на сайте';
  await notifyAdmin(env, `${head} #${sid.slice(0, 6)}:\n\n${text}\n\nОтветьте (reply), и ответ появится у него в чате на сайте.`, `web:${sid}`);
  return res({ ok: true, n: j.n });
}

// Один разговор с сайта = один Durable Object: история читается сразу после записи (в KV запись видна не сразу),
// а открытые окна чата получают новые сообщения по WebSocket в момент ответа.
export class ChatRoom {
  constructor(ctx, env) { this.ctx = ctx; this.env = env; }

  async load(sid) {
    let h = await this.ctx.storage.get('h');
    if (!h) {
      // разговоры, начатые до переезда, лежат в KV
      h = (sid && await this.env.BOT.get(`chat:${sid}`, 'json')) || { msgs: [] };
      await this.ctx.storage.put('h', h);
    }
    return h;
  }

  async fetch(req) {
    const url = new URL(req.url);
    const sid = url.searchParams.get('sid') || '';
    if (url.pathname === '/ws') {
      const [client, server] = Object.values(new WebSocketPair());
      this.ctx.acceptWebSocket(server);
      const h = await this.load(sid);
      server.send(JSON.stringify({ n: h.msgs.length }));
      return new Response(null, { status: 101, webSocket: client });
    }
    const h = await this.load(sid);
    if (url.pathname === '/poll') {
      const after = Number(url.searchParams.get('after')) || 0;
      return Response.json({ msgs: h.msgs.slice(after), n: h.msgs.length });
    }
    if (url.pathname === '/add') {
      const m = await req.json();
      const mine = h.msgs.filter((x) => x.f === 'v');
      // защита от флуда: не больше 30 сообщений от посетителя в разговоре и 1 в 2 секунды
      if (m.f === 'v' && (mine.length >= 30 || (mine.length && Date.now() - mine[mine.length - 1].at < 2000)))
        return Response.json({ error: 'slow' }, { status: 429 });
      if (m.page) h.page = m.page;
      const msg = { f: m.f === 'a' ? 'a' : 'v', t: String(m.t).slice(0, 4000), at: Date.now() };
      h.msgs.push(msg);
      await this.ctx.storage.put('h', h);
      await this.ctx.storage.setAlarm(Date.now() + CHAT_TTL * 1000);
      const out = JSON.stringify({ msgs: [msg], n: h.msgs.length });
      for (const ws of this.ctx.getWebSockets()) { try { ws.send(out); } catch (e) {} }
      return Response.json({ ok: true, n: h.msgs.length, first: m.f === 'v' && mine.length === 0, page: h.page });
    }
    return new Response('not found', { status: 404 });
  }

  webSocketMessage(ws, msg) { if (msg === 'ping') ws.send('pong'); }
  webSocketClose(ws, code) { try { ws.close(code, 'bye'); } catch (e) {} }
  async alarm() { await this.ctx.storage.deleteAll(); }   // разговор без сообщений 30 дней удаляется
}

// Сообщение Азату. Пока он не зарегистрировался через /admin, сообщения копятся в очереди
// и уходят ему сразу после регистрации, чтобы ни одна заявка не потерялась.
async function notifyAdmin(env, text, replyTo) {
  const a = (await env.BOT.get('admin', 'json'))?.id;
  if (!a) {
    const q = (await env.BOT.get('pending', 'json')) || [];
    q.push({ text, replyTo, at: Date.now() });
    await env.BOT.put('pending', JSON.stringify(q.slice(-100)));
    return null;
  }
  const sent = await tg(env)('sendMessage', { chat_id: a, text, disable_web_page_preview: true });
  if (sent?.message_id && replyTo) await env.BOT.put(`reply:${sent.message_id}`, String(replyTo), { expirationTtl: CHAT_TTL * 2 });
  return sent;
}

async function flushPending(env) {
  const q = (await env.BOT.get('pending', 'json')) || [];
  await env.BOT.delete('pending');
  for (const p of q) await notifyAdmin(env, `⏳ Пришло, пока бот ждал /admin (${new Date(p.at).toISOString().slice(0, 16).replace('T', ' ')} UTC):\n${p.text}`, p.replyTo);
  return q.length;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname.startsWith('/chat/')) return chat(req, env, url);
    if (req.method !== 'POST' || req.headers.get('X-Telegram-Bot-Api-Secret-Token') !== env.TG_SECRET)
      return new Response('EVNWEB bot', { status: 403 });
    const u = await req.json().catch(() => ({}));
    try { await handle(u, env); } catch (e) { console.log('error', e.stack || e); }
    return new Response('ok');
  },
};

async function handle(u, env) {
  const api = tg(env);
  const kv = {
    get: async (k, d) => (await env.BOT.get(k, 'json')) ?? d,
    put: (k, v) => env.BOT.put(k, JSON.stringify(v)),
    del: (k) => env.BOT.delete(k),
  };
  const say = (chat, text, markup) => api('sendMessage', { chat_id: chat, text, disable_web_page_preview: true, ...(markup ? { reply_markup: markup } : {}) });
  const log = async (v) => { const k = `lead:${Date.now()}:${v.chat}`; await env.BOT.put(k, JSON.stringify({ ...v, at: new Date().toISOString() })); };
  const admin = async () => (await kv.get('admin', {})).id;
  const toAdmin = async (text, fromChat, msgId) => {
    const a = await admin();
    if (!a) return notifyAdmin(env, text, fromChat);
    const ids = [(await say(a, text))?.message_id];
    if (fromChat && msgId) ids.push((await api('forwardMessage', { chat_id: a, from_chat_id: fromChat, message_id: msgId }))?.message_id);
    for (const id of ids.filter(Boolean)) await env.BOT.put(`reply:${id}`, String(fromChat), { expirationTtl: 60 * 60 * 24 * 60 });
  };
  const contactKb = (label) => ({ keyboard: [[{ text: label, request_contact: true }]], resize_keyboard: true, one_time_keyboard: true });

  const menu = (chat) => say(chat,
    'Բարև Ձեզ։ Ես Ազատն եմ, EVNWEB։ Կայքեր և համակարգեր եմ պատրաստում Հայաստանի բիզնեսների համար։ Ընտրեք ձեր ոլորտը, ցույց կտամ օրինակ։\n\nЗдравствуйте! Я Азат, EVNWEB: делаю сайты и системы для бизнеса в Армении. Выберите вашу сферу, покажу пример.',
    { inline_keyboard: Object.entries(NICHES).map(([k, n]) => [{ text: n[0], callback_data: `n:${k}` }]) });

  const niche = async (chat, k) => {
    const n = NICHES[k] || NICHES.drugoe;
    const rows = [[{ text: '📝 Հայտ թողնել / Оставить заявку', callback_data: `z:${k}` }]];
    if (n[2]) rows.push([{ text: '📄 PDF առաջարկ / Предложение PDF', url: `${MEDIA}/${n[2]}` }]);
    rows.push([{ text: '💬 Գրել Ազատին / Написать Азату', url: TG_LINK }]);
    const markup = { inline_keyboard: rows };
    let sent = null;
    if (n[1]) {
      const p = { chat_id: chat, caption: n[3], reply_markup: markup };
      sent = n[1].endsWith('.mp4') ? await api('sendVideo', { ...p, video: `${MEDIA}/${n[1]}`, supports_streaming: true })
                                   : await api('sendPhoto', { ...p, photo: `${MEDIA}/${n[1]}` });
    }
    if (!sent) await say(chat, n[3], markup);
  };

  if (u.callback_query) {
    const cb = u.callback_query, chat = cb.message.chat.id;
    await api('answerCallbackQuery', { callback_query_id: cb.id });
    const [t, k] = String(cb.data || '').split(':');
    if (t === 'n') { await niche(chat, k); await log({ chat, event: `niche:${k}` }); }
    if (t === 'z') {
      await kv.put(`state:${chat}`, { step: 'contact', niche: k });
      await say(chat, 'Ուղարկեք ձեր հեռախոսահամարը կոճակով և գրեք բիզնեսի անունը։\n\nОтправьте номер кнопкой ниже и напишите название бизнеса.',
        contactKb('📱 Ուղարկել համարը / Отправить номер'));
    }
    return;
  }

  const m = u.message;
  if (!m || m.chat?.type !== 'private') return;
  const chat = m.chat.id;
  const text = String(m.text || '').trim();
  const who = [m.from?.first_name, m.from?.last_name].filter(Boolean).join(' ') + (m.from?.username ? ` @${m.from.username}` : '');
  const st = await kv.get(`state:${chat}`, null);

  // Азат регистрируется как получатель заявок: /admin и свой номер кнопкой
  if (text === '/admin') {
    await kv.put(`state:${chat}`, { step: 'admin' });
    return say(chat, 'Поделитесь своим номером кнопкой ниже.', contactKb('📱 Мой номер'));
  }
  if (m.contact && st?.step === 'admin') {
    await kv.del(`state:${chat}`);
    const own = m.contact.user_id === m.from?.id;
    if (own && m.contact.phone_number.replace(/\D/g, '').endsWith(ADMIN_PHONE)) {
      await kv.put('admin', { id: chat });
      await say(chat, 'Готово: заявки и сообщения клиентов будут приходить сюда. Чтобы ответить клиенту, ответьте (reply) на его сообщение.', { remove_keyboard: true });
      return flushPending(env);
    }
    return say(chat, 'Этот номер не подходит.', { remove_keyboard: true });
  }
  // Ответ Азата клиенту: reply на пересланное сообщение
  if (chat === await admin() && m.reply_to_message) {
    const to = (await env.BOT.get(`reply:${m.reply_to_message.message_id}`)) || m.reply_to_message.forward_from?.id;
    if (String(to).startsWith('web:')) {
      if (!text) return say(chat, 'В чат на сайте уходит только текст.');
      const sid = String(to).slice(4);
      await env.CHAT.get(env.CHAT.idFromName(sid)).fetch(`https://room/add?sid=${sid}`, { method: 'POST', body: JSON.stringify({ f: 'a', t: text }) });
      return say(chat, '✓ отправлено в чат на сайте');
    }
    if (to) { await api('copyMessage', { chat_id: Number(to), from_chat_id: chat, message_id: m.message_id }); return say(chat, '✓ отправлено'); }
    return say(chat, 'Не нашёл, кому отправить: ответьте на сообщение с именем клиента.');
  }
  if (text.startsWith('/start')) {
    const payload = text.slice(6).trim();
    await (NICHES[payload] ? niche(chat, payload) : menu(chat));
    await log({ chat, who, event: 'start', from: payload });
    return toAdmin(`👋 Новый человек в боте: ${who}` + (payload ? ` (пришёл по ссылке: ${payload})` : ''), chat);
  }
  if (m.contact) {
    await kv.put(`state:${chat}`, { step: 'name', niche: st?.niche || '', phone: m.contact.phone_number });
    return say(chat, 'Շնորհակալություն։ Իսկ ո՞րն է բիզնեսի անունը։\n\nСпасибо! А как называется ваш бизнес?', { remove_keyboard: true });
  }
  if (st?.step === 'name' && text) {
    await kv.del(`state:${chat}`);
    await log({ chat, who, event: 'lead', niche: st.niche, phone: st.phone, business: text });
    await say(chat, `Շնորհակալություն։ Ազատը կկապվի ձեզ հետ այսօր։\n\nСпасибо! Азат свяжется с вами сегодня. Если срочно: ${PHONE}`);
    return toAdmin(`🔥 ЗАЯВКА\nНиша: ${st.niche}\nБизнес: ${text}\nТелефон: ${st.phone}\nTelegram: ${who}\n\nОтветьте (reply) на это сообщение, и ответ уйдёт клиенту.`, chat);
  }
  // Любое другое сообщение: пересылаем Азату, клиенту короткий ответ
  if (text || m.photo || m.voice) {
    if (!st) await say(chat, 'Շնորհակալություն, Ազատը շուտով կպատասխանի։\n\nСпасибо! Азат скоро ответит. А пока можно посмотреть примеры: /start');
    return toAdmin(`💬 Сообщение от ${who}:`, chat, m.message_id);
  }
}

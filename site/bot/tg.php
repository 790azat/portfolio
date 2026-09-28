<?php
// Telegram-бот EVNWEB: отвечает тем, кто написал сам (ссылка t.me/<бот> в постах, рекламе, QR),
// показывает пример под нишу, принимает заявку и пересылает всё Азату. Ответ Азата (reply) уходит клиенту.
// config.php создаётся при выкладке из секрета GitHub TELEGRAM_BOT_TOKEN (TG_TOKEN, TG_SECRET).
// Получатель заявок: тот, кто отправит боту /admin и поделится своим номером ADMIN_PHONE.
declare(strict_types=1);
require __DIR__ . '/config.php';
const DATA = __DIR__ . '/data';
const PHONE = '+374 93 40-11-79';
const TG_LINK = 'https://t.me/+37493401179';
const ADMIN_PHONE = '37493401179';
const ADMIN_EMAIL = 'vip.azatazat@gmail.com';
const SITE_URL = 'https://evnweb.am';

if (($_SERVER['HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN'] ?? '') !== TG_SECRET) { http_response_code(403); exit; }
$u = json_decode(file_get_contents('php://input') ?: '{}', true) ?: [];
http_response_code(200);

// Хостинг может не достучаться до api.telegram.org. Поэтому главный ответ человеку уходит прямо в ответе
// на webhook (Telegram сам выполняет этот метод), а запросы к API — только для второстепенного.
$OUT = null;
register_shutdown_function(function () {
    global $OUT;
    if ($OUT) { header('Content-Type: application/json'); echo json_encode($OUT, JSON_UNESCAPED_UNICODE); }
});
function out(string $m, array $p): void {
    global $OUT;
    if ($OUT === null) {
        if (isset($p['reply_markup']) && is_string($p['reply_markup'])) $p['reply_markup'] = json_decode($p['reply_markup'], true);
        $OUT = ['method' => $m] + $p;
    } else api($m, $p);
}
if (isset($_GET['diag'])) {
    $t = microtime(true); $r = api('getMe');
    echo json_encode(['php' => PHP_VERSION, 'getMe' => $r, 'err' => $GLOBALS['API_ERR'] ?? null, 'sec' => round(microtime(true) - $t, 1)]);
    exit;
}

function api(string $m, array $p = []): array {
    $ch = curl_init('https://api.telegram.org/bot' . TG_TOKEN . '/' . $m);
    // Хостинг зависал на IPv6-маршруте до api.telegram.org: только IPv4 и короткое ожидание соединения.
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $p, CURLOPT_RETURNTRANSFER => true,
        CURLOPT_IPRESOLVE => CURL_IPRESOLVE_V4, CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 20]);
    $raw = curl_exec($ch);
    if ($raw === false) $GLOBALS['API_ERR'] = curl_error($ch);
    $r = json_decode((string)$raw, true) ?: [];
    curl_close($ch);
    return $r;
}
function load(string $f, $def) { $p = DATA . "/$f"; return is_file($p) ? (json_decode((string)file_get_contents($p), true) ?? $def) : $def; }
function save(string $f, $v): void { @mkdir(DATA); file_put_contents(DATA . "/$f", json_encode($v, JSON_UNESCAPED_UNICODE), LOCK_EX); }
function logline(array $v): void { @mkdir(DATA); file_put_contents(DATA . '/leads.jsonl', json_encode($v + ['at' => date('c')], JSON_UNESCAPED_UNICODE) . "\n", FILE_APPEND | LOCK_EX); }
function kb(array $rows): string { return json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE); }
function admin(): ?int { return load('admin.json', [])['id'] ?? null; }
function say(int $chat, string $text, ?string $markup = null): void {
    $p = ['chat_id' => $chat, 'text' => $text, 'disable_web_page_preview' => true];
    if ($markup) $p['reply_markup'] = $markup;
    out('sendMessage', $p);
}

const NICHES = [
    'restoran' => ['🍽 Ռեստորան / Ресторан, кафе', '2026-10-nedelya-1/06-reel-restoran/reel.mp4', null,
        "Ռեստորանի կայք՝ մենյու լուսանկարներով 3 լեզվով, սեղանի ամրագրում, ադմին, որտեղ գները փոխում եք ինքներդ։ 280 000 ֏-ից։\n\nСайт ресторана: меню с фото на 3 языках, бронь столов, админка, где цены меняете сами. От 280 000 ֏."],
    'otel' => ['🏨 Հյուրանոց / Отель, гостевой дом', '2026-10-nedelya-1/07-reel-otel/reel.mp4', 'docs/predlozhenie-otel.pdf',
        "Հյուրանոցի կայք՝ ուղիղ ամրագրում առանց Booking-ի միջնորդավճարի, զբաղվածության օրացույց, ադմին։ 450 000 ֏-ից։\n\nСайт отеля: прямая бронь без комиссии Booking, календарь занятости, админка. От 450 000 ֏."],
    'magazin' => ['🛒 Խանութ / Магазин', null, 'docs/predlozhenie-supermarket.pdf',
        "Առցանց խանութ՝ 400 000 ֏-ից, մնացորդների և ժամկետների հաշվառում՝ 650 000 ֏-ից։\n\nОнлайн-магазин от 400 000 ֏, учёт остатков и сроков годности от 650 000 ֏."],
    'salon' => ['💇 Սրահ / Салон, барбершоп', '2026-10-segmenty/01-karusel-salon/2.jpg', null,
        "Կայք առցանց գրանցումով՝ հաճախորդն ինքն է ընտրում վարպետին և ժամը։ 150 000 ֏-ից։\n\nСайт с онлайн-записью: клиент сам выбирает мастера и время. От 150 000 ֏."],
    'klinika' => ['🦷 Կլինիկա / Клиника', '2026-10-segmenty/02-post-stomatologiya/1.jpg', null,
        "Կլինիկայի կայք՝ բժիշկներ, գներ, առցանց գրանցում։ 280 000 ֏-ից։\n\nСайт клиники: врачи, цены, онлайн-запись. От 280 000 ֏."],
    'avto' => ['🚗 Ավտոսերվիս / Автосервис', '2026-10-segmenty/03-post-avtoservis/1.jpg', null,
        "Ավտոսերվիսի կայք առցանց գրանցումով։ 150 000 ֏-ից։\n\nСайт автосервиса с онлайн-записью. От 150 000 ֏."],
    'drugoe' => ['➕ Այլ / Другое', null, null,
        "Լենդինգ՝ 150 000 ֏-ից։ Գրեք, թե ինչով եք զբաղվում, կառաջարկեմ լուծում։\n\nЛендинг от 150 000 ֏. Напишите, чем вы занимаетесь, предложу решение."],
];

function menu(int $chat): void {
    $rows = [];
    foreach (NICHES as $k => $n) $rows[] = [['text' => $n[0], 'callback_data' => "n:$k"]];
    say($chat, "Բարև Ձեզ։ Ես Ազատն եմ, EVNWEB։ Կայքեր և համակարգեր եմ պատրաստում Հայաստանի բիզնեսների համար։ Ընտրեք ձեր ոլորտը, ցույց կտամ օրինակ։\n\nЗдравствуйте! Я Азат, EVNWEB: делаю сайты и системы для бизнеса в Армении. Выберите вашу сферу, покажу пример.", kb($rows));
}

function niche(int $chat, string $k): void {
    $n = NICHES[$k] ?? NICHES['drugoe'];
    $rows = [[['text' => '📝 Հայտ թողնել / Оставить заявку', 'callback_data' => "z:$k"]]];
    if ($n[2]) $rows[] = [['text' => '📄 PDF առաջարկ / Предложение PDF', 'url' => SITE_URL . '/' . $n[2]]];
    $rows[] = [['text' => '💬 Գրել Ազատին / Написать Азату', 'url' => TG_LINK]];
    $p = ['chat_id' => $chat, 'caption' => $n[3], 'reply_markup' => kb($rows)];
    if ($n[1] && is_file(dirname(__DIR__) . "/m/{$n[1]}")) {
        $url = SITE_URL . "/m/{$n[1]}";
        str_ends_with($n[1], '.mp4') ? out('sendVideo', $p + ['video' => $url, 'supports_streaming' => true])
                                     : out('sendPhoto', $p + ['photo' => $url]);
    } else out('sendMessage', ['chat_id' => $chat, 'text' => $n[3], 'reply_markup' => kb($rows), 'disable_web_page_preview' => true]);
}

function toAdmin(string $text, ?int $fromChat = null, ?int $msgId = null): void {
    @mail(ADMIN_EMAIL, '=?UTF-8?B?' . base64_encode('EVNWEB бот: ' . strtok($text, "\n")) . '?=', $text,
          "Content-Type: text/plain; charset=UTF-8\r\nFrom: bot@evnweb.am");
    $a = admin();
    if (!$a) return;
    $ids = [api('sendMessage', ['chat_id' => $a, 'text' => $text])['result']['message_id'] ?? null];
    if ($fromChat && $msgId) $ids[] = api('forwardMessage', ['chat_id' => $a, 'from_chat_id' => $fromChat, 'message_id' => $msgId])['result']['message_id'] ?? null;
    if ($fromChat) {
        $map = load('replies.json', []);
        foreach (array_filter($ids) as $id) $map[(string)$id] = $fromChat;
        save('replies.json', array_slice($map, -500, null, true));
    }
}

$state = load('state.json', []);

if ($cb = $u['callback_query'] ?? null) {
    $chat = (int)$cb['message']['chat']['id'];
    [$t, $k] = explode(':', $cb['data'] . ':');
    if ($t === 'n') { niche($chat, $k); logline(['chat' => $chat, 'event' => "niche:$k"]); }
    if ($t === 'z') {
        $state[(string)$chat] = ['step' => 'contact', 'niche' => $k]; save('state.json', $state);
        say($chat, "Ուղարկեք ձեր հեռախոսահամարը կոճակով և գրեք բիզնեսի անունը։\n\nОтправьте номер кнопкой ниже и напишите название бизнеса.",
            json_encode(['keyboard' => [[['text' => '📱 Ուղարկել համարը / Отправить номер', 'request_contact' => true]]], 'resize_keyboard' => true, 'one_time_keyboard' => true]));
    }
    exit;
}

$m = $u['message'] ?? null;
if (!$m || ($m['chat']['type'] ?? '') !== 'private') exit;
$chat = (int)$m['chat']['id'];
$text = trim((string)($m['text'] ?? ''));
$who = trim(($m['from']['first_name'] ?? '') . ' ' . ($m['from']['last_name'] ?? '')) . (isset($m['from']['username']) ? ' @' . $m['from']['username'] : '');

// Азат регистрируется как получатель заявок: /admin и свой номер кнопкой
if ($text === '/admin') {
    $state[(string)$chat] = ['step' => 'admin']; save('state.json', $state);
    say($chat, 'Поделитесь своим номером кнопкой ниже.', json_encode(['keyboard' => [[['text' => '📱 Мой номер', 'request_contact' => true]]], 'resize_keyboard' => true, 'one_time_keyboard' => true]));
    exit;
}
if (isset($m['contact']) && (($state[(string)$chat]['step'] ?? '') === 'admin')) {
    unset($state[(string)$chat]); save('state.json', $state);
    $own = ($m['contact']['user_id'] ?? 0) === ($m['from']['id'] ?? -1);
    if ($own && str_ends_with(preg_replace('~\D~', '', $m['contact']['phone_number']), ADMIN_PHONE)) {
        save('admin.json', ['id' => $chat]);
        say($chat, 'Готово: заявки и сообщения клиентов будут приходить сюда. Чтобы ответить клиенту, ответьте (reply) на его сообщение.', json_encode(['remove_keyboard' => true]));
    } else say($chat, 'Этот номер не подходит.', json_encode(['remove_keyboard' => true]));
    exit;
}
// Ответ Азата клиенту: reply на пересланное сообщение
if ($chat === admin() && isset($m['reply_to_message'])) {
    $map = load('replies.json', []);
    $to = $map[(string)$m['reply_to_message']['message_id']] ?? ($m['reply_to_message']['forward_from']['id'] ?? null);
    if ($to) { out('copyMessage', ['chat_id' => $to, 'from_chat_id' => $chat, 'message_id' => $m['message_id']]); }
    else say($chat, 'Не нашёл, кому отправить: ответьте на сообщение с именем клиента.');
    exit;
}
if (str_starts_with($text, '/start')) {
    $payload = trim(substr($text, 6));
    logline(['chat' => $chat, 'who' => $who, 'event' => 'start', 'from' => $payload]);
    isset(NICHES[$payload]) ? niche($chat, $payload) : menu($chat);
    toAdmin("👋 Новый человек в боте: $who" . ($payload ? " (пришёл по ссылке: $payload)" : ''), $chat);
    exit;
}
$st = $state[(string)$chat] ?? null;
if (isset($m['contact'])) {
    $phone = $m['contact']['phone_number'];
    $state[(string)$chat] = ['step' => 'name', 'niche' => $st['niche'] ?? '', 'phone' => $phone]; save('state.json', $state);
    say($chat, "Շնորհակալություն։ Իսկ ո՞րն է բիզնեսի անունը։\n\nСпасибо! А как называется ваш бизнес?", json_encode(['remove_keyboard' => true]));
    exit;
}
if ($st && $st['step'] === 'name' && $text !== '') {
    unset($state[(string)$chat]); save('state.json', $state);
    logline(['chat' => $chat, 'who' => $who, 'event' => 'lead', 'niche' => $st['niche'], 'phone' => $st['phone'], 'business' => $text]);
    say($chat, "Շնորհակալություն։ Ազատը կկապվի ձեզ հետ այսօր։\n\nСпасибо! Азат свяжется с вами сегодня. Если срочно: " . PHONE);
    toAdmin("🔥 ЗАЯВКА\nНиша: {$st['niche']}\nБизнес: $text\nТелефон: {$st['phone']}\nTelegram: $who\n\nОтветьте (reply) на это сообщение, и ответ уйдёт клиенту.", $chat);
    exit;
}
// Любое другое сообщение: пересылаем Азату, клиенту короткий ответ
if ($text !== '' || isset($m['photo']) || isset($m['voice'])) {
    if (!$st) say($chat, "Շնորհակալություն, Ազատը շուտով կպատասխանի։\n\nСпасибо! Азат скоро ответит. А пока можно посмотреть примеры: /start");
    toAdmin("💬 Сообщение от $who:\n$text", $chat, (int)$m['message_id']);
}

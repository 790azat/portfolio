"""Публикация в Telegram-канал EVNWEB через бота (Bot API). Файлы загружаются прямо из репозитория.

Нужны секрет TELEGRAM_BOT_TOKEN и переменная TELEGRAM_CHANNEL (@имя_канала или числовой id).
Бот должен быть администратором канала с правом публикации.
"""
import json, os, pathlib, urllib.error, urllib.request, uuid

def _token(t):
    t = ''.join(t.split())
    return t[3:] if t.lower().startswith('bot') and ':' in t else t


def _channel(c):
    # принимаем @evnweb, evnweb, t.me/evnweb, https://t.me/evnweb и числовой id
    c = c.strip().rstrip('/')
    for p in ('https://', 'http://', 't.me/', 'telegram.me/'):
        if c.lower().startswith(p):
            c = c[len(p):]
    if c and not c.startswith('@') and not c.lstrip('-').isdigit():
        c = '@' + c
    return c


TOKEN = _token(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
CHANNEL = _channel(os.environ.get('TELEGRAM_CHANNEL', ''))
SITE = pathlib.Path(__file__).resolve().parent.parent / 'site'
CAPTION_MAX = 1024


class TgError(Exception):
    pass


def enabled():
    return bool(TOKEN and CHANNEL)


def api(method, fields=None, files=None):
    b = uuid.uuid4().hex
    body = b''
    for k, v in (fields or {}).items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, f in (files or {}).items():
        ctype = 'video/mp4' if f.suffix == '.mp4' else 'image/jpeg'
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{f.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
        body += f.read_bytes() + b'\r\n'
    body += f'--{b}--\r\n'.encode()
    url = f'https://api.telegram.org/bot{TOKEN}/{method}'
    if fields or files:
        req = urllib.request.Request(url, data=body, method='POST',
                                     headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)['result']
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            msg = json.loads(raw).get('description') or raw
        except Exception:
            msg = f'{e} {raw[:200]}'.strip()
        raise TgError(f'{method}: {msg}') from None


def check():
    me = api('getMe')
    chat = api('getChat', {'chat_id': CHANNEL})
    member = api('getChatMember', {'chat_id': CHANNEL, 'user_id': me['id']})
    print(f"Telegram: бот @{me['username']}, канал {chat.get('title')} ({chat['id']}), права бота: {member['status']}")
    return me


def publish(pid, kind, media, caption):
    """media: имена файлов в site/m/<pid>/. Возвращает id первого сообщения."""
    files = [SITE / 'm' / pid / m for m in media]
    missing = [f for f in files if not f.exists()]
    if missing:
        raise TgError(f'нет файла {missing[0]}')
    short = caption if len(caption) <= CAPTION_MAX else ''
    if kind == 'reel':
        r = api('sendVideo', {'chat_id': CHANNEL, 'caption': short, 'supports_streaming': 'true'}, {'video': files[0]})
        first = r['message_id']
    elif kind == 'carousel' and len(files) > 1:
        group = [{'type': 'photo', 'media': f'attach://f{i}', **({'caption': short} if i == 0 and short else {})}
                 for i, _ in enumerate(files[:10])]
        r = api('sendMediaGroup', {'chat_id': CHANNEL, 'media': json.dumps(group, ensure_ascii=False)},
                {f'f{i}': f for i, f in enumerate(files[:10])})
        first = r[0]['message_id']
    else:
        r = api('sendPhoto', {'chat_id': CHANNEL, 'caption': short}, {'photo': files[0]})
        first = r['message_id']
    if not short and caption:
        api('sendMessage', {'chat_id': CHANNEL, 'text': caption[:4096], 'disable_web_page_preview': 'true'})
    return first

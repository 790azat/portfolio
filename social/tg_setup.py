#!/usr/bin/env python3
"""Подключает бота к сайту (setWebhook) и проверяет канал. Запуск: publish.yml, режим tg-setup."""
import hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request

import tg

# Первый адрес, где бот реально отвечает (без секретного заголовка tg.php отдаёт 403) и сертификат годный.
CANDIDATES = [os.environ['TELEGRAM_WEBHOOK_URL']] if os.environ.get('TELEGRAM_WEBHOOK_URL') else [
    'https://evnweb.am/bot/tg.php', 'https://www.evnweb.am/bot/tg.php', 'https://s18113211.smrtp.ru/bot/tg.php']


def alive(u):
    try:
        urllib.request.urlopen(u, timeout=15)
        return 'ответил 200, а ждали 403'
    except urllib.error.HTTPError as e:
        return None if e.code == 403 else f'HTTP {e.code}'
    except Exception as e:
        return str(getattr(e, 'reason', e))


import socket
for h in ('evnweb.am', 'www.evnweb.am', 's18113211.smrtp.ru', 'shared-33.smartape.net', 'api.telegram.org'):
    try:
        addrs = sorted({a[4][0] for a in socket.getaddrinfo(h, 443, proto=socket.IPPROTO_TCP)})
    except Exception as e:
        addrs = [str(e)]
    res = []
    for a in addrs:
        try:
            socket.create_connection((a, 443), timeout=8).close(); res.append(f'{a}:443 ok')
        except Exception as e:
            res.append(f'{a}:443 {e}')
        try:
            socket.create_connection((a, 80), timeout=8).close(); res.append(f'{a}:80 ok')
        except Exception as e:
            res.append(f'{a}:80 {e}')
    print('DIAG', h, '|', '; '.join(res))
url = None
for u in CANDIDATES:
    err = alive(u)
    print(f'{u}: {err or "бот на месте"}')
    if not err:
        url = u; break
if not url:
    sys.exit('Бот не отвечает ни по одному адресу')
if not tg.TOKEN:
    sys.exit('Нет секрета TELEGRAM_BOT_TOKEN')
secret = hashlib.sha256(tg.TOKEN.encode()).hexdigest()[:32]
me = tg.api('getMe')
print(f"Бот @{me['username']}")
if tg.CHANNEL:
    tg.check()
tg.api('setWebhook', {'url': url, 'secret_token': secret, 'allowed_updates': json.dumps(['message', 'callback_query']), 'drop_pending_updates': 'true'})
tg.api('setMyCommands', {'commands': json.dumps([{'command': 'start', 'description': 'Примеры и цены / Օրինակներ և գներ'}])})
tg.api('setMyDescription', {'description': 'EVNWEB: сайты и системы для бизнеса в Армении. Покажу пример под вашу сферу и приму заявку.\nEVNWEB՝ կայքեր և համակարգեր Հայաստանի բիզնեսների համար։'})
info = tg.api('getWebhookInfo')
print('Webhook:', info.get('url'), '| ошибка:', info.get('last_error_message') or 'нет', '| в очереди:', info.get('pending_update_count'))

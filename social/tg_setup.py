#!/usr/bin/env python3
"""Подключает бота (setWebhook) и проверяет канал. Запускается из bot.yml после выкладки на Cloudflare."""
import hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request

import tg

# Бот живёт на Cloudflare Workers (bot/worker.js, выкладка .github/workflows/bot.yml передаёт его адрес).
# PHP-копия на evnweb.am — запасная: хостинг SmartApe не пропускает Telegram (2026-09-28).
# Первый адрес, где бот отвечает 403 без секретного заголовка и сертификат годный.
CANDIDATES = [os.environ['TELEGRAM_WEBHOOK_URL']] if os.environ.get('TELEGRAM_WEBHOOK_URL') else []
if not CANDIDATES:
    sys.exit('Адрес бота задаёт выкладка на Cloudflare: запустите workflow «Telegram-бот на Cloudflare» (bot.yml)')


def alive(u):
    try:
        urllib.request.urlopen(u, timeout=15)
        return 'ответил 200, а ждали 403'
    except urllib.error.HTTPError as e:
        return None if e.code == 403 else f'HTTP {e.code}'
    except Exception as e:
        return str(getattr(e, 'reason', e))


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

#!/usr/bin/env python3
"""Подключает бота к сайту (setWebhook) и проверяет канал. Запуск: publish.yml, режим tg-setup."""
import hashlib, json, os, sys, urllib.parse, urllib.request

import tg

url = os.environ.get('TELEGRAM_WEBHOOK_URL') or 'https://evnweb.am/bot/tg.php'
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

#!/usr/bin/env python3
"""ВРЕМЕННАЯ диагностика бота (ветка diag-bot)."""
import hashlib, json, urllib.error, urllib.request
import tg
secret = hashlib.sha256(tg.TOKEN.encode()).hexdigest()[:32]
print('INFO', json.dumps(tg.api('getWebhookInfo'), ensure_ascii=False))
for body in ({'update_id': 1, 'message': {'message_id': 1, 'date': 0, 'chat': {'id': 1, 'type': 'private'}, 'from': {'id': 1, 'is_bot': False, 'first_name': 'T'}, 'text': '/start'}},):
    req = urllib.request.Request('https://evnweb.am/bot/tg.php', data=json.dumps(body).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'X-Telegram-Bot-Api-Secret-Token': secret})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print('POST', r.status, r.read()[:500])
    except urllib.error.HTTPError as e:
        print('POST', e.code, e.read()[:1000])
    except Exception as e:
        print('POST err', e)
print('INFO2', json.dumps(tg.api('getWebhookInfo'), ensure_ascii=False))

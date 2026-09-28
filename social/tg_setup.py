#!/usr/bin/env python3
"""ВРЕМЕННАЯ диагностика бота."""
import hashlib, json, time, urllib.error, urllib.request
import tg
secret = hashlib.sha256(tg.TOKEN.encode()).hexdigest()[:32]
H = {'X-Telegram-Bot-Api-Secret-Token': secret, 'Content-Type': 'application/json'}
def req(url, data=None):
    t = time.time()
    r = urllib.request.Request(url, data=data, headers=H, method='POST' if data else 'GET')
    try:
        with urllib.request.urlopen(r, timeout=90) as x:
            return x.status, x.read()[:700], round(time.time() - t, 1)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:700], round(time.time() - t, 1)
    except Exception as e:
        return 'err', str(e), round(time.time() - t, 1)
print('DIAG', req('https://evnweb.am/bot/tg.php?diag=1'))
upd = {'update_id': 1, 'message': {'message_id': 1, 'date': 0, 'chat': {'id': 1, 'type': 'private'}, 'from': {'id': 1, 'is_bot': False, 'first_name': 'T'}, 'text': '/start'}}
print('START', req('https://evnweb.am/bot/tg.php', json.dumps(upd).encode()))
print('INFO', json.dumps(tg.api('getWebhookInfo'), ensure_ascii=False))

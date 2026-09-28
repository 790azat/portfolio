#!/usr/bin/env python3
"""Список переписок в Direct @evnweb (и Messenger страницы): с кем есть чат, кто написал последним.

Текст сообщений не печатаем: лог Actions могут видеть другие. Только ники, даты и кто ответил.
Нужно право instagram_manage_messages и включённый в Instagram «доступ к сообщениям».
"""
import publish
from publish import MetaError, call

publish.token_expiry()
page, name, ig, igname = publish.accounts()
for platform in ('instagram', 'messenger'):
    try:
        url, n = f'{page}/conversations', 0
        params = dict(platform=platform, fields='updated_time,participants,messages.limit(20){from,created_time}', limit=50)
        while url and n < 400:
            r = call('GET', url, **params)
            for c in r.get('data', []):
                people = [p for p in c.get('participants', {}).get('data', []) if p.get('id') not in (page, ig)]
                who = ', '.join(p.get('username') or p.get('name') or p.get('id') for p in people)
                msgs = c.get('messages', {}).get('data', [])
                ours = [m for m in msgs if (m.get('from') or {}).get('id') in (page, ig)]
                theirs = [m for m in msgs if m not in ours]
                first_ours = min((m['created_time'] for m in ours), default='')
                print(f'CHAT\t{platform}\t{who}\tнаших={len(ours)}\tих={len(theirs)}\tпервое_наше={first_ours[:16]}\tобновлён={c.get("updated_time", "")[:16]}')
                n += 1
            nxt = (r.get('paging') or {}).get('cursors', {}).get('after') if (r.get('paging') or {}).get('next') else None
            if not nxt:
                break
            params['after'] = nxt
        print(f'ИТОГО {platform}: {n} чатов')
    except MetaError as e:
        print(f'ОШИБКА {platform}: {e}')

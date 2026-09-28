#!/usr/bin/env python3
"""Проверка Instagram-профилей потенциальных клиентов через Business Discovery (Meta Graph API).

  python social/ig_leads.py social/leads/handles.txt [--hashtag кафе]

Для каждого username берёт публичные данные бизнес-профиля: имя, описание, ссылку в профиле,
подписчиков, число постов и дату последнего поста. Результат печатается в лог CSV-блоком
(между строками ===CSV=== и ===END===), в репозиторий ничего не сохраняется.
Личные (не бизнес) профили API не показывает: они помечаются «нет данных».
"""
import argparse, csv, io, sys, time

import publish
from publish import MetaError, call

FIELDS = 'username,name,biography,website,followers_count,media_count,media.limit(1){timestamp}'
LIMIT_CODES = ('(code 4/', '(code 17/', '(code 32/', '(code 613/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('handles')
    ap.add_argument('--hashtag', action='append', default=[])
    a = ap.parse_args()
    _, _, ig, igname = publish.accounts()
    if not ig:
        sys.exit('к странице не подключён Instagram')
    print('Проверяю от имени @' + igname)
    names = []
    for line in open(a.handles, encoding='utf-8'):
        u = line.strip().split('instagram.com/')[-1].strip('/@ ').split('?')[0].split('/')[0].lower()
        if u and not u.startswith('#') and u not in names:
            names.append(u)
    rows, left, errs = [], [], {}
    for i, u in enumerate(names):
        try:
            d = call('GET', ig, fields=f'business_discovery.username({u}){{{FIELDS}}}')['business_discovery']
            last = ((d.get('media') or {}).get('data') or [{}])[0].get('timestamp', '')[:10]
            rows.append([u, d.get('name', ''), d.get('followers_count', ''), d.get('media_count', ''), last,
                         d.get('website', ''), ' '.join((d.get('biography') or '').split())[:200], 'ok'])
        except MetaError as e:
            if any(c in str(e) for c in LIMIT_CODES):
                print('Лимит запросов Meta, остановился на', u)
                left = names[i:]
                break
            msg = str(e).split(': ', 1)[-1]
            errs[msg] = errs.get(msg, 0) + 1
            if errs[msg] == 1:
                print('Ошибка на', u, '->', msg)
            rows.append([u, '', '', '', '', '', '', 'нет данных'])
            if len(rows) >= 8 and not any(r[-1] == 'ok' for r in rows):
                print('Первые 8 профилей не прочитались, останавливаюсь: похоже, не хватает прав')
                left = names[i + 1:]
                break
        time.sleep(1)
    for tag in a.hashtag:
        try:
            h = call('GET', 'ig_hashtag_search', user_id=ig, q=tag)['data'][0]['id']
            top = call('GET', f'{h}/recent_media', user_id=ig, fields='permalink,caption,timestamp', limit=50)
            print(f'#{tag}: найдено постов', len(top.get('data', [])))
            for m in top.get('data', []):
                print('  ', m.get('timestamp', '')[:10], m.get('permalink'))
        except MetaError as e:
            print(f'#{tag}: поиск по хэштегу недоступен: {e}')
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['username', 'name', 'followers', 'posts', 'last_post', 'website', 'bio', 'status'])
    w.writerows(rows)
    ok = sum(r[-1] == 'ok' for r in rows)
    print(f'Проверено {len(rows)}, бизнес-профилей {ok}, не успел {len(left)}')
    print('===CSV===')
    print(out.getvalue().rstrip())
    print('===END===')
    if left:
        print('===LEFT===\n' + '\n'.join(left) + '\n===END===')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Публикация партий фабрики EVNWEB в Instagram и Facebook через Meta Graph API.

  python social/publish.py --check     проверить токен: какие страница и Instagram доступны
  python social/publish.py --dry-run   показать, что будет опубликовано сейчас, ничего не публикуя
  python social/publish.py             опубликовать всё, у чего наступило время и стоит approved: true

Токен страницы берётся из переменной окружения META_PAGE_TOKEN (секрет GitHub).
Картинки и видео Meta забирает по ссылке https://evnweb.am/m/<id>/<файл>, их выкладывает deploy.yml.
Что уже опубликовано, записывается в social/published.json, повторно не публикуется.
"""
import argparse, datetime, json, os, pathlib, sys, time, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

import yaml

HERE = pathlib.Path(__file__).resolve().parent
SCHEDULE = HERE / 'schedule.yaml'
LOG = HERE / 'published.json'
API = 'https://graph.facebook.com/' + os.environ.get('META_API_VERSION', 'v23.0')
BASE = os.environ.get('MEDIA_BASE', 'https://evnweb.am').rstrip('/')
TOKEN = os.environ.get('META_PAGE_TOKEN', '')
MAX_TRIES = 3


class MetaError(Exception):
    pass


def call(method, path, **params):
    params['access_token'] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f'{API}/{path}'
    req = urllib.request.Request(url + ('?' + data.decode() if method == 'GET' else ''), data=None if method == 'GET' else data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get('error', {})
            msg = f"{err.get('message')} (code {err.get('code')}/{err.get('error_subcode')})"
        except Exception:
            msg = str(e)
        raise MetaError(f'{method} {path}: {msg}') from None


def reachable(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def accounts():
    me = call('GET', 'me', fields='id,name,instagram_business_account{id,username}')
    ig = me.get('instagram_business_account') or {}
    return me['id'], me.get('name'), ig.get('id'), ig.get('username')


# ---------- Instagram ----------
def ig_wait(cid, what):
    for _ in range(60):  # до 10 минут на обработку видео
        st = call('GET', cid, fields='status_code,status').get('status_code')
        if st == 'FINISHED':
            return
        if st in ('ERROR', 'EXPIRED'):
            raise MetaError(f'Instagram не принял {what}: {st}')
        time.sleep(10)
    raise MetaError(f'Instagram слишком долго обрабатывает {what}')


def ig_publish(ig, kind, urls, caption, cover=None):
    if kind == 'carousel':
        kids = []
        for u in urls:
            c = call('POST', f'{ig}/media', image_url=u, is_carousel_item='true')['id']
            ig_wait(c, u); kids.append(c)
        cid = call('POST', f'{ig}/media', media_type='CAROUSEL', children=','.join(kids), caption=caption)['id']
    elif kind == 'reel':
        p = dict(media_type='REELS', video_url=urls[0], caption=caption, share_to_feed='true')
        if cover:
            p['cover_url'] = cover
        cid = call('POST', f'{ig}/media', **p)['id']
    elif kind == 'story':
        cid = call('POST', f'{ig}/media', media_type='STORIES', image_url=urls[0])['id']
    else:
        cid = call('POST', f'{ig}/media', image_url=urls[0], caption=caption)['id']
    ig_wait(cid, kind)
    return call('POST', f'{ig}/media_publish', creation_id=cid)['id']


# ---------- Facebook ----------
def fb_publish(page, kind, urls, caption):
    if kind == 'reel':
        return call('POST', f'{page}/videos', file_url=urls[0], description=caption)['id']
    if kind == 'story':
        pid = call('POST', f'{page}/photos', url=urls[0], published='false')['id']
        return call('POST', f'{page}/photo_stories', photo_id=pid).get('post_id', pid)
    if kind == 'carousel':
        ids = [call('POST', f'{page}/photos', url=u, published='false')['id'] for u in urls]
        p = {f'attached_media[{i}]': json.dumps({'media_fbid': x}) for i, x in enumerate(ids)}
        return call('POST', f'{page}/feed', message=caption, **p)['id']
    return call('POST', f'{page}/photos', url=urls[0], message=caption)['id']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if not TOKEN:
        sys.exit('Нет META_PAGE_TOKEN: добавьте секрет в Settings → Secrets and variables → Actions')
    page, page_name, ig, ig_name = accounts()
    print(f'Страница Facebook: {page_name} ({page}); Instagram: @{ig_name or "не привязан"}')
    if a.check:
        if not ig:
            sys.exit('Instagram не привязан к странице или это не бизнес-аккаунт')
        return

    sched = yaml.safe_load(SCHEDULE.read_text(encoding='utf-8')) or {}
    tz = ZoneInfo(sched.get('timezone', 'Asia/Yerevan'))
    now = datetime.datetime.now(tz)
    log = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else {}
    failed = False
    for p in sched.get('posts') or []:
        pid = p['id']
        at = p['at'] if isinstance(p['at'], datetime.datetime) else datetime.datetime.strptime(str(p['at'])[:16], '%Y-%m-%d %H:%M')
        at = at.replace(tzinfo=tz)
        if not p.get('approved') or at > now:
            continue
        rec = log.setdefault(pid, {})
        urls = [f'{BASE}/m/{pid}/{f}' for f in p['media']]
        cover = f"{BASE}/m/{pid}/{p['cover']}" if p.get('cover') else None
        for target in p.get('to', ['instagram', 'facebook']):
            if target in rec or rec.get(f'{target}_tries', 0) >= MAX_TRIES:
                continue
            if target == 'instagram' and not ig:
                print(f'{pid}: пропуск Instagram, аккаунт не привязан'); continue
            missing = [u for u in urls + ([cover] if cover else []) if not reachable(u)]
            if missing:
                print(f'{pid}: файлы ещё не выложены на сайт, жду: {missing[0]}'); break
            if a.dry_run:
                print(f'[пробно] {pid} → {target}: {p["kind"]}, {len(urls)} файл(ов)'); continue
            try:
                mid = ig_publish(ig, p['kind'], urls, p.get('caption', ''), cover) if target == 'instagram' \
                    else fb_publish(page, p['kind'], urls, p.get('caption', ''))
                rec[target] = mid; rec[f'{target}_at'] = now.strftime('%Y-%m-%d %H:%M')
                rec.pop(f'{target}_error', None)
                print(f'ОПУБЛИКОВАНО {pid} → {target}: {mid}')
            except MetaError as e:
                failed = True
                rec[f'{target}_tries'] = rec.get(f'{target}_tries', 0) + 1
                rec[f'{target}_error'] = str(e)
                print(f'::error::{pid} → {target}: {e}')
        if not rec:
            log.pop(pid)
    if not a.dry_run:
        LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()

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

import tg

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


def upload(path, file, host=None, **params):
    """POST с файлом (multipart): Meta получает картинку или видео напрямую, сайт не нужен."""
    import uuid
    params['access_token'] = TOKEN
    ctype = {'.png': 'image/png', '.mp4': 'video/mp4'}.get(file.suffix.lower(), 'image/jpeg')
    base = f"{host}/{API.rsplit('/', 1)[-1]}" if host else API
    b = uuid.uuid4().hex
    body = b''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in params.items())
    body += f'--{b}\r\nContent-Disposition: form-data; name="source"; filename="{file.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
    body += file.read_bytes() + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(f'{base}/{path}', data=body, method='POST', headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get('error', {})
            msg = f"{err.get('message')} (code {err.get('code')}/{err.get('error_subcode')})"
        except Exception:
            msg = str(e)
        raise MetaError(f'POST {path}: {msg}') from None


def reachable(url):
    # GET первого байта с обычным User-Agent: хостинг может отвечать 403 на HEAD или на «Python-urllib»
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (evnweb-publisher)', 'Range': 'bytes=0-0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status in (200, 206)
    except Exception as e:
        print(f'  недоступно {url}: {e}')
        return False


def token_expiry():
    try:
        d = call('GET', 'debug_token', input_token=TOKEN).get('data', {})
    except MetaError:
        return None
    print('Приложение:', d.get('application'), '| app_id:', d.get('app_id'))
    print('Тип токена:', d.get('type'), '| права:', ', '.join(d.get('scopes') or []) or '—')
    exp = d.get('expires_at') or d.get('data_access_expires_at')
    return 0 if d.get('expires_at') == 0 else exp


def accounts():
    """Работает и с токеном страницы, и с токеном пользователя (тогда берём токен страницы из me/accounts)."""
    global TOKEN
    fields = 'id,name,instagram_business_account{id,username}'
    try:
        me = call('GET', 'me', fields=fields)
    except MetaError as e:
        if 'nonexisting field' not in str(e):
            raise
        pages = call('GET', 'me/accounts', fields=fields + ',access_token').get('data', [])
        if not pages:
            raise MetaError('у токена нет доступа ни к одной странице (нужно право pages_show_list)')
        want = os.environ.get('META_PAGE_ID')
        me = next((p for p in pages if p['id'] == want), None) if want else None
        me = me or next((p for p in pages if p.get('instagram_business_account')), pages[0])
        print('Токен пользователя: беру токен страницы', me.get('name'), '(доступно страниц:', len(pages), ')')
        TOKEN = me['access_token']
    ig = me.get('instagram_business_account') or {}
    return me['id'], me.get('name'), ig.get('id'), ig.get('username')


# ---------- Instagram ----------
PAGE = None  # id страницы, задаётся в main()


def local_file(url):
    """Файл из репозитория, который лежит по этой ссылке (site/...)."""
    rel = url.split('/site/', 1)[-1] if '/site/' in url else url.split(BASE + '/', 1)[-1]
    f = HERE.parent / 'site' / rel
    return f if f.exists() else None


def ig_upload_video(ig, url, **params):
    """Рилс в Instagram загружаем файлом (resumable upload), а не ссылкой: чужой хостинг Instagram не скачивает."""
    f = local_file(url)
    if not f:
        return call('POST', f'{ig}/media', video_url=url, **params)['id']
    r = call('POST', f'{ig}/media', upload_type='resumable', **params)
    data = f.read_bytes()
    req = urllib.request.Request(r['uri'], data=data, method='POST', headers={
        'Authorization': f'OAuth {TOKEN}', 'offset': '0', 'file_size': str(len(data))})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            json.load(resp)
    except urllib.error.HTTPError as e:
        raise MetaError(f'загрузка видео в Instagram: {e.read()[:300]!r}') from None
    return r['id']


def fb_cdn(url):
    """Instagram не всегда может скачать картинку со стороннего хостинга (ошибка 2207052).
    Загружаем файл из репозитория в Facebook как неопубликованное фото и отдаём Instagram ссылку на CDN Facebook."""
    local = HERE.parent / 'site' / url.split('/site/', 1)[-1] if '/site/' in url else HERE.parent / 'site' / url.split(BASE + '/', 1)[-1]
    if not PAGE or not local.suffix.lower() in ('.jpg', '.jpeg', '.png') or not local.exists():
        return url
    pid = upload(f'{PAGE}/photos', local, published='false')['id']
    imgs = call('GET', pid, fields='images').get('images') or []
    return max(imgs, key=lambda i: i.get('width', 0))['source'] if imgs else url


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
            c = call('POST', f'{ig}/media', image_url=fb_cdn(u), is_carousel_item='true')['id']
            ig_wait(c, u); kids.append(c)
        cid = call('POST', f'{ig}/media', media_type='CAROUSEL', children=','.join(kids), caption=caption)['id']
    elif kind == 'reel':
        p = dict(media_type='REELS', caption=caption, share_to_feed='true')
        if cover:
            p['cover_url'] = fb_cdn(cover)
        cid = ig_upload_video(ig, urls[0], **p)
    elif kind == 'story':
        cid = call('POST', f'{ig}/media', media_type='STORIES', image_url=fb_cdn(urls[0]))['id']
    else:
        cid = call('POST', f'{ig}/media', image_url=fb_cdn(urls[0]), caption=caption)['id']
    ig_wait(cid, kind)
    return call('POST', f'{ig}/media_publish', creation_id=cid)['id']


# ---------- Facebook ----------
def fb_photo(page, url, **params):
    """Фото в Facebook загружаем файлом: по ссылке Facebook не всегда скачивает картинку с хостинга (ошибка 324)."""
    f = local_file(url)
    if f:
        return upload(f'{page}/photos', f, **params)
    return call('POST', f'{page}/photos', url=url, **params)


def fb_publish(page, kind, urls, caption):
    if kind == 'reel':
        f = local_file(urls[0])
        if f:
            return upload(f'{page}/videos', f, description=caption, host='https://graph-video.facebook.com')['id']
        return call('POST', f'{page}/videos', file_url=urls[0], description=caption)['id']
    if kind == 'story':
        pid = fb_photo(page, urls[0], published='false')['id']
        return call('POST', f'{page}/photo_stories', photo_id=pid).get('post_id', pid)
    if kind == 'carousel':
        ids = [fb_photo(page, u, published='false')['id'] for u in urls]
        p = {f'attached_media[{i}]': json.dumps({'media_fbid': x}) for i, x in enumerate(ids)}
        return call('POST', f'{page}/feed', message=caption, **p)['id']
    return fb_photo(page, urls[0], message=caption)['id']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if not TOKEN:
        sys.exit('Нет META_PAGE_TOKEN: добавьте секрет в Settings → Secrets and variables → Actions')
    exp = token_expiry()
    if exp:
        left = (datetime.datetime.fromtimestamp(exp) - datetime.datetime.now()).days
        print(f'Токен действует ещё {left} дн.' + (' Продлите его (Extend Access Token), иначе публикации остановятся.' if left < 7 else ''))
    elif exp == 0:
        print('Токен бессрочный')
    page, page_name, ig, ig_name = accounts()
    global PAGE
    PAGE = page
    print(f'Страница Facebook: {page_name} ({page}); Instagram: @{ig_name or "не привязан"}')
    if a.check:
        if tg.enabled():
            try:
                tg.check()
            except tg.TgError as e:
                print(f'::error::Telegram: {e}')
        else:
            missing = [n for n, v in (('секрет TELEGRAM_BOT_TOKEN', tg.TOKEN), ('переменная TELEGRAM_CHANNEL', tg.CHANNEL)) if not v]
            print('Telegram: не настроен, нет: ' + ', '.join(missing))
        if not ig:
            sys.exit('Instagram не привязан к странице или это не бизнес-аккаунт')
        return

    sched = yaml.safe_load(SCHEDULE.read_text(encoding='utf-8')) or {}
    tz = ZoneInfo(sched.get('timezone', 'Asia/Yerevan'))
    now = datetime.datetime.now(tz)
    log = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else {}
    dlist = HERE / 'delete.yaml'
    deleted = set((yaml.safe_load(dlist.read_text(encoding='utf-8')) or {}).get('delete') or []) if dlist.exists() else set()
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
        targets = list(p.get('to', ['instagram', 'facebook']))
        removed = pid in deleted or any(k.endswith('_deleted_at') for k in rec)
        if tg.enabled() and 'telegram' not in targets and p['kind'] != 'story' and not removed:
            targets.append('telegram')  # канал Telegram получает всё, кроме сторис и удалённых постов
        for target in targets:
            if target in rec or rec.get(f'{target}_tries', 0) >= MAX_TRIES:
                continue
            if target == 'instagram' and not ig:
                print(f'{pid}: пропуск Instagram, аккаунт не привязан'); continue
            if target == 'telegram':
                if not tg.enabled():
                    continue
                if a.dry_run:
                    print(f'[пробно] {pid} → telegram: {p["kind"]}, {len(urls)} файл(ов)'); continue
                try:
                    ids = tg.publish(pid, p['kind'], p['media'], p.get('caption', ''))
                    rec['telegram'], rec['telegram_ids'] = ids[0], ids
                    rec['telegram_at'] = now.strftime('%Y-%m-%d %H:%M'); rec.pop('telegram_error', None)
                    print(f"ОПУБЛИКОВАНО {pid} → telegram: {rec['telegram']}")
                except tg.TgError as e:
                    failed = True
                    rec['telegram_tries'] = rec.get('telegram_tries', 0) + 1
                    rec['telegram_error'] = str(e)
                    print(f'::error::{pid} → telegram: {e}')
                continue
            missing = [u for u in urls + ([cover] if cover else []) if not local_file(u) and not reachable(u)]
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

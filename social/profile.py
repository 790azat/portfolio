#!/usr/bin/env python3
"""Оформляет страницу Facebook по social/profile.yaml: описание, контакты, фото профиля, обложка.
Каждое поле ставится отдельно, в лог пишется, что получилось, а что нет."""
import json, sys

import yaml

import publish

HERE = publish.HERE


def main():
    if not publish.TOKEN:
        sys.exit('Нет META_PAGE_TOKEN')
    page, name, _, _ = publish.accounts()
    print(f'Страница: {name} ({page})')
    cfg = yaml.safe_load((HERE / 'profile.yaml').read_text(encoding='utf-8'))
    url = lambda f: f'{publish.BASE}/m/profile/{f}'
    ok, bad = [], []

    def step(label, fn):
        try:
            fn(); ok.append(label); print('OK', label)
        except publish.MetaError as e:
            bad.append(label); print(f'::warning::{label}: {e}')

    for field in ('about', 'description', 'website', 'phone'):
        if cfg.get(field):
            step(field, lambda f=field: publish.call('POST', page, **{f: cfg[f].strip()}))
    if cfg.get('emails'):
        step('emails', lambda: publish.call('POST', page, emails=json.dumps(cfg['emails'])))
    if cfg.get('picture'):
        if not publish.reachable(url(cfg['picture'])):
            bad.append('picture'); print('::warning::фото профиля ещё не выложено на сайт')
        else:
            step('picture', lambda: publish.call('POST', f'{page}/picture', picture=url(cfg['picture'])))
    if cfg.get('cover'):
        if not publish.reachable(url(cfg['cover'])):
            bad.append('cover'); print('::warning::обложка ещё не выложена на сайт')
        else:
            def cover():
                pid = publish.call('POST', f'{page}/photos', url=url(cfg['cover']), published='false')['id']
                publish.call('POST', page, cover=pid)
            step('cover', cover)
    print('Готово:', ', '.join(ok) or '—', '| Не получилось:', ', '.join(bad) or '—')
    if bad:
        sys.exit(1)


if __name__ == '__main__':
    main()

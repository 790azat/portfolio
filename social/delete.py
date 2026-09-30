#!/usr/bin/env python3
"""Удаление опубликованных постов, перечисленных в social/delete.yaml (id записи из published.json).

Удаляет пост в Instagram, на Facebook и в Telegram-канале (записи из delete_instagram: только в Instagram), отмечает в published.json поле deleted_at. Отменить нельзя.
"""
import datetime, json, pathlib, sys

import yaml

import publish
import tg

HERE = pathlib.Path(__file__).resolve().parent
LIST = HERE / 'delete.yaml'


def main():
    cfg = yaml.safe_load(LIST.read_text(encoding='utf-8')) or {}
    ids = cfg.get('delete') or []
    ig_only = cfg.get('delete_instagram') or []  # только из Instagram: Facebook и Telegram не трогаем
    if not ids and not ig_only:
        print('Нечего удалять'); return
    publish.accounts()
    log = json.loads(publish.LOG.read_text(encoding='utf-8'))
    failed = False
    for pid in ids + [i for i in ig_only if i not in ids]:
        rec = log.get(pid)
        if not rec:
            print(f'{pid}: нет в published.json, пропуск'); continue
        only_ig = pid not in ids
        for target in ('instagram',) if only_ig else ('instagram', 'facebook'):
            mid = rec.get(target)
            if not mid or rec.get(f'{target}_deleted_at'):
                continue
            try:
                publish.call('DELETE', mid)
                rec[f'{target}_deleted_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                print(f'УДАЛЕНО {pid} → {target}: {mid}')
            except publish.MetaError as e:
                failed = True
                print(f'::error::{pid} → {target}: {e}')
        tg_ids = rec.get('telegram_ids') or ([rec['telegram']] if rec.get('telegram') else [])
        if tg_ids and not only_ig and not rec.get('telegram_deleted_at') and tg.enabled():
            try:
                tg.delete(tg_ids)
                rec['telegram_deleted_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                print(f'УДАЛЕНО {pid} → telegram: {tg_ids}')
            except tg.TgError as e:
                failed = True
                print(f'::error::{pid} → telegram: {e}')
    publish.LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()

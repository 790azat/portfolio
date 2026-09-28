#!/usr/bin/env python3
"""Удаление опубликованных постов, перечисленных в social/delete.yaml (id записи из published.json).

Удаляет пост и в Instagram, и на Facebook, отмечает в published.json поле deleted_at. Отменить нельзя.
"""
import datetime, json, pathlib, sys

import yaml

import publish

HERE = pathlib.Path(__file__).resolve().parent
LIST = HERE / 'delete.yaml'


def main():
    ids = (yaml.safe_load(LIST.read_text(encoding='utf-8')) or {}).get('delete') or []
    if not ids:
        print('Нечего удалять'); return
    publish.accounts()
    log = json.loads(publish.LOG.read_text(encoding='utf-8'))
    failed = False
    for pid in ids:
        rec = log.get(pid)
        if not rec:
            print(f'{pid}: нет в published.json, пропуск'); continue
        for target in ('instagram', 'facebook'):
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
    publish.LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()

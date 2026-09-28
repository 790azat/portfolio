#!/usr/bin/env python3
"""Печатает ссылки на опубликованные посты: id из social/published.json → permalink Instagram и Facebook."""
import json, pathlib

import publish
from publish import MetaError, call

log = json.loads((pathlib.Path(__file__).parent / 'published.json').read_text(encoding='utf-8'))
publish.accounts()
for key, v in log.items():
    ig = fb = ''
    try:
        ig = call('GET', v['instagram'], fields='permalink')['permalink'] if v.get('instagram') else ''
    except MetaError as e:
        ig = f'ошибка: {e}'
    try:
        fb = call('GET', v['facebook'], fields='permalink_url').get('permalink_url', '') if v.get('facebook') else ''
    except MetaError:
        fb = ''
    print(f'LINK\t{key}\t{ig}\t{fb}')

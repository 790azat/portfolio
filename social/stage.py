#!/usr/bin/env python3
"""Готовит партию фабрики к публикации: кладёт JPEG/MP4 в site/m/<партия>/ и добавляет записи в schedule.yaml.

  python social/stage.py /mnt/project-files/social/factory 2026-10-nedelya-1 --start 2026-10-05 [--lang hy]

Картинки берутся на языке --lang, подпись: сначала на этом языке, под ней на втором.
Все новые записи получают approved: false, публикация начнётся только после одобрения.
"""
import argparse, datetime, pathlib, re, shutil, subprocess, sys

import yaml
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / 'social' / 'schedule.yaml'
DAYS = ['понедельник', 'вторник', 'сред', 'четверг', 'пятниц', 'суббот', 'воскресенье']
KIND = {'post': 'post', 'square': 'post', 'carousel': 'carousel', 'story': 'story', 'reel': 'reel'}


def when_to_dt(when, start):
    w = (when or '').lower()
    day = next((i for i, d in enumerate(DAYS) if d in w), 0)
    m = re.search(r'(\d{1,2}):(\d{2})', w)
    hh, mm = (int(m[1]), int(m[2])) if m else (10, 0)
    d = start + datetime.timedelta(days=(day - start.weekday()) % 7)
    return f'{d:%Y-%m-%d} {hh:02d}:{mm:02d}'


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which('ffmpeg') or sys.exit('нужен ffmpeg (pip install imageio-ffmpeg)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('factory'); ap.add_argument('batch')
    ap.add_argument('--start', required=True, help='понедельник недели публикации, ГГГГ-ММ-ДД')
    ap.add_argument('--lang', default='hy')
    a = ap.parse_args()
    fac = pathlib.Path(a.factory); out = fac / 'out' / a.batch; briefs = fac / 'briefs' / a.batch
    other = 'hy' if a.lang == 'ru' else 'ru'
    start = datetime.date.fromisoformat(a.start)
    sched = yaml.safe_load(SCHEDULE.read_text(encoding='utf-8')) if SCHEDULE.exists() else None
    sched = sched or {'timezone': 'Asia/Yerevan', 'posts': []}
    sched['posts'] = sched.get('posts') or []
    known = {p['id'] for p in sched['posts']}
    for bf in sorted(briefs.glob('*.y*ml')):
        b = yaml.safe_load(bf.read_text(encoding='utf-8'))
        pid = f'{a.batch}/{bf.stem}'
        src = out / bf.stem / a.lang
        if not src.is_dir():
            print('нет готовых файлов, пропуск:', src); continue
        dst = ROOT / 'site' / 'm' / pid
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        kind = KIND[b.get('type', 'post')]
        entry = {'id': pid, 'title': b.get('title', bf.stem), 'kind': kind}
        if kind == 'reel':
            # Instagram: H.264 + AAC 128k, moov в начале файла
            subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', str(src / 'reel.mp4'), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
                            '-movflags', '+faststart', str(dst / 'reel.mp4')], check=True)
            Image.open(src / 'oblozhka.jpg').convert('RGB').save(dst / 'cover.jpg', quality=90)
            entry.update(media=['reel.mp4'], cover='cover.jpg')
        else:
            files = sorted(src.glob('*.png'), key=lambda f: int(f.stem))
            for f in files:
                Image.open(f).convert('RGB').save(dst / f'{f.stem}.jpg', quality=90, optimize=True)
            entry['media'] = [f'{f.stem}.jpg' for f in files]
        cap = (src / 'podpis.txt').read_text(encoding='utf-8').strip()
        cap2 = (out / bf.stem / other / 'podpis.txt')
        if kind != 'story' and cap2.exists():
            # хэштеги только один раз, в конце
            first, tags = cap.rsplit('\n\n', 1) if '\n\n' in cap else (cap, '')
            second = cap2.read_text(encoding='utf-8').strip().rsplit('\n\n', 1)[0]
            cap = f'{first}\n\n———\n\n{second}\n\n{tags}'.strip()
        entry.update(at=when_to_dt(b.get('when'), start), to=['instagram', 'facebook'], approved=False, caption=cap)
        if pid in known:
            sched['posts'] = [entry if p['id'] == pid else p for p in sched['posts']]
        else:
            sched['posts'].append(entry)
        print(f"{entry['at']}  {kind:8} {pid}")
    sched['posts'].sort(key=lambda p: str(p['at']))
    SCHEDULE.write_text(HEADER + yaml.safe_dump(sched, allow_unicode=True, sort_keys=False, width=1000), encoding='utf-8')


def _str(dumper, v):
    return dumper.represent_scalar('tag:yaml.org,2002:str', v, style='|' if '\n' in v else None)


yaml.SafeDumper.add_representer(str, _str)

HEADER = """# Расписание публикаций EVNWEB в Instagram и Facebook.
# Публикатор (.github/workflows/publish.yml) каждые 30 минут публикует записи, у которых
# наступило время `at` (по Еревану) и стоит `approved: true`. Подпись можно править прямо здесь.
# Уже опубликованное записано в social/published.json и повторно не уходит.
"""

if __name__ == '__main__':
    main()

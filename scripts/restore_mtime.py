"""Готовит даты файлов к выкладке, чтобы lftp mirror заливал только изменённые файлы.

После git checkout у всех файлов дата «сейчас», и mirror заливал весь сайт заново.
Скрипт ставит каждому файлу дату его последнего коммита, а файлам, изменённым после
прошлой выкладки (коммит из файла .deployed-sha на сервере), ставит «сейчас», чтобы
они точно ушли на сервер, даже если размер не поменялся. Без прошлого коммита
(первая выкладка, файл не прочитался) «сейчас» получают все файлы.

    python3 scripts/restore_mtime.py site [ПРОШЛЫЙ_КОММИТ]
"""
import os
import subprocess
import sys
import time


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


folder = sys.argv[1] if len(sys.argv) > 1 else "site"
prev = sys.argv[2].strip() if len(sys.argv) > 2 else ""
files = set(git("ls-files", "-z", folder).stdout.split("\0")) - {""}

when = None
for part in git("log", "--format=%x00%ct", "--name-only", "-z", "--", folder).stdout.split("\0"):
    part = part.strip("\n")
    if part.isdigit() and part not in files:
        when = int(part)
    elif part in files and when:
        os.utime(part, (when, when))

diff = git("diff", "--name-only", "-z", f"{prev}..HEAD", "--", folder) if prev else None
if diff is None or diff.returncode:
    changed = files
    print(f"прошлая выкладка неизвестна ({prev or 'нет файла'}): заливаем всё")
else:
    changed = set(diff.stdout.split("\0")) & files
now = time.time()
for f in changed:
    os.utime(f, (now, now))
print(f"файлов: {len(files)}, изменено с прошлой выкладки: {len(changed)}")
for f in sorted(changed)[:50]:
    print("  ", f)

"""Ставит каждому файлу в папке дату его последнего коммита.

После git checkout у всех файлов дата «сейчас», и lftp mirror заливает весь сайт заново.
С датами из истории на сервер уходят только файлы, изменённые с прошлой выкладки.

    python3 scripts/restore_mtime.py site
"""
import os
import subprocess
import sys

folder = sys.argv[1] if len(sys.argv) > 1 else "site"
files = set(subprocess.run(["git", "ls-files", "-z", folder], capture_output=True, text=True, check=True).stdout.split("\0")) - {""}
log = subprocess.run(["git", "log", "--format=%x00%ct", "--name-only", "-z", "--", folder],
                     capture_output=True, text=True, check=True).stdout
done = 0
when = None
for part in log.split("\0"):
    part = part.strip("\n")
    if not part:
        continue
    if part.isdigit() and part not in files:
        when = int(part)
        continue
    if part in files and when:
        os.utime(part, (when, when))
        files.discard(part)
        done += 1
print(f"даты восстановлены: {done}, без истории: {len(files)}")

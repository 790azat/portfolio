# Автопубликация в Instagram и Facebook

1. Фабрика (`/mnt/project-files/social/factory`) делает партию.
2. `python social/stage.py <папка фабрики> <партия> --start <понедельник>` кладёт JPEG/MP4 в `site/m/<партия>/`
   и добавляет записи в `schedule.yaml` с `approved: false`.
3. После слияния в main `deploy.yml` выкладывает файлы на evnweb.am/m/… (в robots.txt закрыто от поиска).
4. Когда партия одобрена, в `schedule.yaml` ставится `approved: true`.
5. `publish.yml` каждые 30 минут публикует записи, у которых наступило время (по Еревану), и пишет результат в `published.json`.

Секрет: `META_PAGE_TOKEN` (бессрочный токен страницы Facebook, к которой привязан бизнес-Instagram).
Ручной запуск: Actions → «Публикация в Instagram и Facebook» → Run workflow → check / dry-run / publish.
Если публикация не удалась, ошибка записывается в `published.json`, после 3 попыток запись пропускается.

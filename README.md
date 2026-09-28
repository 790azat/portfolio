# EVNWEB — портфолио Азата (evnweb.am)

Статический сайт-портфолио: услуги, демо-проекты со скриншотами, коммерческие предложения (PDF) и контакты.

- `site/` — сам сайт (HTML, CSS, JS, картинки, PDF), выкладывается как есть.
- Три языка: армянский на главной (`/`), русский `/ru/`, английский `/en/`. Страницы собираются из `src/page.html` (разметка) и `src/strings.json` (тексты, у каждого ключа `hy`/`ru`/`en`) командой `python3 scripts/build.py`. Готовые `site/index.html`, `site/ru/index.html`, `site/en/index.html` коммитятся; руками их не правим, иначе проверка упадёт.
- `scripts/check.py` — проверка ссылок, картинок и разметки. Запускается на каждый PR и перед выкладкой.
- `.github/workflows/deploy.yml` — при каждом изменении `main` заливает `site/` по SFTP на SmartApe.

## Как вносятся изменения

Работа идёт в отдельной ветке → pull request → проверка → слияние в `main` → автоматическая выкладка.

## Настройки (GitHub → Settings → Secrets and variables → Actions)

Секреты: `SFTP_USER`, `SFTP_PASSWORD` (те же, что в репозитории `poschitay-site`).

Переменные (необязательно): `SFTP_PATH` — папка на сервере, по умолчанию `www/evnweb.am` (создаётся, если её нет);
`SFTP_HOST` (`shared-33.smartape.net`), `SFTP_PORT` (`22122`).

Выкладка зеркалит `site/` на сервер: файлы, которых нет в `site/`, удаляются (кроме `.well-known/`).

## Локальный просмотр

    cd site && python3 -m http.server 8080

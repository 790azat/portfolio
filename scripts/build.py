"""Собирает три языковые версии сайта из шаблона src/page.html и переводов src/strings.json.

    python3 scripts/build.py          # записать site/index.html (hy), site/ru/index.html, site/en/index.html
    python3 scripts/build.py --check  # только проверить, что собранные файлы совпадают с шаблоном

Тексты правятся в src/strings.json (у каждого ключа три языка), разметка в src/page.html.
Готовые HTML-файлы лежат в site/ и выкладываются как есть.
"""
import html
import json
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://evnweb.am/"

# язык: (папка, подпись в переключателе, og:locale)
LANGS = {
    "hy": ("", "Հայ", "hy_AM"),
    "ru": ("ru/", "Рус", "ru_RU"),
    "en": ("en/", "Eng", "en_US"),
}

TG_ICON = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.9 4.3 18.8 19c-.2 1-.9 1.3-1.7.8l-4.6-3.4-2.2 2.1c-.3.3-.5.5-1 .5l.3-4.7 8.6-7.8c.4-.3-.1-.5-.6-.2L6.9 13 '
           '2.4 11.6c-1-.3-1-1 .2-1.5L20.5 3.2c.8-.3 1.6.2 1.4 1.1Z"/></svg>')

# Армянская версия на главной: если человек раньше выбрал русский или английский, сразу открываем его язык.
REDIRECT = ("<script>try{var l=localStorage.getItem('lang');if(l==='ru'||l==='en')location.replace('/'+l+'/'+location.hash)}catch(e){}</script>\n")


def build():
    tpl = (ROOT / "src/page.html").read_text(encoding="utf-8")
    strings = json.loads((ROOT / "src/strings.json").read_text(encoding="utf-8"))
    for key, tr in strings.items():
        missing = set(LANGS) - set(tr)
        if missing:
            sys.exit(f"strings.json: у ключа {key} нет перевода {sorted(missing)}")

    alternates = "\n".join(f'<link rel="alternate" hreflang="{code}" href="{BASE}{d}">' for code, (d, _, _) in LANGS.items())
    alternates += f'\n<link rel="alternate" hreflang="x-default" href="{BASE}">'

    pages = {}
    for lang, (folder, _, locale) in LANGS.items():
        root = "../" if folder else ""
        switcher = '<div class="lang">' + "".join(
            f'<a href="{root}{d}" hreflang="{code}" lang="{code}" data-lang="{code}"'
            + (' class="on" aria-current="page"' if code == lang else "") + f">{label}</a>"
            for code, (d, label, _) in LANGS.items()
        ) + "</div>"
        values = {
            "lang": lang, "root": root, "url": BASE + folder, "og_locale": locale,
            "alternates": alternates, "switcher": switcher, "tg_icon": TG_ICON,
            "redirect": REDIRECT if lang == "hy" else "",
        }

        def sub(m):
            key, flt = m.group(1), m.group(2)
            if key in values:
                return values[key]
            if key not in strings:
                sys.exit(f"page.html: ключа {key} нет в strings.json")
            text = strings[key][lang]
            return urllib.parse.quote(text, safe="!") if flt == "url" else html.escape(text)

        out = re.sub(r"\{\{(\w+)(?:\|(\w+))?\}\}", sub, tpl)
        pages[SITE / folder / "index.html"] = out

    urls = "".join(f"<url><loc>{BASE}{d}</loc></url>" for d, _, _ in LANGS.values())
    pages[SITE / "sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                                   f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    return pages


if __name__ == "__main__":
    pages = build()
    if "--check" in sys.argv:
        stale = [str(p.relative_to(ROOT)) for p, text in pages.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            sys.exit("Не пересобраны (запустите python3 scripts/build.py): " + ", ".join(stale))
        print("OK: языковые версии совпадают с шаблоном")
    else:
        for path, text in pages.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print("записан", path.relative_to(ROOT))

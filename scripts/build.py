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


# Шрифты, которые нужны первому экрану: подгружаем заранее, чтобы текст не «прыгал»
PRELOAD = {
    "hy": ["NotoSansArmenian-400-armenian", "NotoSerifArmenian-700-armenian"],
    "ru": ["NotoSans-400-cyrillic", "NotoSerif-700-cyrillic"],
    "en": ["NotoSans-400-latin", "NotoSerif-700-latin"],
}

# Цены для разметки schema.org: ключ заголовка услуги в strings.json и цена «от» в драмах
OFFERS = [("p1_h", 150000), ("p2_h", 280000), ("p3_h", 450000), ("p4_h", 400000), ("p5_h", 650000), ("p6_h", 25000)]


def webp_size(path):
    """Ширина и высота картинки WebP (VP8, VP8L, VP8X) по заголовку файла."""
    b = path.read_bytes()[:30]
    kind = b[12:16]
    if kind == b"VP8 ":
        return int.from_bytes(b[26:28], "little") & 0x3FFF, int.from_bytes(b[28:30], "little") & 0x3FFF
    if kind == b"VP8L":
        v = int.from_bytes(b[21:25], "little")
        return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":
        return int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1
    return None


def add_img_sizes(page, folder):
    """Проставляет width/height картинкам: браузер заранее знает размер, страница не сдвигается при загрузке."""
    def fix(m):
        tag, src = m.group(0), m.group(1)
        if " width=" in tag or not src.endswith(".webp"):
            return tag
        size = webp_size(SITE / folder / src)
        return tag[:-1] + f' width="{size[0]}" height="{size[1]}">' if size else tag
    return re.sub(r'<img [^>]*?src="([^"]+)"[^>]*>', fix, page)


def jsonld(lang, strings, url):
    t = lambda k: strings[k][lang]
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ProfessionalService",
                "@id": BASE + "#business",
                "name": "EVNWEB",
                "url": url,
                "logo": BASE + "assets/img/logo-180.png",
                "image": BASE + "assets/img/og.png",
                "description": t("ld_desc"),
                "telephone": "+37493401179",
                "email": "vip.azatazat@gmail.com",
                "founder": {"@type": "Person", "name": t("ld_person")},
                "address": {"@type": "PostalAddress", "addressLocality": t("ld_city"), "addressCountry": "AM"},
                "geo": {"@type": "GeoCoordinates", "latitude": 40.1792, "longitude": 44.4991},
                "areaServed": {"@type": "Country", "name": "Armenia"},
                "availableLanguage": ["hy", "ru", "en"],
                "priceRange": "150000–1500000 AMD",
                "currenciesAccepted": "AMD",
                "sameAs": ["https://t.me/+37493401179", "https://www.instagram.com/evnweb/"],
                "contactPoint": {"@type": "ContactPoint", "telephone": "+37493401179", "contactType": "customer service",
                                 "availableLanguage": ["Armenian", "Russian", "English"]},
                "hasOfferCatalog": {
                    "@type": "OfferCatalog",
                    "name": t("ld_catalog"),
                    "itemListElement": [
                        {"@type": "Offer", "itemOffered": {"@type": "Service", "name": t(key)},
                         "priceSpecification": {"@type": "PriceSpecification", "minPrice": price, "priceCurrency": "AMD"}}
                        for key, price in OFFERS
                    ],
                },
            },
            {"@type": "WebSite", "@id": BASE + "#website", "url": BASE, "name": "EVNWEB", "inLanguage": ["hy", "ru", "en"],
             "publisher": {"@id": BASE + "#business"}},
            {"@type": "WebPage", "url": url, "name": t("title"), "description": t("description"), "inLanguage": lang,
             "isPartOf": {"@id": BASE + "#website"}, "about": {"@id": BASE + "#business"}},
        ],
    }
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{body}</script>'


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
            "og_alternates": "\n".join(f'<meta property="og:locale:alternate" content="{loc}">'
                                       for code, (_, _, loc) in LANGS.items() if code != lang),
            "preload": "\n".join(f'<link rel="preload" href="{root}assets/fonts/{f}.woff2" as="font" type="font/woff2" crossorigin>'
                                 for f in PRELOAD[lang]),
            "jsonld": jsonld(lang, strings, BASE + folder),
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
        pages[SITE / folder / "index.html"] = add_img_sizes(out, folder)

    links = "".join(f'<xhtml:link rel="alternate" hreflang="{code}" href="{BASE}{d}"/>' for code, (d, _, _) in LANGS.items())
    links += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}"/>'
    urls = "".join(f"\n<url><loc>{BASE}{d}</loc>{links}<changefreq>weekly</changefreq><priority>{'1.0' if not d else '0.9'}</priority></url>"
                   for d, _, _ in LANGS.values())
    pages[SITE / "sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
                                   f'{urls}\n</urlset>\n')
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

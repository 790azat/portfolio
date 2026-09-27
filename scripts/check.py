"""Проверка сайта перед выкладкой: все локальные ссылки и картинки существуют, HTML без незакрытых тегов."""
import html.parser
import pathlib
import re
import sys

SITE = pathlib.Path(__file__).resolve().parent.parent / "site"
VOID = {"meta", "link", "img", "br", "input", "hr", "source"}
errors = []


class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.refs = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)
        for name, value in attrs:
            if name in ("href", "src", "data-full") and value:
                self.refs.append(value)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            errors.append(f"лишний или перепутанный </{tag}>")


for page in SITE.glob("*.html"):
    p = Parser()
    p.feed(page.read_text(encoding="utf-8"))
    if p.stack:
        errors.append(f"{page.name}: не закрыты теги {p.stack}")
    for ref in p.refs:
        if re.match(r"^(https?:|mailto:|tel:|viber:|data:|#)", ref) or ref == "#":
            continue
        target = SITE / ref.split("?")[0].split("#")[0]
        if not target.exists():
            errors.append(f"{page.name}: нет файла {ref}")

for css in SITE.rglob("*.css"):
    for ref in re.findall(r"url\(([^)]+)\)", css.read_text(encoding="utf-8")):
        ref = ref.strip("'\"")
        if not ref.startswith("data:") and not (css.parent / ref).exists():
            errors.append(f"{css.relative_to(SITE)}: нет файла {ref}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("OK: ссылки и разметка в порядке")

"""Собирает блок «Реализованные проекты» в src/page.html из src/projects.json.

    python3 scripts/projects.py            # обновить блок в src/page.html и тексты pj_* в src/strings.json
    python3 scripts/projects.py --images DIR  # ещё и сделать картинки из DIR/<shot>.jpg (полные и превью)

Картинки лежат в site/assets/img/projects/: <key>-<n>.webp (для просмотра) и <key>-t.webp (превью карточки).
После этого запустите python3 scripts/build.py.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / "site/assets/img/projects"
START, END = "<!-- projects:start -->", "<!-- projects:end -->"
CAM = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h3l2-3h6l2 3h3a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1Z"/>'
       '<circle cx="12" cy="13" r="4"/></svg>')


def images(src):
    from PIL import Image
    IMG.mkdir(parents=True, exist_ok=True)
    for p in projects:
        for n, shot in enumerate(p["shots"], 1):
            im = Image.open(pathlib.Path(src) / f"{shot}.jpg").convert("RGB")
            if im.width > 1600:
                im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
            im.save(IMG / f"{p['key']}-{n}.webp", quality=82, method=6)
            if n == 1:  # превью 16:10, верх страницы
                w = im.width; h = min(im.height, round(w * 10 / 16))
                t = im.crop((0, 0, w, h)).resize((720, round(720 * h / w)), Image.LANCZOS)
                t.save(IMG / f"{p['key']}-t.webp", quality=80, method=6)


def card(p):
    k, name = p["key"], p["name"]
    cap = f"{name} · {{{{pj_{k}_cat}}}}"
    full = lambda n: f"{{{{root}}}}assets/img/projects/{k}-{n}.webp"
    bar = p["domain"] or name.lower()
    extra = "".join(f'<button hidden data-full="{full(n)}" data-cap="{cap}" aria-label="{cap}"></button>'
                    for n in range(2, len(p["shots"]) + 1))
    return (f'    <article class="pj" data-g>\n'
            f'      <button class="pj__shot" data-full="{full(1)}" data-cap="{cap}" aria-label="{cap}">'
            f'<span class="pj__bar"><i></i><i></i><i></i><b>{bar}</b></span>'
            f'<img src="{{{{root}}}}assets/img/projects/{k}-t.webp" alt="{cap}" loading="lazy">'
            f'<span class="pj__n">{CAM}</span></button>{extra}\n'
            f'      <div class="pj__body"><span class="case__tag">{{{{pj_{k}_cat}}}}</span><h3>{name}</h3><p>{{{{pj_{k}_desc}}}}</p></div>\n'
            f'    </article>\n')


projects = json.loads((ROOT / "src/projects.json").read_text(encoding="utf-8"))
if "--images" in sys.argv:
    images(sys.argv[sys.argv.index("--images") + 1])

page_path = ROOT / "src/page.html"
page = page_path.read_text(encoding="utf-8")
a, b = page.index(START) + len(START), page.index(END)
page = page[:a] + '\n  <div class="projects">\n' + "".join(card(p) for p in projects) + "  </div>\n  " + page[b:]
page_path.write_text(page, encoding="utf-8")

s_path = ROOT / "src/strings.json"
strings = json.loads(s_path.read_text(encoding="utf-8"))
strings = {k: v for k, v in strings.items() if not k.startswith("pj_")}
for p in projects:
    strings[f"pj_{p['key']}_cat"] = p["cat"]
    strings[f"pj_{p['key']}_desc"] = p["desc"]
s_path.write_text("{\n" + ",\n".join(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
                                     for k, v in strings.items()) + "\n}\n", encoding="utf-8")
print(f"{len(projects)} projects")

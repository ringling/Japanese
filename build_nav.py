#!/usr/bin/env python3
"""Regenerate assets/nav-tree.js and inject the sidebar scripts into every page.

Run from the Japansk/ directory after adding a page:  python3 build_nav.py
Idempotent. Only tracked + untracked-but-not-ignored .html files are included.
"""
import html as htmllib
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

files = subprocess.run(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    capture_output=True, text=True, check=True,
).stdout.split("\0")
pages = sorted({f for f in files if f.endswith(".html")
                and "http-equiv=\"refresh\"" not in open(f, encoding="utf-8").read(400)})


def title_of(path):
    m = re.search(r"<title>(.*?)</title>", open(path, encoding="utf-8").read(), re.S)
    return htmllib.unescape(m.group(1)).strip() if m else os.path.basename(path)


def leaf(path, label=None):
    return {"label": label or title_of(path), "href": path}


used = set()


def take(path, label=None):
    used.add(path)
    return leaf(path, label)


DATED = re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日_しゅくだい\.html$")
by_year = {}
for p in pages:
    m = DATED.match(os.path.basename(p))
    if m and p.startswith("2025-2026/files/"):
        y, mo, d = map(int, m.groups())
        by_year.setdefault(y, []).append(((mo, d), take(p, f"{mo}月{d}日 しゅくだい")))
homework = [
    {"label": f"{y}年", "children": [n for _, n in sorted(v, reverse=True)]}
    for y, v in sorted(by_year.items(), reverse=True)
]
if homework:
    homework[0]["open"] = True

recaps = [take(p, "Lesson " + re.search(r"_l(\d+)_", p).group(1) + " 復習")
          for p in pages if re.search(r"復習/marugoto_a2_l\d+_recap\.html$", p)]

week = {}
for p in pages:
    m = re.match(r"files/jlpt_n5_w(\d)_(\w+)\.html$", p)
    if m:
        week.setdefault(m.group(1), []).append(take(p, m.group(2).capitalize()))
week_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weeks = [{"label": f"Week {w}", "children": sorted(v, key=lambda n: week_order.index(n["label"]))}
         for w, v in sorted(week.items())]

a2 = [
    take("2025-2026/index.html", "クラスノート — 全体"),
    {"label": "しゅくだい", "children": homework},
    {"label": "復習 (Lesson recaps)", "children": recaps},
]
for p, lab in [("2025-2026/anki.html", "たんごカード"),
               ("2025-2026/files/katakana-reading.html", "カタカナ読解")]:
    if p in pages:
        a2.append(take(p, lab))

jlpt = [
    {"label": "Planning", "children": [take(p) for p in
        ["files/jlpt_n5_full_schedule.html", "files/jlpt_pacing_tracker.html", "files/jlpt_n5_pensum.html"] if p in pages]},
    {"label": "Daily plans", "children": weeks},
    {"label": "Study tools", "children": [take(p) for p in
        ["files/jlpt_n5_kanji_tracker.html", "files/jlpt_n5_vocab_flashcards.html",
         "files/jlpt_n5_grammar_tool.html", "files/jlpt_n5_grammar_gap_check.html"] if p in pages]},
]

grammar = [take(p, re.sub(r"\s*Grammar Sheet\s*$", "", title_of(p)))
           for p in pages if re.match(r"grammar/\d+_.*\.html$", p)]

tree = [
    take("index.html", "ホーム"),
    {"label": "A2-2 クラスノート 2025–2026", "open": True, "children": a2},
    {"label": "文法 (Grammar sheets)", "children": grammar},
    {"label": "読み物", "children": [take("yobanashi/index.html", "夜話 — Bedtime Stories")]},
    {"label": "JLPT N5", "children": jlpt},
]

orphans = [p for p in pages if p not in used]
if orphans:
    tree.append({"label": "Other", "children": [leaf(p) for p in orphans]})

os.makedirs("assets", exist_ok=True)
with open("assets/nav-tree.js", "w", encoding="utf-8") as f:
    f.write("window.SITE_TREE = " + json.dumps(tree, ensure_ascii=False, indent=1) + ";\n")

MARK = re.compile(r'\n*<script src="[^"]*assets/nav-tree\.js"></script>\n<script src="[^"]*assets/nav\.js" defer></script>\n*')
for p in pages:
    rel = "../" * p.count("/") + "assets/"
    tag = f'<script src="{rel}nav-tree.js"></script>\n<script src="{rel}nav.js" defer></script>\n'
    src = open(p, encoding="utf-8").read()
    src = MARK.sub("\n", src)  # then re-add exactly one block before </body>
    if "</body>" not in src:
        print("skip (no </body>):", p)
        continue
    src = src.replace("</body>", tag.lstrip("\n") + "</body>", 1)
    open(p, "w", encoding="utf-8").write(src)

print(f"{len(pages)} pages, {len(orphans)} orphans")

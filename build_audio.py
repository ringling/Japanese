#!/usr/bin/env python3
"""Build 2025-2026/files/audio.html: every audio clip used on the しゅくだい pages, in one page.

Run from anywhere:  python3 build_audio.py   (build_nav.py runs it too, so a new homework page
is picked up automatically). Idempotent.

For each <audio> on a 2025-2026/files/*しゅくだい.html page it records the source file and a short
description (the exercise <h3>, the row label, or the grammar example sentence for AI clips).
The lesson and track number come from the real file name (aliases are symlinks):
  rikai/155_8_4[1].mp3      → りかい, track 155, lesson 8
  katsudoo/097_9_3_1...mp3  → かつどう, track 097, lesson 9
  tts/L9_bunpou/2-1.mp3     → AI (Gemini TTS), lesson 9
Clips without a lesson in the name (can-do tracks) take the lesson of the page section they sit in.
Each clip is listed once (first seen on the newest page), grouped by lesson → book.
"""
import html as H
import os
import re
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
A2 = os.path.join(ROOT, '2025-2026')
FILES = os.path.join(A2, 'files')
OUT = os.path.join(FILES, 'audio.html')
DATED = re.compile(r'^(\d{4})年(\d{1,2})月(\d{1,2})日_しゅくだい\.html$')
BOOK = {'rikai': 'りかい', 'katsudoo': 'かつどう', 'tts': 'AI音声'}
BOOK_ORDER = {'かつどう': 0, 'りかい': 1, 'AI音声': 2}
KANJI_NUM = '〇一二三四五六七八九'
# まるごと 初級2 A2 かつどう — ないようち らん (p.10). Topic, lesson title.
LESSONS = {
    1: ('新しい 友だち', 'いい なまえですね'), 2: ('新しい 友だち', 'めがねを かけている 人です'),
    3: ('店で 食べる', 'おすすめは 何ですか'), 4: ('店で 食べる', 'どうやって 食べますか'),
    5: ('沖縄旅行', 'ぼうしを 持っていった ほうが いいですよ'), 6: ('沖縄旅行', 'イルカの ショーが 見られます'),
    7: ('日本まつり', '雨が ふったら、どう しますか'), 8: ('日本まつり', 'コンサートは もう はじまりましたか'),
    9: ('とくべつな 日', 'お正月は どう していましたか'), 10: ('とくべつな 日', 'いい ことが ありますように'),
}


def clean(s):
    s = re.sub(r'<rt>.*?</rt>|<rp>.*?</rp>', '', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', H.unescape(s)).strip()


def lesson_of_text(s):
    m = re.search(r'だい\s*(\d+)\s*か', s) or re.search(r'\bL(\d+)\b', s)
    return int(m.group(1)) if m else None


class Page(HTMLParser):
    """Collects (src, h2, h3, block_label, row_label, example) for every <audio>."""

    CAPTURE = {'h2', 'h3'}
    CLS_CAPTURE = {'audio-block-label', 'audio-row-label', 'example-jp', 'masthead-mark'}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.state = {'h2': '', 'h3': '', 'audio-block-label': '', 'audio-row-label': '',
                      'example-jp': '', 'masthead-mark': ''}
        self.cap = None          # [key, depth, buffer]
        self.depth = 0
        self.in_audio = False
        self.clips = []
        self.cur_src = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in ('br', 'img', 'input', 'source', 'meta', 'link', 'hr'):
            self.depth += 1
        if self.cap:
            self.cap[2].append(self.get_starttag_text() or '')
        cls = set((a.get('class') or '').split())
        key = tag if tag in self.CAPTURE else next(iter(cls & self.CLS_CAPTURE), None)
        if key and not self.cap:
            if key == 'h2':  # a new section resets the finer context
                self.state.update({'h3': '', 'audio-block-label': '', 'example-jp': ''})
            if key == 'h3':
                self.state.update({'audio-block-label': '', 'example-jp': ''})
            if key == 'audio-block-label':
                self.state['audio-row-label'] = ''
            self.cap = [key, self.depth, []]
        if tag == 'audio':
            self.in_audio = True
            self.cur_src = a.get('src')
        if tag == 'source' and self.in_audio and not self.cur_src:
            self.cur_src = a.get('src')

    def handle_endtag(self, tag):
        if self.cap and self.depth == self.cap[1]:
            key, _, buf = self.cap
            self.state[key] = clean(''.join(buf))
            self.cap = None
        elif self.cap:
            self.cap[2].append(f'</{tag}>')
        if tag == 'audio':
            if self.cur_src:
                self.clips.append((self.cur_src, dict(self.state)))
            self.in_audio = False
            self.cur_src = None
            self.state['audio-row-label'] = ''
        self.depth -= 1

    def handle_data(self, d):
        if self.cap:
            self.cap[2].append(d)

    def handle_entityref(self, name):
        self.handle_data(f'&{name};')

    def handle_charref(self, name):
        self.handle_data(f'&#{name};')


def classify(src):
    """→ (book, track:int|None, lesson:int|None, real_rel) or None if the file is missing."""
    path = os.path.normpath(os.path.join(FILES, src))
    if not os.path.exists(path):
        return None
    real = os.path.realpath(path)
    rel = os.path.relpath(real, os.path.join(A2, 'audio'))
    top, name = rel.split(os.sep)[0], os.path.basename(real)
    if top == 'tts':
        m = re.match(r'L(\d+)_', rel.split(os.sep)[1])
        return 'AI音声', None, int(m.group(1)) if m else None, rel
    m = re.match(r'^(\d{3})n?_(\d+)_', name)
    if m:
        return BOOK.get(top, top), int(m.group(1)), int(m.group(2)), rel
    m = re.match(r'^track_(\d{3})', name) or re.match(r'^(\d{3})', name)
    track = int(m.group(1)) if m else None
    lesson = None
    if track is not None:  # copied alias: take the lesson from the original NNN_L_… file
        for o in sorted(os.listdir(os.path.dirname(real))):
            mo = re.match(rf'^{track:03d}n?_(\d+)_', o)
            if mo:
                lesson = int(mo.group(1))
                break
        rel = f'{top}/{track:03d}#{os.path.getsize(real)}'  # dedupe copies by track + size
    return BOOK.get(top, top), track, lesson, rel


def pages():
    out = []
    for f in os.listdir(FILES):
        m = DATED.match(f)
        if m:
            out.append((tuple(map(int, m.groups())), f))
    return [f for _, f in sorted(out, reverse=True)]


def describe(st, book):
    if book == 'AI音声' and st['example-jp']:
        return st['example-jp'], 'grammar example'
    h3 = st['h3'] or st['h2']
    label = st['audio-row-label'] or st['audio-block-label'].lstrip('▶ ').strip()
    return h3, label


def build():
    clips = {}      # real_rel → record
    lesson_titles = {}
    for f in pages():
        p = Page()
        p.feed(open(os.path.join(FILES, f), encoding='utf-8').read())
        y, mo, d = map(int, DATED.match(f).groups())
        for src, st in p.clips:
            c = classify(src)
            if not c:
                continue
            book, track, lesson, rel = c
            sec_lesson = lesson_of_text(st['h2'])
            if lesson is None:
                lesson = sec_lesson or lesson_of_text(st['h3'])
            if lesson is None:
                continue
            if rel in clips:
                continue
            what, label = describe(st, book)
            clips[rel] = dict(src=src, book=book, track=track, lesson=lesson, what=what, label=label,
                              page=f, date=f'{mo}月{d}日', variant=os.path.basename(src))
    return clips, lesson_titles


def track_key(c):
    return (BOOK_ORDER.get(c['book'], 9), c['track'] if c['track'] is not None else 999, c['variant'])


def render(clips, titles):
    by_lesson = {}
    for c in clips.values():
        by_lesson.setdefault(c['lesson'], []).append(c)
    lessons = sorted(by_lesson, reverse=True)
    pills = '\n'.join(f'    <a href="#l{n}">L{n}</a>' for n in lessons)
    secs = []
    for n in lessons:
        items = sorted(by_lesson[n], key=track_key)
        groups = []
        for book in sorted({c['book'] for c in items}, key=lambda b: BOOK_ORDER.get(b, 9)):
            rows, groups_by_what = [], {}
            for c in (x for x in items if x['book'] == book):  # already in track order
                groups_by_what.setdefault((c['what'], c['page']), []).append(c)
            for (what, page), cs in groups_by_what.items():
                lines = []
                for c in cs:
                    num = f"{c['track']:03d}" if c['track'] is not None else 'AI'
                    search = H.escape(f"{num} {book} L{n} {what} {c['label']}".lower(), quote=True)
                    lines.append(f'''        <div class="clip" data-search="{search}">
          <span class="clip-num">{num}</span>
          <span class="clip-label">{H.escape(c['label'])}</span>
          <audio controls preload="none" src="{H.escape(c['src'], quote=True)}"></audio>
        </div>''')
                rows.append(f'''      <div class="ex">
        <div class="ex-head"><span class="ex-what">{H.escape(what)}</span>
          <a class="clip-page" href="{H.escape(page, quote=True)}">{cs[0]['date']} しゅくだい →</a></div>
{chr(10).join(lines)}
      </div>''')
            note = ' <span class="ai-note">generated with Gemini TTS — not book audio</span>' if book == 'AI音声' else ''
            groups.append(f'    <h3 class="book">{book} <span class="count">{sum(1 for x in items if x["book"] == book)}</span>{note}</h3>\n' + '\n'.join(rows))
        mark = KANJI_NUM[n] if n < 10 else str(n)
        topic, ttl = LESSONS.get(n, ('', ''))
        title = f'「{H.escape(ttl)}」' if ttl else ''
        if topic:
            title += f' <span class="count">· {H.escape(topic)}</span>'
        secs.append(f'''  <section id="l{n}" class="lesson">
    <div class="section-head">
      <span class="section-num">{mark}</span>
      <h2>だい{n}か {title} <span class="count">{len(items)} clips</span></h2>
    </div>
{chr(10).join(groups)}
  </section>''')
    total = len(clips)
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>オーディオ · しゅくだい</title>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500;700&family=Noto+Serif+JP:wght@400;500;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --ink: #1a1a1a; --ink-soft: #3a3a3a; --paper: #f4efe6; --paper-soft: #ebe4d6; --paper-deep: #e2d9c4;
  --accent: #8b1a1a; --accent-soft: #b85450; --gold: #b8893d; --muted: #6b6357; --rule: #c9bfa9; --rule-soft: #ddd3bd;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 48px 24px; background: var(--paper); color: var(--ink);
  font-family: 'IBM Plex Sans', 'Noto Serif JP', sans-serif; line-height: 1.6;
  background-image: radial-gradient(circle at 15% 10%, rgba(184,137,61,0.05), transparent 40%), radial-gradient(circle at 85% 80%, rgba(139,26,26,0.04), transparent 40%); }}
.container {{ max-width: 880px; margin: 0 auto; }}
.page-nav {{ display: flex; justify-content: space-between; font-family: 'IBM Plex Mono', monospace; font-size: 11px;
  letter-spacing: 1px; padding-bottom: 14px; border-bottom: 1px solid var(--rule); margin-bottom: 36px; }}
.page-nav a {{ color: var(--accent); text-decoration: none; }}
.page-nav .center {{ color: var(--muted); }}
.masthead {{ display: grid; grid-template-columns: auto 1fr; gap: 28px; align-items: center;
  border-bottom: 2px solid var(--ink); padding-bottom: 22px; margin-bottom: 28px; }}
.masthead-mark {{ font-family: 'Shippori Mincho', serif; font-size: 84px; line-height: 1; color: var(--accent); }}
.masthead h1 {{ font-family: 'Shippori Mincho', serif; font-weight: 500; font-size: 34px; margin: 0 0 6px; letter-spacing: 2px; }}
.masthead .sub {{ font-size: 13px; color: var(--muted); }}
.tools {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 36px; }}
.tools input {{ flex: 1 1 220px; font: inherit; font-size: 14px; padding: 7px 12px; background: var(--paper-soft);
  color: var(--ink); border: 1px solid var(--rule); border-radius: 2px; }}
.tools a {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 1px; color: var(--accent);
  background: var(--paper-soft); border: 1px solid var(--rule); padding: 5px 12px; text-decoration: none; border-radius: 2px; }}
.tools a:hover {{ background: var(--paper-deep); }}
.section-head {{ display: flex; align-items: baseline; gap: 16px; border-bottom: 1px solid var(--rule);
  padding-bottom: 10px; margin: 48px 0 8px; }}
.section-num {{ font-family: 'Shippori Mincho', serif; font-size: 28px; color: var(--accent); }}
.section-head h2 {{ font-family: 'Shippori Mincho', serif; font-weight: 500; font-size: 22px; margin: 0; }}
.count {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--muted); font-weight: 400; letter-spacing: 1px; }}
h3.book {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
  color: var(--accent); margin: 24px 0 8px; font-weight: 500; }}
.ai-note {{ color: var(--muted); text-transform: none; letter-spacing: 0; font-style: italic; margin-left: 6px; }}
.ex {{ padding: 12px 0 10px; border-bottom: 1px dashed var(--rule-soft); }}
.ex-head {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 12px; align-items: baseline; margin-bottom: 4px; }}
.ex-what {{ font-family: 'Noto Serif JP', serif; font-size: 14px; color: var(--ink-soft); }}
.clip {{ display: grid; grid-template-columns: 40px minmax(90px, 170px) 1fr; gap: 10px; align-items: center; padding: 2px 0; }}
.clip-num {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--gold); }}
.clip-label {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }}
.clip audio {{ width: 100%; max-width: 420px; height: 30px; }}
.clip-page {{ font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: var(--muted); text-decoration: none; white-space: nowrap; }}
.clip-page:hover {{ color: var(--accent); }}
.hidden {{ display: none; }}
footer {{ margin-top: 60px; padding-top: 20px; border-top: 1px solid var(--rule); font-family: 'IBM Plex Mono', monospace;
  font-size: 10px; color: var(--muted); text-align: center; }}
@media (max-width: 600px) {{ body {{ padding: 28px 16px; }} .masthead-mark {{ font-size: 60px; }} .clip {{ grid-template-columns: 36px 1fr; }} .clip audio {{ grid-column: 1 / -1; }} }}
</style>
<link rel="stylesheet" href="../../assets/theme.css">
<script src="../../assets/theme.js"></script>
</head>
<body>
<div class="container">

  <nav class="page-nav">
    <a href="../index.html">← ホーム</a>
    <span class="center">オーディオ · まるごと A2-2</span>
    <span style="color:var(--rule)">—</span>
  </nav>

  <header class="masthead">
    <div class="masthead-mark">音</div>
    <div>
      <h1>オーディオ</h1>
      <div class="sub">Every audio clip from the しゅくだい pages in one place, newest lesson first: {total} clips.
        Each clip has its track number, the exercise it belongs to and a link to the homework page that uses it.
        Built by <code>build_audio.py</code>, which runs with <code>build_nav.py</code> whenever a new page is added.</div>
    </div>
  </header>

  <div class="tools">
    <input id="q" type="search" placeholder="Filter: track, lesson, exercise… (e.g. 097, L9, かいわ)" autocomplete="off">
{pills}
  </div>

{chr(10).join(secs)}

  <footer>まるごと<ruby>初級<rt>しょきゅう</rt></ruby>2 A2 · オーディオ · generated by build_audio.py</footer>
</div>

<script>
(function () {{
  var q = document.getElementById('q');
  // only one clip plays at a time
  document.addEventListener('play', function (e) {{
    document.querySelectorAll('audio').forEach(function (a) {{ if (a !== e.target) a.pause(); }});
  }}, true);
  q.addEventListener('input', function () {{
    var t = q.value.trim().toLowerCase();
    document.querySelectorAll('.clip').forEach(function (c) {{
      c.classList.toggle('hidden', t && c.dataset.search.indexOf(t) < 0);
    }});
    document.querySelectorAll('.ex').forEach(function (e) {{
      e.classList.toggle('hidden', !e.querySelector('.clip:not(.hidden)'));
    }});
    document.querySelectorAll('section.lesson').forEach(function (s) {{
      s.classList.toggle('hidden', !s.querySelector('.clip:not(.hidden)'));
    }});
    document.querySelectorAll('h3.book').forEach(function (h) {{
      var n = h.nextElementSibling, any = false;
      while (n && n.classList.contains('ex')) {{ if (!n.classList.contains('hidden')) any = true; n = n.nextElementSibling; }}
      h.classList.toggle('hidden', !any);
    }});
  }});
}})();
</script>
</body>
</html>
'''


def main():
    clips, titles = build()
    open(OUT, 'w', encoding='utf-8').write(render(clips, titles))
    per = {}
    for c in clips.values():
        per[c['lesson']] = per.get(c['lesson'], 0) + 1
    print(f'audio.html: {len(clips)} clips · ' + ' '.join(f'L{k}:{v}' for k, v in sorted(per.items())))


if __name__ == '__main__':
    main()

# /// script
# requires-python = ">=3.10"
# dependencies = ["youtube-transcript-api", "fugashi", "unidic-lite"]
# ///
"""Build a 夜話 story for index.html.

Usage: .venv/bin/python build_story.py <video_id> [--lesson N]

1. Uses <id>_ja.txt / <id>_en.txt (downloads them with get-transcript.py if missing).
2. Adds furigana to every kanji word (fugashi + UniDic), applying reading fixes
   from stories/<id>.edit.json → "readings": {"都": "みやこ"}.
3. Lists the story's content words that are new: not in 入門 / 初級1 / A2-2 up to
   lesson N (vocabulary indexes in ../2025-2026/books/vocab_index.json) and not in Anki.
   Glosses / display forms come from stories/<id>.edit.json → "words":
   {"lemma": {"en": "meaning", "w": "display form", "r": "reading"}}; "skip": [lemmas];
   per-line reading fixes: "line_readings": {"5": {"柳": "やなぎ"}}. Missing glosses print as TODO.
4. Writes stories/<id>.json and regenerates stories.js (all stories) for the page.
"""
import json, re, subprocess, sys
from pathlib import Path

import fugashi

HERE = Path(__file__).parent
VAULT = HERE.parent / '2025-2026'
CONTENT_POS = {'名詞', '動詞', '形容詞', '副詞', '形状詞'}
SKIP_POS2 = {'数詞', '固有名詞', '非自立可能'}
KANJI = re.compile(r'[一-鿿々]')


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in (s or ''))


def ruby(surface, reading):
    if not KANJI.search(surface) or not reading or hira(surface) == reading:
        return surface
    s, r = surface, reading
    pre = ''
    while s and r and s[0] == r[0] and not KANJI.match(s[0]):
        pre += s[0]; s, r = s[1:], r[1:]
    post = ''
    while s and r and s[-1] == r[-1] and not KANJI.match(s[-1]):
        post = s[-1] + post; s, r = s[:-1], r[:-1]
    return f'{pre}<ruby>{s}<rt>{r}</rt></ruby>{post}' if s and r else surface


def known_forms(lesson):
    forms = set()
    idx = VAULT / 'books' / 'vocab_index.json'
    if idx.exists():
        for e in json.loads(idx.read_text(encoding='utf-8')):
            if e['seen_before'] or e['lesson'] <= lesson:
                w = e['word']
                dict_form = re.findall(r'【([^】0-9]+)', w)
                base = re.sub(r'【[^】]*】|\([^)]*\)', '', w)
                for f in base.split('／') + dict_form:
                    f = f.strip('～')
                    if f:
                        forms.add(f)
                for k in re.sub(r'\([^)]*\)', '', e['kanji']).split('／'):
                    if k:
                        forms.add(k.strip('～'))
    anki = (VAULT / 'anki.html').read_text(encoding='utf-8')
    for jp in re.findall(r'"jpHtml":"([^"]*)"', anki):
        plain = re.sub(r'<rt>.*?</rt>|<[^>]+>', '', jp)
        reading = ''.join(re.findall(r'<rt>(.*?)</rt>', jp))
        forms.add(plain)
        if reading:
            forms.add(reading)
    return forms


def fetch(video_id):
    if not (HERE / f'{video_id}_ja.txt').exists():
        subprocess.run([sys.executable, str(HERE / 'get-transcript.py'), video_id], cwd=HERE, check=True)


def build(video_id, lesson):
    fetch(video_id)
    ja = [l.strip() for l in (HERE / f'{video_id}_ja.txt').read_text(encoding='utf-8').splitlines() if l.strip()]
    en_path = HERE / f'{video_id}_en.txt'
    en = [l.strip() for l in en_path.read_text(encoding='utf-8').splitlines() if l.strip()] if en_path.exists() else []
    edit_path = HERE / 'stories' / f'{video_id}.edit.json'
    edit = json.loads(edit_path.read_text(encoding='utf-8')) if edit_path.exists() else {}
    fix = edit.get('readings', {})
    line_fix = {int(k) - 1: v for k, v in edit.get('line_readings', {}).items()}
    glosses = edit.get('words', {})
    skip_words = set(edit.get('skip', []))

    tagger = fugashi.Tagger()
    known = known_forms(lesson)
    lines_html, words = [], {}
    for i, line in enumerate(ja):
        out = ''
        lf = line_fix.get(i, {})
        for t in tagger(line):
            s = t.surface
            r = lf.get(s) or fix.get(s) or hira(t.feature.kana)
            out += ruby(s, r) if KANJI.search(s) else s
            f = t.feature
            if f.pos1 not in CONTENT_POS or f.pos2 in SKIP_POS2:
                continue
            lemma = (f.lemma or s).split('-')[0]
            lreading = fix.get(lemma) or hira(f.lForm)
            if not KANJI.search(lemma) and not lreading:
                continue
            if lemma in skip_words or lemma in known or lreading in known:
                continue
            g = glosses.get(lemma, {})
            w = words.setdefault(lemma, {'w': g.get('w', lemma), 'r': g.get('r', lreading), 'pos': f.pos1, 'en': g.get('en', ''), 'lines': []})
            if i not in w['lines']:
                w['lines'].append(i)
        lines_html.append(out)

    title_i = next((i for i, l in enumerate(ja) if re.match(r'^[「『][^。！？]+[」』]$', l)), -1)
    story = {
        'id': video_id,
        'title': ja[title_i].strip('「」『』') if title_i >= 0 else video_id,
        'titleEn': en[title_i].strip('"“”') if title_i >= 0 and title_i < len(en) else '',
        'source': f'https://www.youtube.com/watch?v={video_id}',
        'ja': ja, 'jaHtml': lines_html, 'en': en,
        'words': sorted(words.values(), key=lambda w: w['lines'][0]),
    }
    for w in story['words']:
        w['html'] = ruby(w['w'], w['r'])
    (HERE / 'stories').mkdir(exist_ok=True)
    (HERE / 'stories' / f'{video_id}.json').write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding='utf-8')
    todo = [k for k, w in words.items() if not w['en']]
    print(f"{story['title']}: {len(ja)} lines, {len(story['words'])} new words")
    if todo:
        print('TODO glosses:', ' '.join(f"{w}({words[w]['r']})" for w in todo))


def write_bundle():
    stories = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((HERE / 'stories').glob('*.json')) if not p.name.endswith('.edit.json')]
    (HERE / 'stories.js').write_text('window.STORIES = ' + json.dumps(stories, ensure_ascii=False) + ';\n', encoding='utf-8')
    print(f'stories.js: {len(stories)} stories')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    lesson = int(sys.argv[sys.argv.index('--lesson') + 1]) if '--lesson' in sys.argv else 7
    if '--lesson' in sys.argv:
        args = [a for a in args if a != str(lesson)]
    for vid in args:
        build(vid, lesson)
    write_bundle()

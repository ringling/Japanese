# /// script
# requires-python = ">=3.10"
# dependencies = ["youtube-transcript-api", "fugashi", "unidic-lite", "jamdict", "jamdict-data"]
# ///
"""Build a 夜話 story for the reader (index.html).

Usage: .venv/bin/python build_story.py <video_id> [--lesson N] [--strict] [--add-to-anki]

1. Uses <id>_ja.txt / <id>_en.txt / <id>_ja.times.json (downloads them with
   get-transcript.py if missing).
2. Adds furigana to every kanji word (fugashi + UniDic). Reading fixes come from
   overrides.json (shared) and stories/<id>.edit.json (this story, wins):
   "readings": {"都": "みやこ"}, "line_readings": {"5": {"柳": "やなぎ"}}.
3. Lists the content words that are new: not in 入門 / 初級1 / A2-2 up to lesson N
   (../2025-2026/books/vocab_index.json) and not in Anki. "skip": [lemmas] hides words.
   Glosses: edit.json "words" > overrides.json "words" > a JMdict draft that is written
   back into edit.json with "auto": true. Delete "auto" once you have checked the gloss.
4. Writes stories/<id>.json and stories/index.json (the reader loads these on demand).
--strict      exit 1 on missing/unchecked glosses or JA/EN line-count mismatch
--add-to-anki append the story's new words to ../2025-2026/anki.html (deck 夜話)
"""
import json, re, subprocess, sys
from pathlib import Path

import fugashi

import kana

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


def known_forms(lesson, story_id=None):
    forms = set()
    idx = VAULT / 'books' / 'vocab_index.json'
    if not idx.exists():
        sys.exit(f'{idx} is missing (books/ is local-only). Without it every known word would be listed as new.')
    if True:
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
    vocab = json.loads(re.search(r'const VOCAB = (\[.*?\]);\n', anki, re.S).group(1))
    for v in vocab:
        if story_id and v.get('story') == story_id:
            continue  # this story's own words stay in its list
        jp = v['jpHtml']
        plain = re.sub(r'<rt>.*?</rt>|<[^>]+>', '', jp)
        reading = ''.join(re.findall(r'<rt>(.*?)</rt>', jp))
        forms.add(plain)
        if reading:
            forms.add(reading)
    return forms


def fetch(video_id):
    if not (HERE / f'{video_id}_ja.txt').exists() or not (HERE / f'{video_id}_ja.times.json').exists():
        subprocess.run([sys.executable, str(HERE / 'get-transcript.py'), video_id], cwd=HERE, check=True)


def load_json(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


_jam = None


def draft_gloss(lemma, reading):
    """First JMdict sense for the lemma (a draft for the human to confirm)."""
    global _jam
    if _jam is None:
        from jamdict import Jamdict
        _jam = Jamdict()
    for key in (lemma, reading):
        if not key:
            continue
        res = _jam.lookup(key, lookup_chars=False)
        if res.entries:
            return ', '.join(g.text for g in res.entries[0].senses[0].gloss[:3])
    return ''


def build(video_id, lesson, problems):
    fetch(video_id)
    ja = [l.strip() for l in (HERE / f'{video_id}_ja.txt').read_text(encoding='utf-8').splitlines() if l.strip()]
    en_path = HERE / f'{video_id}_en.txt'
    en = [l.strip() for l in en_path.read_text(encoding='utf-8').splitlines() if l.strip()] if en_path.exists() else []
    times = load_json(HERE / f'{video_id}_ja.times.json', [])
    if en and len(en) != len(ja):
        problems.append(f'{video_id}: JA has {len(ja)} lines, EN has {len(en)} (paired by position)')
    if times and len(times) != len(ja):
        problems.append(f'{video_id}: {len(times)} timestamps for {len(ja)} lines; audio sync disabled')
        times = []

    shared = load_json(HERE / 'overrides.json', {})
    edit_path = HERE / 'stories' / f'{video_id}.edit.json'
    edit = load_json(edit_path, {})
    fix = {**shared.get('readings', {}), **edit.get('readings', {})}
    line_fix = {int(k) - 1: v for k, v in edit.get('line_readings', {}).items()}
    glosses = {**shared.get('words', {}), **edit.get('words', {})}
    skip_words = set(shared.get('skip', [])) | set(edit.get('skip', []))

    tagger = fugashi.Tagger()
    known = known_forms(lesson, video_id)
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
            w = words.setdefault(lemma, {'lemma': lemma, 'w': g.get('w', lemma), 'r': g.get('r', lreading), 'pos': f.pos1,
                                         'en': g.get('en', ''), 'draft': bool(g.get('auto')), 'lines': []})
            if i not in w['lines']:
                w['lines'].append(i)
        lines_html.append(out)

    drafted = False
    for lemma, w in words.items():
        if not w['en']:
            guess = draft_gloss(lemma, w['r'])
            if guess:
                w['en'], w['draft'] = guess, True
                edit.setdefault('words', {})[lemma] = {'en': guess, 'auto': True}
                drafted = True
    if drafted:
        edit_path.parent.mkdir(exist_ok=True)
        edit_path.write_text(json.dumps(edit, ensure_ascii=False, indent=1), encoding='utf-8')

    title_i = next((i for i, l in enumerate(ja) if re.match(r'^[「『][^。！？]+[」』]$', l)), -1)
    story = {
        'id': video_id,
        'title': ja[title_i].strip('「」『』') if title_i >= 0 else video_id,
        'titleEn': en[title_i].strip('"“”') if title_i >= 0 and title_i < len(en) else '',
        'source': f'https://www.youtube.com/watch?v={video_id}',
        'ja': ja, 'jaHtml': lines_html, 'en': en,
        'words': sorted(words.values(), key=lambda w: w['lines'][0]),
    }
    if times:
        story['times'] = times
    for w in story['words']:
        w['html'] = ruby(w['w'], w['r'])
        if not w['draft']:
            del w['draft']
    (HERE / 'stories').mkdir(exist_ok=True)
    (HERE / 'stories' / f'{video_id}.json').write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{story['title']}: {len(ja)} lines, {len(story['words'])} new words, {'audio sync' if times else 'no timestamps'}")
    todo = [w for w in story['words'] if not w['en']]
    review = [w['lemma'] for w in story['words'] if w.get('draft')]
    if todo:
        print('TODO glosses (no dictionary hit):', ' '.join(f"{w['lemma']}({w['r']})" for w in todo))
        problems.append(f'{video_id}: {len(todo)} words without a gloss')
    if review:
        print(f'REVIEW {len(review)} auto-drafted glosses in stories/{video_id}.edit.json (delete "auto" once checked):', ' '.join(review))
        problems.append(f'{video_id}: {len(review)} auto-drafted glosses not yet confirmed')
    return story


def write_index():
    items = []
    for p in sorted((HERE / 'stories').glob('*.json')):
        if p.name.endswith('.edit.json') or p.name == 'index.json':
            continue
        s = json.loads(p.read_text(encoding='utf-8'))
        items.append({'id': s['id'], 'title': s['title'], 'titleEn': s.get('titleEn', ''), 'source': s.get('source', ''),
                      'lines': len(s['ja']), 'words': len(s.get('words', [])), 'audio': bool(s.get('times'))})
    (HERE / 'stories' / 'index.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'stories/index.json: {len(items)} stories')


def add_to_anki(story):
    p = VAULT / 'anki.html'
    s = p.read_text(encoding='utf-8')
    m = re.search(r'const VOCAB = (\[.*?\]);\n', s, re.S)
    vocab = json.loads(m.group(1))
    have = {v['jpClean'] for v in vocab}
    deck = '夜話'
    new = []
    for w in story['words']:
        clean = re.sub(r'\(.*?\)', '', w['w'])
        if clean in have or w.get('draft'):
            continue
        new.append({'jpHtml': w['html'], 'jpClean': clean, 'romaji': kana.romaji(w['r'] or clean), 'en': w['en'], 'deck': deck, 'story': story['id']})
    if new:
        add = ''.join(',\n' + json.dumps(n, ensure_ascii=False, separators=(',', ':')) for n in new)
        end = m.end(1) - 1
        s = s[:end] + add + s[end:]
    if f"id: '{deck}'" not in s:
        d = s.index('const DECKS = [')
        close = s.index('];', d)
        s = s[:close] + f"  {{ id: '{deck}', name: '{deck}', label: '夜話 stories (new words)' }},\n" + s[close:]
    total = len(vocab) + len(new)
    decks = len(re.findall(r"^\s*\{ id: '", s[s.index('const DECKS = ['):], re.M)) - 1
    s = re.sub(r'<div class="home-sub">.*?</div>', f'<div class="home-sub">{total}語 across {decks} lesson decks</div>', s, count=1)
    p.write_text(s, encoding='utf-8')
    print(f'anki.html: {len(new)} words added ({total} total)')


if __name__ == '__main__':
    argv = sys.argv[1:]
    lesson = 7
    if '--lesson' in argv:
        i = argv.index('--lesson')
        lesson = int(argv[i + 1])
        del argv[i:i + 2]
    flags = {a for a in argv if a.startswith('--')}
    problems = []
    for vid in [a for a in argv if not a.startswith('--')]:
        story = build(vid, lesson, problems)
        if '--add-to-anki' in flags:
            if any(w.get('draft') for w in story['words']):
                print('anki: words with unchecked drafts are skipped; confirm and rerun to add them')
            add_to_anki(story)
    write_index()
    for p in problems:
        print('WARNING:', p)
    if '--strict' in flags and problems:
        sys.exit(1)

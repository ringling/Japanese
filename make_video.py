#!/usr/bin/env python3
"""Narrated grammar video: slides + Gemini TTS (Google AI Studio) → MP4.

Usage:
  python3 make_video.py 2025-2026/video/specs/L8_bunpou3.json [--force-audio]

Reads GOOGLE_AI_STUDIO_API_KEY from .env. For each slide in the spec it
  1. renders a 1920x1080 PNG with Playwright (frames cached in the job's tmp dir),
  2. generates one audio clip per speech line with Gemini TTS, saved as
     2025-2026/audio/tts/<id>/NN_MM.mp3 (kept and committed; reused unless --force-audio),
  3. joins slide + its clips into a segment, then concatenates all segments into
     2025-2026/video/<id>.mp4.
"""
import array, base64, html, json, math, os, subprocess, sys, tempfile, time, urllib.error, urllib.request, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = os.environ.get('TTS_MODEL', 'gemini-3.8-flash-tts')
PW = ROOT / '.playwright/node_modules/playwright'
GAP = 0.6       # silence between lines (s)
TAIL = 1.2      # silence after the last line of a slide (s)


def api_key():
    for line in (ROOT / '.env').read_text().splitlines():
        if line.startswith('GOOGLE_AI_STUDIO_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')
    sys.exit('GOOGLE_AI_STUDIO_API_KEY missing from .env')


def tts(text, voice, style, out_mp3):
    body = {
        'contents': [{'parts': [{'text': text}]}],  # text only: any instruction gets read aloud
        'generationConfig': {
            'responseModalities': ['AUDIO'],
            'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}},
        },
    }
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
        data=json.dumps(body).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key()})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 503) or attempt == 7:
                raise
            wait = 15 * (attempt + 1)
            print(f'  HTTP {e.code}, retrying in {wait}s')
            time.sleep(wait)
    part = d['candidates'][0]['content']['parts'][0]['inlineData']
    pcm = base64.b64decode(part['data'])
    rate = 24000
    for bit in part.get('mimeType', '').split(';'):
        if bit.strip().startswith('rate='):
            rate = int(bit.split('=')[1])
    write_mp3(clean_pcm(pcm, rate), rate, out_mp3)


def clean_pcm(pcm, rate, thresh_db=-45):
    """Drop the short noise bursts Gemini TTS leaves before/after the speech, then fade in/out.

    A burst = a loud run shorter than 0.15 s (start) / 0.4 s (end) that is cut off from
    the speech by at least 0.08 s / 0.15 s of silence."""
    a = array.array('h', pcm)
    win = rate // 50  # 20 ms windows
    loud = []
    for i in range(0, len(a), win):
        chunk = a[i:i + win]
        rms = math.sqrt(sum(x * x for x in chunk) / max(1, len(chunk)))
        loud.append(20 * math.log10(max(rms, 1) / 32768) > thresh_db)
    runs = []  # [is_loud, first_window, n_windows]
    for i, v in enumerate(loud):
        if runs and runs[-1][0] == v:
            runs[-1][2] += 1
        else:
            runs.append([v, i, 1])
    start, end = 0, len(loud)
    # ignore quiet padding at either edge; a burst can be followed/preceded by a few quiet ms
    lo = 1 if runs and not runs[0][0] else 0
    hi = len(runs) - 2 if runs and not runs[-1][0] else len(runs) - 1
    if hi - lo >= 2 and runs[lo][2] * 0.02 < 0.15 and runs[lo + 1][2] * 0.02 >= 0.08:
        start = runs[lo + 1][1] + max(0, runs[lo + 1][2] - 3)
    if hi - lo >= 2 and runs[hi][2] * 0.02 < 0.4 and runs[hi - 1][2] * 0.02 >= 0.15:
        end = runs[hi - 1][1] + min(runs[hi - 1][2], 8)
    a = a[start * win:end * win]
    fade = rate // 50
    for k in range(min(fade, len(a) // 2)):
        g = k / fade
        a[k] = int(a[k] * g)
        a[-1 - k] = int(a[-1 - k] * g)
    return a.tobytes()


def write_mp3(pcm, rate, out_mp3):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav = f.name
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-b:a', '96k', str(out_mp3)], check=True)
    os.unlink(wav)


def reclean(mp3, rate=24000):
    """Apply clean_pcm to an already-saved clip."""
    pcm = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(mp3), '-f', 's16le', '-ac', '1', '-ar', str(rate), '-'],
                         capture_output=True, check=True).stdout
    write_mp3(clean_pcm(pcm, rate), rate, mp3)


CSS = """
body{margin:0;width:1920px;height:1080px;background:#1c1c22;color:#e8e4dc;
 font-family:'Noto Serif JP','Hiragino Mincho ProN',serif;display:flex;flex-direction:column;
 justify-content:center;padding:0 140px;box-sizing:border-box}
h1{font-size:40px;font-weight:500;margin:0 0 70px;color:#e8e4dc}
h1 small{font-family:'IBM Plex Sans',sans-serif;color:#9a9488;font-size:34px}
.box{border:2px solid #7c9cc8;background:#262c38;padding:70px 40px;text-align:center}
.formula{font-size:60px;white-space:nowrap;color:#8fb0e0;line-height:2.1}
.gloss{font-family:'IBM Plex Mono',monospace;letter-spacing:5px;text-transform:uppercase;color:#9a9488;font-size:28px;margin-top:20px}
.rows div{font-size:64px;color:#8fb0e0;padding:28px 0;border-bottom:2px dashed #3a3a44}
.label{font-family:'IBM Plex Mono',monospace;letter-spacing:6px;text-transform:uppercase;color:#e08a6a;font-size:30px;margin-bottom:40px}
.line{font-size:56px;line-height:2.3;white-space:nowrap}
.en{font-family:'IBM Plex Sans',sans-serif;font-style:italic;color:#9a9488;font-size:34px;margin-top:50px;line-height:1.5}
rt{font-size:0.42em;color:#c8c2b6}
"""


def slide_html(spec, s):
    head = f"<h1>{html.escape(spec['title'])} <small>— {html.escape(spec['title_en'])}</small></h1>"
    en = f"<div class='en'>{html.escape(s['en'])}</div>"
    if s['kind'] == 'pattern':
        body = f"<div class='box'><div class='formula'>{s['jp']}</div><div class='gloss'>{html.escape(s['en'])}</div></div>"
        en = ''
    elif s['kind'] == 'formation':
        body = "<div class='rows'>" + ''.join(f'<div>{html.escape(r)}</div>' for r in s['rows']) + '</div>'
    else:
        body = f"<div class='label'>{html.escape(s['label'])}</div>" + ''.join(
            f"<div class='line'>{who}) {jp}</div>" for who, jp in s['lines'])
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;500&family=IBM+Plex+Mono&family=IBM+Plex+Sans:ital@0;1&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style></head><body>{head}{body}{en}</body></html>')


def render(pages, outdir):
    js = outdir / 'render.js'
    js.write_text(f"""
const {{ chromium }} = require({json.dumps(str(PW))});
(async () => {{
  const b = await chromium.launch(); const p = await b.newPage({{viewport: {{width: 1920, height: 1080}}}});
  for (const f of {json.dumps([str(x) for x in pages])}) {{
    await p.goto('file://' + f, {{waitUntil: 'networkidle'}}); await p.evaluate(() => document.fonts.ready);
    await p.screenshot({{path: f.replace(/\\.html$/, '.png')}});
  }}
  await b.close();
}})();""")
    subprocess.run(['node', str(js)], check=True)


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def main():
    spec_path = Path(sys.argv[1]).resolve()
    force = '--force-audio' in sys.argv
    spec = json.loads(spec_path.read_text())
    sid = spec['id']
    audio_dir = ROOT / '2025-2026/audio/tts' / sid
    audio_dir.mkdir(parents=True, exist_ok=True)
    work = Path(os.environ.get('CLAUDE_JOB_DIR', tempfile.gettempdir())) / 'tmp' / f'video_{sid}'
    work.mkdir(parents=True, exist_ok=True)

    pages = []
    for i, s in enumerate(spec['slides']):
        p = work / f'slide_{i:02d}.html'
        p.write_text(slide_html(spec, s))
        pages.append(p)
    render(pages, work)

    silence = work / 'gap.mp3'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                    '-t', str(GAP), '-b:a', '96k', str(silence)], check=True)

    segments = []
    for i, s in enumerate(spec['slides']):
        clips = []
        for j, (who, text) in enumerate(s['speech']):
            mp3 = audio_dir / f'{i + 1:02d}_{j + 1:02d}.mp3'
            if force or not mp3.exists():
                print(f'TTS {mp3.name} [{spec["voices"][who]}] {text}')
                tts(text, spec['voices'][who], spec['style'], mp3)
            clips += [mp3, silence]
        lst = work / f'audio_{i:02d}.txt'
        lst.write_text(''.join(f"file '{c}'\n" for c in clips))
        seg_audio = work / f'audio_{i:02d}.m4a'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst),
                        '-af', f'apad=pad_dur={TAIL}', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '128k', str(seg_audio)], check=True)
        seg = work / f'seg_{i:02d}.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-framerate', '30', '-i', str(pages[i].with_suffix('.png')),
                        '-i', str(seg_audio), '-t', f'{duration(seg_audio):.3f}', '-c:v', 'libx264', '-tune', 'stillimage',
                        '-pix_fmt', 'yuv420p', '-c:a', 'copy', str(seg)], check=True)
        segments.append(seg)

    out = ROOT / '2025-2026/video' / f'{sid}.mp4'
    lst = work / 'segments.txt'
    lst.write_text(''.join(f"file '{s}'\n" for s in segments))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst),
                    '-c', 'copy', '-movflags', '+faststart', str(out)], check=True)
    print(f'{out.relative_to(ROOT)}  {duration(out):.1f}s  {out.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()

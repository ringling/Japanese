# /// script
# requires-python = ">=3.10"
# dependencies = ["youtube-transcript-api"]
# ///
"""Download JA/EN subtitles: <id>_<lang>.txt (one segment per line) and
<id>_ja.times.json (start second of every non-empty Japanese line, same order)."""
import json
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

HERE = Path(__file__).parent
video_id = sys.argv[1] if len(sys.argv) > 1 else "kuZdOc1CgBs"
api = YouTubeTranscriptApi()

for lang in ("ja", "en"):
    try:
        transcript = api.fetch(video_id, languages=[lang])
    except Exception as e:
        print(f"[{lang}] not available: {e.__class__.__name__}")
        continue
    segs = [(" ".join(s.text.split()), s.start) for s in transcript]
    segs = [(t, st) for t, st in segs if t]
    (HERE / f"{video_id}_{lang}.txt").write_text("\n".join(t for t, _ in segs), encoding="utf-8")
    if lang == "ja":
        (HERE / f"{video_id}_ja.times.json").write_text(
            json.dumps([round(st, 2) for _, st in segs]), encoding="utf-8")
    print(f"[{lang}] saved {video_id}_{lang}.txt ({len(segs)} lines)")

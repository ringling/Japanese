# /// script
# requires-python = ">=3.10"
# dependencies = ["youtube-transcript-api"]
# ///
import sys
from youtube_transcript_api import YouTubeTranscriptApi

video_id = sys.argv[1] if len(sys.argv) > 1 else "kuZdOc1CgBs"
api = YouTubeTranscriptApi()

for lang in ("ja", "en"):
    try:
        transcript = api.fetch(video_id, languages=[lang])
    except Exception as e:
        print(f"[{lang}] not available: {e.__class__.__name__}")
        continue
    path = f"{video_id}_{lang}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(s.text for s in transcript))
    print(f"[{lang}] saved {path}")
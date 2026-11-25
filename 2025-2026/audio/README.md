# Marugoto A2-2 Audio Files

## `audio/rikai/` — Competences / りかい (yellow book)
Source: `~/work/second-brain/MarugotoElementary2CompetencesMp3/`
552 files · lessons 01–18
Naming: `NNN_lesson_section.mp3` (e.g. `084_5_2_1.mp3`, `084_5_2_1_kaiwa.mp3`)
HTML path from `files/`: `../audio/rikai/NNN_*.mp3`

Clean aliases for tracks referenced in HTML:
- `track_084.mp3` / `track_084_kaiwa.mp3` / `track_084_kaiwa_n.mp3` — L5 p.56 dialogue
- `track_085.mp3` / `track_085_answers.mp3` — L5 p.56 ex.2①
- `track_086.mp3` / `track_086_answers.mp3` — L5 p.57 ex.2②
- `track_081_answers.mp3` — L5 p.54 ex.2
- `track_083_kanji.mp3` — L5 p.55 ex.5

## `audio/katsudoo/` — Activities / かつどう (white book)
Source: `~/work/second-brain/MarugotoElementary2ActivitiesMp3/`
463 files · lessons 01–18 + LessonReview
Naming: `NNN_lesson_section.mp3` (independent numbering from りかい)
HTML path from `files/`: `../audio/katsudoo/NNN_*.mp3`

Note: track numbers overlap between the two sets — 001 in かつどう ≠ 001 in りかい.

## tts/ — generated audio (Gemini TTS via Google AI Studio API)

Audio for page content the textbook has no track for. One folder per set:
`tts/L8_bunpou/<pattern>-<example>.mp3` = grammar examples of だい8か (e.g. `2-3.mp3` = pattern 2, example 3).
`tts/L9_bunpou/<pattern>-<example>.mp3` = grammar examples of だい9か (11/30 page, 10 clips).
A/B dialogues use two voices (A = Kore, B = Puck) joined into one clip with a 0.5 s gap.
Generated with `tts()` in `make_video.py` (key: `GOOGLE_AI_STUDIO_API_KEY` in `.env`); every clip is
trimmed of the noise bursts Gemini adds at the start/end (`clean_pcm`).
The start/end bursts were mostly our own bug: gemini-3.x TTS returns a full WAV file (header + PCM +
~7 KB AI-provenance metadata trailer), and reading it all as raw PCM played the trailer as noise.
`decode_audio()` now reads the WAV properly; `clean_pcm` stays as a safety net.

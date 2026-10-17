# Voices

All recruit lines use one hybrid concert voice, with no cast member's own voice in it. Only the drill instructor speaks alone; the fire watch's single line uses a stock voice. Nothing gets recorded: the chorus is generated.

## Status (2026-10-17)

- **ElevenLabs account:**
  - Starter plan: 3 concurrent requests, MP3 output only.
  - Custom voice slots are mostly free now.
- **Drill instructor:**
  - **Fallback (saved):** Voice Design keynote preview-1, the author's pick.
  - **ElevenLabs clone of Jensen:** created, but blocked at generation (`detected_captcha_voice`, speaker verification required). This route is closed.
  - **Fish Audio clone of Jensen: the DI voice.** Created by the author as "JH Test", private, from 85 s of clean audio. Its test read (take 1, `media/voices/jensen/di-test-fish.mp3`) was the author's pick.
  - **DI lines D01–D07 are cut from that take** (`scripts/di.py`), no new generations needed.
    - Each bark is found by its energy and starts within ±21 ms of its slot.
    - Barks keep their natural length.
    - D07 is off camera, so it starts 0.6 s early and is squeezed slightly so it ends before the fire watch speaks.
    - Review render: `renders/proto/di-pass.mp4`.
  - **Fish API:** API credit is billed separately from the web subscription, and the key currently returns 402 "Insufficient API credit". New Fish reads go through the web app until API credit is added.
  - **Reference audio:** Lex Fridman #494, a studio interview. `scripts/jensen_ref.py` separates out Jensen-only speech with speaker clustering:
    - 35 minutes clean (`jensen-clean.wav`)
    - a 3-minute cut (`jensen-3min.*`)
    - an 85-second cut (`jensen-85s.mp3`)
    - a 30-second cut (`jensen-30s.wav`)
- **Chorus: one raw Eleven Music take** (`scripts/chorus_music.py`, `data/chorus.json`), the author's call. The per-voice stack, the Voice Changer stack and the stack-plus-music blend are all retired.
- **Another Jensen reference set** from an earlier session sits in `reference/voice/jensen/` (`scripts/voice_ref.py`): 10 minutes across three interviews, plus an ElevenLabs-ready upload.

## Solo lines (scripts/di.py)

- **Jensen.** Fish clone "JH Test" with command directives, generated in the Fish web app (the API needs separate credit). Configured in `data/voices.json` `di.reads`:
  - D01 alone (take 2)
  - D02–D04: the author's pick `d02-06-tags-take1`, used up to its clean 0.67 s pause after "Push!"; within 0.32 s of the film.
  - D05 "Auto-merge!": from `d05-06-long-take1`, ending in its clean pause; on its film slot (S14, on camera).
  - D06 "Close your laptops!": its own fresh read (`d06-take2`), on its film slot after lights-out, 1.6 s after D05. Fish's pause cues top out around 0.75 s, so a longer gap means a separate read.
  - D07 alone (take 1), starting 0.6 s early (back to camera)
  - The other takes are listed as `alts`.
- **Fire watch (F01):** the author picked option 5 of six from `scripts/firewatch.py`: a Voice Design young private (design 2), saved as the ElevenLabs voice "MSF Fire watch (young private)".
- **Placement:** every read is placed whole by its audible start, never re-timed (no stretching, squeezing or re-spacing).
- **End hold:** the pass holds the last frame for 1.5 s, so F01 can finish.

## The chorus

- **One generation.**
  - Every recruit line (C01–C17 and R01) goes into one Eleven Music request: `music_v2_5`, seed 3, using the S08 seed-3 styles the author liked.
  - It is planned as one timed chunk per scene, sized to that scene's lines, with a 3 s silent chunk between scenes.
  - One take keeps the crowd voice consistent across the whole chant.
- **Three ways to ask for the pauses were tried; "gaps" won:**
  - **gaps:** all 18 lines present. Five clean pauses, each 3.3–3.8 s and −40 to −51 dB.
  - **chunks:** dropped R01, and two scene changes had no pause.
  - **single:** no real pauses (−14 to −30 dB).
- **Cut and place.**
  - Whisper finds every line in the take.
  - Each scene is cut at the quietest point of its pause, with an 8 ms fade.
  - Each scene is placed so its first line's *audible onset* starts on its slot (Whisper starts words 0.5–0.7 s early after a pause), with at most 0.25 s of lead-in, and never on top of the previous scene.
  - The audio itself is untouched. Each scene's speech ends within −0.5 to +0.9 s of the original slot.
- **Listen for C08:** Whisper hears "drill my agents" rather than "grill".
- **Review:** `renders/proto/full-pass.mp4`, the chorus plus the DI lines over the picture, with no room bed.

## Commands

| Command | What it does |
| --- | --- |
| `python3 scripts/eleven.py account` | plan tier, credits and voice slots |
| `uv run --group analysis --group voice python scripts/jensen_ref.py` | Jensen-only reference audio from the interview |
| `uv run --group analysis python scripts/chorus_music.py generate` then `build gaps` | the one-take chorus: generate the variants, then cut, place and render |
| `uv run --group analysis python scripts/firewatch.py` | F01 voice options from ElevenLabs into `media/voices/firewatch/` |
| `uv run --group analysis --group voice python scripts/di.py` | DI lines cut from the approved Fish reads, placed on their slots; re-renders the full pass |
| `python3 scripts/fish.py tts MODEL_ID "text" out.mp3` | Fish Audio TTS (needs API credit) |
| `uv run --group analysis --group voice python scripts/timing_page.py` | `review/dist/timing.html`: timing review per shot and line (orig vs new, play both, feedback) |
| `uv run --group analysis python scripts/voice_pages.py` | `review/dist/voices.html` (audition, with feedback) and `review/dist/record.html` (record to picture, now optional) |

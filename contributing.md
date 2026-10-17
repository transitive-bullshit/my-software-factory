# Contributing

## Setup

- Python 3.12 with `uv` (`uv sync --all-groups`), Node 24+ (the HyperFrames CLI runs through `npx`, pinned in each project's `package.json`), ffmpeg and yt-dlp.
- API keys, in the environment or `~/.env`: `FAL_KEY` (fal.ai: keyframes, animation, lip sync), `ELEVENLABS_API_KEY` (the chorus and the fire watch), `FISH_AUDIO_API_KEY` (Jensen's voice). Every fal call is cached and logged with its cost in `data/fal-log.jsonl`.
- The source clip, stems, cast photos and voice references are not in git (see below). Fetch the clip first; the rest is rebuilt by the pipeline or kept locally.

Or hand it to a coding agent in this folder:

```text
Read AGENTS.md and contributing.md. Fetch the source clip, run prep, then walk me through data/script.json and the review pages.
```

## Pipeline

```bash
# 1. the source clip, split into vocals and bed, with Whisper word timings (cached)
yt-dlp -f "270+bestaudio[ext=m4a]" --merge-output-format mp4 -o "media/source.%(ext)s" https://www.youtube.com/watch?v=nkGIxGdZoYY
uv run --group analysis python scripts/prep.py
uv run --group analysis python scripts/sheets.py 39 106.5 1      # contact sheets in frames/sheets/

# 2. the script and its review pages (review/dist/)
uv run --group analysis python scripts/storyboard.py
uv run --group analysis --group voice python scripts/timing_page.py

# 3. the voices: one Eleven Music chorus take cut into scenes, then the solo lines on top
uv run --group analysis python scripts/chorus_music.py build gaps
uv run --group analysis --group voice python scripts/di.py                  # the lip sync cut's timeline
uv run --group analysis --group voice python scripts/di.py --variant gen    # the generative cut's own timeline
uv run --group analysis python scripts/voice_pages.py                      # audition and record-to-picture pages

# 4. the cast and the fully generative shots (fal)
uv run --group analysis --group voice --group gen python scripts/cast.py headshots|sheets|page
uv run --group analysis --group voice --group gen python scripts/full.py prep|lipsync|keyframes|animate|resync

# 5. both cuts, checked: renders/full/{lipsync,generative}.mp4 and review/dist/full.html
uv run --group analysis --group voice --group gen python scripts/full.py assemble
uv run --group analysis --group voice --group gen python scripts/full.py audit
uv run --group analysis --group voice --group gen python scripts/full.py page

# 6. the generative cut's credits and captions (HyperFrames, in captions/)
uv run --group analysis python scripts/credits.py                                       # profile pictures, then the card
uv run --group analysis --group voice --group gen python scripts/full.py assemble       # crossfade the card onto the cut
uv run --group analysis --group voice --group gen python scripts/captions.py            # word timings from the vocals
cd captions && npm run captions                                                         # -> renders/full/generative-captioned.mp4
```

## Changing captions or credits

- **Caption wording or timing:** edit `captions/captions.json`, then `npm run captions` in `captions/` (about 1.5 min). Rerun `scripts/captions.py` only when the audio changes.
- **Caption look:** edit `captions/build.mjs`.
- **Credits:** edit `captions/compositions/credits-card.html`, then `npm run credits`, `full.py assemble` and `npm run captions`.
- **Preview:** `npx hyperframes preview` in `captions/` opens Studio with the captions over the cut.

## Where things live

| Step | Code | Output |
| --- | --- | --- |
| Master timeline: shots, cast, every line's timing and parody text | `data/script.json` | |
| Plan, author's decisions, voice setup | `docs/plan.md`, `docs/decisions.md`, `docs/voices.md` | |
| Source prep and word timings | `scripts/prep.py`, `scripts/audio.py` | `media/`, `transcript/` |
| Chorus (one sung take, cut and placed) | `scripts/chorus_music.py` | `data/chorus.json` |
| Drill instructor and fire watch lines | `scripts/di.py`, `scripts/fish.py`, `scripts/eleven.py`, `scripts/firewatch.py` | `data/di*.json`, `data/voices.json` |
| Jensen voice reference | `scripts/voice_ref.py`, `scripts/jensen_ref.py` | `reference/voice/jensen/` |
| fal calls (cached, cost-logged) | `scripts/fal_run.py` | `data/fal-log.jsonl` |
| Cast sheets | `scripts/cast.py` | `media/cast/` |
| Shots, keyframes, lip sync, both cuts | `scripts/full.py` (`scripts/variants.py` for the S07/S08 tests) | `renders/full/` |
| Credits card | `captions/compositions/credits-card.html`, `scripts/credits.py` | `renders/full/credits.mp4` |
| Captions | `scripts/captions.py`, `captions/captions.json`, `captions/build.mjs` | `renders/full/generative-captioned.mp4` |
| Promo cuts | `promo/` (HyperFrames projects) | |
| Review pages | `scripts/storyboard.py`, `timing_page.py`, `voice_pages.py`, `variants_page.py` | `review/dist/` |

## Not in the repo

- `media/`, `reference/`, `transcript/`: the copyrighted source clip and its stems and transcripts, the cast's photos and the voice references, plus every generated take. Never commit them, and never write the film's dialogue into tracked files: refer to its lines by id with a paraphrased gist.
- `renders/`, `frames/`, `review/dist/`, `captions/renders/`, `captions/assets/`, `promo/.review/`: regenerable output. Review pages embed film frames, so they stay local.
- `.claude/skills/`: HyperFrames' project skills; `npx hyperframes skills update` reinstalls them.

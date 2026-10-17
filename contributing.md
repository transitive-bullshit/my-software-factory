# Contributing

## Setup

- Python 3.12 with `uv`: `uv sync` installs the light core (the tests); the scripts name the heavy groups they need (`analysis`, `voice`, `gen`), or `uv sync --all-groups` installs everything. Node 24+ (the HyperFrames CLI runs through `npx`, pinned in each project's `package.json`), ffmpeg and yt-dlp.
- API keys, in the environment or `~/.env`: the names and what each pays for are in [`.env.example`](.env.example). Every fal call is cached and logged with its cost in `data/fal-log.jsonl`, so re-running a step that already succeeded is free.
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
uv run --group analysis --group voice python scripts/di.py                  # the film-timed base (review pages)
uv run --group analysis --group voice python scripts/di.py --variant gen    # the cut's own timeline
uv run --group analysis python scripts/voice_pages.py                      # audition and record-to-picture pages

# 4. the cast and the fully generative shots (fal)
uv run --group analysis --group voice --group gen python scripts/cast.py headshots|sheets|page
uv run --group analysis --group voice --group gen python scripts/full.py prep|keyframes|animate|resync

# 5. the cut, checked: renders/full/generative.mp4 and review/dist/full.html
uv run --group analysis --group voice --group gen python scripts/full.py assemble
uv run --group analysis --group voice --group gen python scripts/full.py audit
uv run --group analysis --group voice --group gen python scripts/full.py page

# 6. the generative cut's title, credits and captions (HyperFrames, in captions/)
cd captions && npm run title && cd ..                                                   # title frame + docs/poster.jpg
uv run --group analysis python scripts/credits.py                                       # profile pictures, then the card
uv run --group analysis --group voice --group gen python scripts/full.py assemble       # title on frame 0, card crossfaded at the end
uv run --group analysis --group voice --group gen python scripts/captions.py            # word timings from the vocals
cd captions && npm run captions                                                         # -> renders/full/generative-captioned.mp4
```

## Redo a shot

Each fal call costs money, so review the keyframe before animating.

1. In `scripts/full.py`, edit the shot's keyframe prompt (`KEYS`) or motion brief (`ANIM`), and bump its revision (`KEY_REV` or `ANIM_REV`) so the old take stays.
2. `full.py keyframes <id>` makes the options in `media/full/keyframes/`; record the pick in `media/full/keyframes/picks.json`.
3. `full.py animate <id>`, then `full.py resync <id>` if the shot is lip-synced afterwards (`RESYNC`, `RESYNC_CROP`).
4. `full.py page` to review it in context, then `full.py assemble`, `full.py audit` and `npm run captions` in `captions/`.

## Title, captions and credits

- **Caption wording or timing:** edit `captions/captions.json`, then `npm run captions` in `captions/` (about 1.5 min). Rerun `scripts/captions.py` only when the audio changes.
- **Caption look:** edit `captions/build.mjs`.
- **Title frame and poster:** edit `captions/compositions/title.html`, then `npm run title` (it takes S07's first frame from the cut and also writes `docs/poster.jpg`), `full.py assemble` and `npm run captions`. The title replaces the cut's first frame, so nothing after it moves.
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
| R2 backup of the generative cut's clips | `scripts/backup.py` | `data/backup.json` |
| Cast sheets | `scripts/cast.py` | `media/cast/` |
| Shots, keyframes, lip sync passes, the cut | `scripts/full.py` (`scripts/variants.py` for the S07/S08 tests) | `renders/full/` |
| Title frame and README poster | `captions/compositions/title.html`, `captions/title.mjs` | `renders/full/title.png`, `docs/poster.jpg` |
| Credits card | `captions/compositions/credits-card.html`, `scripts/credits.py` | `renders/full/credits.mp4` |
| Captions | `scripts/captions.py`, `captions/captions.json`, `captions/build.mjs` | `renders/full/generative-captioned.mp4` |
| Promo cuts | `promo/` (HyperFrames projects) | |
| Review pages | `scripts/storyboard.py`, `timing_page.py`, `voice_pages.py`, `variants_page.py` | `review/dist/` |

## Tests and CI

`uv run pytest -q` checks the committed data offline: the shots tile the source window, every parody line stays within its syllable budget (or records the overrun), every read is placed whole and never re-timed, and the captions match the script without overlapping and match the built caption composition. CI (`.github/workflows/test.yml`) runs them with `py_compile` on every push, with no keys, media or paid APIs.

## Repo map

```text
data/        script.json (the master timeline), chorus and DI placements, voice picks, the fal cost log
docs/        plan, the author's decisions, voice notes, the README poster
scripts/     the Python pipeline (prep, voices, shots, cuts, captions, review pages)
captions/    HyperFrames: the title frame, the caption layer and the credits card
promo/       HyperFrames: promo cuts (the McGurk demo)
tests/       offline checks on data/ and captions/
```

## Not in the repo

- `media/`, `reference/`, `transcript/`: the copyrighted source clip and its stems and transcripts, the cast's photos and the voice references, plus every generated take. Never commit them, and never write the film's dialogue into tracked files: refer to its lines by id with a paraphrased gist.
- The approved clip behind each shot of the fully generative cut is backed up to R2 (paid fal output, otherwise only on one disk). `uv run python scripts/backup.py restore` downloads any that are missing, checked against `data/backup.json`; no keys needed. `backup.py upload --env <file>` adds new ones with the `S3_*` keys.
- `renders/`, `frames/`, `review/dist/`, `captions/renders/`, `captions/assets/`, `promo/.review/`: regenerable output. Review pages embed film frames, so they stay local.
- `.claude/skills/`: HyperFrames' project skills; `npx hyperframes skills update` reinstalls them.

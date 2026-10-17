# Project: my-software-factory

This Is My Software Factory: a parody of the Full Metal Jacket barracks creed scene. AI engineers are the recruits and Jensen Huang is the drill instructor. Python tooling only so far (uv).

## Mental model

- `data/script.json` is the master timeline:
  - the source window (39.34–106.41 s of `media/source.mp4`)
  - shots, with their cast
  - every line, with its original timing, syllable budget and the parody text
- `docs/plan.md` holds:
  - the scope
  - the cast rationale
  - the visual options
  - the generation pipeline
  - the open decisions
- `docs/decisions.md` holds the author's calls; they override the plan.
- `docs/voices.md` holds the voice setup and status:
  - `data/voices.json` holds the voice picks.
  - `data/chorus.json` holds where each chorus line sits in the raw take and on the timeline. The chorus audio drives timing.
- `captions/` is the HyperFrames project for the generative cut's locally rendered layers:
  - the captions: `captions.json` is the one file to edit, and `build.mjs` generates the compositions from it;
  - the end credits card: `compositions/credits-card.html`, edited directly.
- `scripts/storyboard.py` renders the script as a review page in `review/dist/`:
  - the original line next to each parody line
  - playback of the source moment
  - feedback boxes, with a Copy button that collects every note
- Review loop: the author pastes the copied feedback, the agent updates `data/script.json`, bumps `review.version` and rebuilds.
- `promo/` holds short videos that promote the parody. Each is its own HyperFrames project:
  - `promo/mcgurk`: the 16:9 McGurk-effect demo. It is published and locked (read-only, `LOCK.sha256`).
  - `promo/mcgurk-vertical`: the same demo in 9:16 for Shorts, Reels and TikTok.
  - `promo/POSTS.md`: the post copy and published links.
  - `promo/review-sync.sh <name>`: runs HyperFrames Studio on a copy in `promo/.review/<name>`, never on the source.
  - Renders and exports go to `renders/promo/`; the finished files are in `renders/promo/final/`.

## Commands

Setup, the pipeline in order, and where each step's code and output live are in `contributing.md`.

## Conventions

- Use `uv` for Python (`uv add --group analysis <pkg>` for heavy deps).
- Times in `data/script.json` are source-clip seconds. Meme time is `t - window.start`.
- Parody lines stay timing-locked to the original line starts and ends, within ±2 syllables. Record any deliberate overrun in the line's `ref`.
- ElevenLabs: the key comes from `ELEVENLABS_API_KEY` in the environment or `~/.env`; never print it. Stock voices need no voice slot.
- Never re-time generated audio (stretch, squeeze, or cut a read apart to re-space it). Regenerate instead, and place reads whole.
- Put review choices (takes, options) on the timing page, next to the lines they affect.
- Heavy models each run in their own process. MLX and torch together in one process can deadlock.

## Not in git

- The source clip, stems, Whisper transcripts, avatars and reference photos live in `/media`, `/transcript` and `/reference`. Never commit them.
- Never write original film dialogue into tracked files. Reference lines by id with a paraphrased gist.
- The storyboard pulls the original lines from `/transcript` at build time, so its output stays in the ignored `/review/dist`.
- Frames, renders and review pages (`/frames`, `/renders`, `/review/dist`) are derived and ignored.
- `.gitignore` also blocks audio and video by extension.

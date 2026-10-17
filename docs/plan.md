# Plan v1

The meme: the barracks creed scene from Full Metal Jacket, recast with AI engineers swearing allegiance to their software factories, and Jensen Huang as the drill instructor. Source: the [PG-version clip](https://www.youtube.com/watch?v=nkGIxGdZoYY), 1080p29.97, 106.5 s.

The master timeline is `data/script.json`. `uv run --group analysis python scripts/storyboard.py` renders it as a review page with frames (`review/dist/storyboard.html`).

## Scope

**Window: 39.34 → 106.41 s of the source (67.1 s).**
- It opens on the DI's office close-up, so Jensen and his one-word cue land in the first two seconds.
- It ends on the fire watch's last line, 0.07 s before the clip runs out. Add a 1–2 s hold or end card.
- Starting at the first recruit shot (41.54 s) instead gives 64.9 s, but loses Jensen's cue and the poster gag.

| Shot | Meme time | Framing | Who |
| --- | --- | --- | --- |
| S07 | 0.00–2.20 | DI close-up in his office, PRIDE poster on the wall | Jensen; poteto (poster) |
| S08 | 2.20–12.81 | Medium wide, recruit in wire-rim glasses in profile on a lower bunk; the hook plays here | Matt Pocock |
| S09 | 12.81–22.99 | Wide reverse, recruit in dark-framed glasses in the foreground | steipete |
| S10 | 22.99–34.10 | **Close-up** of the wire-rim recruit from S08, low angle | Matt Pocock |
| S11 | 34.10–47.38 | **Close-up** of the heavyset recruit, 3/4 frontal | swyx |
| S12 | 47.38–54.49 | DI walks the hall; fire watch in a chrome helmet behind him | Jensen; Simon Willison |
| S13 | 54.49–57.12 | Wide, same angle as S09; recruits snap rifles down | steipete |
| S14 | 57.12–59.16 | DI in the hall | Jensen |
| S15 | 59.16–67.07 | Lights out, DI silhouetted in the doorway, walks off | Jensen; Simon Willison |

Only two shots are true recruit close-ups (S10, S11). Everything else is wide, so most recruit faces are small and the chorus carries the comedy.

## Cast

Ranked from your Birdclaw archive (synced through 2026-10-16) and by how well each face fits a shot.

| | Last-12-month mentions / likes | Slot | Why |
| --- | --- | --- | --- |
| Jensen Huang | — | DI | He coined "AI factories". The leather jacket replaces the uniform, and his parting order is "We need more GPUs!" |
| poteto | 11 / 20 (most liked) | Office poster: PRIDE → **PRs**, with her avatar | Her "more ambitious" push is in the chant. The avatar is used as-is, as you suggested |
| Matt Pocock | 5 / 16 | S08 hook + **S10 close-up** | Near look-alike for the actor (balding, round wire-rims); delivers the hook and the first hero close-up |
| steipete | 12 / 9 | S09 + S13 wides | Most-mentioned. The S09 recruit wears dark frames like his; a lobster plush on the bunk |
| swyx | 10 / 11 (215 all-time) | **S11 close-up** | Your longest-running tie of the cast; coined "AI Engineer" and gets to chant it. Whoever takes this slot plays the character known as Pyle in the film, with all that implies, so ask first |
| Simon Willison | 4 / 11 | Fire watch; says the last line | Small face, so an easy swap; a deadpan delivery fits him |
| Bench: theo (5 / 1), ThePrimeagen (0 / 0, not in archive) | | Fire watch, or a generated insert close-up cut into S08 or S09 | |

## Script

All 26 lines are timing-locked to the original lines' starts and ends.

Since review round 2, the chant follows the 1941 USMC Rifleman's Creed closely, with agents and AI standing in for the rifle, so the reference reads instantly. The insider jokes sit in a few lines:
- Matt's /grill
- weekly usage limits
- the next model drop
- swearing on AGENTS.md
- review as the new bottleneck
- swyx's "AI Engineer"
- "more ambitious"
- trusting your agents until ASI
- tests are green

Lines that miss the original syllable count by more than 1:

| Line | Parody / original syllables | Fix |
| --- | --- | --- |
| C01 | 8 / 5 | Use the 0.4 s gap after the line |
| F01 | 7 / 4 | Runs ~0.5 s into the end hold |

The DI's tail goes:
1. git as close-order drill: "Ready! Commit! Push!", then "Auto-merge!" as the lights cut
2. "Close your laptops!" gets the reply "Still running, sir!"
3. Jensen walks off with "We need more GPUs!"
4. The fire watch answers "You're absolutely right, sir!"

Alternates for the closing pair are in `data/script.json` (D07, F01).

Original dialogue is referenced only by line id and a paraphrased gist. Whisper's transcript stays in `/transcript`.

## Visual direction

**What V1 changes:** faces only, on the original footage.
- Recruits get face swaps.
- Jensen gets a whole-character replacement, face plus leather jacket. In the Marine uniform he would read as a drill instructor, not Jensen.
- A few flat signs get gags.

Every other pixel is the original film.

There are three routes for the rifles, from least to most generated:

| Route | What changes | Framing and timing | Risk and cost |
| --- | --- | --- | --- |
| **A. Faces only** (V1) | Faces, Jensen's outfit, signs | Identical: it is the original footage | Lowest; about $75–150 |
| **B. Edit the footage** | A, plus rifles become MacBook Pros: a video edit model runs on each original shot before the face swap | Identical: the motion comes from the original | Hand and grain artifacts; adds $30–60 |
| **C. Rebuild each shot** | A new keyframe per shot (cast member holding a MacBook, other engineers in the background bunks, same composition), then animated | Close, but drifts unless the original drives the motion | Most control over who is in frame and what they hold. Highest artifact risk, and some models refuse real faces; about $150–300 |

**If we go with C:**
1. **Build a keyframe per shot by editing the original's first frame**, not by prompting from scratch. Editing keeps the lens, light and composition. Swap the rifle for a MacBook and the faces for the cast, and add engineers where the original has background recruits.
2. **Animate with the original shot as the motion driver.** Use a reference-video model, not plain image-to-video. That keeps the cuts, shot lengths and big moves locked to the original timing, such as the rifle snap on "Push!" and the DI's walk.
3. **Lip-sync the close-ups last**, as in A and B.

Plain image-to-video from a keyframe is cheaper, but it invents the motion and loses the beat-for-beat match. Keep it for inserts.

Driven C and B end up close together: both keep the original as the skeleton. The real decision is how much of the frame may change.

**Cheap probe before deciding (about $2–5):**
- Edit one frame: S10, Matt holding a MacBook.
- Make one 3–5 s driven clip from it.

**Add-ons on any route:**
- **Glowing ending.** At lights-out (S15) the dark barracks glows with laptop screens, paying off "Still running, sir!".
- **Set-dressing gags.** These are flat signs, so they're cheap to track and replace:
  - S07: the PRIDE poster becomes a "PRs" poster with poteto's avatar.
  - S12/S14: the hallway "Divine Worship" board becomes a "Model Worship" service schedule (model names with service times), and the framed portrait becomes Jensen.
  - S09: a lobster plush on steipete's bunk.

## Audio

All voice work runs in ElevenLabs. Setup, status and the recording plan are in [voices.md](voices.md).

**Chorus: one raw Eleven Music take** (author's call, 2026-10-17). Every recruit line comes from a single generation (`music_v2_5`, seed 3), with a silent 3 s gap between scenes so the crowd voice stays consistent. The take is cut at those gaps and laid on the timeline unaltered: no stretching, no room processing. Its timing now drives the edit and the visuals; see [voices.md](voices.md) and `data/chorus.json`.

**Jensen (DI)** is the one voice the audience should recognize. **Now: the Fish Audio clone "JH Test"** (2026-10-17). The ElevenLabs instant clone was blocked at generation (speaker verification), so the notes below on ElevenLabs are history. There are two reference sets:
- `reference/jensen/` from `scripts/jensen_ref.py`: Lex Fridman only, 35 min of Jensen. Its 85 s cut trained the Fish clone.
- Reference audio: `scripts/voice_ref.py` builds it in `reference/voice/jensen/`.
  - Sources: Lex Fridman #494 and The Ezra Klein Show, both studio mics. The Joe Rogan Experience #2422 is used only to anchor the voice print, because of mic bleed.
  - Speaker ID separates him from the hosts.
- Upload `jensen-elevenlabs-upload.mp3` (2:39, one source). ElevenLabs recommends 1–2 minutes, and little improves past 3.
- `jensen-reference.wav` is the full 10-minute set, for retries or a different tool.
- His lines: TTS from the clone, or Voice Changer on a performance to picture for exact timing.

**Fire watch** (F01, one line): a stock library voice, not Simon's.

**Bed.** Removing the vocals leaves a thin bed, because the chanting barely stops.
- Rebuild it from room tone in the gaps plus foley: footsteps, bunk creaks, rifle slaps on S13.
- Use the separated original vocals only as a timing guide.

## Pipeline

Recommended tools as of Oct 2026, from web research. Two claims are spot-checked: sync-3 on fal at $8/min, and ElevenLabs' "No-Go voices" block on prominent public figures. The rest are unverified until we test them.

1. **Voices (ElevenLabs):** chorus and DI as described in Audio above.
2. **Prop edit or rebuild (routes B and C only)** on the original shots: Kling O3 Pro Edit or Runway Aleph 2.0.
3. **Face swap**, one shot at a time, ≤10 s each.
   - Rotate lying-down shots upright first, then rotate back.
   - Close-ups: [DreamID-V](https://github.com/bytedance/DreamID-V) (open weights, needs a rented GPU) or [Kling O3 Pro Edit](https://fal.ai/models/fal-ai/kling-video/o3/pro/video-to-video/edit) on fal ($0.168/s, up to 4 reference images).
   - Jensen with the jacket: [Wan 2.2 Animate Replace](https://fal.ai/models/fal-ai/wan/v2.2-14b/animate/replace) (whole character from one reference).
   - Clean-up and wide shots: FaceFusion locally.
   - Avoid Seedance and Gemini: they reject real faces even on footage you own.
4. **Lip sync, last**: [sync-3 on fal](https://fal.ai/models/fal-ai/sync-lipsync/v3) on S10, S11 and the DI shots.
   - No lip sync on the wides: the parody keeps the rhythm, so the original chanting mouths pass.
   - Any diffusion pass after lip sync would overwrite the mouths, so nothing generative runs after it.
5. **Finish**:
   - Upscale 720p outputs and re-grain to match the 1987 stock.
   - Burn in an "AI PARODY" tag.
   - Post with X's "Made with AI" label on.

**Rough cost:** $75–150 for route A, plus ElevenLabs on your existing plan. Add $30–60 for route B; route C runs about $150–300.

## Risks

- **Copyright.** The footage is Warner Bros'. A DMCA takedown is the realistic risk; parody is a defense, not a guarantee. Don't monetize.
- **Likeness and voice.** No real voices in the chorus. The DI voice is the sensitive one (see Audio). Label it clearly, keep it obviously comic, imply no endorsement.
- **Source quality.** The upload is old 1080p telecined to 29.97 from 24p. If you own the film, a Blu-ray rip of the same scene gives the swap models far more to work with.

## Open decisions

1. DI voice: a Voice Design soundalike in ElevenLabs, or attempt a clone and expect the block?
2. Fire watch: Simon or theo?
3. Route: build A first, or run the route C probe on S10 before deciding?
4. Script edits: use the feedback boxes on the storyboard.

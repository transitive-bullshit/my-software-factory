# Decisions

The author's calls. They override the research in `docs/plan.md`.

## 2026-10-16

- **Cast.**
  - Matt Pocock plays the recruit in wire-rim glasses (S08 hook shot, S10 close-up). It is one character.
  - Peter Steinberger plays the recruit in dark-framed glasses (S09, and the S13 wide from the same angle).
  - swyx takes the heavyset recruit's close-up (S11).
  - ThePrimeagen is benched.
- **Chorus voice.**
  - Use one hybrid concert voice. No cast member's own voice anywhere in the chant: the lines are only ever said in unison.
- **Drill instructor voice.**
  - The DI is the only solo voice.
  - Use ElevenLabs; there's budget for it.
  - Clone Jensen with ElevenLabs Instant Voice Cloning (author's call, 2026-10-17), from clean interview audio in `reference/voice/jensen/`.
- **Visual route.**
  - V1 swaps faces on the original footage.
  - Regenerating each shot (MacBooks, background engineers) is undecided.

## 2026-10-17

- **Script, review round 2.**
  - The chant follows the creed's own wording closely, with agents and AI standing in for the rifle. Recognition beats novelty.
- **Closing.** The previous closing pair was dropped.
- **Script, review round 3.**
  - The Sama line is out. C12 swears on the AGENTS.md file.
  - The chant leans into future tense and resolve ("will ship", "will be more ambitious").
  - C17 spells out LGTM.
- **Script locked** after review round 5. Next comes the voice work.
- **Voices, round 2.**
  - Recording a guide take is out: the chorus must be generated.
  - The DI favourite among the designs is keynote preview-1 (saved as the fallback).
  - The goal is still a custom Jensen voice from his real audio.
  - The Fish Audio clone was created by the author.
- **DI voice: the Fish Audio clone ("JH Test").** The author preferred take 1 of its test read. Keynote preview-1 stays as the fallback.
- **Chorus: the raw Eleven Music take is the source of truth.**
  - The per-voice stack and the stack-plus-music blend don't work in practice.
  - All chorus lines come from ONE generation with pauses between scenes, for a consistent crowd voice.
  - Each scene is cut and placed as it is: no stretching, no room sound.
  - The chorus audio drives timing; the visuals adapt to it scene by scene (approach TBD).
- **D07 is "We need more GPUs!"** (Fish take 1).
- **Jensen, more commanding** (timing review v1):
  - Every DI line is regenerated in Fish with command directives.
  - D02–D06 are one read with natural cadence between the lines. That cadence drives the timeline, and the picture adapts.
- **Fire watch (F01):** a generic soldier voice from ElevenLabs, not anyone's own voice. Options are on the audition page; the author picks.
- **R01 starts faster:** chorus lines are placed by their audible onset, not Whisper's early word start.
- **Voice picks** (audition round 2):
  - D01: take 2. D02–D06: take 2. D07: take 1.
  - F01: the Voice Design young private (design 2), saved as an ElevenLabs voice.
  - D02–D06 pacing is open: the default places each bark on its original slot (paced), and the natural cadence is the alternative (`di.py --alt`).
- **Never re-time generated audio.** No stretching, squeezing, or cutting a read apart to re-space it: it always sounds worse. When pacing is wrong, regenerate the read fresh, with pause cues in the text. Reads are placed whole; the timeline adapts.
- **Reviews happen on the timing page** (`review/dist/timing.html`). Take options sit next to the lines they belong to, with the take in use marked.
- **D02–D06:** the author picked `d02-06-tags-take1`, a fresh Fish read with [pause] cues between commands, used untouched (timing review v4).
- **D05–D06 regenerated** with a longer pause between them, as their own fresh read (`d05-06-long-take1`, 0.73 s between the commands). It starts on D05's slot, which puts "Auto-merge!" back in S14 on camera. D02–D04 still come from `tags-take1`, ending in its clean pause after "Push!".
- **D06 is its own fresh read** (`d06-take2`), starting on its original slot after lights-out. "Auto-merge!" still comes from `d05-06-long-take1`, ending in its clean pause. That leaves 1.6 s between them (2.2 s in the film).
- **Visual variants, test round 1 feedback (S07+S08):**
  - Lip sync on the drill instructor (S07) looks good.
  - On every non-DI shot (the recruits chanting), tone the mouth movement down: sync-3 was too aggressive on S08.
  - Face swap: Jensen looks good but his mouth must follow the audio. Matt is recast from his character sheet. PixVerse is dropped.
- **Lip sync model rule:**
  - sync-3 on the drill instructor.
  - lipsync-2 on every recruit shot: its mouth movement stays close to the actor's own chant. sync-3, even lips-only, opened the jaw too wide.
  - HeyGen needs an audio track inside the input video, so it was skipped.
- **Face swap round 2:** Jensen re-synced with sync-3 on top of the recast. Matt is recast from his character-sheet front view (white t-shirt), then lip-synced with lipsync-2.
- **Generative S08:** MacBook Pro laptops instead of rifles, resting on the recruits' stomachs while they code (keyframe r4).
- **Variants, round 2 feedback:**
  - Face swap is dropped. Only lip sync only and fully generative continue.
  - Lip sync on S08: lipsync-2 barely moves the mouth. Go back to sync-3, but look for a middle ground between the two.
  - Fully generative S08: the Nano Banana Pro keyframe is good. InfiniteTalk is out (the recruits flail). Use current SOTA video models; Matt shouts, but codes calmly with steady hands.
- **Variants, round 3 results** (S07+S08, awaiting the author's review):
  - **Lip sync on S08: React-1** (`sync-lipsync/react-1`), lips only, neutral emotion, temperature 0.5. It is the middle ground between sync-3 and lipsync-2. Mean frame-to-frame change in the mouth box:

    | Source | Change |
    | --- | --- |
    | original | 0.51 |
    | lipsync-2 | 0.57 |
    | React-1 | 0.66 |
    | sync-3 | 0.77 |

    Temperature 0.3 measures the same and is an option on the page. Until the author picks, this replaces lipsync-2 as the rule for recruit shots.
  - **Generative S08: Kling v3 Pro.** Image-to-video from keyframe r4, with a calm-typing prompt and a negative prompt against flailing hands. The clip is trimmed to the shot, then sync-3 handles Matt's shout. The hands stay steady (motion about 5, against InfiniteTalk's 17.7). MiniMax H3 Max Lip Sync is the alternate.
  - **OmniHuman v2 refuses every S08 keyframe** (ByteDance moderation). A probe with the S07 image and the S08 audio passed, so the trigger is the image (several men lying in bunks), not the audio.
  - **Picks:** the cut each variant uses is in `media/variants/round-picks.json`, and the variants page marks it "in use".
- **Variants, round 3 feedback:**
  - **Lip sync only: sync-3 on every shot.** sync-3 is the best S08 version so far. Every other lip sync direction (lipsync-2, React-1) is retired. This replaces the earlier rule of lipsync-2 on recruit shots.
  - **Fully generative S08:** Kling v3 Pro + sync-3 and H3 Max Lip Sync both work. Try one more H3 Max take, prompted for calmer typing. H3 Max Lip Sync takes no prompt, so the calm motion comes from H3 Max image-to-video, tried two ways:
    - with the voice pinned as its soundtrack, in one pass;
    - silent, then H3 Max Lip Sync video-to-video.
- **H3 Max calm-typing takes** (results, awaiting the author's review):
  - **H3 Max image-to-video pushes the camera in on every take**, whatever the prompt says (three seeds, up to "locked-off tripod, the camera never moves"). It cuts away the aisle and leaves the approved composition.
  - **Passing the keyframe as the last frame too** (`end_image_url`) holds the framing. Both anchored takes are on the page:
    - **voice pinned, one pass:** his mouth opens on most loud syllables;
    - **silent, then H3 Max Lip Sync:** gentler, with less shouting.
  - Their hands are calmer than Kling's (frame-to-frame change 2.2–3.2, against 5.7).
  - Kling v3 Pro + sync-3 stays in the cut until the author picks.
- **Fully generative approach, locked:**
  - Each shot is H3 Max image-to-video (`minimax/h3-max/image-to-video`, 1080P) from its approved keyframe, with these settings:
    - the keyframe is passed again as `end_image_url`, so the camera holds;
    - the shot's voice is pinned as `target_audio_url`, so the mouth follows it in the same pass;
    - the prompt describes calm, steady motion;
    - prompt expansion is off.
  - This was the author's pick of the S08 options. Kling and the H3 lip-sync takes are retired for this variant.
- **Lip sync only approach, locked:** sync-3 on every speaking shot of the original footage.
- **Before the full render: the cast sheets need the author's approval.**
  - Every character gets 3–4 high-quality headshots as likeness references.
  - swyx must look like himself, presented respectfully. Nothing of the film's character carries over: not the look, the build, the haircut or the expression.
- **Cast sheets for the full render** (`scripts/cast.py`, awaiting the author's approval):
  - **Headshots:** each character has 4–5 recent, sharp headshots, cropped to head and shoulders, with sources in `reference/cast/<who>/raw/sources.json`. Jensen keeps his 3 Wikimedia photos.
  - **Hair:** the recruits keep their own hair, so they stay recognizable. No buzz cuts.
  - **Simon Willison:** his X avatar is about 13 years old, so only 2026 frames are used (shoulder-length hair, thin rectangular glasses). As the fire watch, his hair hangs from under the chrome helmet.
  - **swyx:** sheet revision 2 asks for his current short, textured hair. Revision 1 took the swept-back hair from a 2024 photo, and one of its options didn't look like him.
  - **Matt:** new, larger headshots (the old ones were 280–480 px). His approved sheet is shown alongside for comparison.
- **Cast sheets approved** (author: "character sheets approved"; no option named, so the recommended options are used):
  - Jensen: his test sheet.
  - Matt: r3 option B.
  - steipete: option B.
  - swyx: r2 option B.
  - Simon: option A.
- **Full render** (`scripts/full.py`):
  - **Who moves their mouth:** only the on-screen speaker's lines go to lip sync, or are pinned as the H3 soundtrack. Off-screen and hidden speakers are heard in the mix but move no mouth:
    - C17 and D04 are off camera.
    - D06 is said in silhouette.
    - R01 and D07 come after the DI has walked off.
  - **Lip sync only:** sync-3 covers the part of each shot where the speaker is the main face, spliced back into the shot:
    - S12 from 1.3 s, once the DI has walked in;
    - S15 from 5.1 s, once the DI has walked off and the fire watch answers.
    - S13 has nobody speaking on screen, so it stays original.
  - **Fully generative:**
    - S07 and S08 come from the approved test.
    - Moving shots get a different first and last keyframe: S12 (the DI walks in) and S15 (he walks off).
    - S13 reuses S09's keyframe: on "Push!" the recruits hit Enter together.
    - S14 reuses the end keyframe of S12.
- **Full render, round 1 results** (awaiting the author's review; both cuts are 68.6 s on the approved mix):
  - **Keyframe picks and reasons:** `media/full/keyframes/picks.json`.
  - **S11 (swyx), redone twice:** the first animation bared clenched teeth under a furrowed brow mid-chant. Both the keyframe and the motion prompt now ask for a warm, confident face, and the final take keeps his brow relaxed and his mouth shaping words naturally.
  - **S15 end frame (r2):** r1 garbled the MODEL WORSHIP board text and lost Jensen's jacket.
  - **Spend:** the full render cost about $17.80 (sync-3 $6.00, keyframes $2.70, H3 $9.10). The project total is about $66 of the ~$80 budget.
- **Full render, round 2 feedback (fully generative):**
  - **S08, S09, S11:** solid.
  - **S07:** "Prompt!" was hard to understand and came too late. Regenerated as new Fish takes (directed to hit the P and T); the clearest by Whisper, `d01-r2/take1`, is in use. It now starts 0.46 s into the shot, at 39.80 instead of the 40.65 slot. Both cuts use it, and the lip sync cut's S07 is re-synced. The keyframe stays: its baked-in black bars are cropped (`key-S07-clean.png`), and it is re-animated with H3 Max.
  - **S10:** the bunks behind him are now full, and Matt's own headshots go into the keyframe for a stronger likeness.
  - **S12–S15, rebuilt as one sequence:**
    - **Hallway:** shorter, so Simon reads clearly without being close. A light switch sits by the dark doorway from S12 on.
    - **The generative cut's own timeline:** "Auto-merge!" comes sooner (`scripts/di.py --variant gen` moves D05 to 95.6 s, 1 s after "Push!"), and S13 is shorter (1.6 s).
    - **S14:** Jensen barks "Auto-merge!", then puts his hand on the switch. S15 opens with the lights off, on the same framing.
    - **S15:** split in two. In the first half he stays put through "Close your laptops!"; in the second he walks off. The short hallway has no far end, so he leaves by a side door past the fire watch.
  - **The lip sync cut** keeps the film's timing, since its footage is the film. Only the new "Prompt!" changes it.
  - **Storyboard:** the review page shows every generative shot with its first and last keyframe, its clip with sound, its line, the motion brief and a feedback box.
  - **Spend:** about $6.30 this round; the project total is about $72.50 of the ~$80 budget.
- **Full render, round 3:**
  - **"S07 isn't using the new take":** the files were right all along. Waveform correlation finds `d01-r2/take1` (0.89, against at most 0.30 for any other take) at 0.46 s in every render and per-shot clip. The review page reused the same file paths every round, so the browser could play cached old renders. Every media link now carries a version stamp (`?v=<mtime>`).
  - **The aspect jump** affected every H3 clip, including the approved S08.
    - **What happens:** H3 puts the keyframe in as frame 0 exactly, then generates frames about 2.5% wider (horizontal only) over the first ~4 frames (~170 ms at 24 fps); the last ~4 frames snap back to the end keyframe.
    - **Cause:** Nano Banana's "16:9" keyframes are really 2752×1536 (1.792), and H3's canvas follows the image (1928×1076).
    - **Fix 1:** keyframes for H3 are now cropped to exactly 16:9 at 1920×1080 (`sixteen_nine`). H3 then renders a true 1920×1080, and the stretch drops to ~0.75% (S13 test). This is what H3's first/last-frame guides advise: match the frames to the target ratio and size.
    - **Fix 2:** every H3 clip's first and last 4 frames are held (`steady`), keeping its length and timing.
    - **Result:** motion in the first 0.2 s after each cut is now 0.1–1.5, against 5–10 before.
    - S07–S11 keep their takes (only the hold is applied); re-rendering them at 16:9 would cost about $5.50. The approved S08 file is untouched; the held copy is `media/full/steady/`.
  - **Fire watch** (author): on guard duty by the left wall from S12a on, out of the DI's way.
    - All of his keyframes are redone: S12a is an edit of round 2's hallway, so the framing and his size stay; then S12b, S14b, S15a and S15b.
    - S15b is now the fire watch alone. In the animation H3 walks the DI out through the dark doorway beside the switch, not down the hall as prompted.
  - **New `full.py audit`** checks every shot of both cuts:
    - the clip was made from the current keyframe picks;
    - the audio it was driven by matches the current voice;
    - the render's frames match the source, and its audio is the cut's mix;
    - the motion right after each cut is calm.
    It reports everything consistent.
  - **Spend:** about $3.70 this round; the project total is about $77 of the ~$80 budget.
- **"Pront" (author, round 3):**
  - **What was wrong:** S07's "Prompt!" read as "Pront" in both cuts, though the raw take is clear.
  - **Cause:** the barracks reverb on every solo line (`scripts/di.py`). Its long low tail (1.4 s) filled the ~0.1 s silence inside "Prompt", which is what makes the P, and smeared the T. The source take and its placement were right; the earlier waveform check proved only which take was in the mix, not how it sounded. This is likely also why the first read sounded hard to understand.
  - **Fix:**
    - while a line is being said, the tail is held at 10%, and it rings out fully once the line ends;
    - the tail is high-passed at 200 Hz.
  - **Result:** the gaps inside every DI and fire watch line are 6–18 dB cleaner ("Prompt" −29 → −46 dB), and the room after each line is unchanged.
  - No regeneration was needed: lip sync and the pinned H3 audio use the dry track, which is unchanged. The audit still reports everything consistent.
- **Budget:** the author added $25, so about $105 in all.
- **Full render, round 4 (author feedback):**
  - **"Still Pront":**
    - **The full chain on a solo line was:** Fish read → cut → `place()` (air-damping low-pass + floor, ceiling and wall copies 3.6–18 ms late) → barracks reverb tail → mix.
    - **Cause:** the early-reflection copies comb-filtered the voice and caused most of the change to the word's spectrum; holding the tail down (round 3) had only fixed part of it.
    - **Fix:** solo lines now get no early reflections, no air damping and no tail while a line is said. Inside every line, the mix is the raw read itself (r = 1.0000, 1.5 ms of distance delay). The room's tail rings out after each line exactly as loud as before.
    - **A/B:** the S07 row of the storyboard plays the raw take, the old processing and the new one side by side.
  - **S12:** starts on a new keyframe (S12a2) with Jensen already walking in on the left, his face from his real photos, so the model doesn't invent a face for the first half.
  - **S15-2:** ends on Jensen walking away down the hall past the fire watch (S15b r7), not through a doorway.
  - **S15-1:** loses its first 0.7 s, the dark beat before "Close your laptops!". The generative cut drops 98.5–99.2 s of its timeline, and its soundtrack is now built from the same shot spans as its picture. The generative cut is 67.9 s.
- **S07 still read as "Pront" in the video (round 5):**
  - **The audio was not the problem:** the clip's audio track is the "now" WAV (r = 0.9996, AAC only, zero offset).
  - **Cause:** the picture. In the H3 animation Jensen's lips never close for the M and P of "Prompt": after the vowel his teeth are bared, the mouth shape of an N or T. Seen and heard together, the brain fuses them into "Pront" (the McGurk effect), so only the video reproduced it.
  - **Fix:** sync-3 over the H3 clip, driven by the same voice (`full.py resync`, `RESYNC = ("S07",)`). The lips now close at ~0.75–0.81 s for the M and P and part for the T, in time with the audio. Cost about $0.30.
  - **Takeaway:** a generated mouth can change what a line sounds like. Check bilabial closures (P, B, M) on short barked lines.
- **Round 5 (author):**
  - **S15-2: the fire watch says his line on camera.** H3's pinned audio hadn't moved his ~100 px face, and sync-3 passed his helmeted face through untouched, even on a 4× crop. Fix: H3 Max Lip Sync on a 4× crop around his head (the whole 5.1 s shot, since it needs 5 s or more; the DI stays outside the crop), blended back through a soft oval over the mouth and jaw (`RESYNC_CROP`). The DI needs no lip sync; his back is to the camera.
  - **End credits** (`scripts/credits.py`): a black card rendered locally from HTML with subtle CSS animation; each frame is a headless Chrome screenshot with the animations paused at that time.
    - It shows "Created by @transitive_bs" and "Featuring" @JensenHuang, @mattpocockuk, @steipete, @swyx, @simonw and @poteto, with their X avatars from the local archive (`media/credits/avatars/`), plus "Made with Opus 5.5 · H3 Max · Fal Sync-3 · ElevenLabs · Fish Audio".
    - The generative cut holds its last frame 0.4 s, crossfades into the card over 1 s while the room tail fades out underneath, and is now 72.7 s.
    - The lip sync cut keeps its plain ending, since its picture shows the film's actors.
- **S10, Matt's close-up (round 5):**
  - **References:** five real side and looking-up frames (`reference/cast/matt/raw/side/`, mostly from the Pragmatic Engineer podcast's side camera) feed an updated sheet, r4 B (author approved). It keeps the r3 look and adds tilted-back, chin-up and big-smile views.
  - **Keyframe:** r5 B (author approved) puts his face toward the camera in three-quarter view, both eyes visible. The original's low-angle profile turned the face away, and no reference could make that read as him.
  - **Animation:** made without the chant pinned (`UNPINNED`). Pinned, H3 tipped his head back mid-shot and turned his face away; unpinned, it holds the approved pose for the whole 11 s. sync-3 then adds the chant to his mouth (`RESYNC`).
  - **Spend:** the project total is about $87.50 of the ~$105 budget.
- **S10, round 6 (author):**
  - **Keyframe:** r6 A (author's pick), an edit of r5 B with Matt looking down toward his laptop in a steep three-quarter near-profile. His real near-profile and steep three-quarter photos keep the side view his.
  - **Animation:** made the same way as round 5, without the chant pinned, then sync-3. His head holds the pose for the whole shot, and his mouth follows the chant.
- **S10 lip sync, round 6 (author):** more vigorous, and "Ship it!" (9.5–9.9 s) was missing.
  - **Cause:** the voice track had "Ship it!", but sync-3 animates a near-profile mouth very timidly and all but skipped it.
  - **Compared:**

    | Lip sync | Mouth motion | During "Ship it!" | Tracks the voice |
    | --- | --- | --- | --- |
    | sync-3 | 1.39 | 1.04 | r = 0.24 |
    | React-1 (face mode, expressiveness 0.9, happy) | 1.07 | 1.01 | r = 0.01 |
    | H3 Max Lip Sync | 1.47 | 1.85 | r = 0.36 |

  - **Fix:** H3 Max Lip Sync on a 2× crop of his face, with only the mouth and jaw blended into the 1080p take (`RESYNC_CROP`), so his eyes and glasses stay sharp. "Ship it!" now opens wide, and the mouth tracks the voice best (r = 0.38). The sync-3 take is kept as `S10-r6-sync3.mp4`.
- **Captions (generative cut only, author's call):**
  - **Rendering:** HyperFrames, not ffmpeg subtitles, in `captions/`. The look is one dark rounded band low in frame, Oswald Bold in capitals (AGENTS.md keeps its case), and each word glows gold as it is sung (karaoke). The DI's one-word barks are a size up. The layer renders on its own as transparent ProRes 4444 and is laid over `renders/full/generative.mp4`, so the footage and sound stay untouched → `renders/full/generative-captioned.mp4`. The credits card carries no captions.
  - **Editing:** `captions/captions.json` holds every line's text and word times. Edit it, then run `npm run captions` in `captions/`. A line's optional `"break"` (word index) sets where it wraps; lines over 50 characters otherwise split into two balanced rows.
  - **Timing** (`scripts/captions.py`, rerun when the audio changes):
    - Whisper only finds each line in its read. Every word is then force-aligned (torchaudio MMS) against the audio it was cut from: the clean DI and fire watch reads, and the chorus take's vocal stem (MelBand RoFormer, cached as `full.stereo.vocals.wav`).
    - Each line starts at its measured audible onset (10% of its peak, as `di.edges`), after the previous line's tail has decayed. The take's raw cut points run up to 0.75 s ahead of the singing (C15, C16).
    - Times then follow the reads' placement onto the cut, including the 0.7 s it drops.
  - **Checked against the finished cut's own separated vocals:**
    - Chorus line starts are within ±25 ms on 17 of 18 lines. C03 is a check artifact; its energy rises at 8.22 s, captioned at 8.24.
    - DI and fire watch starts lead the voice by 0–70 ms.
    - Aligned word starts sit a median 23 ms from the sung consonant dips, against 40 ms for Whisper's.
- **Credits, round 7 (author):**
  - **No frozen frames before the card:** the last frame used to hold 0.4 s, then fade from that still over 1 s; the shot's own motion had already stopped at 66.27 s. Now a 0.8 s crossfade finishes as the last shot ends, so the footage still moves under it. The sound is unchanged: the room tail still fades from 0.4 s after the shot, once "sir!" is done.
  - **The card holds 4.5 s longer** (10.5 s, so the cut runs 76.1 s).
  - **Profile pictures:** the largest copies found of each X picture (`credits.py` AVATARS, sources in `media/credits/sources/`):
    - **Creator:** the author's own 1024 px photo.
    - **Jensen:** NVIDIA's 1920 px press portrait, framed head and shoulders.
    - **Matt:** his YouTube channel's 900 px copy.
    - **Simon and swyx:** their 460 px GitHub copies.
    - **steipete and poteto:** their X originals (512 and 400 px).
  - **Look:** each picture sits in a hairline ring of warm light, set off by a thin black gap. The circles are larger (144 px cast, 128 px creator).
  - **swyx:** the author's 900 px copy of his picture replaces the 460 px GitHub one.
  - **The card moved to HyperFrames** (author's call), replacing `credits.py`'s own headless-Chrome screenshot loop. That loop kept breaking under load: two captures sharing a Chrome profile abort on its lock. The card is now `captions/compositions/credits-card.html`, with its animations on a seekable GSAP timeline and Inter for the system font. `npm run credits` renders it in about 14 s (the old loop took about 5 min), and it can be edited in Studio like the captions. `credits.py` now only prepares the pictures and then calls that render.
- **S10 in the cut was still the sync-3 take (round 7, author):** the approved H3 Lip Sync blend had been written over `S10-r6-ls.mp4`, but the cut's steady and conformed copies were cached under that same name and kept serving the earlier sync-3 version. Derived clips now rebuild whenever their source is newer (`variants.fresh`, used by `conform`, `steady` and `trim_head`). No other shot was stale. The credits' "Made with" line is a size up (24 px).

---
workflow: general-video
flow: automation
storyboard: no
message: "Every sung and barked line reads on screen, in time with the voice"
aspect: 1920x1080
language: en
length: 72.7s
---

## Intent

Captions for "This Is My Software Factory" (the fully generative cut), a parody of the Full Metal Jacket creed scene.
Rendered locally with HyperFrames as an overlay layer: they must "look really solid" and "match up with the vocals
very precisely for each scene". They must be "really easy and quick to make changes to".

## Assets

- ../renders/full/generative.mp4 — the finished generative cut (72.7 s, 1920x1080, 29.97 fps); the captions go over it, the footage stays untouched.
- ../data/script.json — the locked parody lines (the caption text).
- ../data/chorus.json, ../data/di-gen.json, ../data/voices.json — where each line sounds on the generative cut's timeline, and the source reads whose Whisper word timings give per-word timing.

## Customizations

- Word-by-word highlight: each word lights up as it is sung or barked, so the sync is visible.
- One editable source: captions.json (line text, words, timings); a one-command re-render of the caption layer only, composited over the existing cut.

## Notes

- The fully generative cut (the project's only cut since the lip sync cut was dropped).
- Captions end before the credits crossfade (the credits card carries no captions).
- Timings come from our own source reads mapped onto the cut's timeline (it drops 0.7 s at S15-1), not a fresh transcription of the finished mix.
- Design left to the workflow; no storyboard review: one finished render, then the author reviews it.

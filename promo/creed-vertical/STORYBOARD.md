# The AI Engineer's Creed, vertical (9:16)

The 16:9 cut re-framed for phones: YouTube Shorts, Instagram Reels and TikTok. Same timeline frame for frame (2280
frames, 76.08 s) and the same soundtrack sample for sample.

- Footage: `crop.py` takes a full-height 9:16 window (607.5x1080) of the cut's footage
  (`media/full/cuts/generative-video.mp4`; the clips in `renders/full/shots/` run a few frames short) and scales it to
  1080x1920. Windows are centred on the speaker, in source x; pans ease through keyframes:

  | Shot  | Cut (s)     | Framing                                                                                     |
  | ----- | ----------- | ------------------------------------------------------------------------------------------- |
  | S07   | 0.00-2.20   | The DI's face (x 990, as in the McGurk vertical)                                            |
  | S08   | 2.20-12.81  | Matt on the bunk: head and hands (x 1380)                                                   |
  | S09   | 12.81-22.99 | steipete at the left edge (x 304); the lobster is out of frame                              |
  | S10   | 22.99-34.10 | Matt's close-up (x 1460)                                                                    |
  | S11   | 34.10-47.38 | swyx (x 600)                                                                                |
  | S12   | 47.38-54.49 | Follows the DI in from the left (728 to 1160 by 1.95 s), then eases right as he steps in    |
  | S13   | 54.49-56.11 | As S09                                                                                      |
  | S14   | 56.11-59.16 | The DI for "Auto-merge!", then eases right to his hand on the light switch (1.75-2.5 s)     |
  | S15-1 | 59.16-61.26 | His silhouette at the switch (x 1400)                                                       |
  | S15-2 | 61.26-66.37 | Follows him off down the hall, settling with the fire watch in frame for his line (by 4 s)  |

- Captions: `build.mjs` builds them from `../../captions/captions.json`, so the timing is the 16:9 cut's. Same look
  (Oswald 700 capitals on the dark band, the sung word lit gold), at 64px (82px for the DI's barks), wrapped into
  balanced rows inside the safe area's width. They sit low, on the chest (foot at y 1340), except where the face is low
  in frame (S08-S10, S13): there they sit high (top at y 290).
- Phone safe area: every text block sits inside x 100-900, y 260-1360, clear of the platform UI.
- Title (`compositions/title.html`): frame 0 only, as in the 16:9 cut: the title in three rows and "A parody of Full
  Metal Jacket" in the lower third of the DI's first frame, clear of his face and inside a profile grid's 3:4 crop. It
  is the post's cover; the thumbnail is that frame.
- Clip (`export.py clip`): the creed's opening alone (0-8.15 s: the title frame, "Prompt!", C01 and C02) with a 0.25 s
  fade out, the vertical twin of the wide clip (`scripts/release.py clip`).
- Credits (`compositions/credits-card.html`): the 16:9 card stacked, the cast in a 3x2 grid; it crossfades in over the
  last 0.8 s of S15-2, as in the 16:9 cut.

Render (about 5 min): `crop.py`, `npm run overlay`, then `export.py` writes `renders/promo/final/ai-engineers-creed-vertical.mp4`
and `-thumbnail.jpg` and checks the length and the audio against the 16:9 files (`export.py draft` makes a review copy).

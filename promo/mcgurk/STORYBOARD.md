# McGurk effect demo (for AI engineers)

Locked 2026-10-17: this wide cut is final. The vertical variant is `../mcgurk-vertical`.

One generated shot (S07 of the fully generative cut), the same audio twice. "After" is the lip-synced fix (sync-3,
lips close for the M and P), "before" is the H3-only take whose lips never close. Watching the before clip, most
people hear "Pront". 1920x1080, ~49.4 s, hard cuts, no fade-in: frame 0 is the after clip's first frame.

| # | Time (s) | Picture | Sound |
| --- | --- | --- | --- |
| 1 | 0.00–2.20 | after.mp4, no caption | "Prompt!" |
| 2 | 2.20–4.05 | Black card, typed: `> Same exact audio...` | silence |
| 3 | 4.05–6.25 | before.mp4, no caption | "Prompt!" (heard as "Pront") |
| 4 | 6.25–10.75 | Black card, typed: `> Did you hear "Pront" in the second one?` ("Pront" misspelled on purpose, in red), then in italics `it's the exact same audio, I promise!` | silence |
| 5 | 10.75–15.15 | after.mp4, caption `original => "Prompt"`; before.mp4, caption `same audio => "Pront"` | "Prompt!" twice |
| 6 | 15.15–23.40 | Card C, typed and wrapped: "Wait, wtf is going on? / Both shots have the exact same audio; only the lip sync changes. / This is an example of the **McGurk effect**. / Let's listen again..." | silence |
| 7 | 23.40–38.00 | after.mp4 (caption `original`, no word), before.mp4 (no caption), rewind, the pair again, rewind, the pair a third time. No words in the captions, so nothing biases the listener | |
| 8 | 38.00–49.37 | Card D, the recap: "**The McGurk effect**: what you see changes what you hear. / If a generated mouth never closes for P, B or M, viewers hear a different word, even over perfect audio. / When you lip-sync AI video, check the closures, not just the timing." | silence |

Assets: `assets/after.mp4` and `assets/before.mp4` are `renders/full/compare/` (byte-identical audio), and
`assets/rewind.mp4` is the before clip reversed at 3x with ffmpeg (HyperFrames has no reverse playback). Type: JetBrains Mono (OFL).
Render: `npm run render` (hyperframes 0.8.168) -> `../../renders/promo/mcgurk.mp4`.

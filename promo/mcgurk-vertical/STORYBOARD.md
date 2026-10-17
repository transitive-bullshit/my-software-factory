# McGurk effect demo, vertical (9:16)

The locked wide cut (`../mcgurk/STORYBOARD.md`) re-laid out for phones: Shorts, Reels and TikTok. The timeline, text and
audio are the same, scene for scene and sample for sample.

- Clips: `crop.sh` takes a full-height 9:16 window of each wide clip (608x1080 at x=686, centred on the face) and scales
  it to 1080x1920, so the mouth sits mid-screen. The audio is copied untouched.
- Text stays inside the phone safe area (x 100-900, y 260-1360), clear of the platform UI on the top, bottom and the
  right-hand buttons. Cards wrap in place: JetBrains Mono at 60px (A, B) and 50px (C, D).
- Captions sit on the chest, centred on the frame (y 1254, moved 7.5% lower than first laid out); the rewind badge is
  top left, inside the safe area.

Render: `npx hyperframes render -o ../../renders/promo/final/mcgurk-vertical-master.mp4 --fps 30 --crf 12`, then
`export.py` -> `renders/promo/final/mcgurk-vertical.mp4`.

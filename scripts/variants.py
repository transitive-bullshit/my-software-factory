"""Visual variants of the test scenes (S07 + S08), all on the approved audio.

  lipsync     the original footage; only the speaking mouths are re-synced, with sync-3 on every shot
  generative  no original footage: character sheets, then keyframes composed like the original shots but generated
              from a written description (Nano Banana Pro). S07 is animated from the audio (OmniHuman v2). S08 is
              animated with calm typing (Kling v3 Pro or H3 Max), then lip-synced (generative-r3, generative-r4).

Every fal call is cached by its output path and logged with its estimated cost in data/fal-log.jsonl.

  uv run --group analysis --group voice --group gen python scripts/variants.py prep|lipsync|frames|generative|generative-r3|generative-r4|assemble|all
  (frames = the character sheets and keyframes only; picks go in media/variants/generative/picks.json)
"""

import json
import subprocess
import sys
import traceback
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import fal_run  # noqa: E402
from audio import ROOT, SR, SRC, ff  # noqa: E402

OUT = ROOT / "media" / "variants"
SHOTS = ("S07", "S08")
FPS = "30000/1001"
CAST = {
  "jensen": ["reference/cast/jensen/jensen-1.jpg", "reference/cast/jensen/jensen-2.jpg", "reference/cast/jensen/jensen-3.jpg"],
  "matt": ["reference/cast/matt/matt-x.jpg", "reference/cast/matt/matt-studio.jpg", "reference/cast/matt/matt-vertical.jpg"],
}
# bump a character's revision when its references change; keyframes and animations of its shots follow
REV = {"jensen": 1, "matt": 2}
SHOT_CAST = {"S07": "jensen", "S08": "matt"}
# bump a shot's revision when its keyframe brief changes; its animation follows
# (S08 r3: laptops instead of rifles; r4: the laptops rest on the recruits' stomachs, not held up)
SHOT_REV = {"S07": 1, "S08": 4}
# shots generative() animates (OmniHuman v2). Its moderation rejects every S08 keyframe (men lying in bunks), so S08 is
# animated by generative-r3/r4 instead
ANIMATED = ("S07",)


def tag(rev: int) -> str:
  return "" if rev == 1 else f"-r{rev}"
POTETO = "reference/avatars/poteto.jpg"


def rel(p: Path) -> str:
  return str(p.relative_to(ROOT))


def spans() -> dict[str, tuple[float, float]]:
  script = json.loads((ROOT / "data" / "script.json").read_text())
  return {s["id"]: (s["start"], s["end"]) for s in script["shots"] if s["id"] in SHOTS}


def window_start() -> float:
  return json.loads((ROOT / "data" / "script.json").read_text())["window"]["start"]


def first_video(files: list[str]) -> Path:
  return ROOT / next(f for f in files if f.endswith((".mp4", ".mov", ".webm")))


def first_image(files: list[str]) -> Path:
  return ROOT / next(f for f in files if f.endswith((".png", ".jpg", ".jpeg", ".webp")))


def prep() -> None:
  """Per shot: the original video, its voice (the raw reads that are heard in it), and the approved mix."""
  d = OUT / "shots"
  d.mkdir(parents=True, exist_ok=True)
  w0 = window_start()
  solo = sf.read(ROOT / "media" / "voices" / "di" / "di-dry.wav", dtype="float32")[0]
  chorus = sf.read(ROOT / "media" / "voices" / "chorus-music" / json.loads((ROOT / "data" / "chorus.json").read_text())["variant"]
                   / "track.wav", dtype="float32")[0]
  chorus = chorus.mean(1) if chorus.ndim > 1 else chorus
  mix = sf.read(ROOT / "media" / "voices" / "full-pass.wav", dtype="float32")[0]
  for sid, (a, b) in spans().items():
    video = d / f"{sid}.mp4"
    if not video.exists():
      ff("-ss", f"{a:.3f}", "-i", str(SRC), "-t", f"{b - a:.3f}", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(video))
    i, j = int((a - w0) * SR), int((b - w0) * SR)
    voice = np.zeros(j - i, np.float32)
    for track in (solo, chorus):
      seg = track[i:j]
      voice[: len(seg)] += seg
    voice *= 0.9 / (np.abs(voice).max() + 1e-9)
    sf.write(d / f"{sid}-voice.wav", voice, SR, subtype="PCM_16")
    # OmniHuman needs at least 4 s of audio: pad with silence, trim the video back afterwards
    sf.write(d / f"{sid}-voice-4s.wav", np.pad(voice, (0, max(0, int(4.05 * SR) - len(voice)))), SR, subtype="PCM_16")
    sf.write(d / f"{sid}-mix.wav", mix[i:j], SR, subtype="PCM_16")
    print(f"{sid}: {b - a:.2f}s  {rel(video)}")


def lipsync() -> None:
  for sid, (a, b) in spans().items():
    files = fal_run.run("fal-ai/sync-lipsync/v3",
                        {"video_url": f"@media/variants/shots/{sid}.mp4", "audio_url": f"@media/variants/shots/{sid}-voice.wav",
                         "sync_mode": "cut_off"},
                        OUT / "lipsync" / sid, est_cost=round((b - a) / 60 * 8, 2), job=f"variants/lipsync/{sid}")
    print(sid, files)


def fresh(dest: Path, src: Path) -> bool:
  """A derived file is reusable only if it is newer than its source: a source re-made under the same name (a new lip
  sync written over S10-r6-ls.mp4, round 6) must not keep serving the old take."""
  return dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime


def conform(src: Path, seconds: float, dest: Path, inset: tuple[int, int, int, int] | None = None) -> Path:
  """1920x1080 at 29.97 fps, exactly `seconds` long (the last frame is held if the clip is short).
  `inset` (left, right, top, bottom px) trims black bars a model baked in, then the frame is scaled to fill."""
  if not fresh(dest, src):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if inset:
      l, r, t, b = inset
      fit = f"crop=iw-{l + r}:ih-{t + b}:{l}:{t},scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    else:
      w, h = (int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                               "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True).stdout.split(",")[:2])
      # near-16:9 (H3 Max renders 1928x1076): fill and crop the sliver instead of padding thin black bars
      fit = ("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080" if abs(w / h / (16 / 9) - 1) < 0.03
             else "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2")
    ff("-i", str(src), "-an", "-vf", f"{fit},fps={FPS},tpad=stop_mode=clone:stop_duration=2", "-t", f"{seconds:.3f}",
       "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(dest))
  return dest


def concat(parts: list[Path], dest: Path) -> Path:
  if not dest.exists():
    lst = dest.with_suffix(".txt")
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dest))
  return dest


SHEETS = {
  "jensen": ("Character reference sheet of the man in these photos (Jensen Huang), keeping his exact face, grey hair and "
             "glasses. Three full-length views side by side on a plain light-grey studio background: front, three-quarter, "
             "profile. He is cast as a stern 1980s Marine drill instructor: his signature black leather jacket over a black "
             "t-shirt, dark trousers, and a tan drill instructor campaign hat. Commanding posture. Even soft light, photographic."),
  "matt": ("Character reference sheet of the man in this photo (Matt Pocock), keeping his exact face, hairline and glasses. "
           "Three views side by side on a plain light-grey studio background: front, three-quarter, profile, head and "
           "shoulders. He is cast as a 1980s Marine recruit: very short buzzed hair, plain white crew-neck t-shirt. "
           "Earnest, slightly anxious expression. Even soft light, photographic."),
}
KEYFRAMES = {
  "S07": ("A new film still, not a copy of any existing film: a medium close-up, eye level and frontal, of a drill "
          "instructor standing in a small 1980s Marine Corps office at night, staring straight into the lens, mouth "
          "slightly open as if about to bark an order. He is the man from the character sheet: black leather jacket, tan "
          "campaign hat. Behind him, slightly out of focus: a dark chalkboard on a pale green wall, a wooden desk with a "
          "couple of small trophies, and on the right a small poster reading 'PRs' above the anime girl holding a sweet "
          "potato from the second image. Warm practical light, muted khaki and green, 35mm film grain, 1987 look, 16:9."),
  "S08": ("A new film still, not a copy of any existing film: a medium-wide, locked-off shot down the long aisle of a "
          "1980s Marine barracks squad bay at night. In the foreground, a recruit lies on his back on a lower bunk, seen in "
          "profile with his head at the right of frame, an open silver MacBook Pro laptop resting flat on his stomach, "
          "screen tilted up toward his face, both hands on the keyboard typing code, the screen's cool glow on his face, "
          "mouth open mid-chant. He is the man from the character sheet: white t-shirt, glasses. Double bunks with olive "
          "wool blankets recede down the aisle; the other recruits lie in them on their backs, each with an open laptop "
          "resting on his stomach, typing: a row of glowing screens. Nobody holds a laptop up in the air. No weapons anywhere. Polished floor, overhead fluorescent lights, cool green walls, 35mm film grain, "
          "1987 look, 16:9."),
}
MOTION = {
  "S07": "The drill instructor barks a single short command, then holds a hard stare. Static camera, no cuts.",
  "S08": ("The recruit lying in the foreground keeps typing on the open laptop resting on his stomach while he chants "
          "loudly in unison with the room. The recruits in the background bunks type and chant too. Static camera, no cuts."),
}


def generative(animate: bool = True) -> None:
  d = OUT / "generative"
  sheets = {}
  for who, prompt in SHEETS.items():
    files = fal_run.run("fal-ai/nano-banana-pro/edit",
                        {"prompt": prompt, "image_urls": ["@" + p for p in CAST[who]], "aspect_ratio": "16:9", "resolution": "2K",
                         "num_images": 1, "output_format": "png"},
                        d / f"sheet-{who}{tag(REV[who])}", est_cost=0.15, job=f"variants/generative/sheet-{who}{tag(REV[who])}")
    sheets[who] = first_image(files)
    print("sheet", who, files)
  refs = {"S07": [sheets["jensen"], ROOT / POTETO], "S08": [sheets["matt"]]}
  picks = json.loads((d / "picks.json").read_text()) if (d / "picks.json").exists() else {}
  sp = spans()
  for sid, prompt in KEYFRAMES.items():
    files = fal_run.run("fal-ai/nano-banana-pro/edit",
                        {"prompt": prompt, "image_urls": ["@" + rel(p) for p in refs[sid]], "aspect_ratio": "16:9",
                         "resolution": "2K", "num_images": 2, "output_format": "png"},
                        d / f"key-{sid}{tag(SHOT_REV[sid])}", est_cost=0.30, job=f"variants/generative/key-{sid}{tag(SHOT_REV[sid])}")
    print("keyframe", sid, files)
    if not animate or sid not in ANIMATED:
      continue
    key = ROOT / picks.get(sid, files[0])
    a, b = sp[sid]
    audio = f"media/variants/shots/{sid}-voice{'-4s' if b - a < 4 else ''}.wav"
    t = tag(SHOT_REV[sid])
    files = fal_run.run("bytedance/omnihuman/v2", {"image_url": "@" + rel(key), "audio_url": "@" + audio, "prompt": MOTION[sid]},
                        d / f"omni-{sid}{t}", est_cost=round(0.105 * max(4.05, b - a), 2), job=f"variants/generative/omni-{sid}{t}")
    print("omnihuman", sid, files)


# S08 candidates per variant (output prefixes under media/variants); the one in the cut comes from round-picks.json
OPTIONS = {
  "generative": {"Kling v3 Pro (calm typing) + sync-3": "generative/kling-S08-r4-ls",
                 "H3 Max Lip Sync (round 3)": "generative/h3-S08-r4",
                 "H3 Max calm typing, voice pinned (one pass)": "generative/h3audio-S08-r4-anchor",
                 "H3 Max calm typing + H3 Max Lip Sync": "generative/h3calm-S08-r4-anchor-ls"},
}
DEFAULT_PICKS = {"lipsync": {"S07": "lipsync/S07", "S08": "lipsync/S08"},
                 "generative": {"S07": "generative/omni-S07", "S08": "generative/kling-S08-r4-ls"}}


def round_picks() -> dict:
  p = OUT / "round-picks.json"
  picks = json.loads(p.read_text()) if p.exists() else DEFAULT_PICKS
  return {k: v for k, v in picks.items() if k != "why"}


# black bars baked into some generated clips (measured): (left, right, top, bottom) px
INSETS = {("generative", "S07"): (0, 0, 11, 11)}  # the S08 r4 render has none


def assemble() -> None:
  sp = spans()
  d = OUT / "cuts"
  d.mkdir(parents=True, exist_ok=True)
  mix = d / "mix-s07-s08.wav"
  if not mix.exists():
    sf.write(mix, np.concatenate([sf.read(OUT / "shots" / f"{sid}-mix.wav", dtype="float32")[0] for sid in SHOTS]), SR)

  def found(prefix: Path) -> Path | None:
    # exact name first: "S08" must not pick up "S08-lipsync2" (sorts ahead of "S08.mp4")
    exact = [prefix.parent / (prefix.name + ext) for ext in (".mp4", ".mov", ".webm")]
    hits = [p for p in exact if p.exists()] or sorted(p for p in prefix.parent.glob(prefix.name + "-*") if p.suffix in (".mp4", ".mov", ".webm"))
    return hits[0] if hits else None

  picks = round_picks()
  sources = {"original": {sid: OUT / "shots" / f"{sid}.mp4" for sid in SHOTS}}
  for name, per in picks.items():
    sources[name] = {sid: found(OUT / per[sid]) for sid in SHOTS}
  # every S08 candidate as its own clip with the shot's audio, for the options blocks on the review page
  opt_dir = ROOT / "renders" / "variants" / "options"
  opt_dir.mkdir(parents=True, exist_ok=True)
  a8, b8 = sp["S08"]
  for variant, opts in OPTIONS.items():
    for label, prefix in opts.items():
      src = found(OUT / prefix)
      if not src:
        continue
      clip = conform(src, b8 - a8, d / f"opt-{variant}-{Path(prefix).name}.mp4")
      out = opt_dir / f"{variant}-{Path(prefix).name}.mp4"
      ff("-i", str(clip), "-i", str(OUT / "shots" / "S08-mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
         "-b:a", "192k", "-shortest", str(out))
  total = sum(b - a for a, b in sp.values())
  for name, srcs in sources.items():
    if any(v is None for v in srcs.values()):
      print(f"skip {name}: missing {[k for k, v in srcs.items() if v is None]}")
      continue
    if "both" in srcs:
      video = conform(srcs["both"], total, d / f"{name}-video.mp4")
    else:
      video = concat([conform(srcs[sid], b - a, d / f"{name}-{sid}.mp4", INSETS.get((name, sid))) for sid, (a, b) in sp.items()],
                     d / f"{name}-video.mp4")
    out = ROOT / "renders" / "variants" / f"{name}-s07-s08.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-i", str(video), "-i", str(mix), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out))
    print(rel(out))


CALM = ("Static, locked-off camera, no camera movement, no cuts. The recruit lying on his back in the foreground calmly types "
        "on the open laptop resting on his stomach: hands stay on the keyboard with small, steady typing motions, arms still. "
        "He chants loudly, mouth open on each word, head and body relaxed and still. The recruits in the background bunks lie "
        "still, typing calmly on their laptops.")
CALM_NEG = "flailing arms, waving hands, lifting the laptop, fast motion, jerky motion, camera movement, zoom, cuts, blur, distortion, low quality"
# H3 Max takes no negative prompt, so the calm is spelled out more
CALM_H3 = ("Static, locked-off camera, no camera movement, no cuts. The recruit lying on his back in the foreground calmly types "
           "on the open laptop resting flat on his stomach the whole time, like a programmer focused on his code: both hands stay "
           "on the keyboard, only his fingers move in small, steady, relaxed keystrokes; wrists, arms and shoulders stay still. "
           "He chants loudly, mouth opening on each word, while his head and body stay relaxed and still on the pillow. The "
           "laptop never moves. The recruits in the background bunks lie still, typing calmly on their laptops.")


def generative_r3() -> None:
  """S08 without InfiniteTalk: Kling v3 Pro for calm typing motion, then sync-3 for the shouting; and H3 Max Lip Sync in one pass."""
  d = OUT / "generative"
  a, b = spans()["S08"]
  key = ROOT / json.loads((d / "picks.json").read_text())["S08"]
  t = tag(SHOT_REV["S08"])
  try:
    files = fal_run.run("fal-ai/kling-video/v3/pro/image-to-video",
                        {"start_image_url": "@" + rel(key), "prompt": CALM, "negative_prompt": CALM_NEG, "duration": "11",
                         "generate_audio": False, "cfg_scale": 0.6},
                        d / f"kling-S08{t}", est_cost=round(0.112 * 11, 2), job=f"variants/generative/kling-S08{t}")
    kling = first_video(files)
    trimmed = d / f"kling-S08{t}-trim.mp4"
    if not trimmed.exists():
      ff("-i", str(kling), "-t", f"{b - a:.3f}", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(trimmed))
    print("kling+sync3", fal_run.run("fal-ai/sync-lipsync/v3",
                                     {"video_url": "@" + rel(trimmed), "audio_url": "@media/variants/shots/S08-voice.wav", "sync_mode": "cut_off"},
                                     d / f"kling-S08{t}-ls", est_cost=round((b - a) / 60 * 8, 2), job=f"variants/generative/kling-S08{t}-ls"))
  except Exception as e:
    print(f"kling failed: {str(e)[:220]}")
  try:
    print("h3", fal_run.run("minimax/h3-max/lip-sync/image-to-video",
                            {"image_url": "@" + rel(key), "audio_url": "@media/variants/shots/S08-voice.wav", "resolution": "768P",
                             "enable_transcription": True},
                            d / f"h3-S08{t}", est_cost=round(0.08 * (b - a), 2), job=f"variants/generative/h3-S08{t}"))
  except Exception as e:
    print(f"h3 failed: {str(e)[:220]}")


# H3 Max pushed the camera in on the first try (seed 7), so later takes open and close on the locked camera
CALM_H3_LOCKED = ("Locked-off tripod shot: the camera does not move at all for the whole clip. No push-in, no zoom, no dolly, no pan; "
                  "the framing stays exactly as in the first frame, with the full aisle of bunks visible. " + CALM_H3.split("no cuts. ", 1)[1]
                  + " The camera never moves.")
# (suffix, prompt, seed, anchor) per take; the motion-only takes listed in H3_LIPSYNC also get H3 Max Lip Sync.
# The prompt alone never held the camera (every take pushes in), so "anchor" also passes the keyframe as the last frame.
H3_TAKES = [("", CALM_H3, 7, False), ("-s11", CALM_H3_LOCKED, 11, False), ("-s23", CALM_H3_LOCKED, 23, False),
            ("-anchor", CALM_H3_LOCKED, 7, True)]
H3_LIPSYNC = ("", "-anchor")


def generative_r4() -> None:
  """S08 with H3 Max, prompted for calmer typing (its Lip Sync endpoint takes no prompt): image-to-video with the voice
  pinned as its soundtrack in one pass, and image-to-video without audio followed by H3 Max Lip Sync video-to-video."""
  d = OUT / "generative"
  a, b = spans()["S08"]
  key = ROOT / json.loads((d / "picks.json").read_text())["S08"]
  t = tag(SHOT_REV["S08"])
  i2v_cost = round(0.104 * (b - a + 0.7), 2)
  for sfx, prompt, seed, anchor in H3_TAKES:
    base = {"image_url": "@" + rel(key), "prompt": prompt, "duration": round(b - a, 2), "resolution": "1080P",
            "prompt_expansion_mode": "disabled", "seed": seed, **({"end_image_url": "@" + rel(key)} if anchor else {})}
    try:
      print("h3 pinned voice", sfx, fal_run.run("minimax/h3-max/image-to-video", {**base, "target_audio_url": "@media/variants/shots/S08-voice.wav"},
                                                d / f"h3audio-S08{t}{sfx}", est_cost=i2v_cost, job=f"variants/generative/h3audio-S08{t}{sfx}"))
      motion = first_video(fal_run.run("minimax/h3-max/image-to-video", base, d / f"h3calm-S08{t}{sfx}-motion", est_cost=i2v_cost,
                                       job=f"variants/generative/h3calm-S08{t}{sfx}-motion"))
      if sfx in H3_LIPSYNC:
        print("h3 calm + lip sync", sfx, fal_run.run("minimax/h3-max/lip-sync/video-to-video",
                                                     {"video_url": "@" + rel(motion), "audio_url": "@media/variants/shots/S08-voice.wav",
                                                      "duration_mode": "cut_off", "resolution": "768P"},
                                                     d / f"h3calm-S08{t}{sfx}-ls", est_cost=round(0.2 * (b - a), 2),
                                                     job=f"variants/generative/h3calm-S08{t}{sfx}-ls"))
    except Exception as e:
      print(f"h3 {sfx or 'seed 7'} failed: {str(e)[:220]}")


STEPS = {"prep": prep, "lipsync": lipsync, "frames": lambda: generative(animate=False), "generative": generative,
         "generative-r3": generative_r3, "generative-r4": generative_r4, "assemble": assemble}

if __name__ == "__main__":
  todo = list(STEPS) if sys.argv[1:] == ["all"] else sys.argv[1:]
  if not todo or any(t not in STEPS for t in todo):
    sys.exit(__doc__)
  for t in todo:
    try:
      print(f"== {t}")
      STEPS[t]()
    except Exception:  # keep going: one failed variant shouldn't block the others
      traceback.print_exc()

"""The full video (S07–S15), fully generative, on the approved audio.

No original footage: a keyframe per shot drawn from the approved cast sheets (Nano Banana Pro edit), animated with H3 Max
image-to-video: the keyframes are the first and last frame (so the camera holds), and the on-screen speaker's lines are
pinned as the soundtrack (so his mouth follows them). S08 comes from the approved S07+S08 test (scripts/variants.py); S07
is re-made from its approved keyframe with the new "Prompt!" read. The cut has its own timeline from S13 on
(scripts/di.py --variant gen: "Auto-merge!" comes sooner) and splits S15 at the end of "Close your laptops!", so the DI
walks off only after it. Every fal call is cached by its output path and logged with its estimated cost
(data/fal-log.jsonl). Keyframe picks: media/full/keyframes/picks.json (default: the first option). (A second cut, the
film's own footage re-lip-synced with sync-3, was dropped in round 8.)

  uv run --group analysis --group voice --group gen python scripts/full.py prep|keyframes [ids]|animate [ids]|resync [ids]|assemble|audit|page
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import fal_run  # noqa: E402
from audio import END_HOLD, ROOT, SR, ff  # noqa: E402
from variants import CALM_H3_LOCKED, conform, first_image, first_video, fresh, rel  # noqa: E402

OUT = ROOT / "media" / "full"
RENDERS = ROOT / "renders" / "full"
FIRST, LAST = "S07", "S15"
# lines whose speaker is on screen: the only ones the pinned soundtrack and the lip sync passes get (off-screen and
# hidden speakers are heard in the mix but move no mouth)
ONSCREEN = {"S07": ["D01"], "S08": ["C01", "C02", "C03", "C04"], "S09": ["C05", "C06", "C07"], "S10": ["C08", "C09", "C10", "C11"],
            "S11": ["C12", "C13", "C14", "C15", "C16"], "S12": ["D02", "D03"], "S13": [], "S14": ["D05"],
            "S15-1": [], "S15-2": ["F01"]}  # S15-1: D06 is said in silhouette, no visible mouth
PAD = (0.12, 0.2)  # seconds of each line's own track kept before and after it

APPROVED = {"S08": "media/variants/generative/h3audio-S08-r4-anchor.mp4"}  # shots taken from the S07+S08 test
# black bars baked into some generated clips (measured): (left, right, top, bottom) px. None left: S07's came from its
# keyframe, which is now cropped clean (media/full/keyframes/key-S07-clean.png)
INSETS: dict[str, tuple[int, int, int, int]] = {}

# the cut's own spans from S13 on (author: get to "Auto-merge!" faster; D05 moved to 95.6 s by scripts/di.py
# --variant gen). S15 splits where "Close your laptops!" ends, so the DI only walks off after his line.
# S15-1 starts 0.7 s late (author, round 4): the dark beat before "Close your laptops!" was too long; the cut drops
# 98.5–99.2 s of the timeline (silence), and the clip loses its first 0.7 s (TRIM_HEAD)
GEN_SPANS = {"S13": (93.83, 95.45), "S14": (95.45, 98.5), "S15-1": (99.2, 101.3), "S15-2": (101.3, 106.41)}
TRIM_HEAD = {"S15-1": 0.7}  # seconds cut from the start of a shot's clip
# the cut's timeline (scripts/di.py --variant gen): solo lines placed (data/), the dry solo track and the mix
# (media/voices/), per-shot audio (media/full/)
CUT = {"di": "di-gen.json", "dry": "di/di-dry-gen.wav", "mix": "full-pass-gen.wav", "shots": "shots-gen"}

# the approved cast sheets (cast review: the author approved the set; options as recommended)
SHEETS = {"jensen": "media/variants/generative/sheet-jensen.png", "matt": "media/cast/sheet-matt-r4-1.png",
          "steipete": "media/cast/sheet-steipete-1.png", "swyx": "media/cast/sheet-swyx-r2-1.png", "simonw": "media/cast/sheet-simonw.png"}
# the approved test keyframes (S07's with its baked-in black bars cropped off)
TEST_KEYS = {"S07": "media/full/keyframes/key-S07-clean.png", "S08": "media/variants/generative/key-S08-r4-1.png"}
FILM = "35mm film grain, 1987 look, 16:9."
BARRACKS = ("the same 1980s Marine barracks squad bay at night as in the second image: double bunks with olive wool blankets, "
            "pale green walls, overhead fluorescent lights")
HALLWAY = ("a 1980s Marine barracks hallway at night: cream walls, a polished reddish-brown floor, plain doors on both sides, a "
           "gridded window at the far end, fluorescent ceiling lights. On the right wall, a red bulletin board headed 'MODEL "
           "WORSHIP' that lists services ('OPUS 0900', 'GPT 1000', 'GEMINI 1100'), and beside it a small framed portrait photo of "
           "the man in the leather jacket from the character sheet (Jensen Huang)")
# keyframes in dependency order; refs: "sheet:<who>" or "key:<id>" (a test keyframe or a pick from this list)
KEYS = {
  "S09": (["sheet:steipete", "key:S08"],
          "A new film still, not a copy of any existing film: a wide, locked-off shot from a low angle near the foot of a lower "
          f"bunk, looking down the length of {BARRACKS}. In the foreground, filling the lower third of the frame, a recruit lies "
          "on his back on a lower bunk, his head at the left of frame and his bare feet toward the right. He is the man from "
          "the character sheet (thin glasses, short beard, small earring), in a white t-shirt and white shorts. An open silver "
          "MacBook Pro rests flat on his stomach, both hands on the keyboard, the screen's glow on his face, mouth open "
          "mid-chant. A small red plush lobster toy sits on the blanket by his feet. Behind him the bunks recede down the room; "
          "the other recruits lie on their backs, each with an open laptop resting on his stomach. No weapons anywhere. " + FILM),
  # r3 (author, round 5): r2 still didn't look like him: no reference covered the angle. His rev-4 sheet (with
  # tilted-back, looking-up views) and real photos at that angle; r3 still drifted to a tilted-back profile, so r4 turns
  # his face toward the camera (both eyes visible), which is where his likeness reads; r4 still put the camera behind
  # his head, so r5 anchors face and angle on the real looking-up photo (first image) and shoots from beside the bunk
  # r6 (author, round 6): looking down at his laptop, closer to a side profile. An edit of the approved r5 B (same shot,
  # laptop and bunks); his real near-profile and steep three-quarter photos keep the side view his
  "S10": (["file:media/full/keyframes/key-S10-r5-1.png", "sheet:matt", "file:reference/cast/matt/headshot-3.jpg",
           "file:reference/cast/matt/headshot-8.jpg", "file:reference/cast/matt/headshot-7.jpg"],
          "Edit the first image. Turn the recruit's head so he looks down at the laptop screen resting on his stomach, seen "
          "closer to a side profile: his face turned toward the laptop at the left of frame, his eyes on the screen, mouth "
          "open mid-chant, the screen's cool glow on his face. Keep his exact face from the other images (Matt Pocock): long "
          "narrow face, cheekbones, ears, bald crown with short sides, round tortoiseshell glasses, light stubble and light "
          "moustache, as in the side views of the photos; no earring. Keep everything else exactly the same: the framing, the "
          "pillow, the white t-shirt, his hands on the keyboard, the laptop, the bunks and recruits behind him and the light."),
  "S11": (["sheet:swyx", "key:S08"],
          "A new film still, not a copy of any existing film: a close-up of a recruit lying back on a lower bunk against an "
          "olive wool blanket, his head at the upper left of frame, three-quarter frontal, chanting with conviction, mouth open "
          "mid-word. He is the man from the character sheet: keep his exact likeness, face, build and his short, textured black "
          "hair. White t-shirt. An open silver MacBook Pro rests on his stomach, both hands on the keyboard, the screen's glow on "
          "his face; a warm, confident expression with a relaxed brow and a slight smile, lips just parted on a word. On the "
          "right, slightly out of focus, another recruit lies on the next "
          f"bunk typing on his own laptop, in {BARRACKS}. No weapons anywhere. " + FILM),
  # r2 (author): a shorter hallway so the fire watch reads clearly (not too close), and the light switch the DI will use
  # for lights-out is on the wall from the start
  # r5 (author): the fire watch on guard duty by the left wall, out of the DI's way. An edit of round 2's hallway
  # (key-S12a-r3-1, the framing and his size already right); a fresh draw (r4) made him much bigger in frame
  "S12a": (["file:media/full/keyframes/key-S12a-r3-1.png"],
           "Edit the image. Move the fire watch recruit from the middle of the hallway to its left side: on guard duty, he stands "
           "at rigid attention close to the left wall, at the same distance from the camera and the same size in frame, facing "
           "the camera, leaving the middle of the hallway clear. Keep everything else exactly the same: the hallway, the "
           "framing, the bulletin board, the portrait, the dark doorway, the light switch and the light."),
  # r6 (author): the DI is already walking in on the left, his face sharp and true to his photos, so the model doesn't
  # invent a face for the first half of S12. An edit of the picked r5 (the fire watch already by the left wall)
  "S12a2": (["file:media/full/keyframes/key-S12a-r5-1.png", "file:reference/cast/jensen/jensen-3.jpg",
             "file:reference/cast/jensen/jensen-1.jpg", "key:S07"],
            "Edit the first image. Add the drill instructor walking into the hallway from the left, in the left foreground, "
            "closer to the camera than the fire watch and not covering him: seen from the waist up, mid-stride, his face turned "
            "toward the camera in a three-quarter view, sharp and well lit. He is the man in the second and third images (Jensen "
            "Huang): keep his exact face, glasses and grey hair. Dressed as in the fourth image: black leather jacket over a "
            "black t-shirt, tan campaign hat. Keep everything else exactly the same: the fire watch at attention against the "
            "left wall, the hallway, the bulletin board, the light switch, the light and the framing."),
  "S12b": (["key:S12a", "sheet:jensen", "key:S07"],
           "Edit the first image. Keep everything exactly as it is: the hallway, the fire watch at attention against the left "
           "wall exactly where he stands, the bulletin board, the light switch, the light and the framing. Add the drill instructor in the foreground, right of centre and close "
           "to the light switch, seen from the waist up and facing the camera, mouth open mid-bark: the man from the second "
           "image (Jensen Huang), dressed as in the third image: black leather jacket over a black t-shirt, tan campaign hat."),
  "S14b": (["key:S12b"],
           "Edit the image. Keep everything exactly as it is: the hallway, the fire watch at attention against the left wall, the "
           "bulletin board, the light and the framing. The drill instructor has stepped to the wall on the right and put his right hand on the light "
           "switch plate, about to switch off the lights, his face still turned toward the camera."),
  "S15a": (["key:S14b"],
           "Edit the image. Same framing, same hallway, same fire watch at attention against the left wall, same pose of the drill instructor with his "
           "hand at the light switch. He has just switched off the squad bay lights: the area near the camera is now dark, lit "
           "only by a cool deep-blue night light, and the drill instructor is a dark blue silhouette, his face in shadow, while "
           "the hallway beyond stays lit."),
  # r7 (author): the end frame is the DI walking away down the hallway past the fire watch, still in frame (r6 left him
  # out, and the animation sent him through the doorway beside the switch)
  "S15b": (["key:S15a"],
           "Edit the image. The drill instructor has walked down the middle of the hallway and is just past the fire watch, seen "
           "from behind, walking away toward the window at the far end: smaller in frame, still in his black leather jacket and "
           "campaign hat. Remove him from the foreground. Everything else stays exactly the same: the framing, the dark blue "
           "foreground, the dark doorway on the right, the light switch on the wall, the lit hallway and the fire watch at "
           "attention against the left wall. The bulletin board keeps its exact text: 'MODEL WORSHIP', 'OPUS 0900', 'GPT 1000', "
           "'GEMINI 1100'."),
}
# a new rev gets a new output name. S15b r2: r1 garbled the board text and lost the jacket. S11 r2: a warm face, not a
# shout. Round 2 (author feedback): S10 r2 (likeness, full bunks); the hallway rebuilt shorter with the light switch (r3
# for S12a, S12b, S15a and S15b; S14b is new)
# Round 3 (author): the fire watch stands by the left wall from S12a on, out of the DI's way (S12a r4, S12b r4, S14b r2,
# S15a r4, S15b r5)
KEY_REV = {"S11": 2, "S10": 6, "S12a": 5, "S12a2": 6, "S12b": 4, "S14b": 2, "S15a": 4, "S15b": 7}


def key_name(kid: str) -> str:
  return f"key-{kid}" + (f"-r{KEY_REV[kid]}" if kid in KEY_REV else "")
LOCK = ("Locked-off tripod shot: the camera does not move at all for the whole clip. No push-in, no zoom, no dolly, no pan; "
        "the framing stays exactly as in the first frame.")
TYPING = CALM_H3_LOCKED.split(" The recruit lying on his back", 1)[1].split(" The camera never moves.")[0]
# (first keyframe, last keyframe, motion) per generated shot
ANIM = {
  "S07": ("S07", "S07", LOCK + " The drill instructor barks one short command straight into the lens, then holds a hard stare. The "
          "camera never moves."),
  "S09": ("S09", "S09", LOCK + " The recruit lying on his back" + TYPING + " The camera never moves."),
  # r4 (round 5): r3 tipped his head back toward the ceiling between the keyframes, turning his face away into profile;
  # his face now stays toward the camera as in the first frame
  # r6 (round 6): the keyframe now has him looking down at his laptop (author's pick); his head stays in that pose
  "S10": ("S10", "S10", LOCK + " The recruit lying back on the pillow keeps his head still, exactly as in the first frame, his "
          "eyes on the laptop screen. He chants, only his mouth and jaw moving on each word, while his fingers type calmly "
          "on the laptop resting on his stomach; wrists and arms stay still. The recruits in the bunks behind lie still, "
          "typing calmly. The camera never moves."),
  # rev 2: rev 1 bared clenched teeth under a furrowed brow mid-chant, a sneer that does not suit him; rev 3: from the warm keyframe
  "S11": ("S11", "S11", LOCK + " The recruit lying back on the bunk chants each word clearly and confidently, with a calm, friendly "
          "face: relaxed brow, lips shaping each word naturally, no grimace. His fingers type calmly on the laptop resting on his "
          "stomach; wrists and arms stay still, head and body relaxed. The recruit in the background bunk lies still, typing "
          "calmly. The camera never moves."),
  # round 4: starts with the DI already walking in on the left (S12a2), so his face comes from real photos, not the model
  "S12": ("S12a2", "S12b", "Locked-off tripod shot: the camera does not move at all. The drill instructor, walking in from the "
          "left, crosses the foreground and stops right of centre, facing the camera, then barks two short commands. "
          "Behind him the fire watch stands perfectly still at rigid attention. The camera never moves."),
  "S13": ("S09", "S09", LOCK + " On a sharp command, every recruit presses the Enter key on his laptop at the same moment with "
          "one firm keystroke, then lies still. The laptops stay flat on their stomachs. The camera never moves."),
  # round 2 (author): he finishes "Auto-merge!", then goes to the light switch; S15 opens with the lights already off
  "S14": ("S12b", "S14b", LOCK + " The drill instructor barks one short command, then steps to the wall on the right and puts his "
          "hand on the light switch. The fire watch stays perfectly still at attention. The camera never moves."),
  "S15-1": ("S15a", "S15a", LOCK + " Lights out. The drill instructor, a dark silhouette at the light switch, barks one last command "
            "without moving from the spot. The fire watch stands perfectly still at attention. The camera never moves."),
  "S15-2": ("S15a", "S15b", "Locked-off tripod shot: the camera does not move at all. Lights out. The drill instructor, a dark "
            "silhouette at the light switch, turns and walks away from the camera down the middle of the lit hallway, past the "
            "fire watch, toward the window at the far end. The fire watch stands perfectly "
            "still at attention against the left wall the whole time and, near the end, calls out one short reply. The camera "
            "never moves."),
}
# shots animated without their voice pinned, then lip-synced with sync-3 (RESYNC): S10 (round 5), where the pinned chant
# made H3 tip his head back and turn his face away from the camera between the keyframes, losing his likeness
UNPINNED = ("S10",)
# bump a shot to redo its animation (new output name). Round 2: S10 (new keyframe), S12 (new hallway), S13 (shorter)
# round 3: the hallway shots (fire watch by the left wall) and S13, all from exact-16:9 keyframes (S13 r3 is the test take)
ANIM_REV = {"S11": 3, "S10": 6, "S12": 4, "S13": 3, "S14": 3, "S15-1": 2, "S15-2": 3}  # round 4: S12 (DI walks in), S15-2 (walks past)


def script() -> dict:
  return json.loads((ROOT / "data" / "script.json").read_text())


def spans() -> dict[str, tuple[float, float]]:
  """Each shot's span of the source timeline: the film's up to S12, then the cut's own (GEN_SPANS)."""
  film = {s["id"]: (s["start"], s["end"]) for s in script()["shots"] if FIRST <= s["id"] <= LAST}
  return {k: v for k, v in film.items() if k < "S13"} | GEN_SPANS


def out_start() -> dict[str, float]:
  """Where each shot starts in the render (seconds): the spans laid end to end."""
  t, out = 0.0, {}
  for sid, (a, b) in spans().items():
    out[sid] = t
    t += b - a
  return out


def placed() -> dict[str, tuple[float, float]]:
  """Where every line sounds on the cut's timeline (source-clip seconds): solo lines from data/di-gen.json, chorus
  from data/chorus.json."""
  out = {k: tuple(v["placed"]) for k, v in json.loads((ROOT / "data" / CUT["di"]).read_text())["lines"].items()}
  out.update({k: tuple(v["placed"]) for k, v in json.loads((ROOT / "data" / "chorus.json").read_text())["lines"].items()})
  return out


def mono(path: Path) -> np.ndarray:
  y = sf.read(path, dtype="float32")[0]
  return y.mean(1) if y.ndim > 1 else y


def prep() -> None:
  """Per shot: its on-screen voice (only the lines whose speaker is on screen) and its slice of the cut's mix."""
  w0 = script()["window"]["start"]
  chorus = mono(ROOT / "media" / "voices" / "chorus-music" / json.loads((ROOT / "data" / "chorus.json").read_text())["variant"] / "track.wav")
  ramp = int(0.01 * SR)
  d = OUT / CUT["shots"]
  d.mkdir(parents=True, exist_ok=True)
  solo = mono(ROOT / "media" / "voices" / CUT["dry"])
  mix = sf.read(ROOT / "media" / "voices" / CUT["mix"], dtype="float32")[0]
  at = placed()
  for sid, (a, b) in spans().items():
    i, j = int((a - w0) * SR), int((b - w0) * SR)
    voice = np.zeros(j - i, np.float32)
    for lid in ONSCREEN[sid]:
      track = solo if lid[0] in "DF" else chorus
      p, q = max(i, int((at[lid][0] - PAD[0] - w0) * SR)), min(j, int((at[lid][1] + PAD[1] - w0) * SR))
      seg = track[p:q].copy()
      seg[:ramp] *= np.linspace(0, 1, ramp)
      seg[-ramp:] *= np.linspace(1, 0, ramp)
      voice[p - i : q - i] += seg
    if np.abs(voice).max() > 0:
      voice *= 0.9 / np.abs(voice).max()
    sf.write(d / f"{sid}-voice.wav", voice, SR, subtype="PCM_16")
    sf.write(d / f"{sid}-mix.wav", mix[i:j], SR, subtype="PCM_16")
    print(f"{sid:6} {a - w0:5.2f}-{b - w0:5.2f}s  on screen: {', '.join(ONSCREEN[sid]) or '-'}")


def join(parts: list[Path], dest: Path) -> Path:
  """Stream-copy concat (parts already conformed); always rebuilt, so a changed part is never stale."""
  lst = dest.with_suffix(".txt")
  lst.write_text("".join(f"file '{p}'\n" for p in parts))
  ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dest))
  return dest


def key_picks() -> dict[str, str]:
  p = OUT / "keyframes" / "picks.json"
  return {k: v for k, v in json.loads(p.read_text()).items() if k != "why"} if p.exists() else {}


def key_path(kid: str) -> str:
  if kid in TEST_KEYS:
    return TEST_KEYS[kid]
  picked = key_picks().get(kid)
  if picked:
    return picked
  hits = sorted((OUT / "keyframes").glob(f"{key_name(kid)}.png"))
  if not hits:
    sys.exit(f"keyframe {kid} not generated yet")
  return rel(hits[0])


def keyframes(ids: list[str]) -> None:
  for kid in ids or list(KEYS):
    refs, prompt = KEYS[kid]
    urls = ["@" + (SHEETS[r[6:]] if r.startswith("sheet:") else r[5:] if r.startswith("file:") else key_path(r[4:])) for r in refs]
    files = fal_run.run("fal-ai/nano-banana-pro/edit",
                        {"prompt": prompt, "image_urls": urls, "aspect_ratio": "16:9", "resolution": "2K", "num_images": 2, "output_format": "png"},
                        OUT / "keyframes" / key_name(kid), est_cost=0.30, job=f"full/keyframes/{key_name(kid)}")
    print(kid, files)


def sixteen_nine(path: str) -> str:
  """The keyframe cropped to exactly 16:9 at 1920x1080. Nano Banana's "16:9" is 2752x1536 (1.792); fed that, H3 renders
  1928x1076 and stretches its generated frames ~2.5% wider than the keyframe it starts and ends on. At exactly 16:9 the
  stretch drops to ~0.75% (S13 test, round 3)."""
  dest = OUT / "keyframes" / "169" / Path(path).name
  if not dest.exists():
    from PIL import Image
    dest.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(ROOT / path).convert("RGB")
    w = min(im.width, round(im.height * 16 / 9))
    h = round(w * 9 / 16)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    im.crop((x, y, x + w, y + h)).resize((1920, 1080), Image.LANCZOS).save(dest)
  return rel(dest)


def animate(ids: list[str]) -> None:
  sp = spans()
  for sid in ids or list(ANIM):
    first, last, motion = ANIM[sid]
    a, b = sp[sid]
    args = {"image_url": "@" + sixteen_nine(key_path(first)), "end_image_url": "@" + sixteen_nine(key_path(last)), "prompt": motion,
            "duration": round(b - a, 2),
            "resolution": "1080P", "prompt_expansion_mode": "disabled", "seed": 7}
    if ONSCREEN[sid] and sid not in UNPINNED:
      args["target_audio_url"] = "@" + rel(OUT / CUT["shots"] / f"{sid}-voice.wav")
    name = f"{sid}" + (f"-r{ANIM_REV[sid]}" if sid in ANIM_REV else "")
    try:
      print(sid, fal_run.run("minimax/h3-max/image-to-video", args, OUT / "generative" / name, est_cost=round(0.104 * (b - a + 0.7), 2),
                             job=f"full/generative/{name}"))
    except Exception as e:
      print(f"{sid} failed: {str(e)[:200]}")


# shots that get a lip sync pass over the H3 clip, driven by the same voice, from the given second on (spliced back
# into the shot). S07 (round 5): the lips never closed for the M and P of "Prompt!", so it read as "Pront"
# over a clean track. S15-2 (round 5): the fire watch's "You're absolutely right, sir!" moved no mouth; synced from
# 2.0 s, once the DI has his back to the camera, so the fire watch is the only face.
RESYNC = {"S07": 0.0, "S15-2": 0.0, "S10": 0.0}
# a face too small to sync in place (S15-2: the fire watch's is ~100 px tall) is synced on a crop scaled up 4x, then
# only the mouth and jaw are blended back through a soft oval: (x, y, size) of the crop in the 1920x1080 frame, the
# oval's centre and radii inside the crop, and the model. sync-3 left the helmeted face untouched (passed it through),
# so S15-2 uses H3 Max Lip Sync on the whole shot's crop (it needs 5 s or more; the DI stays outside the crop).
RESYNC_CROP = {"S15-2": ((225, 300, 200), (100, 112, 52, 46), "h3"),
               # S10 (round 6): sync-3 kept Matt's near-profile mouth timid and all but skipped "Ship it!"; React-1 (face,
               # expressiveness 0.9) moved even less. H3 Lip Sync moved most and tracked the voice best, but renders 768p,
               # so it syncs a 2x crop of his face and only the mouth and jaw are blended into the 1080p take
               "S10": ((1100, 200, 560), (240, 400, 150, 120), "h3")}


def gen_name(sid: str) -> str:
  return f"{sid}" + (f"-r{ANIM_REV[sid]}" if sid in ANIM_REV else "")


def small_face(sid: str, clip: Path, voice: Path, name: str, cost: float) -> Path:
  """sync-3 on a 4x crop around a small face, blended back over the clip through a soft oval around the mouth."""
  from PIL import Image, ImageDraw, ImageFilter
  d = OUT / "generative"
  (x, y, size), (cx, cy, rx, ry), model = RESYNC_CROP[sid]
  big = d / f"{name}-crop.mp4"
  up = 4 if size <= 256 else 2  # the face about 1000 px across for the model
  ff("-i", str(clip), "-an", "-vf", f"scale=1920:1080,crop={size}:{size}:{x}:{y},scale={size * up}:{size * up}:flags=lanczos",
     "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(big))
  dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(big)],
                             capture_output=True, text=True).stdout)
  if model == "h3":
    synced = first_video(fal_run.run("minimax/h3-max/lip-sync/video-to-video",
                                     {"video_url": "@" + rel(big), "audio_url": "@" + rel(voice), "duration_mode": "cut_off", "resolution": "768P"},
                                     d / f"{name}-crop-h3", est_cost=round(0.2 * dur, 2), job=f"full/generative/{name}-crop-h3"))
  else:
    synced = first_video(fal_run.run("fal-ai/sync-lipsync/v3", {"video_url": "@" + rel(big), "audio_url": "@" + rel(voice), "sync_mode": "cut_off"},
                                     d / f"{name}-crop-ls", est_cost=cost, job=f"full/generative/{name}-crop"))
  mask = Image.new("L", (size, size), 0)
  ImageDraw.Draw(mask).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
  mask = mask.filter(ImageFilter.GaussianBlur(max(10, size // 25)))
  mask_png = d / f"{name}-mask.png"
  mask.save(mask_png)
  out = d / f"{name}.mp4" if clip.name.endswith(f"{Path(clip).stem}.mp4") and "-from" not in clip.name else d / f"{name}-part.mp4"
  ff("-i", str(clip), "-i", str(synced), "-loop", "1", "-i", str(mask_png), "-filter_complex",
     f"[0:v]scale=1920:1080,setsar=1[base];[1:v]scale={size}:{size}:flags=lanczos,format=rgba[f];[2:v]format=gray,scale={size}:{size}[m];"
     f"[f][m]alphamerge[fm];[base][fm]overlay={x}:{y}:shortest=1,format=yuv420p[v]", "-map", "[v]", "-an",
     "-c:v", "libx264", "-crf", "14", str(out))
  return out


def resync(ids: list[str]) -> None:
  a_b = spans()
  d = OUT / "generative"
  for sid in ids or list(RESYNC):
    a, b = a_b[sid]
    o = RESYNC[sid]
    clip = steady(d / f"{gen_name(sid)}.mp4")
    voice = OUT / CUT["shots"] / f"{sid}-voice.wav"
    name = f"{gen_name(sid)}-ls"
    if o:  # sync only from where the speaker is the only face
      seg_v, seg_a = d / f"{name}-from.mp4", d / f"{name}-from.wav"
      ff("-ss", f"{o:.3f}", "-i", str(clip), "-t", f"{b - a - o:.3f}", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(seg_v))
      y = sf.read(voice, dtype="float32")[0]
      sf.write(seg_a, y[int(o * SR):], SR, subtype="PCM_16")
      clip, voice = seg_v, seg_a
    if sid in RESYNC_CROP:
      synced = small_face(sid, clip, voice, name, round((b - a - o) / 60 * 8, 2))
    else:
      synced = first_video(fal_run.run("fal-ai/sync-lipsync/v3", {"video_url": "@" + rel(clip), "audio_url": "@" + rel(voice), "sync_mode": "cut_off"},
                                       d / (f"{name}-part" if o else name), est_cost=round((b - a - o) / 60 * 8, 2), job=f"full/generative/{name}"))
    if o:
      head = d / f"{name}-head.mp4"
      ff("-i", str(steady(d / f"{gen_name(sid)}.mp4")), "-t", f"{o:.3f}", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(head))
      join([conform(head, o, d / f"{name}-head-c.mp4"), conform(synced, b - a - o, d / f"{name}-part-c.mp4")], d / f"{name}.mp4")
    print(sid, rel(d / f"{name}.mp4"))


def sources() -> dict[str, Path | None]:
  """The approved clip each shot is cut from: its H3 take, or that take's lip sync pass where it has one."""
  out = {}
  for sid in spans():
    if sid in APPROVED:
      out[sid] = ROOT / APPROVED[sid]
    else:
      p = OUT / "generative" / f"{gen_name(sid)}.mp4"
      synced = p.with_name(f"{p.stem}-ls.mp4")
      out[sid] = synced if sid in RESYNC and synced.exists() else p if p.exists() else None
  return out


# H3 Max puts the keyframe in as frame 0 exactly, then generates the rest about 2.5% wider (horizontal only; its own
# internal frame shape mapped back to the canvas), so the first ~4 frames visibly stretch, and the last ~4 snap back to
# the end keyframe. Those frames are replaced by a hold of the first and last steady frame: same length and timing, so
# the pinned lip sync stays put.
STEADY = 4  # frames at each end (H3 renders 24 fps: about 170 ms)


def steady(src: Path) -> Path:
  dest = OUT / "steady" / f"{src.parent.name}-{src.stem}.mp4"
  if not fresh(dest, src):
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
                            "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True).stdout.strip())
    k = STEADY
    ff("-i", str(src), "-an", "-vf", f"trim=start_frame={k}:end_frame={n - k},setpts=PTS-STARTPTS,"
       f"tpad=start={k}:start_mode=clone:stop={k}:stop_mode=clone", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(dest))
  return dest


def trim_head(src: Path, secs: float) -> Path:
  dest = src.with_name(f"{src.stem}-from{secs:g}.mp4")
  if not fresh(dest, src):
    ff("-ss", f"{secs:.3f}", "-i", str(src), "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(dest))
  return dest


def cut_audio() -> Path:
  """The cut's soundtrack: its mix over each shot's span, in order, then the end hold. Where the cut drops time
  (GEN_SPANS), the audio drops the same time."""
  w0 = script()["window"]["start"]
  mix, sr = sf.read(ROOT / "media" / "voices" / CUT["mix"], dtype="float32")
  sp = list(spans().values())
  parts = [mix[int((a - w0) * sr):int((b - w0) * sr)] for a, b in sp]
  end = int((sp[-1][1] - w0) * sr)
  parts.append(mix[end:end + int(END_HOLD * sr)])
  dest = OUT / "cuts" / "generative-audio.wav"
  sf.write(dest, np.concatenate(parts), sr)
  return dest


# the cut ends on the credits card (scripts/credits.py, author round 5): the footage crossfades into it while it still
# moves (the crossfade finishes as the last shot ends: no frozen frames, author round 7), and the room tail fades out
# underneath once the fire watch's line is done
CREDITS = RENDERS / "credits.mp4"
# its first frame is the title card (captions/compositions/title.html, `npm run title`), so a post's preview shows the
# title: it replaces frame 0 in place, so every later frame and the audio keep their timing (author round 8)
TITLE = RENDERS / "title.png"
XFADE = 0.8  # seconds of crossfade, ending with the last shot
TAIL_FADE = 0.4, 1.5  # the room tail fades from this long after the last shot, over this long


def assemble() -> None:
  d = OUT / "cuts"
  d.mkdir(parents=True, exist_ok=True)
  RENDERS.mkdir(parents=True, exist_ok=True)
  sp = spans()
  srcs = sources()
  missing = [k for k, v in srcs.items() if v is None]
  if missing:
    sys.exit(f"missing clips for {missing}")
  # cut names carry the source's name, so a new pick or take never reuses a stale cut; every shot is an H3 Max clip
  srcs = {sid: steady(p) for sid, p in srcs.items()}
  srcs = {sid: trim_head(p, TRIM_HEAD[sid]) if sid in TRIM_HEAD else p for sid, p in srcs.items()}
  parts = [conform(srcs[sid], b - a, d / f"generative-{sid}-{srcs[sid].parent.name}-{srcs[sid].stem}.mp4", INSETS.get(sid))
           for sid, (a, b) in sp.items()]
  clips = RENDERS / "shots"
  clips.mkdir(parents=True, exist_ok=True)
  for part, sid in zip(parts, sp):
    ff("-i", str(part), "-i", str(OUT / CUT["shots"] / f"{sid}-mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
       "-c:a", "aac", "-b:a", "160k", "-shortest", str(clips / f"generative-{sid}.mp4"))
  video = join(parts, d / "generative-video.mp4")
  out = RENDERS / "generative.mp4"
  if CREDITS.exists():
    body = sum(b - a for a, b in sp.values())
    card = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(CREDITS)],
                                capture_output=True, text=True).stdout)
    total = body - XFADE + card
    titled = TITLE.exists()
    ff("-i", str(video), "-i", str(CREDITS), "-i", str(cut_audio()), *(["-i", str(TITLE)] if titled else []), "-filter_complex",
       f"[0:v]setsar=1,fps=30000/1001,settb=1001/30000[a];"
       f"[1:v]setsar=1,fps=30000/1001,settb=1001/30000[c];"
       f"[a][c]xfade=transition=fade:duration={XFADE}:offset={body - XFADE:.3f}" + (",format=yuv420p[x];[x][3:v]overlay=0:0:enable='eq(n,0)'" if titled else "")
       + ",format=yuv420p[v];"
       f"[2:a]apad,atrim=0:{total:.3f},afade=t=out:st={body + TAIL_FADE[0]:.3f}:d={TAIL_FADE[1]}[au]",
       "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", str(out))
  else:
    ff("-i", str(video), "-i", str(cut_audio()), "-map", "0:v", "-map", "1:a",
       "-vf", f"tpad=stop_mode=clone:stop_duration={END_HOLD}", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
       "-c:a", "aac", "-b:a", "192k", "-shortest", str(out))
  print(rel(out))


def audit() -> None:
  """Is every shot of the cut what it should be? Per shot: the clip was made from the current keyframe picks (fal call
  log), the audio it was driven by (H3 and sync-3 return it as their soundtrack) matches the current per-shot voice, and
  in the final render the shot's frames match its source and the audio is the cut's mix."""
  from scipy.signal import correlate

  def pcm(path: Path, t0: float | None = None, dur: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{t0:.3f}"] if t0 is not None else []) + (["-t", f"{dur:.3f}"] if dur else [])
    raw = subprocess.run(cmd + ["-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)

  def match(a: np.ndarray, b: np.ndarray) -> float:
    """Peak normalised correlation of the shorter signal inside the longer (1.0 = same audio)."""
    a, b = (a, b) if len(a) <= len(b) else (b, a)
    if len(a) < 1600 or np.abs(a).max() < 1e-4:
      return float("nan")
    c = correlate(b, a, mode="valid", method="fft")
    norm = np.sqrt((a**2).sum() * np.convolve(b**2, np.ones(len(a)), "valid"))
    return float((c / np.maximum(norm, 0.05 * norm.max())).max())  # near-silent windows can't fake a match

  def driving_clip(src: Path) -> Path:
    """The clip that carries the voice it was driven by: a blended or spliced shot is silent, its synced crop or part isn't."""
    for p in (src.with_name(f"{src.stem}-crop-h3.mp4"), src.with_name(f"{src.stem}-part.mp4"), src):
      if p.exists() and subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(p)],
                                       capture_output=True, text=True).stdout.strip():
        return p
    return src

  def frame(path: Path, t: float) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=192:108,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(np.float32)

  log = {}
  for line in (ROOT / "data" / "fal-log.jsonl").read_text().splitlines():
    r = json.loads(line)
    for o in r.get("outputs") or []:
      log[o] = r
  log["media/full/generative/S13-r3.mp4"] = log.get("media/full/generative/test169-S13.mp4")  # the 16:9 test take, kept as S13

  def same_image(x: str, y: str) -> bool:
    from PIL import Image
    a, b = (np.asarray(Image.open(ROOT / p).convert("RGB")) for p in (x, y))
    return a.shape == b.shape and np.abs(a.astype(int) - b).mean() < 0.5
  bad = 0
  print(f"== renders/full/generative.mp4 (mix: {CUT['mix']})")
  render = RENDERS / "generative.mp4"
  whole = match(pcm(render), pcm(OUT / "cuts" / "generative-audio.wav"))
  print(f"   render audio vs the cut's soundtrack: {whole:.3f}")
  bad += not whole > 0.98
  srcs, starts = sources(), out_start()
  for sid, (a, b) in spans().items():
    src = srcs[sid]
    notes = []
    if src is None:
      print(f"   {sid:6} MISSING source"); bad += 1; continue
    r = log.get(rel(src.with_name(src.stem.removesuffix("-ls") + src.suffix)))
    if sid in ANIM:
      first, last, _ = ANIM[sid]
      want = {sixteen_nine(key_path(first)), sixteen_nine(key_path(last)), key_path(first), key_path(last)}
      used = {r["args"].get("image_url", "")[1:], r["args"].get("end_image_url", "")[1:]} if r else set()
      ok = bool(used) and all(u in want or any(same_image(u, w) for w in want if w.endswith(".png")) for u in used)
      notes.append("keyframes " + ("current" if ok else f"STALE {sorted(used)}"))
      bad += not ok
    if ONSCREEN[sid] and sid not in APPROVED:
      driven = match(pcm(driving_clip(src)), pcm(OUT / CUT["shots"] / f"{sid}-voice.wav"))
      notes.append(f"driven by current voice {driven:.2f}")
      bad += not driven > 0.9
    # the render's frame mid-shot vs the source's (after the same hold)
    mid = (b - a) / 2
    diff = np.abs(frame(render, starts[sid] + mid) - frame(steady(src), TRIM_HEAD.get(sid, 0.0) + mid)).mean()
    notes.append(f"frame vs source {diff:.1f}")
    bad += not diff < 12
    print(f"   {sid:6} {rel(src):52} " + " | ".join(notes))
  # the H3 opening stretch: motion right after each cut should be calm
  worst = []
  for t in starts.values():
    f = [frame(render, t + k / 30 + 0.017) for k in range(6)]
    worst.append(max(np.abs(f[k + 1] - f[k]).mean() for k in range(5)))
  print(f"   motion in the first 0.2 s after each cut: {' '.join(f'{x:.1f}' for x in worst)}")
  bad += not max(worst) < 3
  print("all consistent" if not bad else f"{bad} problem(s)")


def page() -> None:
  from variants_page import box, esc, media, render_page  # noqa: E402

  w0 = script()["window"]["start"]
  rows = [json.loads(l) for l in (ROOT / "data" / "fal-log.jsonl").read_text().splitlines()]
  spent = {k: sum(r.get("est_cost_usd") or 0 for r in rows if r["job"].startswith(f"full/{k}")) for k in ("keyframes", "generative")}
  total = sum(r.get("est_cost_usd") or 0 for r in rows)
  lines = {ln["id"]: ln for ln in script()["lines"]}
  d01 = next(r for r in json.loads((ROOT / "data" / "voices.json").read_text())["di"]["reads"] if r["lines"] == ["D01"])

  def said(sid: str) -> str:
    return " · ".join(lines[l]["parody"] for l in ONSCREEN[sid]) or "(no one speaks on screen)"

  def span(sid: str) -> str:
    a, b = spans()[sid]
    t = out_start()[sid]
    return f"{t:.1f}–{t + b - a:.1f}s"

  board = []
  for sid in spans():
    if sid in ANIM:
      first, last, motion = ANIM[sid]
      frames = [(first, "first frame")] + ([(last, "last frame")] if last != first else [])
    else:
      frames, motion = [(sid, "keyframe")], "The approved S07+S08 test take."
    figs = "".join(f'<figure>{media(key_path(k), "img")}<figcaption>{esc(k)} · {cap}</figcaption></figure>' for k, cap in frames)
    takes = ""
    if sid == "S07":
      takes = ('<div class="takes"><b>S07 audio, A/B</b>'
               + "".join(f'<div><span class="dim">{label}</span>{media(f, "audio")}</div>' for label, f in (
                 ("raw take 1, placed", "media/voices/di/ab/S07-raw-take.wav"),
                 ("before (reverb + early reflections: \"Pront\")", "media/voices/di/ab/S07-before.wav"),
                 ("now (in the cut)", "media/voices/di/ab/S07-now.wav")))
               + '</div><div class="takes"><b>"Prompt!" takes</b> (in use first)'
               + "".join(f'<div><span class="dim">{"in use" if n == 0 else f"alt {n}"} · {esc(Path(f).parent.name)}/{esc(Path(f).stem)}</span>{media(f, "audio")}</div>'
                         for n, f in enumerate([d01["file"], *d01.get("alts", [])]))
               + "</div>")
    when = span(sid)
    board.append(f'<div class="sb"><div class="sbk">{figs}</div><div class="sbv">{media(f"renders/full/shots/generative-{sid}.mp4")}</div>'
                 f'<div class="sbt"><b>{sid}</b> <span class="dim">{when}</span><div class="said">{esc(said(sid))}</div>'
                 f'<details><summary class="dim">Motion brief</summary><p class="dim">{esc(motion)}</p></details>{takes}'
                 f'{box(f"generative-{sid}", f"Fully generative · {sid} ({when})", "Keyframes, likeness, motion, timing…")}</div></div>')
  body = ('<p class="sub">Round 2 of the full video (0:00–1:08.6). The fully generative cut is rebuilt from your notes. '
          f'fal spend so far ≈ ${total:.2f} (call log estimates; the fal dashboard is authoritative) of the ~$80 budget.</p>'
          '<section class="variant" id="generative"><h2>Fully generative <span>full render spend ≈ '
          f'${spent["keyframes"] + spent["generative"]:.2f}</span></h2><div class="grid2"><div>{media("renders/full/generative.mp4")}</div>'
          '<div><p>Each shot: its keyframes (first and last frame; the camera holds between them), animated with H3 Max with the '
          'on-screen speaker\'s lines pinned as the soundtrack. This cut gets to "Auto-merge!" sooner than the film, and S15 '
          'splits so the DI only walks off after "Close your laptops!".</p></div></div>'
          f'{box("generative", "Fully generative", "Overall: ready, or what to change?")}'
          f'<h3>Storyboard</h3><div class="board">{"".join(board)}</div></section>'
          f'<section class="variant"><h2>0 · Original footage, approved audio</h2><div class="grid2"><div>{media("renders/proto/full-pass.mp4")}</div>'
          '<div><p>No visual change: the reference.</p></div></div></section>'
          + f'<div class="general"><label>General</label>{box("general", "General", "Anything else?")}</div>'
          '<style>.shots {display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:10px; margin-top:12px} '
          '.said {font-size:13px; margin:4px 0} .board {display:grid; gap:14px} '
          '.sb {display:grid; grid-template-columns:minmax(0,1.3fr) minmax(0,1fr) minmax(0,1fr); gap:12px; align-items:start; '
          'border-top:1px solid var(--line); padding-top:12px} .sbk {display:grid; gap:6px} .sbk img {aspect-ratio:16/9; object-fit:cover} '
          '.takes {font-size:13px; margin:8px 0} .takes audio {width:100%; height:30px} '
          '@media (max-width:820px) {.sb {grid-template-columns:1fr}}</style>')
  dest = ROOT / "review" / "dist" / "full.html"
  dest.write_text(render_page("Software Factory Full", "full render, round 2", body, "full:v2", "Full render feedback"))
  print(rel(dest))


STEPS = {"prep": prep, "keyframes": keyframes, "animate": animate, "resync": resync, "assemble": assemble,
         "audit": audit, "page": page}

if __name__ == "__main__":
  step, ids = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
  if step not in STEPS:
    sys.exit(__doc__)
  print(f"== {step}")
  STEPS[step](ids) if step in ("keyframes", "animate", "resync") else STEPS[step]()

"""Storyboard review page from data/script.json -> review/dist/storyboard.html (ignored: it embeds film frames
and the original lines).

Per shot and per line: a frame, timecodes, the original line (pulled at build time from the local Whisper
transcript in /transcript, never stored in tracked files) next to the parody, a button that plays the original
moment from media/source.mp4, and a feedback box. Feedback drafts persist in the browser per review version; the
Copy button collects every non-empty note as plain text to paste back to the agent.

Run: uv run --group analysis python scripts/storyboard.py
"""

import base64
import html
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "media" / "source.mp4"
FRAMES = ROOT / "frames" / "board"
AVATARS = ROOT / "reference" / "avatars"
WHISPER = ROOT / "transcript" / "whisper-vocals.json"
YT_CAPTIONS = ROOT / "media" / "source.en.json3"
OUT = ROOT / "review" / "dist" / "storyboard.html"
LOW_CONFIDENCE = 0.5


def frame(t: float, width: int = 480) -> str:
  path = FRAMES / f"{t:07.2f}-{width}.jpg"
  if not path.exists():
    subprocess.run(
      ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(SRC), "-frames:v", "1",
       "-vf", f"scale={width}:-2", "-q:v", "4", str(path)],
      check=True,
    )
  return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def avatar(handle: str) -> str:
  for p in AVATARS.glob(f"{handle}.*"):
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
  return ""


def load_words() -> tuple[list[dict], list[dict]]:
  whisper = []
  if WHISPER.exists():
    for seg in json.loads(WHISPER.read_text())["segments"]:
      whisper += seg.get("words", [])
  captions = []
  if YT_CAPTIONS.exists():
    for e in json.loads(YT_CAPTIONS.read_text()).get("events", []):
      for sg in e.get("segs", []):
        if sg["utf8"].strip():
          captions.append({"start": (e["tStartMs"] + sg.get("tOffsetMs", 0)) / 1000, "word": sg["utf8"]})
  return whisper, captions


def original_line(ln: dict, whisper: list[dict], captions: list[dict]) -> tuple[str, str]:
  """The original line as HTML (low-confidence words marked) and where it came from."""
  a, b = ln["start"], ln["end"]
  words = [w for w in whisper if a - 0.2 <= (w["start"] + w["end"]) / 2 <= b + 0.25]
  if words:
    parts = []
    for w in words:
      text = html.escape(w["word"].strip())
      parts.append(f'<span class="unsure">{text}?</span>' if w.get("probability", 1) < LOW_CONFIDENCE else text)
    return " ".join(parts), "Whisper"
  words = [w for w in captions if a - 0.5 <= w["start"] <= b + 0.6]
  if words:
    return " ".join(html.escape(w["word"].strip()) for w in words), "YouTube captions"
  return '<span class="unsure">(not caught by the transcript)</span>', ""


def feedback_box(fid: str, label: str, placeholder: str) -> str:
  return (
    f'<textarea class="fb" rows="1" data-id="{fid}" data-label="{html.escape(label, quote=True)}" '
    f'placeholder="{html.escape(placeholder, quote=True)}"></textarea>'
  )


def main() -> None:
  FRAMES.mkdir(parents=True, exist_ok=True)
  OUT.parent.mkdir(parents=True, exist_ok=True)
  data = json.loads((ROOT / "data" / "script.json").read_text())
  version = data.get("review", {}).get("version", 1)
  t0, t1 = data["window"]["start"], data["window"]["end"]
  cast = data["cast"]
  whisper, captions = load_words()
  esc = html.escape
  video_src = Path("../../media/source.mp4").as_posix()

  cast_html = "".join(
    f'<figure class="person"><img src="{avatar(c["x"])}" alt=""><figcaption><b>{esc(c["name"])}</b>'
    f'<span>{esc(c["role"])}</span></figcaption></figure>'
    for c in cast.values()
  )

  shots_html = []
  for s in data["shots"]:
    lines = [ln for ln in data["lines"] if ln["shot"].split(">")[0] == s["id"]]
    who = ", ".join(cast[k]["name"] for k in s["cast"])
    rows = []
    for ln in lines:
      mid = (ln["start"] + ln["end"]) / 2
      delta = ln["syl"] - ln["origSyl"]
      fit = "ok" if abs(delta) <= 1 else "warn" if abs(delta) <= 2 else "over"
      voice = ln["voice"].replace("chorus+", "chorus, ")
      for k, c in cast.items():
        voice = voice.replace(k, c["name"])
      orig, orig_src = original_line(ln, whisper, captions)
      rows.append(
        f'<li class="line" id="{ln["id"]}"><img src="{frame(mid)}" alt="" loading="lazy">'
        f'<div class="body"><div class="meta"><code>{ln["id"]}</code>'
        f'<span>{ln["start"] - t0:5.2f}–{ln["end"] - t0:5.2f}s</span>'
        f'<span class="dim">src {ln["start"]:.2f}</span>'
        f'<span class="fit {fit}">{ln["syl"]}/{ln["origSyl"]} syl</span>'
        f'<span class="voice">{esc(voice)}</span>'
        f'<button class="play" data-start="{ln["start"] - 0.15:.2f}" data-end="{ln["end"] + 0.25:.2f}">▶ Original</button></div>'
        f'<div class="compare"><div class="col orig"><span class="label">Original'
        f'{f" · {orig_src}" if orig_src else ""}</span><p>{orig}</p></div>'
        f'<div class="col parody"><span class="label">Parody</span><p>{esc(ln["parody"])}</p></div></div>'
        f'<p class="ref">{esc(ln["ref"])}</p>'
        f'{feedback_box(ln["id"], f"{ln["id"]} · {ln["parody"]}", f"Feedback on {ln["id"]}…")}'
        f'</div></li>'
      )
    shots_html.append(
      f'<section class="shot" id="{s["id"]}"><header><img src="{frame(s["start"] + 0.4, 640)}" alt="" loading="lazy">'
      f'<div><h2>{s["id"]} <span>{s["start"] - t0:.2f}–{s["end"] - t0:.2f}s · {s["end"] - s["start"]:.1f}s</span>'
      f'<button class="play" data-start="{s["start"]:.2f}" data-end="{s["end"]:.2f}">▶ Play shot</button></h2>'
      f'<p><b>{esc(s["framing"])}</b>: {esc(s["subject"])}</p>'
      f'<p>Cast: <b>{esc(who)}</b> · swap: {esc(s["swap"])}</p>'
      f'<p class="dim">{esc(s["notes"])}</p>'
      f'{feedback_box(s["id"], f"{s["id"]} (shot)", f"Feedback on shot {s["id"]}: casting, framing, gags…")}'
      f'</div></header>'
      f'<ol>{"".join(rows) or "<li class=empty>No dialogue.</li>"}</ol></section>'
    )

  page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Software Factory Storyboard</title>
<style>
:root {{ --bg:#f6f4ef; --card:#fff; --ink:#1d1c1a; --dim:#6b675f; --line:#e4e0d6; --field:#fbfaf7; --accent:#4a5a2a; --accent-ink:#fff; --ok:#2f7a3b; --warn:#a36a00; --over:#b03a2e; --orig:#f1eee6; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141412; --card:#1e1d1a; --ink:#ecebe6; --dim:#9c978c; --line:#33312c; --field:#171614; --accent:#a9bd77; --accent-ink:#141412; --ok:#6fcf7f; --warn:#e7b04a; --over:#ef7c6e; --orig:#262521; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 ui-sans-serif,system-ui,-apple-system,sans-serif; }}
main {{ max-width:1080px; margin:0 auto; padding:16px 16px 96px; }}
.bar {{ position:sticky; top:0; z-index:5; background:color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }}
.bar-in {{ max-width:1080px; margin:0 auto; padding:10px 16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap }}
.bar h1 {{ font-size:17px; margin:0; flex:1 1 auto; letter-spacing:-.01em }}
.bar h1 span {{ color:var(--dim); font-weight:400 }}
button {{ font:inherit; font-size:13px; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:7px; padding:5px 10px; cursor:pointer; white-space:nowrap }}
button:hover {{ border-color:var(--dim) }}
button.primary {{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); font-weight:600 }}
button:disabled {{ opacity:.45; cursor:default }}
.count {{ font-size:13px; color:var(--dim) }}
.sub {{ color:var(--dim); margin:14px 0 18px }}
.general {{ margin:0 0 24px }}
.general label {{ font-weight:600; display:block; margin-bottom:6px }}
.cast {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; margin-bottom:28px }}
.person {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden }}
.person img {{ width:100%; aspect-ratio:1; object-fit:cover; display:block }}
.person figcaption {{ padding:8px 10px; font-size:13px }}
.person span {{ display:block; color:var(--dim); font-size:12px }}
.shot {{ background:var(--card); border:1px solid var(--line); border-radius:12px; margin:0 0 20px; overflow:hidden; scroll-margin-top:64px }}
.shot header {{ display:grid; grid-template-columns:minmax(0,320px) 1fr; gap:16px; padding:14px; border-bottom:1px solid var(--line) }}
.shot header img {{ width:100%; border-radius:6px; display:block }}
.shot h2 {{ margin:0 0 6px; font-size:18px; display:flex; gap:10px; align-items:baseline; flex-wrap:wrap }}
.shot h2 span {{ color:var(--dim); font-weight:400; font-size:14px }}
.shot header p {{ margin:2px 0 }}
.dim {{ color:var(--dim) }}
ol {{ list-style:none; margin:0; padding:0 }}
.line {{ display:grid; grid-template-columns:160px minmax(0,1fr); gap:14px; padding:12px 14px; border-top:1px solid var(--line); scroll-margin-top:64px }}
.line:first-child {{ border-top:0 }}
.line > img {{ width:100%; border-radius:4px; display:block }}
.meta {{ display:flex; flex-wrap:wrap; gap:4px 12px; font-size:13px; color:var(--dim); align-items:center }}
.meta code {{ color:var(--accent); font-weight:600 }}
.meta .play {{ margin-left:auto }}
.fit {{ font-weight:600 }} .fit.ok {{ color:var(--ok) }} .fit.warn {{ color:var(--warn) }} .fit.over {{ color:var(--over) }}
.compare {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:8px 0 4px }}
.col {{ border-radius:8px; padding:8px 10px }}
.col.orig {{ background:var(--orig) }}
.col.parody {{ border:1px solid var(--line) }}
.col .label {{ display:block; font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--dim); margin-bottom:2px }}
.col p {{ margin:0; text-wrap:pretty }}
.col.orig p {{ color:var(--dim) }}
.col.parody p {{ font-size:17px; font-weight:600 }}
.unsure {{ font-style:italic; opacity:.75 }}
.ref {{ margin:2px 0 6px; color:var(--dim); font-size:13px }}
textarea.fb {{ width:100%; min-height:34px; resize:vertical; font:inherit; font-size:14px; color:var(--ink); background:var(--field); border:1px solid var(--line); border-radius:8px; padding:7px 10px; overflow:hidden; margin-top:6px }}
textarea.fb:focus {{ outline:2px solid color-mix(in srgb, var(--accent) 55%, transparent); outline-offset:0; border-color:transparent }}
textarea.fb.filled {{ border-color:var(--accent) }}
.empty {{ padding:12px 14px; color:var(--dim) }}
.player {{ position:fixed; right:16px; bottom:16px; width:min(380px, calc(100vw - 32px)); background:#000; border-radius:10px; overflow:hidden; box-shadow:0 8px 30px rgba(0,0,0,.35); z-index:10; display:none }}
.player.on {{ display:block }}
.player video {{ width:100%; display:block }}
.player button {{ position:absolute; top:6px; right:6px; background:rgba(0,0,0,.6); color:#fff; border:0 }}
.toast {{ position:fixed; left:50%; bottom:20px; transform:translateX(-50%); background:var(--ink); color:var(--bg); padding:8px 14px; border-radius:8px; font-size:14px; opacity:0; transition:opacity .2s; pointer-events:none; z-index:20 }}
.toast.on {{ opacity:1 }}
.foot {{ display:flex; gap:10px; justify-content:flex-end; align-items:center; margin-top:8px }}
@media (max-width:720px) {{ .shot header {{ grid-template-columns:1fr }} .line {{ grid-template-columns:1fr }} .line > img {{ max-width:240px }} .compare {{ grid-template-columns:1fr }} }}
</style></head><body>
<div class="bar"><div class="bar-in">
<h1>This Is My Software Factory <span>· storyboard v{version}</span></h1>
<button class="play" data-start="{t0:.2f}" data-end="{t1:.2f}">▶ Play original</button>
<span class="count" id="count">No notes yet</span>
<button id="clear">Clear</button>
<button class="primary copy">Copy feedback</button>
</div></div>
<main>
<p class="sub">Source {t0:.2f}–{t1:.2f}s ({t1 - t0:.1f}s). Timecodes are meme time; "src" is the source clip. Syllables are parody/original. Original lines are the speech-to-text transcript of the clip: <span class="unsure">italic?</span> words are low confidence, and the PG edit overdubs some DI lines. Notes save in this browser as you type; Copy feedback grabs every non-empty one.</p>
<div class="general"><label for="fb-general">General feedback</label>
{feedback_box("general", "General", "Overall notes: tone, pacing, cast, jokes that miss…")}</div>
<div class="cast">{cast_html}</div>
{"".join(shots_html)}
<div class="foot"><span class="count" id="count2"></span><button class="primary copy">Copy feedback</button></div>
</main>
<div class="player" id="player"><video id="video" src="{video_src}" preload="metadata" playsinline controls></video><button id="close" aria-label="Close player">✕</button></div>
<div class="toast" id="toast" role="status"></div>
<script>
const VERSION = {version}
const KEY = id => `my-software-factory:storyboard:v${{VERSION}}:${{id}}`
const store = {{
  get(id) {{ try {{ return localStorage.getItem(KEY(id)) || '' }} catch {{ return '' }} }},
  set(id, v) {{ try {{ v ? localStorage.setItem(KEY(id), v) : localStorage.removeItem(KEY(id)) }} catch {{}} }},
}}
const boxes = [...document.querySelectorAll('textarea.fb')]
const grow = t => {{ t.style.height = 'auto'; t.style.height = t.scrollHeight + 2 + 'px' }}
const refresh = () => {{
  const n = boxes.filter(b => b.value.trim()).length
  const label = n ? `${{n}} note${{n === 1 ? '' : 's'}}` : 'No notes yet'
  document.getElementById('count').textContent = label
  document.getElementById('count2').textContent = label
  document.querySelectorAll('button.copy').forEach(b => (b.disabled = !n))
}}
for (const b of boxes) {{
  b.value = store.get(b.dataset.id)
  b.classList.toggle('filled', !!b.value.trim())
  grow(b)
  b.addEventListener('input', () => {{
    store.set(b.dataset.id, b.value)
    b.classList.toggle('filled', !!b.value.trim())
    grow(b)
    refresh()
  }})
}}
refresh()

const toast = msg => {{
  const t = document.getElementById('toast')
  t.textContent = msg
  t.classList.add('on')
  clearTimeout(toast.timer)
  toast.timer = setTimeout(() => t.classList.remove('on'), 1800)
}}
const exportText = () => {{
  const notes = boxes.filter(b => b.value.trim()).map(b => `${{b.dataset.label}}\\n${{b.value.trim()}}`)
  return `Storyboard v${{VERSION}} feedback (${{notes.length}} notes)\\n\\n` + notes.join('\\n\\n') + '\\n'
}}
const copy = async text => {{
  try {{ await navigator.clipboard.writeText(text); return true }} catch {{}}
  const t = document.createElement('textarea')
  t.value = text
  t.style.position = 'fixed'
  t.style.opacity = '0'
  document.body.appendChild(t)
  t.select()
  const ok = document.execCommand('copy')
  t.remove()
  return ok
}}
document.querySelectorAll('button.copy').forEach(btn => btn.addEventListener('click', async () => {{
  const n = boxes.filter(b => b.value.trim()).length
  toast((await copy(exportText())) ? `Copied ${{n}} note${{n === 1 ? '' : 's'}}` : 'Copy failed: select and copy manually')
}}))
document.getElementById('clear').addEventListener('click', () => {{
  if (!boxes.some(b => b.value.trim()) || !confirm('Clear all feedback for this version?')) return
  for (const b of boxes) {{ b.value = ''; store.set(b.dataset.id, ''); b.classList.remove('filled'); grow(b) }}
  refresh()
}})

const player = document.getElementById('player')
const video = document.getElementById('video')
let stopAt = null
document.querySelectorAll('button.play').forEach(btn => btn.addEventListener('click', () => {{
  player.classList.add('on')
  stopAt = parseFloat(btn.dataset.end)
  video.currentTime = Math.max(0, parseFloat(btn.dataset.start))
  video.play().catch(() => {{}})
}}))
video.addEventListener('timeupdate', () => {{ if (stopAt !== null && video.currentTime >= stopAt) {{ video.pause(); stopAt = null }} }})
video.addEventListener('error', () => {{
  document.querySelectorAll('button.play').forEach(b => {{ b.disabled = true; b.title = 'media/source.mp4 not found next to this page' }})
}})
document.getElementById('close').addEventListener('click', () => {{ video.pause(); player.classList.remove('on') }})
</script>
</body></html>"""
  OUT.write_text(page)
  print(OUT.relative_to(ROOT))


if __name__ == "__main__":
  main()

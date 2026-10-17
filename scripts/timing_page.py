"""Timing review page -> review/dist/timing.html (ignored: it embeds film frames and the original lines).

Shot by shot, like the storyboard, but about timing. For every line: the original slot next to where the new audio
actually sounds (data/chorus.json for the chorus, data/di.json for the drill instructor), with the start/end shift.
Each shot gets a two-lane timeline (original vs new, with the cuts marked) and buttons that play the new pass
(renders/proto/full-pass.mp4) or the original clip over the picture. Feedback boxes per line and per shot; the Copy
button collects every non-empty note, labelled with the line and its timings.

Run: uv run --group analysis python scripts/timing_page.py
"""

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audio import decode, find_line, whisper_words  # noqa: E402
from di import edges  # noqa: E402
from storyboard import ROOT, feedback_box, frame, load_words, original_line  # noqa: E402

OUT = ROOT / "review" / "dist" / "timing.html"
esc = html.escape


def describe(path: Path, lines: list[dict]) -> str:
  """A take's length, or for a multi-line read the pauses Fish left between its lines (audible edges)."""
  y, words = decode(path), whisper_words(path)
  found, cur = [], 0
  for ln in lines:
    hit = find_line(words, ln["parody"], cur)
    if not hit:
      return "couldn't find every line in this take"
    found.append(edges(y, words, hit[0], hit[1]))
    cur = hit[1] + 1
  if len(found) == 1:
    return f"{found[0][1] - found[0][0]:.2f} s"
  gaps = [max(0.0, b[0] - a[1]) for a, b in zip(found, found[1:])]
  return "pauses " + " · ".join(f"{g:.2f}" for g in gaps) + f" s · {found[-1][1] - found[0][0]:.1f} s overall"


def shift_class(d: float) -> str:
  return "ok" if abs(d) <= 0.15 else "warn" if abs(d) <= 0.5 else "over"


def main() -> None:
  script = json.loads((ROOT / "data" / "script.json").read_text())
  w0, w1 = script["window"]["start"], script["window"]["end"]
  version = script.get("review", {}).get("timing", 1)
  placed: dict[str, list[float]] = {}
  block_lines: set[str] = set()
  for f in ("chorus.json", "di.json"):
    p = ROOT / "data" / f
    if p.exists():
      for k, v in json.loads(p.read_text())["lines"].items():
        placed[k] = v["placed"]
        if v.get("mode") == "block":
          block_lines.add(k)
  cast = script["cast"]
  # take options per read, shown in the shot where the read's first line is
  voices = json.loads((ROOT / "data" / "voices.json").read_text())
  by_id = {ln["id"]: ln for ln in script["lines"]}
  takes: dict[str, dict] = {}
  for r in voices["di"].get("reads", []):
    ids = r["lines"]
    label = ids[0] if len(ids) == 1 else f"{ids[0]}–{ids[-1]}"
    takes[ids[0]] = {"label": label, "ids": ids, "files": [r["file"], *r.get("alts", [])], "in_use": r["file"]}
  fw = voices.get("fireWatch", {})
  if fw.get("options") and (ROOT / fw["options"]).exists():
    opts = json.loads((ROOT / fw["options"]).read_text())
    takes["F01"] = {"label": "F01", "ids": ["F01"], "files": [o["file"] for o in opts], "names": [o["name"] for o in opts],
                    "in_use": fw.get("read")}
  whisper, captions = load_words()
  t = lambda x: x - w0  # noqa: E731  source seconds -> meme seconds

  summary_rows, sections = [], []
  for s in script["shots"]:
    lines = [ln for ln in script["lines"] if ln["shot"].split(">")[0] == s["id"]]
    news = [placed[ln["id"]] for ln in lines if ln["id"] in placed]
    lo = min([s["start"]] + [ln["start"] for ln in lines] + [p[0] for p in news]) - 0.2
    hi = max([s["end"]] + [ln["end"] for ln in lines] + [p[1] for p in news]) + 0.3
    pct = lambda x: 100 * (x - lo) / (hi - lo)  # noqa: E731

    def block(a: float, b: float, cls: str, label: str) -> str:
      return (f'<div class="blk {cls}" style="left:{pct(a):.2f}%;width:{max(0.6, pct(b) - pct(a)):.2f}%" '
              f'title="{esc(label)} {t(a):.2f}–{t(b):.2f}s">{esc(label)}</div>')

    orig_lane = "".join(block(ln["start"], ln["end"], "orig", ln["id"]) for ln in lines)
    new_lane = "".join(
      block(*placed[ln["id"]], "di" if ln["voice"] == "jensen" else "chorus", ln["id"]) for ln in lines if ln["id"] in placed
    )
    ticks = "".join(
      f'<div class="tick" style="left:{pct(x + w0):.2f}%"><span>{x:.0f}s</span></div>'
      for x in range(int(t(lo)) + 1, int(t(hi)) + 1)
    )
    cuts = "".join(f'<div class="cut" style="left:{pct(x):.2f}%"></div>' for x in (s["start"], s["end"]) if lo < x < hi)
    timeline = (
      f'<div class="timeline"><div class="lane"><span class="lname">Original</span><div class="track">{cuts}{orig_lane}</div></div>'
      f'<div class="lane"><span class="lname">New</span><div class="track">{cuts}{new_lane}</div></div>'
      f'<div class="lane ticks"><span class="lname"></span><div class="track">{ticks}</div></div></div>'
    )

    rows = []
    for ln in lines:
      a, b = ln["start"], ln["end"]
      new = placed.get(ln["id"])
      orig_html, orig_src = original_line(ln, whisper, captions)
      if new:
        ds, de = new[0] - a, new[1] - b
        timing = (f'<span>orig {t(a):.2f}–{t(b):.2f} <i>({b - a:.2f}s)</i></span>'
                  f'<span>new {t(new[0]):.2f}–{t(new[1]):.2f} <i>({new[1] - new[0]:.2f}s)</i></span>'
                  f'<span class="d {shift_class(ds)}">start {ds:+.2f}s</span><span class="d {shift_class(de)}">end {de:+.2f}s</span>')
        play_new = f'<button class="play" data-src="new" data-start="{new[0] - 0.4:.2f}" data-end="{new[1] + 0.4:.2f}">▶ New</button>'
        label = f"{ln['id']} · {ln['parody']} (orig {t(a):.2f}–{t(b):.2f}, new {t(new[0]):.2f}–{t(new[1]):.2f})"
      else:
        timing = f'<span>orig {t(a):.2f}–{t(b):.2f} <i>({b - a:.2f}s)</i></span><span class="d over">no audio yet</span>'
        play_new, label = "", f"{ln['id']} · {ln['parody']} (orig {t(a):.2f}–{t(b):.2f}, no audio yet)"
      voice = "Jensen" if ln["voice"] == "jensen" else "Fire watch" if ln["id"] == "F01" else "Chorus"
      if ln["id"] in block_lines:
        timing += '<span class="dim">· one read: natural cadence, the picture adapts</span>'
      rows.append(
        f'<li class="line" id="{ln["id"]}"><img src="{frame((a + b) / 2)}" alt="" loading="lazy">'
        f'<div class="body"><div class="meta"><code>{ln["id"]}</code><span class="voice">{voice}</span>{timing}'
        f'<span class="btns">{play_new}<button class="play" data-src="orig" data-start="{a - 0.4:.2f}" data-end="{b + 0.4:.2f}">▶ Original</button></span></div>'
        f'<div class="compare"><div class="col orig"><span class="label">Original{f" · {orig_src}" if orig_src else ""}</span><p>{orig_html}</p></div>'
        f'<div class="col parody"><span class="label">New</span><p>{esc(ln["parody"])}</p></div></div>'
        f'{feedback_box(ln["id"], label, f"Timing on {ln["id"]}: early, late, too long, overlaps…")}</div></li>'
      )

    if news:
      first, last = min(p[0] for p in news), max(p[1] for p in news)
      voiced = [ln for ln in lines if ln["id"] in placed]  # compare like with like: lines that have new audio
      o0, o1 = min(ln["start"] for ln in voiced), max(ln["end"] for ln in voiced)
      drift = last - o1
      summary_rows.append(
        f'<tr><td><a href="#{s["id"]}">{s["id"]}</a></td><td>{t(s["start"]):.2f}–{t(s["end"]):.2f}</td>'
        f'<td>{t(o0):.2f}–{t(o1):.2f}</td><td>{t(first):.2f}–{t(last):.2f}</td>'
        f'<td class="d {shift_class(drift)}">{drift:+.2f}s</td></tr>'
      )
    options = ""
    for ln in lines:
      tk = takes.get(ln["id"])
      if not tk:
        continue
      cards = []
      for i, f in enumerate(tk["files"]):
        name = tk["names"][i] if "names" in tk else Path(f).stem
        use = f == tk["in_use"]
        cards.append(
          f'<div class="opt{" use" if use else ""}"><div class="oname">{i + 1}. {esc(name)}{" · in use" if use else ""}</div>'
          f'<audio controls preload="none" src="../../{f}"></audio>'
          f'<div class="odesc">{esc(describe(ROOT / f, [by_id[x] for x in tk["ids"]]))}</div></div>'
        )
      options += (
        f'<div class="options"><h3>Takes for {tk["label"]}</h3><div class="ogrid">{"".join(cards)}</div>'
        f'{feedback_box("takes-" + tk["label"], f"Takes for {tk['label']}", "Which take? Anything to regenerate?")}</div>'
      )
    who = ", ".join(cast[k]["name"] for k in s["cast"])
    sections.append(
      f'<section class="shot" id="{s["id"]}"><header><img src="{frame(s["start"] + 0.4, 640)}" alt="" loading="lazy">'
      f'<div><h2>{s["id"]} <span>{t(s["start"]):.2f}–{t(s["end"]):.2f}s · {s["end"] - s["start"]:.1f}s</span>'
      f'<button class="play" data-src="new" data-start="{lo:.2f}" data-end="{hi:.2f}">▶ New</button>'
      f'<button class="play" data-src="orig" data-start="{lo:.2f}" data-end="{hi:.2f}">▶ Original</button></h2>'
      f'<p><b>{esc(s["framing"])}</b>: {esc(s["subject"])}</p><p>Cast: <b>{esc(who)}</b></p>'
      f'{feedback_box(s["id"], f"{s["id"]} (scene timing)", f"Timing on scene {s["id"]}: pacing, cut points, gaps…")}</div></header>'
      f'{timeline}{options}<ol>{"".join(rows) or "<li class=empty>No dialogue.</li>"}</ol></section>'
    )

  page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Software Factory Timing</title>
<style>
:root {{ --bg:#f6f4ef; --card:#fff; --ink:#1d1c1a; --dim:#6b675f; --line:#e4e0d6; --field:#fbfaf7; --accent:#4a5a2a; --accent-ink:#fff; --ok:#2f7a3b; --warn:#a36a00; --over:#b03a2e; --orig:#f1eee6; --c-orig:#b9b2a3; --c-chorus:#6f8f3a; --c-di:#c07a2c; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141412; --card:#1e1d1a; --ink:#ecebe6; --dim:#9c978c; --line:#33312c; --field:#171614; --accent:#a9bd77; --accent-ink:#141412; --ok:#6fcf7f; --warn:#e7b04a; --over:#ef7c6e; --orig:#262521; --c-orig:#5d584e; --c-chorus:#8fb153; --c-di:#e09a4a; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 ui-sans-serif,system-ui,-apple-system,sans-serif; }}
main {{ max-width:1080px; margin:0 auto; padding:16px 16px 120px; }}
.bar {{ position:sticky; top:0; z-index:5; background:color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }}
.bar-in {{ max-width:1080px; margin:0 auto; padding:10px 16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap }}
.bar h1 {{ font-size:17px; margin:0; flex:1 1 auto }} .bar h1 span {{ color:var(--dim); font-weight:400 }}
button {{ font:inherit; font-size:13px; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:7px; padding:4px 9px; cursor:pointer; white-space:nowrap }}
button:hover {{ border-color:var(--dim) }}
button.primary {{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); font-weight:600 }}
button:disabled {{ opacity:.45; cursor:default }}
.count, .dim {{ color:var(--dim) }} .count {{ font-size:13px }}
.sub {{ color:var(--dim); margin:14px 0 14px }}
.legend {{ display:flex; gap:14px; flex-wrap:wrap; font-size:13px; color:var(--dim); margin-bottom:14px }}
.legend i {{ display:inline-block; width:14px; height:10px; border-radius:3px; margin-right:5px; vertical-align:middle }}
table.summary {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:hidden; margin-bottom:22px; font-size:14px }}
table.summary th, table.summary td {{ text-align:left; padding:7px 12px; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums }}
table.summary th {{ color:var(--dim); font-weight:500; font-size:12px; text-transform:uppercase; letter-spacing:.05em }}
table.summary a {{ color:var(--accent); font-weight:600; text-decoration:none }}
.general {{ margin:0 0 22px }} .general label {{ font-weight:600; display:block; margin-bottom:6px }}
.shot {{ background:var(--card); border:1px solid var(--line); border-radius:12px; margin:0 0 20px; overflow:hidden; scroll-margin-top:64px }}
.shot header {{ display:grid; grid-template-columns:minmax(0,300px) 1fr; gap:16px; padding:14px; border-bottom:1px solid var(--line) }}
.shot header img {{ width:100%; border-radius:6px; display:block }}
.shot h2 {{ margin:0 0 6px; font-size:18px; display:flex; gap:8px; align-items:baseline; flex-wrap:wrap }}
.shot h2 span {{ color:var(--dim); font-weight:400; font-size:14px; margin-right:4px }}
.shot header p {{ margin:2px 0 }}
.timeline {{ padding:12px 14px 6px; border-bottom:1px solid var(--line) }}
.lane {{ display:grid; grid-template-columns:62px 1fr; align-items:center; gap:8px; margin-bottom:6px }}
.lname {{ font-size:12px; color:var(--dim) }}
.track {{ position:relative; height:24px; background:var(--field); border:1px solid var(--line); border-radius:6px }}
.lane.ticks .track {{ height:14px; background:none; border:0 }}
.blk {{ position:absolute; top:2px; bottom:2px; border-radius:4px; font-size:11px; font-weight:600; color:#fff; padding:0 4px; overflow:hidden; white-space:nowrap; line-height:20px }}
.blk.orig {{ background:var(--c-orig) }} .blk.chorus {{ background:var(--c-chorus) }} .blk.di {{ background:var(--c-di) }}
.cut {{ position:absolute; top:-3px; bottom:-3px; width:0; border-left:2px dashed var(--dim); opacity:.6 }}
.tick {{ position:absolute; top:0; height:6px; border-left:1px solid var(--dim) }}
.tick span {{ position:absolute; top:4px; left:-10px; font-size:10px; color:var(--dim) }}
ol {{ list-style:none; margin:0; padding:0 }}
.line {{ display:grid; grid-template-columns:150px minmax(0,1fr); gap:14px; padding:12px 14px; border-top:1px solid var(--line); scroll-margin-top:64px }}
.line:first-child {{ border-top:0 }}
.line > img {{ width:100%; border-radius:4px; display:block }}
.meta {{ display:flex; flex-wrap:wrap; gap:4px 12px; font-size:13px; color:var(--dim); align-items:center; font-variant-numeric:tabular-nums }}
.meta code {{ color:var(--accent); font-weight:600 }}
.meta i {{ font-style:normal; opacity:.75 }}
.meta .btns {{ margin-left:auto; display:flex; gap:6px }}
.d {{ font-weight:600 }} .d.ok {{ color:var(--ok) }} .d.warn {{ color:var(--warn) }} .d.over {{ color:var(--over) }}
.compare {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:8px 0 2px }}
.col {{ border-radius:8px; padding:7px 10px }}
.col.orig {{ background:var(--orig) }} .col.parody {{ border:1px solid var(--line) }}
.col .label {{ display:block; font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--dim); margin-bottom:2px }}
.col p {{ margin:0 }} .col.orig p {{ color:var(--dim) }} .col.parody p {{ font-weight:600 }}
.unsure {{ font-style:italic; opacity:.75 }}
textarea.fb {{ width:100%; min-height:34px; resize:vertical; font:inherit; font-size:14px; color:var(--ink); background:var(--field); border:1px solid var(--line); border-radius:8px; padding:7px 10px; overflow:hidden; margin-top:8px }}
textarea.fb.filled {{ border-color:var(--accent) }}
.empty {{ padding:12px 14px; color:var(--dim) }}
.options {{ padding:12px 14px; border-bottom:1px solid var(--line) }}
.options h3 {{ margin:0 0 8px; font-size:14px }}
.ogrid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:8px }}
.opt {{ border:1px solid var(--line); border-radius:8px; padding:8px 10px }}
.opt.use {{ border-color:var(--accent); background:color-mix(in srgb, var(--accent) 8%, var(--card)) }}
.oname {{ font-size:13px; font-weight:600; margin-bottom:6px }}
.odesc {{ font-size:12px; color:var(--dim); margin-top:4px; font-variant-numeric:tabular-nums }}
.opt audio {{ width:100%; height:32px }}
.player {{ position:fixed; right:16px; bottom:16px; width:min(400px, calc(100vw - 32px)); background:#000; border-radius:10px; overflow:hidden; box-shadow:0 8px 30px rgba(0,0,0,.35); z-index:10; display:none }}
.player.on {{ display:block }}
.player video {{ width:100%; display:block }}
.player .ptag {{ position:absolute; top:6px; left:8px; color:#fff; font-size:12px; font-weight:600; background:rgba(0,0,0,.55); padding:2px 7px; border-radius:5px }}
.player .close {{ position:absolute; top:6px; right:6px; background:rgba(0,0,0,.6); color:#fff; border:0 }}
.toast {{ position:fixed; left:50%; bottom:20px; transform:translateX(-50%); background:var(--ink); color:var(--bg); padding:8px 14px; border-radius:8px; font-size:14px; opacity:0; transition:opacity .2s; pointer-events:none; z-index:20 }}
.toast.on {{ opacity:1 }}
.foot {{ display:flex; gap:10px; justify-content:flex-end; align-items:center; margin-top:8px }}
@media (max-width:720px) {{ .shot header {{ grid-template-columns:1fr }} .line {{ grid-template-columns:1fr }} .line > img {{ max-width:220px }} .compare {{ grid-template-columns:1fr }} .meta .btns {{ margin-left:0 }} }}
</style></head><body>
<div class="bar"><div class="bar-in">
<h1>This Is My Software Factory <span>· timing review v{version}</span></h1>
<button class="play" data-src="new" data-start="{w0:.2f}" data-end="{w1:.2f}">▶ Whole pass</button>
<span class="count" id="count">No notes yet</span>
<button id="clear">Clear</button>
<button class="primary copy">Copy feedback</button>
</div></div>
<main>
<p class="sub">Every line's original slot next to where the new audio sounds (the raw chorus take and Jensen's lines). Times are meme seconds.
"▶ New" plays the new pass over the picture; "▶ Original" plays the film. Shifts: green within 0.15 s, amber within 0.5 s, red beyond.</p>
<div class="legend"><span><i style="background:var(--c-orig)"></i>Original slot</span><span><i style="background:var(--c-chorus)"></i>New: chorus</span>
<span><i style="background:var(--c-di)"></i>New: Jensen</span><span><i style="border-left:2px dashed var(--dim);border-radius:0;width:2px"></i>Cut</span></div>
<table class="summary"><tr><th>Shot</th><th>Shot span</th><th>Original lines</th><th>New lines</th><th>New ends</th></tr>{"".join(summary_rows)}</table>
<div class="general"><label>General timing feedback</label>{feedback_box("general", "General", "Overall pacing, gaps, what to move…")}</div>
{"".join(sections)}
<div class="foot"><span class="count" id="count2"></span><button class="primary copy">Copy feedback</button></div>
</main>
<div class="player" id="player"><video id="video" preload="metadata" playsinline controls></video><span class="ptag" id="ptag"></span><button class="close" id="close" aria-label="Close player">✕</button></div>
<div class="toast" id="toast" role="status"></div>
<script>
const VERSION = {version}
const W0 = {w0}
const SRC = {{ new: '../../renders/proto/full-pass.mp4', orig: '../../media/source.mp4' }}
const OFFSET = {{ new: W0, orig: 0 }}
const KEY = id => `my-software-factory:timing:v${{VERSION}}:${{id}}`
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
  b.value = store.get(b.dataset.id); b.classList.toggle('filled', !!b.value.trim()); grow(b)
  b.addEventListener('input', () => {{ store.set(b.dataset.id, b.value); b.classList.toggle('filled', !!b.value.trim()); grow(b); refresh() }})
}}
refresh()
const toast = msg => {{ const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('on'), 1800) }}
const copy = async text => {{
  try {{ await navigator.clipboard.writeText(text); return true }} catch {{}}
  const t = document.createElement('textarea'); t.value = text; t.style.position = 'fixed'; t.style.opacity = '0'
  document.body.appendChild(t); t.select(); const ok = document.execCommand('copy'); t.remove(); return ok
}}
document.querySelectorAll('button.copy').forEach(btn => btn.addEventListener('click', async () => {{
  const notes = boxes.filter(b => b.value.trim()).map(b => `${{b.dataset.label}}\\n${{b.value.trim()}}`)
  const ok = await copy(`Timing review v${{VERSION}} feedback (${{notes.length}} notes)\\n\\n` + notes.join('\\n\\n') + '\\n')
  toast(ok ? `Copied ${{notes.length}} note${{notes.length === 1 ? '' : 's'}}` : 'Copy failed')
}}))
document.getElementById('clear').addEventListener('click', () => {{
  if (!boxes.some(b => b.value.trim()) || !confirm('Clear all timing feedback for this version?')) return
  for (const b of boxes) {{ b.value = ''; store.set(b.dataset.id, ''); b.classList.remove('filled'); grow(b) }}
  refresh()
}})

const player = document.getElementById('player'), video = document.getElementById('video')
let stopAt = null, current = null
document.querySelectorAll('button.play').forEach(btn => btn.addEventListener('click', () => {{
  const which = btn.dataset.src, start = parseFloat(btn.dataset.start), end = parseFloat(btn.dataset.end)
  player.classList.add('on')
  document.getElementById('ptag').textContent = which === 'new' ? 'New pass' : 'Original'
  const go = () => {{ video.currentTime = Math.max(0, start - OFFSET[which]); stopAt = end - OFFSET[which]; video.play().catch(() => {{}}) }}
  if (current !== which) {{ current = which; video.src = SRC[which]; video.addEventListener('loadedmetadata', go, {{ once: true }}) }} else go()
}}))
video.addEventListener('timeupdate', () => {{ if (stopAt !== null && video.currentTime >= stopAt) {{ video.pause(); stopAt = null }} }})
document.getElementById('close').addEventListener('click', () => {{ video.pause(); player.classList.remove('on') }})
</script>
</body></html>"""
  OUT.parent.mkdir(parents=True, exist_ok=True)
  OUT.write_text(page)
  print(OUT.relative_to(ROOT))


if __name__ == "__main__":
  main()

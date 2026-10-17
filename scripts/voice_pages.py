"""Voice review pages -> review/dist/ (ignored: they point at the copyrighted clip and the takes).

  voices.html  audition: the DI Voice Design previews, the chorus prototype and the stock chorus voices,
               each with a feedback box and a Copy button (same loop as the storyboard)
  record.html  record-to-picture: plays the source clip with the parody lines as a teleprompter, clicks you in
               before each of your lines, and records the take in the browser, already synced to picture

Run: uv run --group analysis python scripts/voice_pages.py
"""

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "review" / "dist"
REL = "../.."  # from review/dist back to the project root
esc = html.escape

CSS = """
:root { --bg:#f6f4ef; --card:#fff; --ink:#1d1c1a; --dim:#6b675f; --line:#e4e0d6; --field:#fbfaf7; --accent:#4a5a2a; --accent-ink:#fff; --rec:#c0392b; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141412; --card:#1e1d1a; --ink:#ecebe6; --dim:#9c978c; --line:#33312c; --field:#171614; --accent:#a9bd77; --accent-ink:#141412; --rec:#ef6b5b; } }
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 ui-sans-serif,system-ui,-apple-system,sans-serif; }
main { max-width:1080px; margin:0 auto; padding:16px 16px 80px; }
.bar { position:sticky; top:0; z-index:5; background:color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }
.bar-in { max-width:1080px; margin:0 auto; padding:10px 16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap }
.bar h1 { font-size:17px; margin:0; flex:1 1 auto } .bar h1 span { color:var(--dim); font-weight:400 }
button, select { font:inherit; font-size:13px; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:7px; padding:5px 10px; cursor:pointer }
button.primary { background:var(--accent); color:var(--accent-ink); border-color:var(--accent); font-weight:600 }
button:disabled { opacity:.45; cursor:default }
.count, .dim { color:var(--dim) } .count { font-size:13px }
h2 { font-size:19px; margin:28px 0 4px } h2 + p { margin:0 0 12px; color:var(--dim) }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:12px }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px }
.card h3 { margin:0 0 6px; font-size:15px } .card p { margin:0 0 8px; font-size:13px; color:var(--dim) }
audio, video { width:100%; display:block } video { border-radius:8px; background:#000 }
textarea.fb { width:100%; min-height:34px; resize:vertical; font:inherit; font-size:14px; color:var(--ink); background:var(--field); border:1px solid var(--line); border-radius:8px; padding:7px 10px; overflow:hidden; margin-top:8px }
textarea.fb.filled { border-color:var(--accent) }
.toast { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); background:var(--ink); color:var(--bg); padding:8px 14px; border-radius:8px; font-size:14px; opacity:0; transition:opacity .2s; pointer-events:none; z-index:20 }
.toast.on { opacity:1 }
"""

FEEDBACK_JS = """
const KEY = id => `my-software-factory:${PAGE}:${id}`
const store = {
  get(id) { try { return localStorage.getItem(KEY(id)) || '' } catch { return '' } },
  set(id, v) { try { v ? localStorage.setItem(KEY(id), v) : localStorage.removeItem(KEY(id)) } catch {} },
}
const boxes = [...document.querySelectorAll('textarea.fb')]
const grow = t => { t.style.height = 'auto'; t.style.height = t.scrollHeight + 2 + 'px' }
const refresh = () => {
  const n = boxes.filter(b => b.value.trim()).length
  document.getElementById('count').textContent = n ? `${n} note${n === 1 ? '' : 's'}` : 'No notes yet'
  document.querySelectorAll('button.copy').forEach(b => (b.disabled = !n))
}
for (const b of boxes) {
  b.value = store.get(b.dataset.id); b.classList.toggle('filled', !!b.value.trim()); grow(b)
  b.addEventListener('input', () => { store.set(b.dataset.id, b.value); b.classList.toggle('filled', !!b.value.trim()); grow(b); refresh() })
}
refresh()
const toast = msg => { const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('on'), 1800) }
const copy = async text => {
  try { await navigator.clipboard.writeText(text); return true } catch {}
  const t = document.createElement('textarea'); t.value = text; t.style.position = 'fixed'; t.style.opacity = '0'
  document.body.appendChild(t); t.select(); const ok = document.execCommand('copy'); t.remove(); return ok
}
document.querySelectorAll('button.copy').forEach(btn => btn.addEventListener('click', async () => {
  const notes = boxes.filter(b => b.value.trim()).map(b => `${b.dataset.label}\\n${b.value.trim()}`)
  const ok = await copy(`${TITLE} feedback (${notes.length} notes)\\n\\n` + notes.join('\\n\\n') + '\\n')
  toast(ok ? `Copied ${notes.length} note${notes.length === 1 ? '' : 's'}` : 'Copy failed')
}))
"""


def box(fid: str, label: str, placeholder: str = "Notes…") -> str:
  return (f'<textarea class="fb" rows="1" data-id="{esc(fid, quote=True)}" data-label="{esc(label, quote=True)}" '
          f'placeholder="{esc(placeholder, quote=True)}"></textarea>')


def page(title: str, sub: str, body: str, bar_extra: str, script: str) -> str:
  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<div class="bar"><div class="bar-in"><h1>This Is My Software Factory <span>· {esc(sub)}</span></h1>{bar_extra}</div></div>
<main>{body}</main><div class="toast" id="toast" role="status"></div>
<script>{script}</script></body></html>"""


def voices_page() -> str:
  voices = json.loads((ROOT / "data" / "voices.json").read_text())
  design_root = ROOT / "media" / "voices" / "design"
  di_cards = []
  for spec_dir in sorted(design_root.iterdir()) if design_root.exists() else []:
    meta = json.loads((spec_dir / "previews.json").read_text())
    rows = "".join(
      f'<h3 style="margin-top:12px">{esc(p["file"].removesuffix(".mp3"))}</h3>'
      f'<audio controls preload="none" src="{REL}/media/voices/design/{spec_dir.name}/{p["file"]}"></audio>'
      f'{box(f"di-{spec_dir.name}-{p['file'].split('.')[0]}", f"DI voice {spec_dir.name}/{p['file']}", "Keep, cut, or what to change…")}'
      for p in meta["previews"]
    )
    di_cards.append(f'<div class="card"><h3>{esc(spec_dir.name)}</h3><p>{esc(meta["spec"]["voice_description"])}</p>{rows}</div>')
  def media(rel: str, kind: str = "audio") -> str:
    if not (ROOT / rel).exists():
      return ""
    if kind == "video":
      return f'<video controls preload="metadata" src="{REL}/{rel}"></video>'
    return f'<audio controls preload="none" src="{REL}/{rel}"></audio>'

  def card(title: str, note: str, body: str, fid: str, label: str, prompt: str) -> str:
    return f'<div class="card"><h3>{esc(title)}</h3><p>{esc(note)}</p>{body}{box(fid, label, prompt)}</div>' if body else ""

  chorus_meta = json.loads((ROOT / "data" / "chorus.json").read_text()) if (ROOT / "data" / "chorus.json").exists() else None
  pass_cards = [
    card("Full pass over picture", "The raw Eleven Music chorus, cut at its scene pauses and laid on the timeline, plus Jensen's lines. No room bed.",
         media("renders/proto/full-pass.mp4", "video"), "full-pass", "Full pass (chorus + DI) over picture", "Timing, levels, anything off?"),
    card("The chorus take, raw", "One Eleven Music generation (music_v2_5, seed 3) with every recruit line and a silent 3 s gap between scenes. "
         "Whisper hears C08 as \"drill my agents\" rather than \"grill\": listen for it.",
         media(chorus_meta["source"]) if chorus_meta else "", "chorus-raw", "Chorus take, raw (gaps, seed 3)", "Consistent? Any line to regenerate?"),
  ]
  vj = json.loads((ROOT / "data" / "voices.json").read_text())
  in_use = {r["file"] for r in vj["di"].get("reads", [])} | {vj.get("fireWatch", {}).get("read")}

  def takes(title: str, note: str, files: list[str], fid: str, label: str) -> str:
    rows = "".join(
      f'<h3 style="margin-top:10px">Take {i + 1}{" · in use" if f in in_use else ""}</h3>' + media(f) for i, f in enumerate(files)
    )
    return card(title, note, rows, fid, label, "Which take? Commanding enough?")

  J = "media/voices/jensen/"
  test_cards = [
    takes("D01 \"Prompt!\"", "Fish clone with a command directive.", [J + "d01-cmd-take1.mp3", J + "d01-cmd-take2.mp3"], "di-d01", "D01 takes"),
    takes("D02–D06, one read", "Ready! Commit! Push! … Auto-merge! … Close your laptops!, in one breath with its own cadence; "
          "the timeline adapts to it.", [J + "d02-06-cmd-take1.mp3", J + "d02-06-cmd-take2.mp3"], "di-d02-06", "D02–D06 takes"),
    takes("D07 \"We need more GPUs!\"", "Command directive, over his shoulder.", [J + "d07-cmd-take1.mp3", J + "d07-cmd-take2.mp3"],
          "di-d07", "D07 takes (commanding)"),
    card("Earlier: calm test read", "The first Fish read (D01–D06 were cut from this before).",
         media("media/voices/jensen/di-test-fish.mp3"), "di-test-fish", "DI test read, Fish clone (calm)", "Notes?"),
  ]
  fw_cards = []
  fw_opts = ROOT / "media" / "voices" / "firewatch" / "options.json"
  for i, o in enumerate(json.loads(fw_opts.read_text()) if fw_opts.exists() else []):
    fw_cards.append(card(f"{i + 1}. {o['name']}" + (" · in use" if o["file"] in in_use else ""), o["description"][:140],
                         media(o["file"]), f"fw-{i + 1}", f"F01 option {i + 1}: {o['name']}", "Pick this one?"))
  body = (
    '<h2>Full pass</h2><p>Everything that exists so far, over the original picture. F01 uses option 1 until you pick a fire watch voice.</p>'
    f'<div class="grid">{"".join(pass_cards)}</div>'
    '<h2>Drill instructor</h2><p>The Fish Audio clone of Jensen, regenerated with command directives. "In use" marks the take in the full pass.</p>'
    f'<div class="grid">{"".join(test_cards)}</div>'
    '<h2>Fire watch (F01): pick a voice</h2><p>ElevenLabs: a stock voice, two soldier voices from the library, three Voice Design young privates. '
    'Option 1 is a placeholder in the pass until you pick.</p>'
    f'<div class="grid">{"".join(fw_cards)}</div>'
    '<h2>Earlier: Voice Design previews</h2><p>From three generic descriptions (he is never named). Keynote preview-1 is the saved fallback.</p>'
    f'<div class="grid">{"".join(di_cards)}</div>'
    f'<h2>General</h2>{box("general", "General")}'
  )
  bar = '<span class="count" id="count"></span><button class="primary copy">Copy feedback</button>'
  return page("Software Factory Voices", "voice audition", body, bar,
              "const PAGE = 'voices'\nconst TITLE = 'Voice audition'\n" + FEEDBACK_JS)


def record_page() -> str:
  script = json.loads((ROOT / "data" / "script.json").read_text())
  w = script["window"]
  lines = [{"id": ln["id"], "start": ln["start"], "end": ln["end"], "text": ln["parody"], "voice": ln["voice"]} for ln in script["lines"]]
  body = f"""
<style>
.stage {{ display:grid; grid-template-columns:minmax(0,1.3fr) minmax(0,1fr); gap:16px; align-items:start }}
.prompter {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; min-height:300px }}
.now {{ font-size:30px; font-weight:700; line-height:1.2; min-height:2.5em; text-wrap:balance }}
.now.mine {{ color:var(--accent) }} .now.other {{ color:var(--dim); font-size:22px }}
.who {{ font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:var(--dim); margin-bottom:4px }}
.progress {{ height:6px; background:var(--line); border-radius:3px; overflow:hidden; margin:12px 0 18px }}
.progress div {{ height:100%; width:0; background:var(--accent) }}
.next {{ font-size:17px; color:var(--dim) }} .next b {{ color:var(--ink) }}
.countdown {{ font-size:44px; font-weight:800; color:var(--rec); height:54px }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:12px 0 }}
.controls label {{ font-size:13px; color:var(--dim); display:flex; gap:6px; align-items:center }}
.rec {{ background:var(--rec); color:#fff; border-color:var(--rec); font-weight:700 }}
.status {{ font-size:13px; color:var(--dim) }}
.takes li {{ margin:4px 0 }}
@media (max-width:820px) {{ .stage {{ grid-template-columns:1fr }} }}
</style>
<p class="dim">Wear headphones. Pick a take, press Record: the clip starts 2 s before the window and stops at the end; the take downloads
already synced to picture. Your lines show in green with a 3-2-1 count; everyone else's are grey. Keep the room dry (closet, duvet) and
perform to the original's rhythm: turn its volume up to rehearse, down to record.</p>
<div class="controls">
  <label>Take <select id="take">
    <option value="chorus">Chorus (all recruit lines) · record 3 times</option>
    <option value="lead">Lead (recruit lines, dry and clean)</option>
    <option value="di">Drill instructor (D01–D07)</option>
    <option value="firewatch">Fire watch (F01)</option>
  </select></label>
  <label>Original volume <input id="vol" type="range" min="0" max="1" step="0.05" value="0.3"></label>
  <label><input id="clicks" type="checkbox" checked> Count-in clicks</label>
  <button id="rehearse">▶ Rehearse</button>
  <button id="record" class="rec">● Record take</button>
  <button id="stop">■ Stop</button>
  <span class="status" id="status">Ready</span>
</div>
<div class="stage">
  <video id="video" src="{REL}/media/source.mp4" preload="auto" playsinline></video>
  <div class="prompter">
    <div class="countdown" id="countdown"></div>
    <div class="who" id="who"></div>
    <div class="now" id="now">Press Rehearse or Record</div>
    <div class="progress"><div id="bar"></div></div>
    <div class="next" id="next"></div>
  </div>
</div>
<h2>Takes to record</h2>
<ol class="takes">
  <li><b>Chorus × 3:</b> every recruit line, chanted like a barracks in unison. Each take goes through all ten voices; three takes give the stack natural looseness.</li>
  <li><b>Lead × 1:</b> the same lines, dry and clean. It drives lip sync on Matt's and swyx's close-ups.</li>
  <li><b>Drill instructor × 1:</b> D01–D07, barked, in the accent and cadence you want. Voice Changer maps it onto the designed voice.</li>
  <li><b>Fire watch × 1:</b> F01, eager and sycophantic.</li>
</ol>
<p class="dim">Takes land in your Downloads folder as <code>chorus-1__src-…__offset-….webm</code> (the name carries the sync); move them to <code>media/takes/</code>. If the browser won't give
the page the mic, record in QuickTime while the page plays and tell me: the lines get snapped onto their slots in post either way.</p>
"""
  js = f"""
const LINES = {json.dumps(lines)}
const W = {json.dumps({"start": w["start"], "end": w["end"]})}
const PREROLL = 2
const MINE = {{
  chorus: l => l.voice.startsWith('chorus'),
  lead: l => l.voice.startsWith('chorus'),
  di: l => l.voice === 'jensen',
  firewatch: l => l.id === 'F01',
}}
const $ = id => document.getElementById(id)
const video = $('video')
let mode = null, recorder = null, chunks = [], stream = null, ctx = null, clicked = new Set(), playStartedAt = null, recStartedAt = null
video.volume = parseFloat($('vol').value)
$('vol').oninput = e => (video.volume = parseFloat(e.target.value))
const status = s => ($('status').textContent = s)
const click = (hi) => {{
  if (!$('clicks').checked) return
  ctx = ctx || new AudioContext()
  const o = ctx.createOscillator(), g = ctx.createGain()
  o.frequency.value = hi ? 1760 : 1320
  g.gain.setValueAtTime(0.25, ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.06)
  o.connect(g).connect(ctx.destination); o.start(); o.stop(ctx.currentTime + 0.07)
}}
function tick() {{
  if (video.paused) return
  const t = video.currentTime, take = $('take').value, mine = MINE[take]
  const cur = LINES.find(l => t >= l.start - 0.05 && t <= l.end + 0.1)
  const next = LINES.find(l => l.start > t + 0.05)
  if (cur) {{
    $('now').textContent = cur.text
    $('now').className = 'now ' + (mine(cur) ? 'mine' : 'other')
    $('who').textContent = cur.id + (mine(cur) ? ' · you' : '')
    $('bar').style.width = Math.min(100, (100 * (t - cur.start)) / (cur.end - cur.start)) + '%'
  }} else {{
    $('now').textContent = ''
    $('who').textContent = ''
    $('bar').style.width = '0'
  }}
  if (next) {{
    const dt = next.start - t
    $('next').innerHTML = `Next: <b>${{next.text}}</b> <span>(${{next.id}}, in ${{dt.toFixed(1)}} s)</span>`
    if (mine(next)) {{
      const n = dt <= 0.5 ? 1 : dt <= 1.0 ? 2 : dt <= 1.5 ? 3 : 0
      $('countdown').textContent = n ? String(n) : ''
      const key = next.id + ':' + n
      if (n && !clicked.has(key)) {{ clicked.add(key); click(n === 1) }}
    }} else $('countdown').textContent = ''
  }} else $('next').textContent = ''
  if (t >= W.end + 0.3) finish()
  requestAnimationFrame(tick)
}}
video.addEventListener('playing', () => {{ if (playStartedAt === null) playStartedAt = performance.now(); requestAnimationFrame(tick) }})
async function start(recording) {{
  stopAll(false)
  mode = recording ? 'record' : 'rehearse'
  clicked = new Set(); playStartedAt = null
  if (recording) {{
    try {{
      stream = await navigator.mediaDevices.getUserMedia({{ audio: {{ echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 }} }})
    }} catch (e) {{
      status('Mic blocked: record in QuickTime while you rehearse'); mode = null; return
    }}
    chunks = []
    recorder = new MediaRecorder(stream, {{ mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : '' }})
    recorder.ondataavailable = e => e.data.size && chunks.push(e.data)
    recorder.onstop = save
    await new Promise(r => {{ recorder.onstart = () => {{ recStartedAt = performance.now(); r() }}; recorder.start() }})
    status('● Recording')
  }} else status('Rehearsing')
  video.currentTime = Math.max(0, W.start - PREROLL)
  await new Promise(r => video.addEventListener('seeked', r, {{ once: true }}))
  video.play()
}}
function save() {{
  const take = $('take').value
  const n = (parseInt(localStorage.getItem('msf:take:' + take) || '0') + 1)
  try {{ localStorage.setItem('msf:take:' + take, String(n)) }} catch {{}}
  // t=0 of the file is recStartedAt; the clip was at (W.start - PREROLL) at playStartedAt
  const offset = ((playStartedAt - recStartedAt) / 1000).toFixed(3)
  const name = `${{take}}-${{n}}__src-${{(W.start - PREROLL).toFixed(2)}}__offset-${{offset}}.webm`
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob(chunks, {{ type: 'audio/webm' }}))
  a.download = name
  a.click()
  status('Saved ' + name)
}}
function stopAll(keep = true) {{
  video.pause()
  if (recorder && recorder.state !== 'inactive') {{ keep ? recorder.stop() : (recorder.onstop = null, recorder.stop()) }}
  if (stream) stream.getTracks().forEach(t => t.stop())
  recorder = null; stream = null
  if (!keep) status('Ready')
}}
function finish() {{ if (mode) {{ const m = mode; mode = null; stopAll(m === 'record'); if (m !== 'record') status('Done') }} }}
$('rehearse').onclick = () => start(false)
$('record').onclick = () => start(true)
$('stop').onclick = () => {{ const m = mode; mode = null; stopAll(m === 'record') }}
"""
  return page("Software Factory Recorder", "record to picture", body, "", js)


def main() -> None:
  DIST.mkdir(parents=True, exist_ok=True)
  (DIST / "voices.html").write_text(voices_page())
  (DIST / "record.html").write_text(record_page())
  print("review/dist/voices.html\nreview/dist/record.html")


if __name__ == "__main__":
  main()

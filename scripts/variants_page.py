"""Variants review page -> review/dist/variants.html (ignored: it embeds the film and real-person renders).

The S07+S08 test cut of each visual variant on the approved audio, the original for reference, the alternates
and generated stills behind each variant, what each cost (data/fal-log.jsonl) and what the full video would cost.
Feedback boxes per variant and per shot, with the same Copy button as the other review pages.

Run: uv run --group analysis python scripts/variants_page.py
"""

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from variants import OPTIONS, round_picks  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "review" / "dist" / "variants.html"
REL = "../.."
esc = html.escape

VARIANTS = [
  {
    "id": "lipsync", "title": "1 · Lip sync only",
    "how": "The original footage; only the speaking mouths are re-synced to the approved lines, with sync-3 on every shot: "
           "the drill instructor (S07) and the recruit (S08).",
    "jobs": ("variants/lipsync/",),
    "full": "sync-3 on every remaining speaking shot (~45 s more): about $6.",
    "notes": ["S07 and S08: sync-3 (approved). The gentler directions (lipsync-2, React-1) are retired."],
  },
  {
    "id": "generative", "title": "3 · Fully generative",
    "how": "No original footage. Character sheets and keyframes (Nano Banana Pro), then animated from the approved audio. S07: "
           "OmniHuman v2. S08: Kling v3 Pro animates calm typing from your approved still (prompted: hands steady on the keyboard, "
           "arms still, static camera), then sync-3 adds the shouting. The S08 options add H3 Max: its round-3 lip sync take, and two new takes prompted for "
           "calmer typing (H3 Max Lip Sync takes no prompt, so the calm motion comes from H3 Max image-to-video first).",
    "jobs": ("variants/generative/",),
    "full": "A keyframe per shot (~$2) plus motion and lip sync for the remaining ~54 s (~$15–25 with Kling + sync-3): about $17–27.",
    "notes": ["InfiniteTalk is out (it made the recruits flail).",
              "S08: the cut uses the option marked 'in use'; pick another in its box.",
              "OmniHuman rejects the S08 stills (any version: rifles or laptops); the S08 chorus audio passes with the S07 image, so its moderation flags the image itself (several men lying in bunks).",
              "Test spend includes every superseded S08 attempt."],
  },
]


def media(rel: str, kind: str = "video") -> str:
  if not (ROOT / rel).exists():
    return '<p class="dim">(not rendered)</p>'
  # a version stamp per file: renders keep their paths from round to round, and browsers cache local media
  src = f"{REL}/{rel}?v={int((ROOT / rel).stat().st_mtime)}"
  if kind == "img":
    return f'<a href="{src}" target="_blank"><img src="{src}" alt="" loading="lazy"></a>'
  if kind == "audio":
    return f'<audio controls preload="none" src="{src}"></audio>'
  return f'<video controls preload="metadata" src="{src}"></video>'


def box(fid: str, label: str, placeholder: str) -> str:
  return (f'<textarea class="fb" rows="1" data-id="{esc(fid, quote=True)}" data-label="{esc(label, quote=True)}" '
          f'placeholder="{esc(placeholder, quote=True)}"></textarea>')


def spend() -> tuple[dict[str, float], float]:
  log = ROOT / "data" / "fal-log.jsonl"
  per: dict[str, float] = {v["id"]: 0.0 for v in VARIANTS}
  total = 0.0
  for line in log.read_text().splitlines() if log.exists() else []:
    r = json.loads(line)
    c = r.get("est_cost_usd") or 0.0
    total += c
    for v in VARIANTS:
      if any(r.get("job", "").startswith(j) for j in v["jobs"]):
        per[v["id"]] += c
  return per, total


def render_page(title: str, subtitle: str, body: str, key: str, heading: str) -> str:
  """A review page: sticky bar with the note count and Copy button, the body, feedback boxes saved per browser under `key`."""
  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
:root {{ --bg:#f6f4ef; --card:#fff; --ink:#1d1c1a; --dim:#6b675f; --line:#e4e0d6; --field:#fbfaf7; --accent:#4a5a2a; --accent-ink:#fff; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141412; --card:#1e1d1a; --ink:#ecebe6; --dim:#9c978c; --line:#33312c; --field:#171614; --accent:#a9bd77; --accent-ink:#141412; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 ui-sans-serif,system-ui,-apple-system,sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:16px 16px 80px; }}
.bar {{ position:sticky; top:0; z-index:5; background:color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }}
.bar-in {{ max-width:1180px; margin:0 auto; padding:10px 16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap }}
.bar h1 {{ font-size:17px; margin:0; flex:1 1 auto }} .bar h1 span {{ color:var(--dim); font-weight:400 }}
button {{ font:inherit; font-size:13px; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:7px; padding:5px 10px; cursor:pointer }}
button.primary {{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); font-weight:600 }}
button:disabled {{ opacity:.45; cursor:default }}
.count, .dim {{ color:var(--dim) }} .count {{ font-size:13px }}
.sub {{ color:var(--dim); margin:14px 0 18px }}
.variant {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; margin:0 0 18px }}
.variant h2 {{ margin:0 0 10px; font-size:19px }} .variant h2 span {{ color:var(--dim); font-weight:400; font-size:14px; margin-left:8px }}
.variant h3 {{ margin:16px 0 8px; font-size:15px }}
.grid2 {{ display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); gap:16px; align-items:start }}
.grid3 {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:12px }}
.grid2 p, .grid2 li {{ margin:0 0 8px }} .grid2 ul {{ padding-left:18px; margin:0 0 8px }}
video, img {{ width:100%; display:block; border-radius:8px; background:#000 }}
figure {{ margin:0 }} figcaption {{ font-size:13px; color:var(--dim); margin-top:4px }}
textarea.fb {{ width:100%; min-height:34px; resize:vertical; font:inherit; font-size:14px; color:var(--ink); background:var(--field); border:1px solid var(--line); border-radius:8px; padding:7px 10px; overflow:hidden; margin-top:8px }}
textarea.fb.filled {{ border-color:var(--accent) }}
.general label {{ font-weight:600; display:block; margin-bottom:6px }}
.opt.use video {{ outline:3px solid var(--accent) }}
.toast {{ position:fixed; left:50%; bottom:20px; transform:translateX(-50%); background:var(--ink); color:var(--bg); padding:8px 14px; border-radius:8px; font-size:14px; opacity:0; transition:opacity .2s; pointer-events:none; z-index:20 }}
.toast.on {{ opacity:1 }}
@media (max-width:820px) {{ .grid2 {{ grid-template-columns:1fr }} }}
</style></head><body>
<div class="bar"><div class="bar-in"><h1>This Is My Software Factory <span>· {esc(subtitle)}</span></h1>
<span class="count" id="count">No notes yet</span><button class="primary copy">Copy feedback</button></div></div>
<main>{body}</main><div class="toast" id="toast" role="status"></div>
<script>
const KEY = id => `my-software-factory:{key}:${{id}}`
const store = {{
  get(id) {{ try {{ return localStorage.getItem(KEY(id)) || '' }} catch {{ return '' }} }},
  set(id, v) {{ try {{ v ? localStorage.setItem(KEY(id), v) : localStorage.removeItem(KEY(id)) }} catch {{}} }},
}}
const boxes = [...document.querySelectorAll('textarea.fb')]
const grow = t => {{ t.style.height = 'auto'; t.style.height = t.scrollHeight + 2 + 'px' }}
const refresh = () => {{
  const n = boxes.filter(b => b.value.trim()).length
  document.getElementById('count').textContent = n ? `${{n}} note${{n === 1 ? '' : 's'}}` : 'No notes yet'
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
  toast((await copy(`{heading} (${{notes.length}} notes)\\n\\n` + notes.join('\\n\\n') + '\\n')) ? `Copied ${{notes.length}} notes` : 'Copy failed')
}}))
</script></body></html>"""


def main() -> None:
  per, total = spend()
  picks = round_picks()
  keys = json.loads((ROOT / "media" / "variants" / "generative" / "picks.json").read_text())
  cards = []
  for v in VARIANTS:
    shot_boxes = "".join(box(f"{v['id']}-{s}", f"{v['title']} · {s}", f"{s} in this variant: likeness, lip sync, artifacts…") for s in ("S07", "S08"))
    opts = []
    for label, prefix in OPTIONS.get(v["id"], {}).items():
      clip = f"renders/variants/options/{v['id']}-{Path(prefix).name}.mp4"
      if not (ROOT / clip).exists():
        continue
      use = picks[v["id"]]["S08"] == prefix
      fid, flabel = f"opt-{v['id']}-{Path(prefix).name}", f"{v['title']} · S08 option: {label}"
      opts.append(f'<figure class="opt{" use" if use else ""}">{media(clip)}<figcaption><b>{esc(label)}</b>{" · in use" if use else ""}</figcaption>'
                  f'{box(fid, flabel, "Better or worse than the one in use?")}</figure>')
    cards.append(
      f'<section class="variant" id="{v["id"]}"><h2>{esc(v["title"])} <span>test spend ≈ ${per[v["id"]]:.2f}</span></h2>'
      f'<div class="grid2"><div>{media(f"renders/variants/{v["id"]}-s07-s08.mp4")}</div>'
      f'<div><p>{esc(v["how"])}</p><ul>{"".join(f"<li>{esc(n)}</li>" for n in v["notes"])}</ul>'
      f'<p class="dim"><b>Full video:</b> {esc(v["full"])}</p></div></div>'
      f'{box(v["id"], v["title"], "Overall: is this the direction?")}{shot_boxes}'
      + (f'<h3>S08 options</h3><div class="grid3">{"".join(opts)}</div>' if opts else "") + '</section>'
    )
  extras = (
    '<section class="variant"><h2>Behind the variants</h2>'
    '<h3>Character sheets (from the reference photos)</h3><div class="grid3">'
    f'<figure>{media("media/variants/generative/sheet-jensen.png", "img")}<figcaption>Jensen: 3 Wikimedia Commons photos</figcaption></figure>'
    f'<figure>{media("media/variants/generative/sheet-matt-r2.png", "img")}<figcaption>Matt (rev 2): his X avatar + your 2 headshots</figcaption></figure>'
    f'<figure>{media("reference/avatars/poteto.jpg", "img")}<figcaption>poteto: her avatar, for the PRs poster</figcaption></figure></div>'
    '<h3>Keyframes (picked → animated)</h3><div class="grid3">'
    + "".join(f'<figure>{media(keys[s], "img")}<figcaption>{s}: {esc(keys["why"][s])}</figcaption></figure>' for s in ("S07", "S08"))
    + f'</div>{box("behind", "Sheets, keyframes, alternates", "Anything to change in the references or keyframes?")}</section>'
  )
  body = (
    '<p class="sub">Round 3. S07 + S08 (0:00–0:12.8) in each visual direction, all on the approved audio. The original footage is first for reference. '
    f'fal spend so far ≈ ${total:.2f} (call log estimates; the fal dashboard is authoritative) of the ~$80 budget.</p>'
    f'<section class="variant"><h2>0 · Original footage, approved audio</h2><div class="grid2"><div>{media("renders/variants/original-s07-s08.mp4")}</div>'
    '<div><p>No visual change: the reference every variant is measured against.</p></div></div></section>'
    + "".join(cards) + extras
    + f'<div class="general"><label>General</label>{box("general", "General", "Which direction, and why?")}</div>'
  )
  page = render_page("Software Factory Variants", "visual variants, S07 + S08", body, "variants:v3", "Variants review feedback")
  OUT.parent.mkdir(parents=True, exist_ok=True)
  OUT.write_text(page)
  print(OUT.relative_to(ROOT))


if __name__ == "__main__":
  main()

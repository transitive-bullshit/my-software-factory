// Builds the caption layer from captions.json (the one place to edit wording and timing):
//   compositions/captions.html  the caption track: one cue per line, words lit as they are sung (asr-keyword-glow, karaoke)
//   index.html                  preview: the caption track over the generative cut (npm run dev)
//   compositions/overlay.html   the caption track alone on a transparent canvas: what `npm run captions` renders
// All generated: edit captions.json (or the look below), then rebuild.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const data = JSON.parse(readFileSync(join(here, "captions.json"), "utf8"));
const video = resolve(here, "..", data.video);
const duration = Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video]).toString().trim());
const W = 1920, H = 1080;
const comps = join(here, "compositions");

// the plate for preview: the cut itself, linked into the project's assets
mkdirSync(join(here, "assets"), { recursive: true });
const plate = join(here, "assets", "generative.mp4");
if (!existsSync(plate)) symlinkSync(relative(join(here, "assets"), video), plate);

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// shouted orders read in capitals; a file name like AGENTS.md keeps its own case
const shout = (t) => (/[a-z]\.[a-z]/i.test(t) ? t : t.toUpperCase());
const sec = (x) => Number(x.toFixed(3));
// a line too long for one row splits into two rows of near-equal length; a line's "break" (word index) in
// captions.json overrides where, and "break": 0 keeps it on one row
const ROW_CHARS = 50;
const rowBreak = (ln) => {
  if (ln.break !== undefined) return ln.break;
  const len = (ws) => ws.map((w) => w.text).join(" ").length;
  if (len(ln.words) <= ROW_CHARS) return 0;
  let best = 0;
  for (let k = 1; k < ln.words.length; k++) {
    if (!best || Math.abs(len(ln.words.slice(0, k)) - len(ln.words.slice(k))) < Math.abs(len(ln.words.slice(0, best)) - len(ln.words.slice(best)))) best = k;
  }
  return best;
};

const ID = "captions";
const subcomp = () => {
  const timings = {};
  const lines = data.lines.map((ln, i) => {
    const words = ln.words.map((w, j) => {
      const key = `l${i}w${j}`;
      timings[key] = { start: sec(w.start), end: sec(w.end) };
      return `<span class="word" data-word="${key}">${esc(shout(w.text))}</span>`;
    });
    const cut = rowBreak(ln);
    const rows = cut ? [words.slice(0, cut), words.slice(cut)] : [words];
    // a cue per line, all on the one caption track; the shot it falls in is noted for Studio
    return `        <div id="cap-${ln.id}" class="clip caption-line" data-start="${sec(ln.in)}" data-duration="${sec(ln.out - ln.in)}" data-track-index="0" data-track-kind="captions" data-shot="${ln.shot}" data-speaker="${ln.speaker}">
          <div class="band">${rows.map((r) => `<div class="row">${r.join(" ")}</div>`).join("")}</div>
        </div>`;
  });
  const windows = data.lines.map((ln) => ({ id: `cap-${ln.id}`, in: sec(ln.in), out: sec(ln.out) }));
  return `<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
  </head>
  <body>
    <template>
      <style>
        #root {
          position: absolute;
          inset: 0;
          font-family: "Oswald", sans-serif;
        }
        .caption-line {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 78px;
          display: flex;
          justify-content: center;
        }
        .band {
          display: flex;
          flex-direction: column;
          align-items: center;
          max-width: 1640px;
          padding: 14px 40px 18px;
          border-radius: 14px;
          background: rgba(13, 14, 11, 0.66);
          font-weight: 700;
          font-size: 58px;
          line-height: 1.12;
          letter-spacing: 0.02em;
          color: rgb(182, 176, 162);
        }
        .row {
          display: flex;
          justify-content: center;
          align-items: baseline;
          column-gap: 0.4em;
          white-space: nowrap;
        }
        /* the drill instructor's barked one-word orders hit a size up */
        .caption-line[data-speaker="jensen"] .band {
          font-size: 68px;
        }
        .word {
          display: inline-block;
          transform-origin: 50% 60%;
        }
      </style>
      <div id="root" data-composition-id="${ID}" data-width="${W}" data-height="${H}">
${lines.join("\n")}
      </div>
      <script>
        // asr-keyword-glow, karaoke: one linear driver over the whole cut lights each word on its own timing
        const TIMINGS = ${JSON.stringify(timings)};
        const WINDOWS = ${JSON.stringify(windows)};
        const ATTACK = 0.06, RELEASE = 0.2, REST = 0.12, MAX_BLUR = 32, MAX_SCALE = 0.07;
        const REST_RGB = { r: 182, g: 176, b: 162 }, ACTIVE_RGB = { r: 255, g: 196, b: 72 };
        const lerp = (a, b, t) => Math.round(a + (b - a) * t);
        function envelope(t, start, end) {
          if (t < start) return 0;
          if (t < end) return Math.min((t - start) / ATTACK, 1);
          if (t < end + RELEASE) return 1 - ((t - end) / RELEASE) * (1 - REST);
          return REST;
        }
        const tl = gsap.timeline({ paused: true });
        const words = Array.from(document.querySelectorAll('[data-composition-id="${ID}"] .word'));
        const driver = { t: 0 };
        tl.to(driver, {
          t: ${sec(duration)},
          duration: ${sec(duration)},
          ease: "none",
          onUpdate: () => {
            for (const el of words) {
              const w = TIMINGS[el.dataset.word];
              const env = envelope(driver.t, w.start, w.end);
              el.style.color = "rgb(" + lerp(REST_RGB.r, ACTIVE_RGB.r, env) + "," + lerp(REST_RGB.g, ACTIVE_RGB.g, env) + "," + lerp(REST_RGB.b, ACTIVE_RGB.b, env) + ")";
              el.style.textShadow = "0 0 " + (MAX_BLUR * env).toFixed(1) + "px rgba(255, 170, 40, " + (0.85 * env).toFixed(3) + ")";
              el.style.transform = "scale(" + (1 + MAX_SCALE * env * env).toFixed(4) + ")"; // the lift drops faster than the glow
            }
          },
        }, 0);
        // each line's band rises in as the line starts and fades as it hands over
        for (const w of WINDOWS) {
          const band = document.querySelector("#" + w.id + " .band");
          tl.fromTo(band, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.16, ease: "power2.out" }, w.in);
          tl.to(band, { opacity: 0, duration: 0.12, ease: "power1.in" }, Math.max(w.in + 0.16, w.out - 0.12));
        }
        window.__timelines["${ID}"] = tl;
      </script>
    </template>
  </body>
</html>
`;
};

// the caption track: one host for the whole cut, marked as captions
const track = (src) => `    <div
      id="${ID}"
      data-composition-id="${ID}"
      data-composition-src="${src}"
      data-start="0"
      data-duration="${sec(duration)}"
      data-track-index="1"
      data-track-kind="captions"
      data-width="${W}"
      data-height="${H}"
    ></div>`;

const page = (id, background, inner) => `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${W}, height=${H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { margin: 0; width: ${W}px; height: ${H}px; overflow: hidden; background: ${background}; }
      #root { position: relative; width: 100%; height: 100%; }
      #plate { position: absolute; inset: 0; width: 100%; height: 100%; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="${id}" data-start="0" data-duration="${sec(duration)}" data-width="${W}" data-height="${H}" data-fps="30000/1001">
${inner}
    </div>
    <script>
      window.__timelines["${id}"] = gsap.timeline({ paused: true });
    </script>
  </body>
</html>
`;

mkdirSync(comps, { recursive: true });
for (const f of readdirSync(comps)) if (/^captions(-.*)?\.html$/.test(f)) rmSync(join(comps, f));
writeFileSync(join(comps, `${ID}.html`), subcomp());
const plateTag = `    <video id="plate" class="clip" src="assets/generative.mp4" playsinline data-has-audio="true" data-start="0" data-duration="${sec(duration)}" data-track-index="0"></video>`;
writeFileSync(join(here, "index.html"), page("main", "#000", `${plateTag}\n${track(`compositions/${ID}.html`)}`));
// a rendered composition resolves its sources from the project root, wherever it sits
writeFileSync(join(comps, "overlay.html"), page("overlay", "transparent", track(`compositions/${ID}.html`)));
rmSync(join(here, "overlay.html"), { force: true });
console.log(`built ${data.lines.length} caption lines over ${duration.toFixed(3)} s`);

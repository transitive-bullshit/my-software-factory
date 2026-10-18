// Builds the vertical cut's HyperFrames layer from ../../captions/captions.json (the one place to edit wording and
// timing, shared with the 16:9 cut, so the timing is identical):
//   compositions/captions.html  the caption track: one cue per line, words lit as they are sung (the 16:9 look, larger,
//                               wrapped inside the phone safe area)
//   index.html                  preview: the plate (crop.py), the soundtrack, the captions, the title frame and the credits
//   compositions/overlay.html   the same layer alone on a transparent canvas: what `npm run overlay` renders
// The title frame (compositions/title.html) and the credits card (compositions/credits-card.html) are edited directly.
// All else generated: edit captions.json (or the look below), then rebuild.
import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");
const data = JSON.parse(readFileSync(join(root, "captions", "captions.json"), "utf8"));
const probe = (file, entries) => execFileSync("ffprobe", ["-v", "error", "-select_streams", "v:0", "-show_entries", entries, "-of", "csv=p=0", file]).toString().trim();
const cut = resolve(root, data.video); // the 16:9 cut: its frame count sets the length, as for its captions
const FPS = 30000 / 1001;
const frames = Number(probe(cut, "stream=nb_frames"));
const duration = frames / FPS;
// the credits card takes the 16:9 card's frames, the cut's last (scripts/full.py; its 0.8 s crossfade is in the card)
const creditsFrames = Number(probe(join(root, "renders/full/credits.mp4"), "stream=nb_frames"));
const CREDITS = { at: (frames - creditsFrames) / FPS, duration: creditsFrames / FPS };
const plateDuration = Number(probe(join(here, "assets/plate.mp4"), "format=duration"));
const W = 1080, H = 1920;
const comps = join(here, "compositions");
const assets = join(here, "assets");

// the soundtrack for preview (export.py lays the lossless file on the final cut) and the credits' profile pictures
mkdirSync(join(assets, "avatars"), { recursive: true });
const sound = join(assets, "soundtrack.wav");
if (!existsSync(sound)) symlinkSync(relative(assets, join(root, "renders/full/generative-soundtrack.wav")), sound);
const avatars = join(root, "captions/assets/avatars");
for (const f of readdirSync(avatars)) copyFileSync(join(avatars, f), join(assets, "avatars", f));

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// shouted orders read in capitals; a file name like AGENTS.md keeps its own case
const shout = (t) => (/[a-z]\.[a-z]/i.test(t) ? t : t.toUpperCase());
const sec = (x) => Number(x.toFixed(3));
// Where a cue sits: low (on the chest, the band's foot at the bottom of the safe area) unless the speaker's face is low
// in the crop, where it sits high (its head at the top of the safe area). Phone safe area: x 100-900, y 260-1360.
const HIGH = new Set(["S08", "S09", "S10", "S13"]);

const ID = "captions";
const subcomp = () => {
  const timings = {};
  const lines = data.lines.map((ln, i) => {
    const words = ln.words.map((w, j) => {
      const key = `l${i}w${j}`;
      timings[key] = { start: sec(w.start), end: sec(w.end) };
      return `<span class="word" data-word="${key}">${esc(shout(w.text))}</span>`;
    });
    // a cue per line, all on the one caption track; the browser wraps it into balanced rows
    return `        <div id="cap-${ln.id}" class="clip caption-line ${HIGH.has(ln.shot) ? "high" : "low"}" data-start="${sec(ln.in)}" data-duration="${sec(ln.out - ln.in)}" data-track-index="0" data-track-kind="captions" data-shot="${ln.shot}" data-speaker="${ln.speaker}">
          <div class="band">${words.join(" ")}</div>
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
        /* centred in the safe area's width (x 100-900), clear of the platform buttons on the right */
        .caption-line {
          position: absolute;
          left: 100px;
          width: 800px;
          display: flex;
          justify-content: center;
        }
        .caption-line.low {
          bottom: 580px;
        }
        .caption-line.high {
          top: 290px;
        }
        .band {
          max-width: 800px;
          padding: 16px 38px 22px;
          border-radius: 16px;
          background: rgba(13, 14, 11, 0.66);
          font-weight: 700;
          font-size: 64px;
          line-height: 1.12;
          letter-spacing: 0.02em;
          word-spacing: 0.12em;
          text-align: center;
          text-wrap: balance;
          color: rgb(182, 176, 162);
        }
        /* the drill instructor's barked orders hit a size up */
        .caption-line[data-speaker="jensen"] .band {
          font-size: 82px;
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
        // asr-keyword-glow, karaoke (as the 16:9 captions): one linear driver over the whole cut lights each word on its own timing
        const TIMINGS = ${JSON.stringify(timings)};
        const WINDOWS = ${JSON.stringify(windows)};
        const ATTACK = 0.06, RELEASE = 0.2, REST = 0.12, MAX_BLUR = 40, MAX_SCALE = 0.07;
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
          tl.fromTo(band, { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.16, ease: "power2.out" }, w.in);
          tl.to(band, { opacity: 0, duration: 0.12, ease: "power1.in" }, Math.max(w.in + 0.16, w.out - 0.12));
        }
        window.__timelines["${ID}"] = tl;
      </script>
    </template>
  </body>
</html>
`;
};

const host = (id, src, start, dur, track, kind) => `    <div
      id="${id}"
      data-composition-id="${id}"
      data-composition-src="${src}"
      data-start="${sec(start)}"
      data-duration="${sec(dur)}"
      data-track-index="${track}"
      data-track-kind="${kind}"
      data-width="${W}"
      data-height="${H}"
    ></div>`;
// the layer, bottom to top: the title on frame 0 only (a post's preview and cover; nothing after it moves), the credits,
// and the captions over both (the 16:9 cut lays its captions over the credits' crossfade too)
const layer = [
  host("title", "compositions/title.html", 0, 0.02, 2, "graphics"),
  host("credits-card", "compositions/credits-card.html", CREDITS.at, CREDITS.duration, 3, "graphics"),
  host(ID, `compositions/${ID}.html`, 0, duration, 4, "captions"),
].join("\n");

const page = (id, background, inner) => `<!doctype html>
<html lang="en" data-resolution="portrait">
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
writeFileSync(join(comps, `${ID}.html`), subcomp());
const plate = `    <video id="plate" class="clip" src="assets/plate.mp4" playsinline muted data-start="0" data-duration="${sec(plateDuration)}" data-track-index="0"></video>
    <audio id="soundtrack" class="clip" src="assets/soundtrack.wav" data-start="0" data-duration="${sec(duration)}" data-track-index="1"></audio>`;
writeFileSync(join(here, "index.html"), page("main", "#000", `${plate}\n${layer}`));
writeFileSync(join(comps, "overlay.html"), page("overlay", "transparent", layer));
console.log(`built ${data.lines.length} caption lines over ${duration.toFixed(3)} s (${frames} frames); credits from ${CREDITS.at.toFixed(3)} s`);

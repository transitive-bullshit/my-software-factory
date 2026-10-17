// The title frame and poster (compositions/title.html): its background is the first frame of S07 as the cut shows it,
// then one rendered frame -> ../renders/full/title.png (scripts/full.py puts it on the cut's first frame)
// and ../docs/poster.jpg (the README poster). Rerun after S07 changes, then `full.py assemble` and `npm run captions`.
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const ff = (...args) => execFileSync("ffmpeg", ["-v", "error", "-y", ...args], { stdio: "inherit" });

mkdirSync(join(here, "assets"), { recursive: true });
ff("-i", join(root, "renders/full/shots/generative-S07.mp4"), "-frames:v", "1", join(here, "assets/title-bg.png"));

const frames = join(here, "renders/title");
rmSync(frames, { recursive: true, force: true });
execFileSync("npx", ["--yes", "hyperframes@0.8.168", "render", "-c", "compositions/title.html", "--format", "png-sequence", "--fps", "1", "-o", frames, "--quiet"],
  { cwd: here, stdio: "inherit" });

const title = join(root, "renders/full/title.png");
copyFileSync(join(frames, "frame_000001.png"), title);
ff("-i", title, "-vf", "scale=1280:720:flags=lanczos", "-q:v", "3", join(root, "docs/poster.jpg"));
console.log(title);

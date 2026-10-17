// Lays the rendered caption overlay (renders/captions-overlay.mov, transparent ProRes 4444) over the generative cut:
// the footage and its sound are untouched, only the caption layer is added -> ../renders/full/generative-captioned.mp4
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const data = JSON.parse(readFileSync(join(here, "captions.json"), "utf8"));
const video = resolve(here, "..", data.video);
const overlay = join(here, "renders", "captions-overlay.mov");
const out = video.replace(/\.mp4$/, "-captioned.mp4");
execFileSync("ffmpeg", ["-v", "error", "-y", "-i", video, "-i", overlay, "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]",
  "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-c:a", "copy", out], { stdio: "inherit" });
console.log(out);

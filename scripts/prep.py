"""Prepare the source clip for analysis (cached; outputs stay in the ignored /media and /transcript).

1. Decode media/source.mp4 -> media/work/mix.wav (44.1k stereo)
2. Split vocals from the room/effects bed (MelBand RoFormer) -> media/work/stems/
3. Whisper word timestamps on the vocal stem and the full mix -> transcript/whisper-*.json

Run: uv run --group analysis python scripts/prep.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "media" / "source.mp4"
WORK = ROOT / "media" / "work"
STEMS = WORK / "stems"
OUT = ROOT / "transcript"
SEP_MODEL = "vocals_mel_band_roformer.ckpt"


def run_py(code: str) -> None:
  # each heavy model runs in its own process: MLX and torch in one process can deadlock
  subprocess.run([sys.executable, "-c", code], check=True)


def main() -> None:
  WORK.mkdir(parents=True, exist_ok=True)
  STEMS.mkdir(parents=True, exist_ok=True)
  OUT.mkdir(parents=True, exist_ok=True)

  mix = WORK / "mix.wav"
  if not mix.exists():
    subprocess.run(
      ["ffmpeg", "-v", "error", "-y", "-i", str(SRC), "-vn", "-ac", "2", "-ar", "44100", str(mix)],
      check=True,
    )

  vocals = STEMS / "vocals.wav"
  if not vocals.exists():
    run_py(f"""
from audio_separator.separator import Separator
s = Separator(output_dir={str(STEMS)!r}, output_format="WAV")
s.load_model(model_filename={SEP_MODEL!r})
s.separate({str(mix)!r}, custom_output_names={{"Vocals": "vocals", "Other": "bed"}})
""")

  for name, audio in [("vocals", vocals), ("mix", mix)]:
    out = OUT / f"whisper-{name}.json"
    if out.exists():
      continue
    run_py(f"""
import json, mlx_whisper
r = mlx_whisper.transcribe({str(audio)!r}, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                           language="en", word_timestamps=True, condition_on_previous_text=False)
open({str(out)!r}, "w").write(json.dumps(r, indent=1))
""")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
  main()

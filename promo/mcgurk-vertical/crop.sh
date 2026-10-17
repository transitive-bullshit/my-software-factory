#!/bin/sh
# The vertical clips: a full-height 9:16 window (608x1080, centred on the speaker's face at x=990) of each locked wide
# clip, scaled to 1080x1920. The audio is copied untouched, so it stays byte-identical to the wide cut.
set -eu
cd "$(dirname "$0")"
for name in after before rewind; do
  ffmpeg -v error -y -i "../mcgurk/assets/$name.mp4" -vf "crop=608:1080:686:0,scale=1080:1920:flags=lanczos,setsar=1" \
    -c:v libx264 -preset slow -crf 10 -pix_fmt yuv420p -c:a copy -movflags +faststart "assets/$name.mp4"
done

#!/bin/sh
# HyperFrames Studio is for review only: it runs on a copy in promo/.review/<project>, which this overwrites from the
# source of truth (promo/<project>). Anything done in the Studio, undo included, stays in the copy and is discarded on
# the next sync. Starts the Studio on the copy if it isn't running.
#
#   promo/review-sync.sh mcgurk
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
name="${1:-mcgurk}"
src="$here/$name"
dst="$here/.review/$name"
mkdir -p "$dst"
# the copy keeps its own Studio state (.hyperframes, thumbnails); everything else mirrors the source
rsync -a --delete --exclude .hyperframes --exclude .thumbnails --exclude node_modules "$src/" "$dst/"
cd "$dst"
# `preview --status` exits 0 either way, so look for a live server address
if ! npx --yes hyperframes@0.8.168 preview --status 2>/dev/null | grep -Eq '(localhost|127\.0\.0\.1):[0-9]+'; then
  npx --yes hyperframes@0.8.168 preview --background --no-open >/dev/null
fi
npx --yes hyperframes@0.8.168 preview --status 2>/dev/null | grep -Eo 'Studio +http[^ ]+' | awk '{print $2}'

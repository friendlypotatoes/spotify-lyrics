#!/usr/bin/env sh
f="${SPOTIFY_LYRICS_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/spotify-lyrics.txt}"
if [ -r "$f" ]; then
  cat "$f"
else
  printf '%s\n%s' "No readable file:" "$f"
fi

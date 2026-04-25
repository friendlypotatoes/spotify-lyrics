#!/usr/bin/env bash
LYRICS_FILE="$HOME/.local/state/spotify-lyrics.txt"

if [[ -f "$LYRICS_FILE" ]]; then
    # Backward-compat: older versions wrote Pango markup + HTML entities.
    # Eww label is now configured with :text, so strip tags and unescape.
    python3 - "$LYRICS_FILE" <<'PY'
import html, re, sys
path = sys.argv[1]
s = open(path, "r", encoding="utf-8", errors="replace").read()
s = html.unescape(s)
s = re.sub(r"<[^>]+>", "", s)
sys.stdout.write(s.strip() + "\n")
PY
else
    echo '. . .'
fi

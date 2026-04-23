set -eu
EWW_CONFIG="${SPOTIFY_LYRICS_EWW_CONFIG:-$HOME/personal/spotify-lyrics/eww}"
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if eww -c "$EWW_CONFIG" ping 2>/dev/null; then
    exec eww -c "$EWW_CONFIG" open spotify_lyrics_preview
  fi
  sleep 0.4
done
exit 1

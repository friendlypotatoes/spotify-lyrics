# spotify-lyrics

Poll **MPRIS** (via **playerctl**), fetch synced lyrics from **[LRCLIB](https://lrclib.net/docs)**, and display them in an **[eww](https://elkowar.github.io/eww/)** strip (or print to the terminal).

---

## What this does

1. **playerctl** watches Spotify (or any MPRIS player) for track changes
2. On track change, synced lyrics are fetched from **LRCLIB**
3. The active lyric line is written to `~/.local/state/spotify-lyrics.txt`
4. The **eww** widget polls that file and shows track info + lyrics in a top bar

**You need two things running for the eww strip:** the lyrics writer (`main.py`) **and** eww. The widget only reads the file; it does not fetch lyrics itself.

---

## Requirements

| Item | Command to check | Notes |
|------|------------------|-------|
| **Python 3.12+** | `python3 --version` | Matches `requires-python` in `pyproject.toml`. |
| **uv** | `uv --version` | Recommended. Creates `.venv` automatically. |
| **playerctl** | `playerctl --version` | System package. |
| **MPRIS player** | — | Spotify (desktop or Flatpak). Must be **playing or paused**, not stopped. |
| **eww** (optional) | `eww --version` | Only for the bar widget. |
| **Ubuntu font** (optional) | `fc-list \| grep -i ubuntu` | Used in the widget stylesheet. |

---

## Install

```bash
git clone https://github.com/your-username/spotify-lyrics.git
cd spotify-lyrics

# Python deps
curl -LsSf https://astral.sh/uv/install.sh | sh   # if needed
uv sync

# System deps (Debian/Ubuntu)
sudo apt install playerctl fonts-ubuntu

# eww: from your distro or https://github.com/elkowar/eww/releases
```

Fedora: `sudo dnf install playerctl` · Arch: `sudo pacman -S playerctl`

---

## Eww strip (full setup)

Do these steps **in order**.

### 1. Make the poll script executable

```bash
chmod +x eww/scripts/poll-lyrics.sh
```

### 2. Symlink eww config

```bash
# -n: replace ~/.config/eww itself; plain ln -sf would create eww/eww inside the repo
ln -sfn "$PWD/eww" ~/.config/eww
```

This makes `~/.config/eww/scripts/poll-lyrics.sh` and `~/.config/eww/assets/spotify.svg` point at this repo. **Do not skip this** — the widget uses those paths.

If you already ran `ln -sf` and see `eww/eww/eww/...` in the repo, delete the nested link and re-run with `-n`:

```bash
rm -f eww/eww
ln -sfn "$PWD/eww" ~/.config/eww
```

### 3. Start the lyrics writer (keep this running)

```bash
uv run python main.py --player spotify --foreground
```

Or daemonized (no terminal output):

```bash
uv run python main.py --player spotify
```

In daemon mode, lyrics are written to `~/.local/state/spotify-lyrics.txt` automatically.

**Start Spotify and play a track.** Then verify the file is updating:

```bash
cat ~/.local/state/spotify-lyrics.txt
# should show markup with the current lyric line, not stay empty

~/.config/eww/scripts/poll-lyrics.sh
# should print the current lyric as plain text
```

If the file stays at `. . .` or "Waiting for player", Spotify is not visible to playerctl — see [Troubleshooting](#troubleshooting).

### 4. Start eww and open the window

In a **second terminal**:

```bash
eww daemon
eww open spotify_lyrics_preview
```

The strip appears at the **top center** of the screen.

After editing `eww.yuck` or `eww.scss`:

```bash
eww reload
```

---

## Terminal-only mode

No eww, no lyrics file — prints synced lines to stdout:

```bash
uv run python main.py --player spotify --foreground
```

(`--foreground` skips the lyrics file and daemon fork.)

Custom lyrics file path:

```bash
uv run python main.py --player spotify --lyrics-file /path/to/lyrics.txt
```

---

## Start at login

### Lyrics writer (systemd)

```bash
mkdir -p ~/.config/systemd/user
cp contrib/spotify-lyrics-writer.service ~/.config/systemd/user/
# Edit WorkingDirectory= if your clone is not ~/personal/spotify-lyrics
systemctl --user daemon-reload
systemctl --user enable --now spotify-lyrics-writer.service
```

### Eww window (compositor)

Example Hyprland `exec-once`:

```bash
exec-once = ~/personal/spotify-lyrics/contrib/open-eww-lyrics-window.sh
```

The writer must be running **before** eww opens the window.

---

## Troubleshooting

### Widget shows only `. . .` or track name but no lyrics

1. **Is the writer running?** `pgrep -af 'main.py.*spotify'` — if empty, start step 3 above.
2. **Is the file updating?** `cat ~/.local/state/spotify-lyrics.txt` while a track plays.
3. **Did you symlink eww?** `ls -l ~/.config/eww/scripts/poll-lyrics.sh` must point at this repo.
4. **Is Spotify playing?** `playerctl --player=spotify status` should say `Playing` or `Paused`.

### `failed to open window spotify_lyrics_preview`

```bash
eww daemon
eww reload
eww open spotify_lyrics_preview
eww logs    # read errors
```

### `playerctl: command not found`

Install playerctl (see [Install](#install)).

### `No lyrics found` / file has no lyric text

LRCLIB may not have synced lyrics for that track. Check https://lrclib.net manually.

### Text looks wrong

```bash
sudo apt install fonts-ubuntu
```

---

## LRCLIB

Lyrics come from the public **[LRCLIB API](https://lrclib.net/docs)** (`/api/get-cached` then `/api/get`). Track duration from the player should be within about ±2 seconds of the library entry.

---

## License

MIT

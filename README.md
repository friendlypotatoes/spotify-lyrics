# spotify-lyrics

Poll **MPRIS** (via **playerctl**), fetch synced lyrics from **[LRCLIB](https://lrclib.net/docs)**, and either print to the terminal or write **Pango markup** for an **[eww](https://elkowar.github.io/eww/)** strip widget.

---

## Requirements

| Item | Notes |
|------|--------|
| **Python 3.12+** | Matches `requires-python` in `pyproject.toml`. |
| **[uv](https://docs.astral.sh/uv/)** (recommended) | Used to create the project venv and run `main.py`. You can use plain `python3` instead if you install nothing else. |
| **[playerctl](https://github.com/altdesktop/playerctl)** | Talks to Spotify (or any MPRIS player). |
| **MPRIS player** | e.g. Spotify (desktop or Flatpak). Optional: set `PLAYERCTL_PLAYER` or pass `--player spotify`. |
| **Network** | For LRCLIB HTTP requests (no API key). |
| **eww** (optional) | Only if you use the included `eww/` widget. |
| **Ubuntu font** (optional) | Pango markup uses `Ubuntu`; install `fonts-ubuntu` (Debian/Ubuntu) if text looks wrong. |

---

## Install (step-by-step)

### 1. Clone and enter the repo

```bash
git clone <your-remote-url> spotify-lyrics
cd spotify-lyrics
```

### 2. Install a Python toolchain

Using **uv** (creates `.venv` in the project):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if uv is not installed yet
uv sync
```

### 3. Install system packages

Examples for Debian/Ubuntu:

```bash
sudo apt install playerctl fonts-ubuntu
```

Install **eww** from your distro or [upstream releases](https://github.com/elkowar/eww/releases) if you want the bar widget.

### 4. Choose a lyrics file path

`main.py` and `eww/scripts/poll-lyrics.sh` must use the **same** file.

- Default used by the poll script: **`$XDG_STATE_HOME/spotify-lyrics.txt`** (usually `~/.local/state/spotify-lyrics.txt`).
- Override for both: `export SPOTIFY_LYRICS_FILE=/path/to/file.txt`.

### 5. Run the lyrics writer

Foreground (logs on stderr, good for testing):

```bash
uv run python main.py --foreground --player spotify \
  --lyrics-file "${XDG_STATE_HOME:-$HOME/.local/state}/spotify-lyrics.txt"
```

Background-style (detached process; add `--log-file` if you want logs):

```bash
uv run python main.py --player spotify \
  --lyrics-file "${XDG_STATE_HOME:-$HOME/.local/state}/spotify-lyrics.txt"
```

### 6. (Optional) eww widget

1. Make the poll script executable:

   ```bash
   chmod +x eww/scripts/poll-lyrics.sh
   ```

2. Point eww at this config directory (pick one):

   - **Symlink:** `ln -sf "$PWD/eww" ~/.config/eww`
   - **Or** pass **`-c`** every time: `eww -c "$PWD/eww" …`

3. Start the daemon and open the window:

   ```bash
   eww -c "$HOME/personal/spotify-lyrics/eww" daemon
   eww -c "$HOME/personal/spotify-lyrics/eww" open spotify_lyrics_preview
   ```

4. After editing `eww.yuck` / `eww.scss`:

   ```bash
   eww -c "$HOME/personal/spotify-lyrics/eww" reload
   ```

**Hyprland:** if the layer looks opaque, try a layerrule for the window **namespace** in `eww.yuck` (see comment there), e.g. `layerrule = ignorezero, ^(spotify-lyrics-preview)$`, and adjust with `hyprctl layers`.

### 7. (Optional) Start automatically at login

- **Lyrics process:** copy `contrib/spotify-lyrics-writer.service` to `~/.config/systemd/user/`, fix paths if needed, then:

  ```bash
  systemctl --user daemon-reload
  systemctl --user enable --now spotify-lyrics-writer.service
  ```

- **Eww window:** your compositor must already run **`eww daemon`** for the same config. Then run `contrib/open-eww-lyrics-window.sh` once (e.g. Hyprland `exec-once` after the bar starts eww).

---

## LRCLIB

Lyrics are fetched from the public **[LRCLIB API](https://lrclib.net/docs)** (`/api/get-cached` then `/api/get`). Duration from the player should match the library (about ±2 seconds per their docs).

---

## License

Add a license if you publish the repo.

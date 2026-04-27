# spotify-lyrics

Poll **MPRIS** (via **playerctl**), fetch synced lyrics from **[LRCLIB](https://lrclib.net/docs)**, and either print to the terminal or write **Pango markup** for an **[eww](https://elkowar.github.io/eww/)** strip widget.

---

## What this does

1. **playerctl** watches your Spotify (or any MPRIS-compatible player) for track changes
2. When a new track plays, it fetches synced lyrics from **LRCLIB**
3. The lyrics are written to a file (default: `~/.local/state/spotify-lyrics.txt`)
4. If using eww, the widget reads this file and displays lyrics in a strip

---

## Requirements

| Item | Command to check | Notes |
|------|------------------|-------|
| **Python 3.12+** | `python3 --version` | Required. Matches `requires-python` in `pyproject.toml`. |
| **uv** | `uv --version` | Recommended. Creates `.venv` automatically. |
| **playerctl** | `playerctl --version` | Must be installed system-wide. |
| **MPRIS player** | — | Spotify (desktop or Flatpak). |
| **eww** (optional) | `eww --version` | Only if you want the bar widget. |
| **Ubuntu font** (optional) | `fc-list \| grep -i ubuntu` | For correct Pango rendering. |

---

## Install (step-by-step)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/spotify-lyrics.git
cd spotify-lyrics
```

### 2. Install uv and Python dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# This creates .venv and installs dependencies
uv sync
```

### 3. Install system dependencies

**Debian/Ubuntu:**

```bash
sudo apt install playerctl fonts-ubuntu
```

**Fedora:**

```bash
sudo dnf install playerctl
```

**Arch:**

```bash
sudo pacman -S playerctl
```

### 4. Install eww (optional)

From your distro package manager, or download a release from [elkowar/eww](https://github.com/elkowar/eww/releases).

---

## Running the lyrics writer

### Quick start

```bash
# Make executable
chmod +x eww/scripts/poll-lyrics.sh

# Run the main script
uv run python main.py --player spotify
```

This will:
- Poll Spotify for track changes
- Fetch lyrics from LRCLIB when tracks change
- Write lyrics to `~/.local/state/spotify-lyrics.txt`

### With foreground logging (for debugging)

```bash
uv run python main.py --foreground --player spotify
```

### Specify custom file path

```bash
uv run python main.py --player spotify --lyrics-file /path/to/lyrics.txt
```

---

## Running eww widget (optional)

The eww widget reads the lyrics file and displays it in a strip.

### Step 1: Make scripts executable

```bash
chmod +x eww/scripts/poll-lyrics.sh
```

### Step 2: Point eww to the config directory

Choose **one** method:

**Option A: Symlink (recommended)**

```bash
ln -sf "$PWD/eww" ~/.config/eww
```

**Option B: Pass `-c` flag every time**

```bash
eww -c "$PWD/eww" ...
```

### Step 3: Start eww daemon

```bash
eww daemon
```

### Step 4: Open the lyrics window

```bash
eww open spotify_lyrics_preview
```

You should now see the lyrics strip at the bottom of your screen.

### Step 5: Reload after changes

If you edit `eww.yuck` or `eww.scss`:

```bash
eww reload
```

---

## Starting automatically at login

### Option A: Systemd user service (recommended)

1. Copy the service file:

```bash
mkdir -p ~/.config/systemd/user
cp contrib/spotify-lyrics-writer.service ~/.config/systemd/user/
```

2. Edit the service file to fix paths if needed (e.g., adjust `/home/pakpahan/personal/spotify-lyrics` to your actual path).

3. Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now spotify-lyrics-writer.service
```

4. Check status:

```bash
systemctl --user status spotify-lyrics-writer.service
```

### Option B: Shell script in compositor config

Add to your window manager's config (e.g., Hyprland `~/.config/hypr/hyprland.conf`):

```bash
exec-once = ~/personal/spotify-lyrics/contrib/open-eww-lyrics-window.sh
```

Make sure the lyrics writer process is running first.

---

## Troubleshooting

### "playerctl: command not found"

Install playerctl (see Step 3 above).

### "No lyrics found"

LRCLIB may not have lyrics for that track. Try searching manually at https://lrclib.net.

### "eww: command not found"

Install eww from your distro or download from [releases](https://github.com/elkowar/eww/releases).

### eww window not showing

1. Check if eww daemon is running: `eww daemon`
2. Check if the window is open: `eww list-windows`
3. Try opening again: `eww open spotify_lyrics_preview`

### Lyrics not updating

1. Check if the writer process is running: `ps aux | grep main.py`
2. Check the lyrics file: `cat ~/.local/state/spotify-lyrics.txt`
3. Run with `--foreground` to see logs

### Text looks wrong / missing characters

Install the Ubuntu font:

```bash
# Debian/Ubuntu
sudo apt install fonts-ubuntu

# Or manually download and install
```

---

## LRCLIB

Lyrics are fetched from the public **[LRCLIB API](https://lrclib.net/docs)** (`/api/get-cached` then `/api/get`). Duration from the player should match the library (about ±2 seconds per their docs).

---

## License

MIT
#!/usr/bin/env python3
"""
Poll MPRIS via playerctl, fetch synced lyrics from LRCLIB, and print/update the
active line from playback position.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import re
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from subprocess import CompletedProcess, TimeoutExpired, run
from typing import Any

LRCLIB_BASE = "https://lrclib.net"
USER_AGENT = "spotify-lyrics/0.1.0 (https://github.com/local/spotify-lyrics)"

LRC_LINE_RE = re.compile(
    r"^\[(\d+):(\d{2})(?:\.(\d{1,3}))?\]\s*(.*)$",
)


@dataclass(frozen=True)
class LyricLine:
    t: float
    text: str


def run_playerctl(args: list[str], *, timeout: float = 5.0) -> CompletedProcess[str]:
    try:
        return run(
            ["playerctl", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except TimeoutExpired:
        return CompletedProcess(["playerctl", *args], 124, "", "")


def playerctl_str(args: list[str], *, default: str = "") -> str:
    try:
        p = run_playerctl(args)
    except (FileNotFoundError, TimeoutExpired):
        return default
    if p.returncode != 0:
        return default
    return p.stdout.strip()


def playerctl_float(args: list[str], *, default: float | None = None) -> float | None:
    s = playerctl_str(args)
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def get_player_metadata(player: str | None) -> dict[str, Any] | None:
    base = ["--player", player] if player else []
    status = playerctl_str([*base, "status"])
    if not status or status.lower() not in {"playing", "paused"}:
        return None

    # One round-trip: Spotify often stalls on sequential metadata calls.
    sep = "\x1f"
    fmt = "{{title}}" + sep + "{{artist}}" + sep + "{{album}}" + sep + "{{mpris:length}}"
    meta_line = playerctl_str([*base, "metadata", "--format", fmt])
    if sep in meta_line:
        parts = meta_line.split(sep)
        while len(parts) < 4:
            parts.append("")
        title, artist, album, length_us = (p.strip() for p in parts[:4])
    else:
        title = playerctl_str([*base, "metadata", "title"])
        artist = playerctl_str([*base, "metadata", "artist"])
        album = playerctl_str([*base, "metadata", "album"])
        length_us = playerctl_str([*base, "metadata", "mpris:length"])

    if not title and not artist:
        return None

    duration: float | None = None
    if length_us:
        try:
            duration = max(0.0, int(length_us) / 1_000_000)
        except ValueError:
            duration = None

    position = playerctl_float([*base, "position"], default=None)
    if position is None:
        position = 0.0

    return {
        "status": status.lower(),
        "title": title or "Unknown Title",
        "artist": artist or "Unknown Artist",
        "album": album or "Unknown Album",
        "duration": duration,
        "position": max(0.0, position),
        "base": base,
    }


def _http_get_json(path: str, query: dict[str, str | float | int]) -> Any:
    qs = urllib.parse.urlencode(query)
    url = f"{LRCLIB_BASE}{path}?{qs}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def fetch_lrclib_lyrics(
    *,
    track_name: str,
    artist_name: str,
    album_name: str,
    duration: float | None,
    prefer_cached: bool,
) -> tuple[list[LyricLine], dict[str, Any] | None]:
    if duration is None or duration <= 0:
        return [], None

    query = {
        "track_name": track_name,
        "artist_name": artist_name,
        "album_name": album_name,
        "duration": int(round(duration)),
    }
    order = (["/api/get-cached", "/api/get"] if prefer_cached else ["/api/get", "/api/get-cached"])
    last_data: dict[str, Any] | None = None
    for ep in order:
        try:
            data = _http_get_json(ep, query)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        last_data = data if isinstance(data, dict) else None
        synced = data.get("syncedLyrics") if isinstance(data, dict) else None
        if not synced or not isinstance(synced, str):
            continue
        parsed = parse_lrc(synced)
        if parsed:
            return parsed, data if isinstance(data, dict) else None
    return [], last_data


def _fraction_to_seconds(frac: str | None) -> float:
    if not frac:
        return 0.0
    if len(frac) == 2:
        return int(frac) / 100.0
    if len(frac) == 3:
        return int(frac) / 1000.0
    return int(frac) / (10 ** len(frac))


def parse_lrc(text: str) -> list[LyricLine]:
    lines: list[LyricLine] = []
    for raw in text.splitlines():
        m = LRC_LINE_RE.match(raw.strip())
        if not m:
            continue
        mm, ss, frac, lyric = m.groups()
        t = int(mm) * 60 + int(ss) + _fraction_to_seconds(frac)
        if lyric.strip():
            lines.append(LyricLine(t=t, text=lyric.strip()))
    lines.sort(key=lambda x: x.t)
    return lines


def current_lyric_index(lines: list[LyricLine], position: float) -> int | None:
    if not lines:
        return None
    lo, hi = 0, len(lines) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if lines[mid].t <= position:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def render_status(meta: dict[str, Any], idx: int | None, lines: list[LyricLine]) -> str:
    title = meta["title"]
    artist = meta["artist"]
    pos = meta["position"]
    if idx is None or idx < 0:
        lyric = "…"
    else:
        lyric = lines[idx].text
    return f"{artist} — {title} [{pos:0.1f}s]\n{lyric}"


def _esc(s: str) -> str:
    return html.escape(s, quote=False)


def render_eww_markup(
    _meta: dict[str, Any],
    idx: int | None,
    lines: list[LyricLine],
) -> str:
    if not lines:
        return '<span font_desc="Ubuntu Bold 8" foreground="#ffffff">No synced lyrics</span>'
    if idx is None or idx < 0:
        return '<span font_desc="Ubuntu Bold 8" foreground="#ffffff">. . .</span>'
    text = lines[idx].text.replace("\n", " ").strip()
    if not text:
        return '<span font_desc="Ubuntu Bold 8" foreground="#ffffff">. . .</span>'
    if len(text) > 120:
        text = text[:117] + ". . ."
    return f'<span font_desc="Ubuntu Bold 8" foreground="#ffffff">{html.escape(text)}</span>'


def write_atomic(path: str, content: str) -> None:
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def daemonize() -> None:
    if os.fork() > 0:
        raise SystemExit(0)
    os.setsid()
    if os.fork() > 0:
        raise SystemExit(0)
    os.chdir("/")
    sys.stdin.close()
    sys.stdout.flush()
    sys.stderr.flush()
    with open(os.devnull, "rb") as devnull:
        os.dup2(devnull.fileno(), 0)
    with open(os.devnull, "ab") as devnull:
        os.dup2(devnull.fileno(), 1)
        os.dup2(devnull.fileno(), 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="LRCLIB + playerctl synced lyrics daemon")
    parser.add_argument(
        "--foreground",
        "-f",
        action="store_true",
        help="Stay attached to the terminal (no fork, logs to stderr)",
    )
    parser.add_argument(
        "--player",
        default=os.environ.get("PLAYERCTL_PLAYER"),
        help="playerctl --player value (default: env PLAYERCTL_PLAYER or playerctl default)",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=0.25,
        help="Seconds between position/metadata polls (default: 0.25)",
    )
    parser.add_argument(
        "--lyrics-file",
        default="",
        help="If set, atomically write current status + lyric here (useful in daemon mode)",
    )
    parser.add_argument(
        "--no-cache-first",
        action="store_true",
        help="Call /api/get before /api/get-cached (slower, may hit external sources)",
    )
    parser.add_argument(
        "--log-file",
        default="",
        help="Append logs here when daemonized (default: discard)",
    )
    args = parser.parse_args()

    stop = False

    def _stop(*_: Any) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if not args.foreground:
        daemonize()

    if args.foreground:
        logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr, force=True)
    elif args.log_file:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(message)s",
            filename=args.log_file,
            force=True,
        )
    else:
        logging.basicConfig(level=logging.CRITICAL, force=True)

    log = logging.getLogger("spotify-lyrics")

    player = args.player
    prefer_cached = not args.no_cache_first

    last_sig: tuple[Any, ...] | None = None
    lines: list[LyricLine] = []
    last_file_payload: str | None = None
    last_render: str | None = None
    printed_idle_line = False

    while not stop:
        meta = get_player_metadata(player)
        if meta is None:
            lines = []
            last_sig = None
            idle_eww = (
                '<span font_desc="Ubuntu Bold 8" foreground="#ffffff">'
                ". . . ."
                "</span>"
            )
            if args.lyrics_file:
                if idle_eww != last_file_payload:
                    write_atomic(args.lyrics_file, idle_eww)
                    last_file_payload = idle_eww
            elif args.foreground:
                if last_render is not None:
                    sys.stdout.write("\033[2A\033[J")
                    last_render = None
                sys.stdout.write("\r\x1b[2KWaiting for player…")
                sys.stdout.flush()
                printed_idle_line = True
            time.sleep(max(0.05, args.poll))
            continue

        sig = (meta["title"], meta["artist"], meta["album"], meta["duration"])
        if sig != last_sig:
            last_sig = sig
            try:
                lines, info = fetch_lrclib_lyrics(
                    track_name=meta["title"],
                    artist_name=meta["artist"],
                    album_name=meta["album"],
                    duration=meta["duration"],
                    prefer_cached=prefer_cached,
                )
            except Exception as e:
                log.info("LRCLIB error for %s — %s: %s", meta["artist"], meta["title"], e)
                lines = []
                info = None

            if lines:
                log.info("Loaded %d synced lines for %s — %s", len(lines), meta["artist"], meta["title"])
            elif info and info.get("instrumental"):
                log.info("Instrumental / no text: %s — %s", meta["artist"], meta["title"])
            else:
                log.info("No synced lyrics: %s — %s", meta["artist"], meta["title"])

        pos = meta["position"]
        idx = current_lyric_index(lines, pos) if lines else None

        if args.lyrics_file:
            msg = render_eww_markup(meta, idx, lines)
            if msg != last_file_payload:
                write_atomic(args.lyrics_file, msg)
                last_file_payload = msg
        elif args.foreground:
            out = render_status(meta, idx, lines)
            if out != last_render:
                if printed_idle_line:
                    sys.stdout.write("\r\x1b[2K\n")
                    printed_idle_line = False
                if last_render is not None:
                    sys.stdout.write("\033[2A\033[J")
                sys.stdout.write(out + "\n")
                sys.stdout.flush()
                last_render = out

        time.sleep(max(0.05, args.poll))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)

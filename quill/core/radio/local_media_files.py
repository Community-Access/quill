"""Files in, playlists out: finding media on disk, and M3U/PLS both ways.

The other half of :mod:`quill.core.radio.local_media`. That module is the shelf;
this one is the door -- walking a folder for playable files in the order a
person reads them, and reading or writing the playlist files every other media
player understands.

**Why not Import Stations' parsers.** :mod:`quill.core.radio.playlist_import`
reads M3U and PLS too, but for *stations*: it keeps only ``http`` addresses and
drops everything else, which is exactly right for a station list and exactly
wrong here, where every line worth keeping is a file path -- often a relative
one, written by Winamp or foobar2000 next to the music it names.

**Relative paths are written when they can be.** An M3U saved inside the music
folder names its tracks relative to itself, so the folder can be moved or
copied to another computer with the playlist still working. A track on another
drive is written in full, because no relative path can reach it.

wx-free, strict-typed, no network.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from quill.core.radio.local_media import Playlist, is_media_file, path_key
from quill.core.radio.natural_order import natural_key

__all__ = [
    "IMPORT_WILDCARD",
    "PlaylistEntry",
    "export_m3u",
    "find_media_files",
    "name_for_files",
    "parse_playlist_text",
    "read_playlist_file",
]

#: The Import Playlist picker.
IMPORT_WILDCARD = (
    "Playlists (*.m3u;*.m3u8;*.pls)|*.m3u;*.m3u8;*.pls"
    "|M3U playlist (*.m3u;*.m3u8)|*.m3u;*.m3u8"
    "|PLS playlist (*.pls)|*.pls"
    "|All files (*.*)|*.*"
)

#: The Export picker: M3U8 first, because UTF-8 keeps every accented title.
EXPORT_WILDCARD = "M3U8 playlist (*.m3u8)|*.m3u8|M3U playlist (*.m3u)|*.m3u"


# --- finding files ---------------------------------------------------------------


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def find_media_files(
    paths: Sequence[Path | str],
    *,
    recursive: bool = True,
    should_stop: Callable[[], bool] | None = None,
) -> list[Path]:
    """Every playable file in *paths*, folders opened, in reading order.

    A file named directly is kept in the order given; a folder contributes its
    files sorted the way a person reads them (track 2 before track 10), then its
    subfolders in the same order, so an album folder of discs plays disc one
    first. Unreadable folders are skipped rather than failing the whole add.
    """
    found: list[Path] = []
    seen: set[str] = set()

    def _keep(candidate: Path) -> None:
        key = path_key(str(candidate))
        if key not in seen and is_media_file(candidate):
            seen.add(key)
            found.append(candidate)

    def _walk(folder: Path) -> None:
        if should_stop is not None and should_stop():
            return
        try:
            children = list(folder.iterdir())
        except OSError:
            return
        for child in sorted((c for c in children if _is_file(c)), key=_name_key):
            _keep(child)
        if recursive:
            for child in sorted((c for c in children if _is_dir(c)), key=_name_key):
                _walk(child)

    for raw in paths:
        path = Path(raw)
        if _is_dir(path):
            _walk(path)
        elif _is_file(path):
            _keep(path)
    return found


def _name_key(path: Path) -> tuple[object, ...]:
    return natural_key(path.name)


def new_files_in(playlist: Playlist, *, recursive: bool = True) -> list[Path]:
    """Files in the playlist's folder that the playlist does not hold yet.

    What keeps a folder playlist in step with the folder: run when the playlist
    is opened, so music copied in since last time is simply there.
    """
    if not playlist.folder:
        return []
    known = playlist.paths()
    return [
        path
        for path in find_media_files([playlist.folder], recursive=recursive)
        if path_key(str(path)) not in known
    ]


def name_for_files(paths: Sequence[Path | str]) -> str:
    """A name for a playlist made from *paths*: their shared folder's name.

    Twelve tracks from ``D:\\Music\\Abbey Road`` make a playlist called "Abbey
    Road" -- which is what anybody would have typed. Files from all over fall
    back to "My Playlist".
    """
    parents = {str(Path(p).parent) for p in paths}
    if len(parents) == 1:
        name = Path(next(iter(parents))).name
        if name:
            return name
    return "My Playlist"


# --- reading playlist files -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlaylistEntry:
    """One line of an imported playlist that names a file."""

    path: str
    title: str = ""
    duration_seconds: int = 0


def _resolve(line: str, base_dir: Path) -> str:
    """A playlist line as an absolute path, or "" when it is not a local file."""
    text = line.strip().strip('"')
    if not text:
        return ""
    lowered = text.lower()
    if lowered.startswith("file:"):
        parsed = urlparse(text)
        local = unquote(parsed.path)
        if parsed.netloc:  # file://server/share/x.mp3
            local = f"//{parsed.netloc}{local}"
        elif len(local) > 2 and local[0] == "/" and local[2] == ":":  # /C:/Music
            local = local[1:]
        return str(Path(local))
    if "://" in text:
        return ""  # a stream address: Import Stations is where those go
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return os.path.normpath(str(candidate))


def _extinf(line: str) -> tuple[int, str]:
    """``#EXTINF:187,Artist - Title`` -> ``(187, "Artist - Title")``."""
    _, _, rest = line.partition(":")
    length, _, title = rest.partition(",")
    try:
        seconds = int(float(length.strip().split(" ")[0]))
    except ValueError:
        seconds = 0
    return max(0, seconds), title.strip()


def _numbered(key: str, prefix: str) -> int:
    """``"File3"`` -> 3 for prefix ``"file"``; 0 when the key is not that field."""
    lowered = key.strip().lower()
    number = lowered[len(prefix) :]
    return int(number) if lowered.startswith(prefix) and number.isdigit() else 0


def _parse_pls(text: str, base_dir: Path) -> tuple[list[PlaylistEntry], int]:
    files: dict[int, str] = {}
    titles: dict[int, str] = {}
    lengths: dict[int, int] = {}
    for raw in text.splitlines():
        key, sep, value = raw.strip().partition("=")
        if not sep:
            continue
        if number := _numbered(key, "file"):
            files[number] = value.strip()
        elif number := _numbered(key, "title"):
            titles[number] = value.strip()
        elif number := _numbered(key, "length"):
            try:
                lengths[number] = max(0, int(value.strip()))
            except ValueError:
                lengths[number] = 0
    entries: list[PlaylistEntry] = []
    skipped = 0
    for number in sorted(files):
        path = _resolve(files[number], base_dir)
        if not path:
            skipped += 1
            continue
        entries.append(PlaylistEntry(path, titles.get(number, ""), lengths.get(number, 0)))
    return entries, skipped


def parse_playlist_text(
    text: str, *, base_dir: Path, filename: str = ""
) -> tuple[list[PlaylistEntry], int]:
    """The file entries in an M3U, M3U8 or PLS playlist, and how many were not.

    Returns ``(entries, skipped)``. *skipped* counts lines that named something
    other than a local file -- stream addresses, mostly -- so the importer can
    say how many it left out rather than leave the listener counting.
    """
    if filename.lower().endswith(".pls") or text.lstrip().lower().startswith("[playlist]"):
        return _parse_pls(text, base_dir)
    entries: list[PlaylistEntry] = []
    skipped = 0
    pending: tuple[int, str] = (0, "")
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.upper().startswith("#EXTINF"):
            pending = _extinf(line)
            continue
        if line.startswith("#"):
            continue
        path = _resolve(line, base_dir)
        if path:
            entries.append(PlaylistEntry(path, pending[1], pending[0]))
        else:
            skipped += 1
        pending = (0, "")
    return entries, skipped


def read_playlist_file(path: Path) -> tuple[list[PlaylistEntry], int]:
    """Read and parse a playlist file. Raises ``OSError`` if it cannot be read.

    UTF-8 first (every ``.m3u8``, and most modern ``.m3u``); a file that is not
    valid UTF-8 is an older Windows player's, written in the system code page.
    """
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    return parse_playlist_text(text, base_dir=path.parent, filename=path.name)


# --- writing them ------------------------------------------------------------------


def _relative_or_absolute(item_path: str, playlist_dir: Path | None) -> str:
    if playlist_dir is None:
        return item_path
    try:
        relative = os.path.relpath(item_path, playlist_dir)
    except ValueError:  # another drive: no relative path reaches it
        return item_path
    return item_path if relative.startswith("..") else relative


def export_m3u(playlist: Playlist, *, playlist_dir: Path | None = None) -> str:
    """The playlist as extended M3U text, readable by any media player.

    ``#EXTINF`` carries the length and "Artist - Title", the form Winamp wrote
    and everything since reads. *playlist_dir* is where the file will be saved:
    tracks under it are written relative to it, so the folder travels.
    """
    lines = ["#EXTM3U", f"#PLAYLIST:{' '.join(playlist.name.split())}"]
    for item in playlist.items:
        label = item.display_title
        if item.artist:
            label = f"{item.artist} - {label}"
        seconds = item.duration_seconds if item.duration_seconds > 0 else -1
        lines.append(f"#EXTINF:{seconds},{' '.join(label.split())}")
        lines.append(_relative_or_absolute(item.path, playlist_dir))
    return "\n".join(lines) + "\n"

"""Folder feeds: every master in a folder becomes a podcast episode.

The single-book feed (``rss.py``) covers "publish this audiobook". This module
covers running a whole show from one folder: each chaptered master found in
the folder is an episode (title from its tags, duration probed when ffprobe is
available, chapters linked via the ``…chapters.json`` sidecar, pubDate from the
file's modification time), with the show settings and per-episode descriptions
persisted in ``<folder>/.quill/feed.json`` so the feed can be regenerated on
demand after every new build. Also writes an accessible HTML show-notes page
next to the feed. Local file IO only — uploading stays the SFTP destination's
explicit job. wx-free, strict-typed.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quill.core.publish.rss import FeedItem, rfc2822, write_rss
from quill.core.speech.ffmpeg import AudioMetadata
from quill.core.storage import write_json_atomic

#: Same project folder the speech profile uses (``.quill/speech-project.json``).
FEED_DIRNAME = ".quill"
FEED_FILENAME = "feed.json"
#: Master formats a folder feed treats as episodes.
EPISODE_SUFFIXES = {".mp3", ".m4b", ".m4a"}


@dataclass(slots=True)
class EpisodeConfig:
    """Per-episode overrides, keyed by filename in :class:`FeedFolderConfig`."""

    title: str = ""
    description: str = ""


@dataclass(slots=True)
class FeedFolderConfig:
    """The show: everything needed to regenerate the folder's feed on demand."""

    title: str = ""
    author: str = ""
    description: str = ""
    media_base: str = ""
    feed_url: str = ""
    cover_url: str = ""
    episodes: dict[str, EpisodeConfig] = field(default_factory=dict)

    def episode(self, filename: str) -> EpisodeConfig:
        """The (created-on-demand) overrides for *filename*."""
        if filename not in self.episodes:
            self.episodes[filename] = EpisodeConfig()
        return self.episodes[filename]


def _config_path(folder: Path) -> Path:
    return folder / FEED_DIRNAME / FEED_FILENAME


def load_feed_config(folder: Path) -> FeedFolderConfig:
    """The folder's saved show settings (defaults when absent or junk)."""
    path = _config_path(folder)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return FeedFolderConfig()
    if not isinstance(data, dict):
        return FeedFolderConfig()
    episodes: dict[str, EpisodeConfig] = {}
    raw_episodes = data.get("episodes")
    if isinstance(raw_episodes, dict):
        for name, entry in raw_episodes.items():
            if isinstance(entry, dict):
                episodes[str(name)] = EpisodeConfig(
                    title=str(entry.get("title", "")),
                    description=str(entry.get("description", "")),
                )
    return FeedFolderConfig(
        title=str(data.get("title", "")),
        author=str(data.get("author", "")),
        description=str(data.get("description", "")),
        media_base=str(data.get("media_base", "")),
        feed_url=str(data.get("feed_url", "")),
        cover_url=str(data.get("cover_url", "")),
        episodes=episodes,
    )


def save_feed_config(folder: Path, config: FeedFolderConfig) -> Path:
    """Persist *config* atomically to ``<folder>/.quill/feed.json``."""
    path = _config_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        path,
        {
            "title": config.title,
            "author": config.author,
            "description": config.description,
            "media_base": config.media_base,
            "feed_url": config.feed_url,
            "cover_url": config.cover_url,
            "episodes": {
                name: {"title": e.title, "description": e.description}
                for name, e in sorted(config.episodes.items())
                if e.title or e.description
            },
        },
    )
    return path


def discover_masters(folder: Path) -> list[Path]:
    """The folder's episode masters, oldest first (episode 1 = oldest file)."""
    masters = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EPISODE_SUFFIXES]
    return sorted(masters, key=lambda p: (p.stat().st_mtime, p.name.lower()))


def _episode_title(path: Path, config: FeedFolderConfig) -> str:
    override = config.episodes.get(path.name)
    if override is not None and override.title:
        return override.title
    try:
        from quill.core.speech.book_file import read_book

        tags = read_book(path).tags
        return tags.title or tags.album or path.stem
    except Exception:  # noqa: BLE001 - a tagless file is still an episode
        return path.stem


def _episode_duration_s(path: Path) -> int:
    try:
        from quill.core.speech.ffmpeg import probe_duration_ms

        return max(0, probe_duration_ms(path) // 1000)
    except Exception:  # noqa: BLE001 - no ffprobe = no duration, not no feed
        return 0


def folder_feed_items(folder: Path, config: FeedFolderConfig) -> list[FeedItem]:
    """One :class:`FeedItem` per master in *folder*, oldest first."""
    base = config.media_base.strip().rstrip("/")
    items: list[FeedItem] = []
    for path in discover_masters(folder):
        override = config.episodes.get(path.name)
        items.append(
            FeedItem(
                path=path,
                media_url=f"{base}/{path.name}" if base else path.name,
                title=_episode_title(path, config),
                description=override.description if override is not None else "",
                duration_s=_episode_duration_s(path),
                has_chapters=path.with_suffix(".chapters.json").is_file(),
                pub_date=rfc2822(datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)),
            )
        )
    return items


def feed_tags(config: FeedFolderConfig, folder: Path) -> AudioMetadata:
    """The channel-level tags the show settings imply."""
    return AudioMetadata(
        album=config.title or folder.name,
        artist=config.author,
        comment=config.description,
    )


def write_folder_feed(folder: Path, config: FeedFolderConfig) -> tuple[Path, int]:
    """(Re)generate ``<folder>/feed.rss`` from the masters currently present.

    Returns the written path and the episode count. Raises :class:`ValueError`
    when the folder holds no masters (an empty feed is a mistake, not a show).
    """
    items = folder_feed_items(folder, config)
    if not items:
        raise ValueError("No MP3, M4B, or M4A masters were found in that folder.")
    written = write_rss(
        items,
        feed_tags(config, folder),
        folder / "feed.rss",
        feed_url=config.feed_url,
        description=config.description,
        cover_url=config.cover_url,
    )
    return written, len(items)


def _chapter_list_html(path: Path) -> str:
    """An ordered list of the episode's chapters (from its Pod-2.0 sidecar)."""
    sidecar = path.with_suffix(".chapters.json")
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    chapters = data.get("chapters") if isinstance(data, dict) else None
    if not isinstance(chapters, list) or not chapters:
        return ""
    rows: list[str] = []
    for entry in chapters:
        if not isinstance(entry, dict):
            continue
        start = entry.get("startTime")
        seconds = int(float(start)) if isinstance(start, (int, float)) else 0
        stamp = f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"
        title = html.escape(str(entry.get("title") or ""))
        url = str(entry.get("url") or "")
        if url:
            title = f'<a href="{html.escape(url, quote=True)}">{title}</a>'
        rows.append(f"      <li>{stamp} — {title}</li>")
    if not rows:
        return ""
    return "    <ol>\n" + "\n".join(rows) + "\n    </ol>\n"


def write_show_notes(folder: Path, config: FeedFolderConfig) -> Path:
    """An accessible HTML show-notes page next to the feed.

    Semantic headings only (h1 show, h2 per episode), plain lists for
    chapters, no scripts or styling requirements — readable in any browser
    and navigable by heading with a screen reader.
    """
    items = folder_feed_items(folder, config)
    show = html.escape(config.title or folder.name)
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>{show} — Show Notes</title>",
        "</head>",
        "<body>",
        f"  <h1>{show}</h1>",
    ]
    if config.description:
        lines.append(f"  <p>{html.escape(config.description)}</p>")
    for index, item in enumerate(items, start=1):
        lines.append(f"  <h2>Episode {index}: {html.escape(item.title)}</h2>")
        if item.description:
            lines.append(f"  <p>{html.escape(item.description)}</p>")
        meta: list[str] = []
        if item.duration_s:
            meta.append(f"Duration {item.duration_s // 60} min {item.duration_s % 60} s")
        if item.pub_date:
            meta.append(f"Published {html.escape(item.pub_date)}")
        if meta:
            lines.append(f"  <p>{' · '.join(meta)}</p>")
        listen = html.escape(item.media_url, quote=True)
        lines.append(f'  <p><a href="{listen}">Listen ({html.escape(item.path.name)})</a></p>')
        chapter_html = _chapter_list_html(item.path)
        if chapter_html:
            lines.append("  <h3>Chapters</h3>")
            lines.append(chapter_html.rstrip("\n"))
    lines += ["</body>", "</html>", ""]
    target = folder / "show-notes.html"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target

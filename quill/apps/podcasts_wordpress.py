"""QUILL Cast's door to WordPress: Post This Episode (wordpress.md 15 item 9).

An adapter with no WordPress code of its own. It turns the selected episode
into the shared :class:`~quill.core.wordpress.episode.Episode` -- its downloaded
file, its show notes, its chapters, and the transcript Cast already cached --
and hands it to :func:`quill.ui.wordpress_family.post_episode`, which is the same
code QUILL and QUILL Lite run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.wordpress.episode import Chapter, Episode


def cast_episode(show: Any, episode: Any) -> Episode:
    """What Cast knows about one episode, in the shared shape."""
    raw_path = str(getattr(episode, "downloaded_path", "") or "")
    path = Path(raw_path) if raw_path else None
    notes = str(getattr(episode, "description", "") or "")
    return Episode(
        title=str(getattr(episode, "title", "") or "Untitled episode"),
        audio_path=path,
        show_notes=notes,
        chapters=_chapters(path, notes, int(getattr(episode, "duration_seconds", 0) or 0)),
        transcript=_transcript(show, episode),
        podcast=str(getattr(show, "title", "") or ""),
        audio_url=str(getattr(episode, "audio_url", "") or ""),
    )


def _chapters(path: Path | None, notes: str, seconds: int) -> tuple[Chapter, ...]:
    from quill.core.podcasts.chapter_sources import (
        parse_show_notes_chapters,
        read_file_chapters,
    )

    found: list[Any] = []
    if path is not None and path.is_file():
        try:
            found = list(read_file_chapters(path))
        except Exception:  # noqa: BLE001 - a file with unreadable tags still posts
            found = []
    if not found and notes:
        found = list(parse_show_notes_chapters(notes, total_ms=seconds * 1000))
    return tuple(Chapter(c.start_ms / 1000.0, str(c.title)) for c in found)


def _transcript(show: Any, episode: Any) -> str:
    from quill.core.podcasts.transcripts import load_cached_transcript

    try:
        return load_cached_transcript(str(show.id), str(episode.guid))
    except Exception:  # noqa: BLE001 - no cached transcript is the same as none
        return ""


def post_selected_episode(app: Any) -> None:
    """Episode > Post This Episode to WordPress."""
    from quill.ui import wordpress_family as fam

    selected = app._selected_episode()
    fam.post_episode(app, cast_episode(*selected) if selected else None)

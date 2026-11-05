"""Posts made from a file: an episode with its player, or a document as a page.

Two shapes the family apps and the editors share (wordpress.md 9.6, 15 item 9):

* **Post This Episode** (QUILL Cast, QUILL Studio): an audio player, the show
  notes, the chapters as a list with their times, and the transcript folded
  into a Details block so it does not swamp the page.
* **Also Publish as a Page**: a converted PDF or Word file, with a link back to
  the original in the library, said plainly with its type and size.

Both come out as Markdown plus the islands that hold the blocks Markdown has no
words for (the audio player), which is exactly the shape a WordPress document
opened in QUILL or QUILL Lite has (:mod:`quill.core.wordpress.fences`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.wordpress import listening as ls
from quill.core.wordpress.site import human_size

TRANSCRIPT_SUMMARY = "Read the transcript"


@dataclass(frozen=True)
class Chapter:
    start: float
    title: str


@dataclass(frozen=True)
class Episode:
    """What a family app knows about one episode, handed to the shared code."""

    title: str
    audio_path: Path | None = None
    show_notes: str = ""
    chapters: tuple[Chapter, ...] = ()
    transcript: str = ""
    podcast: str = ""
    #: Where the episode already lives online, when there is no local file.
    audio_url: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def clock(seconds: float) -> str:
    total = int(max(0.0, seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def notes_markdown(notes: str) -> str:
    """Show notes as Markdown: HTML from a feed is converted, plain text is kept."""
    text = notes.strip()
    if not text:
        return ""
    if re.search(r"<[a-zA-Z][^>]*>", text):
        from quill.core.html_to_markdown import html_to_markdown

        return html_to_markdown(text).strip()
    return text


def episode_post(episode: Episode, *, media_id: int, src: str) -> tuple[str, dict[str, str]]:
    """The post's Markdown and islands: player, show notes, chapters, transcript."""
    islands = {"episode-player-1": ls.audio_block(media_id, src)}
    parts = [ls.island_fence("core/audio", "episode-player-1", "player")]
    notes = notes_markdown(episode.show_notes)
    if notes:
        parts.append(notes)
    if episode.chapters:
        rows = [f"- {clock(c.start)} {c.title.strip() or 'Untitled'}" for c in episode.chapters]
        parts.append("## Chapters\n\n" + "\n".join(rows))
    if episode.transcript.strip():
        parts.append(ls.details_markdown(TRANSCRIPT_SUMMARY, episode.transcript))
    return "\n\n".join(parts) + "\n", islands


def document_page(text: str, *, file_name: str, src: str, size: int) -> str:
    """A converted document's Markdown, with a plain link to the original first."""
    kind = Path(file_name).suffix.lstrip(".").upper() or "file"
    if kind in {"DOC", "DOCX"}:
        kind = "Word"
    size_text = f", {human_size(size)}" if size else ""
    link = f"[Download the original {kind} document{size_text}]({src})"
    body = text.strip()
    return f"{link}\n\n{body}\n" if body else f"{link}\n"


def title_from_file(name: str) -> str:
    stem = Path(name).stem
    words = re.sub(r"[_\-]+", " ", stem).strip()
    return words[:1].upper() + words[1:] if words else "Untitled"

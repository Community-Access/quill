"""Work handed to the family's editor, saying where it came from (FUX-02).

Quill Cast and Quill Radio read transcripts and show notes; QUILL is where
somebody keeps them. Until 2026-11-24 the standalone apps' "Open in QUILL" and
"Send to Editor" put the text on the clipboard and said "Show notes copied to
clipboard", even for a transcript, and Radio's button was dimmed for good. The
journey the pilots chose (Cast, a saved place, then QUILL; see
``docs/design/2026-11-19-family-ux-pilots.md`` section 3) needs the opposite:
the words arrive in QUILL as a document that names the episode, the show, the
app and the moment, with the cursor on the line you were reading.

This is the pure half. :mod:`quill.ui.editor_handoff` writes the file and opens
it through the family's own launcher; nothing here is a new kind of handoff.

The plan's three kinds of handoff, told apart:

* **A reference** -- a path to a file that already exists, handed to another
  app (Scribe's Next Steps, a WordPress draft). Nothing is copied.
* **A copy** -- what this module makes: the text becomes a new Markdown file in
  the app's folder in Documents, named after what it is. The original (the
  feed, the cached transcript) is untouched.
* **A transformed output** -- Scribe and Converter results, in their own
  output folders.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

#: How many "name (n).md" to try before giving up on a readable name.
_MAX_NAMES = 500


def destination(folder: Path, filename: str, content: str) -> Path:
    """Where *content* is written as *filename* in *folder*.

    Sending the same thing twice reopens the first copy rather than making a
    second. A different document under the same name -- another show's
    "Episode 1", or this transcript after you edited your copy -- gets
    ``name (2).md``: nothing anybody wrote is ever written over.
    """
    stem, suffix = Path(filename).stem, Path(filename).suffix
    for number in range(1, _MAX_NAMES + 1):
        candidate = folder / (filename if number == 1 else f"{stem} ({number}){suffix}")
        try:
            if not candidate.exists():
                return candidate
            if candidate.read_text(encoding="utf-8") == content:
                return candidate
        except (OSError, UnicodeDecodeError):
            continue
    raise OSError(f"Too many documents called {filename} in {folder}.")


def origin_sentence(source_app: str, *, at: str = "") -> str:
    """The line that says where a transcript came from, and the way back."""
    moment = f" at {at} in the audio" if at else ""
    return (
        f"Sent from {source_app}{moment}. To hear any line again, play it in "
        f"{source_app}, open its transcript and press Enter on that line."
    )


def bookmark_lines(bookmarks: Sequence[tuple[int, str]]) -> list[str]:
    """Your bookmarks in this episode, by time, with their notes, then the
    Transcript heading -- always there, so heading navigation reaches it."""
    from quill.core.podcasts.transcript_export import timestamp

    lines: list[str] = []
    if bookmarks:
        lines = ["## Your bookmarks", ""]
        for position_ms, note in sorted(bookmarks, key=lambda row: row[0]):
            words = " ".join(str(note or "").split())
            lines.append(f"- {timestamp(position_ms)}{f': {words}' if words else ''}")
        lines.append("")
    return [*lines, "## Transcript", ""]


def transcript_document(
    cues: Sequence[Any],
    *,
    caret_index: int = -1,
    source_app: str,
    bookmarks: Sequence[tuple[int, str]] = (),
    **markdown: Any,
) -> tuple[str, int | None]:
    """The transcript as a QUILL document, and the line the cursor goes to.

    *markdown* is :func:`~quill.core.podcasts.transcript_export.cues_to_markdown`'s
    own keywords (detail, show, episode, source URL, automatic), so the
    document has the shape Save As gives it, the person's chosen detail
    included. The line is that of the cue at *caret_index* (1-based), or
    ``None`` when the caret is on no line.
    """
    from quill.core.podcasts import transcript_export

    at = ""
    if 0 <= caret_index < len(cues) and str(getattr(cues[caret_index], "text", "")).strip():
        at = transcript_export.timestamp(getattr(cues[caret_index], "start_ms", 0))
    preface = [origin_sentence(source_app, at=at), "", *bookmark_lines(bookmarks)]
    text = transcript_export.cues_to_markdown(cues, preface=preface, **markdown)
    if not at:
        return text, None
    # A cue can hold a line break (a two-line caption), so count the lines
    # each one really takes rather than assuming one per cue.
    detail = transcript_export.normalize_detail(markdown.get("detail"))
    heights = [
        row.count("\n") + 1 if row else 0
        for row in (transcript_export.cue_line(cue, detail) for cue in cues)
    ]
    first_body_line = len(text.splitlines()) - sum(heights) + 1
    return text, first_body_line + sum(heights[:caret_index])


def text_document(text: str, *, kind: str, title: str, show: str, source_app: str) -> str:
    """Plain text (show notes, a transcript) as a QUILL document that names
    the episode, the show and the app it came from."""
    lines = [f"# {title.strip() or kind.capitalize()}", ""]
    if show.strip():
        lines.extend([f"*{show.strip()}*", ""])
    lines.extend([f"{kind.capitalize()}, from {source_app}.", "", text.strip()])
    return "\n".join(lines).rstrip() + "\n"


def document_filename(*, kind: str, title: str, show: str) -> str:
    """``Show - Episode.md`` for a transcript (as Save As names it), and
    ``Show - Episode show notes.md`` for the notes."""
    from quill.core.podcasts.transcript_export import safe_filename

    episode = title if kind == "transcript" else f"{title} {kind}".strip()
    return safe_filename(show, episode)


__all__ = [
    "bookmark_lines",
    "destination",
    "document_filename",
    "origin_sentence",
    "text_document",
    "transcript_document",
]

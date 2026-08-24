"""A transcript on its way out of QUILL: Markdown, and how much of it to keep.

The reader could already save plain text, WebVTT and SubRip. Those are the
formats another *player* wants. Markdown is the format a **person** wants: it
opens in anything, it keeps the speakers as text rather than as a subtitle
convention, and it is what somebody quoting an episode in an email, a document
or a blog post is going to paste.

**Why the detail is a choice and not a fixed shape.** A transcript has two
kinds of scaffolding, and which of them is useful depends entirely on what the
transcript is for:

* **Speakers** matter when the point is *who said it* -- an interview, a panel,
  a court recording.
* **Timestamps** matter when the point is *where it is* -- citing a moment,
  making a clip, checking a quotation against the audio.
* **Both** is right for study notes, and **neither** is right when what you
  want is simply the words, which is far more often than a subtitle format
  admits.

So the export offers all four, the choice is remembered once
(``PodcastSettings.transcript_detail``) and shared by every surface that
exports -- Quill Radio's reader and QUILL Cast's alike, because a transcript
saved from one app and a transcript saved from the other should not come out
differently shaped.

Everything here is pure: no wx, no filesystem, no clock. The writers take cues
and return a string, which is what makes them testable against fixtures rather
than against a dialog.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

#: The four shapes an exported transcript can take, and how each is offered.
#: The ids are stored, so they are stable; the labels are read aloud.
SPEAKERS = "speakers"
TIMESTAMPS = "timestamps"
BOTH = "both"
PLAIN = "plain"

DETAIL_CHOICES: tuple[tuple[str, str], ...] = (
    (SPEAKERS, "Speakers only"),
    (TIMESTAMPS, "Timestamps only"),
    (BOTH, "Speakers and timestamps"),
    (PLAIN, "Just the words"),
)

#: What a new installation gets. Speakers, because a transcript that has them
#: is nearly always a conversation, and a conversation with the speakers
#: stripped out is a wall nobody can read.
DEFAULT_DETAIL = SPEAKERS

_VALID = {choice for choice, _label in DETAIL_CHOICES}

#: Windows forbids these in a file name; the rest of the world tolerates them
#: but a transcript called ``Show: Episode?.md`` helps nobody either.
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def normalize_detail(value: object) -> str:
    """A stored setting as a valid detail id (pure). Junk reads as the default.

    Same rule the rest of the settings follow: a file with a typo in it should
    behave like a file with nothing in it.
    """
    return value if isinstance(value, str) and value in _VALID else DEFAULT_DETAIL


def detail_label(value: object) -> str:
    """The display label for a stored detail id."""
    wanted = normalize_detail(value)
    for choice, label in DETAIL_CHOICES:
        if choice == wanted:
            return label
    return DETAIL_CHOICES[0][1]


def detail_index(value: object) -> int:
    """Which row of :data:`DETAIL_CHOICES` a stored id is (pure)."""
    wanted = normalize_detail(value)
    for position, (choice, _label) in enumerate(DETAIL_CHOICES):
        if choice == wanted:
            return position
    return 0


def detail_from_index(position: object) -> str:
    """The id at *position*, or the default. Total for a wx selection."""
    if not isinstance(position, int) or not 0 <= position < len(DETAIL_CHOICES):
        return DEFAULT_DETAIL
    return DETAIL_CHOICES[position][0]


def timestamp(ms: object) -> str:
    """``1:02:03`` or ``2:03`` from milliseconds (pure).

    The written form, not the spoken one: this goes in a file, beside other
    words, where a colon is unambiguous. Anything that speaks a position uses
    ``speak_duration`` instead -- read aloud, "2:03" is a guess.
    """
    if isinstance(ms, bool) or not isinstance(ms, (int, float)):
        return "0:00"
    total = max(0, int(ms)) // 1000
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def safe_filename(show: str, episode: str, *, extension: str = "md") -> str:
    """``Show - Episode.md``, safe on every filesystem (pure).

    Named after what it is rather than after an id, because the file lands in
    somebody's Downloads folder among a hundred others and has to be
    recognisable there a month later.
    """
    parts = [part.strip() for part in (show, episode) if str(part or "").strip()]
    stem = " - ".join(parts) or "Transcript"
    stem = _UNSAFE.sub("", stem).strip().strip(".")
    stem = re.sub(r"\s+", " ", stem)
    # Long enough for a real title, short of every filesystem's own ceiling
    # once a path is in front of it.
    if len(stem) > 120:
        stem = stem[:120].rstrip()
    return f"{stem or 'Transcript'}.{extension}"


def _line(cue: Any, detail: str) -> str:
    """One cue as one Markdown line (pure)."""
    text = str(getattr(cue, "text", "") or "").strip()
    if not text:
        return ""
    speaker = str(getattr(cue, "speaker", "") or "").strip()
    stamp = timestamp(getattr(cue, "start_ms", 0))
    want_speaker = detail in (SPEAKERS, BOTH) and bool(speaker)
    want_stamp = detail in (TIMESTAMPS, BOTH)
    if want_speaker and want_stamp:
        return f"**{speaker}** ({stamp}): {text}"
    if want_speaker:
        return f"**{speaker}:** {text}"
    if want_stamp:
        return f"({stamp}) {text}"
    return text


def cues_to_markdown(
    cues: Sequence[Any],
    *,
    detail: str = DEFAULT_DETAIL,
    show: str = "",
    episode: str = "",
    source_url: str = "",
    is_automatic: bool = False,
) -> str:
    """*cues* as a Markdown document (pure).

    The heading names the episode and the show, because a transcript in a
    folder with no heading is a wall of speech nobody can place. An automatic
    transcript **says so in the file**, not only in the window it was read in:
    the file outlives the window, and a machine transcript passed on as a human
    one is a confident wrong answer arriving somewhere nobody can check it.
    """
    wanted = normalize_detail(detail)
    lines: list[str] = []
    title = str(episode or "").strip()
    heading = title or "Transcript"
    lines.append(f"# {heading}")
    lines.append("")
    subtitle = [part for part in (str(show or "").strip(),) if part]
    if subtitle:
        lines.append(f"*{subtitle[0]}*")
        lines.append("")
    if is_automatic:
        lines.append(
            "> These are automatic captions, machine-generated from the audio, so expect mistakes."
        )
        lines.append("")
    if source_url:
        lines.append(f"Source: {source_url}")
        lines.append("")
    body = [_line(cue, wanted) for cue in cues]
    lines.extend(line for line in body if line)
    return "\n".join(lines).rstrip() + "\n"

"""Chapter-list import and export: Audacity labels, CUE, timestamps, JSON, CSV.

wx-free, strict-typed. Ported from ChapterForge (``s:\\code99\\forum``, MIT) and
re-based on QUILL's :class:`~quill.core.speech.chapters.Chapter`. Producers are
pure text functions (the caller writes the file); the parser auto-detects the
format, tolerates junk lines, and always returns contiguous chapters tiling
``[0, total_ms]`` so an imported plan is immediately valid for a build.

Formats:

- **Audacity labels** — ``start<TAB>end<TAB>title`` in seconds, one per line.
- **Timestamps** — ``H:MM:SS<TAB>Title`` lines (show-notes style; a leading
  ``-`` after the time is tolerated on import).
- **CUE sheet** — ``TRACK``/``TITLE``/``INDEX 01 MM:SS:FF`` (75 frames/second).
- **Podcasting 2.0 JSON** — ``{"version": "1.2.0", "chapters": [{startTime,
  title, url?, img?}]}`` (the ``…chapters.json`` sidecar format).
- **CSV** — export only: number, title, start, duration.
"""

from __future__ import annotations

import csv
import io
import json
import re

from quill.core.speech.chapters import Chapter

#: Export formats accepted by :func:`export_chapter_text`.
EXPORT_FORMATS: tuple[str, ...] = ("audacity", "timestamps", "cue", "pod2", "csv")

POD2_VERSION = "1.2.0"


class ChapterParseError(ValueError):
    """The text contained no usable chapter markers."""


def format_timestamp(ms: int) -> str:
    """Format milliseconds as ``H:MM:SS`` (or ``M:SS`` under an hour)."""
    total_seconds = int(round(ms / 1000))
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _ts_to_ms(token: str) -> int | None:
    """Parse ``M:SS``, ``H:MM:SS`` (optionally fractional) into ms, else None."""
    token = token.strip()
    if not re.match(r"^\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$", token):
        return None
    try:
        nums = [float(p) for p in token.split(":")]
    except ValueError:
        return None
    if len(nums) == 2:
        secs = nums[0] * 60 + nums[1]
    else:
        secs = nums[0] * 3600 + nums[1] * 60 + nums[2]
    return int(round(secs * 1000))


# --------------------------------------------------------------------------- export


def chapters_to_audacity(chapters: list[Chapter]) -> str:
    """Audacity label track: ``start<TAB>end<TAB>title`` (seconds)."""
    return (
        "\n".join(
            f"{c.start_ms / 1000.0:.6f}\t{c.end_ms / 1000.0:.6f}\t{c.title}" for c in chapters
        )
        + "\n"
    )


def chapters_to_timestamps(chapters: list[Chapter]) -> str:
    """Simple ``H:MM:SS<TAB>Title`` lines (e.g. for show notes)."""
    return "".join(f"{format_timestamp(c.start_ms)}\t{c.title}\n" for c in chapters)


def _ms_to_cue(ms: int) -> str:
    """CUE index time ``MM:SS:FF`` (FF = 1/75-second frames)."""
    total_frames = int(round(ms / 1000.0 * 75))
    minutes, rem = divmod(total_frames, 75 * 60)
    seconds, frames = divmod(rem, 75)
    return f"{minutes:02d}:{seconds:02d}:{frames:02d}"


def chapters_to_cue(
    chapters: list[Chapter],
    audio_filename: str,
    *,
    performer: str = "",
    album: str = "",
) -> str:
    """A CUE sheet naming *audio_filename*, one TRACK per chapter."""
    lines: list[str] = []
    if performer:
        lines.append(f'PERFORMER "{performer}"')
    if album:
        lines.append(f'TITLE "{album}"')
    lines.append(f'FILE "{audio_filename}" MP3')
    for i, c in enumerate(chapters, start=1):
        lines.append(f"  TRACK {i:02d} AUDIO")
        lines.append(f'    TITLE "{c.title}"')
        if performer:
            lines.append(f'    PERFORMER "{performer}"')
        lines.append(f"    INDEX 01 {_ms_to_cue(c.start_ms)}")
    return "\n".join(lines) + "\n"


def chapters_to_pod2(chapters: list[Chapter]) -> str:
    """Podcasting 2.0 chapters JSON (the ``…chapters.json`` sidecar body).

    Per-chapter ``url`` and ``img`` ride along when set, so a link or image
    attached to a chapter survives export, import, and re-export.
    """
    entries: list[dict[str, object]] = []
    for c in chapters:
        entry: dict[str, object] = {"startTime": round(c.start_ms / 1000.0, 3), "title": c.title}
        if c.url:
            entry["url"] = c.url
        if c.image:
            entry["img"] = c.image
        entries.append(entry)
    data = {"version": POD2_VERSION, "chapters": entries}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def chapters_to_csv(chapters: list[Chapter]) -> str:
    """CSV export: number, title, start, duration (human-readable times)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["#", "Title", "Start", "Duration"])
    for i, c in enumerate(chapters, start=1):
        writer.writerow([i, c.title, format_timestamp(c.start_ms), format_timestamp(c.duration_ms)])
    return buf.getvalue()


def export_chapter_text(
    chapters: list[Chapter],
    fmt: str,
    *,
    audio_filename: str = "",
    performer: str = "",
    album: str = "",
) -> str:
    """Render *chapters* as *fmt* (one of :data:`EXPORT_FORMATS`); pure text."""
    fmt = fmt.strip().lower()
    if fmt == "audacity":
        return chapters_to_audacity(chapters)
    if fmt == "timestamps":
        return chapters_to_timestamps(chapters)
    if fmt == "cue":
        return chapters_to_cue(chapters, audio_filename, performer=performer, album=album)
    if fmt == "pod2":
        return chapters_to_pod2(chapters)
    if fmt == "csv":
        return chapters_to_csv(chapters)
    raise ValueError(f"Unknown chapter export format: {fmt!r}")


def suggested_extension(fmt: str) -> str:
    """The natural file extension for an export format."""
    return {
        "audacity": ".txt",
        "timestamps": ".txt",
        "cue": ".cue",
        "pod2": ".chapters.json",
        "csv": ".csv",
    }.get(fmt.strip().lower(), ".txt")


# --------------------------------------------------------------------------- import


def titles_from_text(text: str) -> list[str]:
    """Extract just the chapter *titles* from any chapter-list text, in order.

    Used by the pre-build plan editor, where chapter boundaries come from the
    source files and only the names can usefully be imported. Accepts the same
    formats as :func:`parse_chapter_text` plus plain one-title-per-line text;
    comment lines (``#``/``;``) and blank lines are skipped.
    """
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return [title for _ms, title in _parse_pod2_pairs(text)]
    lines = text.splitlines()
    if any("INDEX 01" in line.upper() for line in lines):
        return [title for _ms, title in _parse_cue_pairs(lines)]
    csv_titles = _titles_from_csv(text)
    if csv_titles:
        return csv_titles
    titles: list[str] = []
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith((";", "#")):
            continue
        cols = s.split("\t")
        if len(cols) >= 3 and _is_float(cols[0]) and _is_float(cols[1]):
            titles.append(cols[2].strip() or f"Chapter {len(titles) + 1}")
            continue
        match = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*(.*)", s)
        if match:
            title = match.group(2).strip().lstrip("- ").strip()
            titles.append(title or f"Chapter {len(titles) + 1}")
            continue
        titles.append(s)
    return titles


def _titles_from_csv(text: str) -> list[str]:
    """Titles from CSV text, or ``[]`` when the text does not look like CSV.

    A header row naming a ``Title`` column selects that column (the shape our
    own CSV export writes); without one, a numeric first column selects the
    second column, so a hand-made ``track,title`` sheet also works. Single-
    column text is not treated as CSV — the plain-line parser handles it.
    """
    rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
    if not rows or max(len(row) for row in rows) < 2:
        return []
    header = [cell.strip().lower() for cell in rows[0]]
    if "title" in header:
        column = header.index("title")
        body = rows[1:]
    elif rows[0][0].strip().isdigit():
        column = 1
        body = rows
    else:
        return []
    titles: list[str] = []
    for row in body:
        cell = row[column].strip() if column < len(row) else ""
        titles.append(cell or f"Chapter {len(titles) + 1}")
    return titles


def _parse_cue_pairs(lines: list[str]) -> list[tuple[int, str]]:
    pairs: list[tuple[int, str]] = []
    title = ""
    for raw in lines:
        s = raw.strip()
        upper = s.upper()
        if upper.startswith("TITLE "):
            title = s[6:].strip().strip('"')
        elif upper.startswith("INDEX 01"):
            token = s.split()[-1]
            parts = token.split(":")
            if len(parts) == 3:
                try:
                    mm, ss, ff = (int(p) for p in parts)
                except ValueError:
                    continue
                ms = int(round((mm * 60 + ss + ff / 75.0) * 1000))
                pairs.append((ms, title or f"Chapter {len(pairs) + 1}"))
                title = ""
    return pairs


def _parse_pod2_pairs(text: str) -> list[tuple[int, str]]:
    return [(ms, title) for ms, title, _url, _img in _parse_pod2_entries(text)]


def _parse_pod2_entries(text: str) -> list[tuple[int, str, str, str]]:
    """Podcasting 2.0 entries as ``(ms, title, url, img)`` tuples."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    entries = data.get("chapters") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    parsed: list[tuple[int, str, str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        start = entry.get("startTime")
        if not isinstance(start, (int, float)):
            continue
        title = str(entry.get("title") or f"Chapter {len(parsed) + 1}")
        parsed.append((
            int(round(float(start) * 1000)),
            title,
            str(entry.get("url") or ""),
            str(entry.get("img") or ""),
        ))
    return parsed


def _is_float(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def parse_chapter_text(text: str, total_ms: int) -> list[Chapter]:
    """Parse chapter markers out of *text*, auto-detecting the format.

    Accepts Audacity labels, CUE sheets, plain timestamp lines, and Podcasting
    2.0 chapters JSON. Markers at or beyond *total_ms* are dropped; a missing
    0:00 marker is added; duplicates keep the first title. The result is
    contiguous chapters tiling ``[0, total_ms]``. Raises
    :class:`ChapterParseError` when nothing usable is found.
    """
    if total_ms <= 0:
        raise ChapterParseError("The target file has no known duration.")
    stripped = text.lstrip()
    lines = text.splitlines()
    pairs: list[tuple[int, str]] = []
    extras_by_start: dict[int, tuple[str, str]] = {}
    if stripped.startswith("{"):
        entries = _parse_pod2_entries(text)
        pairs = [(ms, title) for ms, title, _u, _i in entries]
        extras_by_start = {ms: (url, img) for ms, _t, url, img in entries if url or img}
    elif any("INDEX 01" in line.upper() for line in lines):
        pairs = _parse_cue_pairs(lines)
    else:
        for raw in lines:
            s = raw.strip()
            if not s or s.startswith((";", "#")):
                continue
            cols = s.split("\t")
            if len(cols) >= 3 and _is_float(cols[0]) and _is_float(cols[1]):
                # Audacity label row: start<TAB>end<TAB>title (seconds).
                pairs.append((
                    int(round(float(cols[0]) * 1000)),
                    cols[2].strip() or f"Chapter {len(pairs) + 1}",
                ))
                continue
            match = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*(.*)", s)
            if match:
                ms = _ts_to_ms(match.group(1))
                if ms is not None:
                    title = match.group(2).strip().lstrip("- ").strip()
                    pairs.append((ms, title or f"Chapter {len(pairs) + 1}"))

    pairs = [(ms, title) for ms, title in pairs if 0 <= ms < total_ms]
    if not pairs:
        raise ChapterParseError("No chapter markers were found in that file.")

    title_by_start: dict[int, str] = {}
    for ms, title in pairs:
        title_by_start.setdefault(ms, title)
    starts = sorted(title_by_start)
    if starts[0] != 0:
        starts.insert(0, 0)
        title_by_start.setdefault(0, "Chapter 1")
    chapters: list[Chapter] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else total_ms
        if end <= start:
            continue
        url, img = extras_by_start.get(start, ("", ""))
        chapters.append(
            Chapter(
                index=len(chapters),
                title=title_by_start.get(start, f"Chapter {i + 1}"),
                start_ms=start,
                end_ms=end,
                url=url,
                image=img,
            )
        )
    return chapters

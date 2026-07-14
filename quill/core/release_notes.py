"""Abbreviated, per-release "What's New" notes sourced from ``CHANGELOG.md``.

The changelog is the single source of truth. This module slices out a single
version's section and flattens it to plain text suitable for a read-only
multi-line ``TextCtrl`` (the same control help text and wizards use), so the
Check-for-Updates dialog and the Help > What's New command can show users a
short, screen-reader-friendly summary of what a release contains.

Pure domain logic: no ``wx`` imports, safe to call from unit tests and from
the release pipeline (``scripts/extract_release_body.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

from quill.core.text_utils import strip_md_to_plain

_HEADING = re.compile(r"^##\s+(?P<title>.+?)\s*$")
_BASE_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")


def _canon(value: str) -> str:
    """Canonical comparison form for a version string or heading title.

    Drops a trailing ``(...)`` annotation and a leading ``v``, lower-cases,
    treats ``-``/``_`` as spaces, splits letter/digit runs (``beta1`` ->
    ``beta 1``), and collapses whitespace. This makes a git tag
    (``v0.8.0-beta1``), the running build's short version (``0.8.0 Beta 1``),
    and the changelog heading (``0.8.0 Beta 1 (in development)``) all canonical
    to ``0.8.0 beta 1``.
    """
    text = value.split("(", 1)[0].strip().lower()
    if text.startswith("v"):
        text = text[1:]
    text = re.sub(r"[-_]", " ", text)
    text = re.sub(r"(?<=[a-z])(?=\d)", " ", text)
    text = re.sub(r"(?<=\d)(?=[a-z])", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _base_version(value: str) -> str:
    """The ``major.minor[.patch]`` core of a version string, or ``""``."""
    match = _BASE_VERSION.search(value)
    return match.group(0) if match else ""


def _find_section_start(lines: list[str], version: str) -> int | None:
    """Index of the ``## `` heading naming ``version``, or ``None``.

    An exact (canonicalized) match always wins, so ``0.8.0 Beta 1`` resolves to
    its own section even when a newer ``0.8.0 Beta 2`` section sits above it.
    Only when no exact match exists does a bare ``major.minor.patch`` prefix
    match the newest section sharing that core version.
    """
    target = _canon(version)
    base = _base_version(target)
    headings: list[tuple[int, str]] = [
        (index, _canon(match.group("title")))
        for index, line in enumerate(lines)
        if (match := _HEADING.match(line))
    ]
    for index, head in headings:
        if head == target:
            return index
    if base:
        for index, head in headings:
            if head.startswith(base):
                return index
    return None


def extract_version_section(changelog_text: str, version: str) -> str:
    """Return the body of the ``## <version>`` section, heading line excluded.

    Everything from just after the matching ``## `` heading up to (but not
    including) the next ``## `` heading is returned, trimmed. Returns ``""``
    when no section matches ``version``.
    """
    lines = changelog_text.splitlines()
    start = _find_section_start(lines, version)
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        if _HEADING.match(line):
            break
        body.append(line)
    return "\n".join(body).strip()


def find_changelog() -> Path | None:
    """Locate ``CHANGELOG.md`` in a packaged build or a dev checkout.

    Frozen builds stage a copy beside the package root (``quill/CHANGELOG.md``);
    development checkouts keep it at the repository root. The first existing
    candidate wins.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "CHANGELOG.md",  # quill/CHANGELOG.md (packaged build)
        here.parents[2] / "CHANGELOG.md",  # repository root (dev checkout)
        here.parents[3] / "CHANGELOG.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_changelog_text() -> str:
    """Read the bundled/checked-out changelog, or ``""`` when unavailable."""
    path = find_changelog()
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def release_notes_for(version: str) -> str:
    """Plain-text "What's New" for ``version``, flattened from the changelog.

    Returns ``""`` when the changelog is missing or has no matching section so
    callers can fall back to their own message.
    """
    section = extract_version_section(load_changelog_text(), version)
    return strip_md_to_plain(section) if section else ""


def current_release_notes() -> str:
    """Plain-text "What's New" for the running build's version."""
    from quill import build_info

    return release_notes_for(build_info.get_short_version())


__all__ = [
    "current_release_notes",
    "extract_version_section",
    "find_changelog",
    "load_changelog_text",
    "release_notes_for",
]

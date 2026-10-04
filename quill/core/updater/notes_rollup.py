"""Stable release notes rolled up from the Beta sections before them (plan 4.5).

A Stable build's notes say what changed since the previous *Stable* one, but
the changelog is written a Beta at a time. :func:`rollup` merges every section
after ``--from`` up to and including ``--to`` into one "What's new since X"
section:

* the subsections (``### Added``, ``### Fixed`` ...) are merged by name, oldest
  Beta first, so each heading appears once;
* a line marked ``[beta-only]`` -- "fixed a bug introduced in Beta 1" -- is
  dropped, with the lines indented under it, because nobody on Stable ever
  had that bug;
* each Beta's "Known rough edges" list is dropped: it described a Beta;
* **"Before you update"** goes at the top whenever a data format moved
  between the two builds, in the words :func:`~quill.core.updater.going_back.format_words`
  uses, because once the newer build has saved, going back means restoring a
  copy.

:func:`notes_summary` turns the same text into the feed's plain-text summary
(at most 4000 characters, ``update_notice.MAX_NOTE_CHARS``), so the GitHub
release, the feed and the update window never say different things.

Changelog headings may be ``## [3.3.0] - 2026-10-20``,
``## 3.3.0-beta.2 (Beta) - 2026-10-03`` or ``## 1.0.0 Beta 1``: anything
:class:`~quill.core.versioning.ReleaseVersion` can read.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from quill.core.versioning import ReleaseVersion, sort_key

__all__ = [
    "BETA_ONLY",
    "Rollup",
    "moved_formats",
    "notes_summary",
    "parse_sections",
    "rollup",
]

BETA_ONLY = "[beta-only]"
_SECTION = re.compile(r"^##\s+(?P<title>.+?)\s*$")
_SUBSECTION = re.compile(r"^###\s+(?P<title>.+?)\s*$")
_DROPPED_SUBSECTIONS = ("known rough edges",)
_SUMMARY_LIMIT = 4000


def _heading_version(title: str) -> str:
    """``3.3.0-beta.2`` from ``[3.3.0-beta.2] - 2026-10-03`` or ``1.0.0 Beta 1 (Beta)``."""
    text = title.split("(", 1)[0]
    text = re.split(r"\s+-\s+", text, maxsplit=1)[0]
    text = text.strip().strip("[]").strip()
    parsed = ReleaseVersion.try_parse(text)
    return parsed.semver().partition("+")[0] if parsed is not None else ""


def parse_sections(changelog: str) -> list[tuple[str, str]]:
    """``(version, body)`` for every ``## <version>`` section, in file order."""
    sections: list[tuple[str, list[str]]] = []
    inside = False
    for line in changelog.splitlines():
        match = _SECTION.match(line)
        if match:
            version = _heading_version(match.group("title"))
            inside = bool(version)
            if inside:
                sections.append((version, []))
            continue
        if inside:
            sections[-1][1].append(line)
    return [(v, "\n".join(body).strip()) for v, body in sections]


def _drop_beta_only(lines: list[str]) -> list[str]:
    kept: list[str] = []
    skipping_indent: int | None = None
    for line in lines:
        indent = len(line) - len(line.lstrip())
        if skipping_indent is not None:
            if line.strip() and indent > skipping_indent:
                continue
            skipping_indent = None
        if BETA_ONLY in line.lower():
            skipping_indent = indent
            continue
        kept.append(line)
    return kept


def _tidy(lines: list[str]) -> list[str]:
    """No leading, trailing or doubled blank lines."""
    out: list[str] = []
    for line in lines:
        if not line.strip() and (not out or not out[-1].strip()):
            continue
        out.append(line.rstrip())
    while out and not out[-1].strip():
        out.pop()
    return out


def moved_formats(before: Mapping[str, int], after: Mapping[str, int]) -> list[str]:
    """Format ids *after* writes at a version *before* cannot read."""
    return [f for f, v in sorted(after.items()) if v > before.get(f, 0)]


@dataclass(frozen=True)
class Rollup:
    app_name: str
    from_version: str
    to_version: str
    #: The versions whose sections were merged, oldest first.
    merged: tuple[str, ...]
    #: Format ids that moved, for "Before you update".
    moved: tuple[str, ...] = ()
    #: The merged subsections, in first-seen order: ``("", intro lines)`` first.
    parts: tuple[tuple[str, tuple[str, ...]], ...] = field(default_factory=tuple)

    @property
    def heading(self) -> str:
        return (
            f"What's new since {_shown(self.from_version)}" if self.from_version else ("What's new")
        )

    def before_you_update(self) -> str:
        if not self.moved:
            return ""
        from quill.core.updater.going_back import format_words

        back = (
            f"going back to {_shown(self.from_version)} means restoring a copy"
            if self.from_version
            else "going back to an older version means restoring a copy"
        )
        return (
            f"This version saves your {format_words(self.moved)} in a newer way. "
            f"Once you update, {back}."
        )

    def markdown(self) -> str:
        lines = [f"## {self.heading}", ""]
        warning = self.before_you_update()
        if warning:
            lines += ["### Before you update", "", warning, ""]
        for title, body in self.parts:
            if title:
                lines += [f"### {title}", ""]
            lines += [*body, ""]
        return "\n".join(_tidy(lines)) + "\n"


def _shown(version: str) -> str:
    parsed = ReleaseVersion.try_parse(version)
    # Release notes talk about the release ("3.2.0"), never one build of it.
    return parsed.display(with_build=False) if parsed is not None else version


def rollup(
    changelog: str,
    *,
    app_name: str,
    from_version: str,
    to_version: str,
    formats_before: Mapping[str, int] | None = None,
    formats_after: Mapping[str, int] | None = None,
) -> Rollup:
    """Merge every section after *from_version*, up to *to_version*.

    An empty *from_version* means "since the newest final-numbered section
    below *to_version*" (the previous Stable), or every section when there is
    none. *formats_before* is the older build's ``reads_formats``;
    *formats_after* the newer build's ``data_formats``. Without both, nothing
    is said about formats.
    """
    target = sort_key(to_version)
    sections = parse_sections(changelog)
    floor = from_version
    if not floor:
        finals = [
            v
            for v, _ in sections
            if sort_key(v) < target
            and (p := ReleaseVersion.try_parse(v)) is not None
            and p.stage == "final"
        ]
        floor = max(finals, key=sort_key, default="")
    chosen = [
        (v, body)
        for v, body in sections
        if sort_key(v) <= target and (not floor or sort_key(v) > sort_key(floor))
    ]
    chosen.sort(key=lambda pair: sort_key(pair[0]))
    order: list[str] = []
    merged: dict[str, list[str]] = {}
    for _version, body in chosen:
        title = ""
        for line in _drop_beta_only(body.splitlines()):
            match = _SUBSECTION.match(line)
            if match:
                title = match.group("title").strip()
                continue
            if title.lower() in _DROPPED_SUBSECTIONS:
                continue
            key = title
            if key not in merged:
                merged[key] = []
                order.append(key)
            merged[key].append(line)
    parts = tuple(
        (key, tuple(_tidy(merged[key])))
        for key in sorted(order, key=lambda k: (k != "", order.index(k)))
        if _tidy(merged[key])
    )
    moved: tuple[str, ...] = ()
    if formats_before is not None and formats_after is not None:
        moved = tuple(moved_formats(formats_before, formats_after))
    return Rollup(
        app_name=app_name,
        from_version=floor,
        to_version=to_version,
        merged=tuple(v for v, _ in chosen),
        moved=moved,
        parts=parts,
    )


def notes_summary(markdown: str, limit: int = _SUMMARY_LIMIT) -> str:
    """The feed's plain-text ``notes_summary`` from the rolled-up markdown."""
    from quill.core.text_utils import strip_md_to_plain

    text = strip_md_to_plain(markdown).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip() + "..."

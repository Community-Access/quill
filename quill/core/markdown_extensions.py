"""Deterministic Markdown structure tools (issue #257).

QUILL's only table-of-contents generator used to be the AI agent profile in
``assistant_agents.py`` (``agent_id="toc"``), which sends the document to a
language model. That is useful, but it means a screen-reader user with AI
disabled — or simply working offline, or wanting a result that is guaranteed
to match the headings exactly — had no way to get a table of contents at all.

This module is the non-AI alternative: ``generate_toc`` builds a table of
contents purely by parsing ATX (``#``) headings, with no network call and no
model in the loop. It is deterministic, so the same document always produces
the same TOC, and it is wired into the ``core.markdown_profiles`` feature
(category ``"markdown"``), not ``future.ai``.

The slug algorithm mirrors :func:`quill.core.browser_preview._slugify` so a
generated TOC's links match the heading ``id`` attributes the preview
renderer already produces.

No ``wx`` imports; pure data and string processing, fully unit-tested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def slugify(value: str) -> str:
    """Slugify a heading title the same way the preview renderer does."""
    normalized = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return normalized or "section"


@dataclass(frozen=True, slots=True)
class Heading:
    line: int  # 1-based
    level: int  # 1-6
    title: str
    slug: str  # de-duplicated, stable within one document


def extract_headings(text: str) -> list[Heading]:
    """Return every ATX heading in *text*, in document order, with unique slugs."""
    seen: dict[str, int] = {}
    headings: list[Heading] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = _HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        base_slug = slugify(title)
        count = seen.get(base_slug, 0)
        seen[base_slug] = count + 1
        slug = base_slug if count == 0 else f"{base_slug}-{count + 1}"
        headings.append(Heading(line=line_no, level=level, title=title, slug=slug))
    return headings


@dataclass(frozen=True, slots=True)
class MarkdownDiagnostic:
    severity: str  # "info" | "warning"
    message: str
    line: int = 0


def check_heading_structure(text: str) -> list[MarkdownDiagnostic]:
    """Phase-1 accessibility checks for heading structure (PRD #257 section 14.3)."""
    headings = extract_headings(text)
    diagnostics: list[MarkdownDiagnostic] = []
    if not headings:
        return diagnostics
    if headings[0].level != 1:
        diagnostics.append(
            MarkdownDiagnostic(
                "warning",
                f"Document starts with a level {headings[0].level} heading "
                "instead of a level 1 heading.",
                headings[0].line,
            )
        )
    previous_level = headings[0].level
    for heading in headings[1:]:
        if heading.level > previous_level + 1:
            diagnostics.append(
                MarkdownDiagnostic(
                    "warning",
                    f"Heading level skipped from {previous_level} to {heading.level} "
                    f'at "{heading.title}".',
                    heading.line,
                )
            )
        if not heading.title:
            diagnostics.append(MarkdownDiagnostic("warning", "Empty heading found.", heading.line))
        previous_level = heading.level
    return diagnostics


TOC_MARKER = "[TOC]"


def generate_toc(text: str, *, min_level: int = 1, max_level: int = 6) -> str:
    """Build a nested Markdown bullet list of links from *text*'s headings.

    Only headings within ``[min_level, max_level]`` are included. Returns an
    empty string when no headings are found.
    """
    headings = [h for h in extract_headings(text) if min_level <= h.level <= max_level]
    if not headings:
        return ""
    base_level = min(h.level for h in headings)
    lines = []
    for heading in headings:
        indent = "  " * (heading.level - base_level)
        lines.append(f"{indent}- [{heading.title}](#{heading.slug})")
    return "\n".join(lines)


def insert_toc(text: str) -> tuple[str, int]:
    """Return *text* with a TOC inserted, plus how many headings it contains.

    If the document contains a ``[TOC]`` marker on its own line, the TOC
    replaces that marker. Otherwise the TOC is inserted after the first
    heading (or at the top of the document if there is none).
    """
    headings = extract_headings(text)
    toc = generate_toc(text)
    if not toc:
        return text, 0
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == TOC_MARKER:
            lines[index] = toc
            return "\n".join(lines), len(headings)
    if headings:
        insert_after = headings[0].line  # 1-based; insert after this line
        lines = lines[:insert_after] + ["", toc, ""] + lines[insert_after:]
    else:
        lines = [toc, "", *lines]
    return "\n".join(lines), len(headings)


def apply_nl2br(text: str) -> str:
    """Preserve single line breaks by converting them to Markdown hard breaks.

    Within each paragraph (a run of non-blank lines), every line except the
    last gets a trailing Markdown hard-break (two spaces). Blank lines that
    separate paragraphs, and code fences, are left untouched.
    """
    lines = text.splitlines(keepends=False)
    out: list[str] = []
    in_code = False
    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code or not line.strip():
            out.append(line)
            continue
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if next_line.strip() and not next_line.strip().startswith("```"):
            out.append(line.rstrip() + "  ")
        else:
            out.append(line)
    return "\n".join(out)


def describe_processing_status(profile_name: str, extension_names: list[str]) -> str:
    """Screen-reader-friendly summary line (PRD #257 section 13.4)."""
    if not extension_names:
        return f"Markdown profile: {profile_name}. No extensions enabled."
    count = len(extension_names)
    noun = "extension" if count == 1 else "extensions"
    names = ", ".join(extension_names)
    return f"Markdown profile: {profile_name}. {count} {noun} enabled: {names}."

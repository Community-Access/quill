"""Conversion profiles for the Pandoc Import / Export menu (issue #262).

Issue #262 lists seven "conversion profiles" that hide Pandoc's flag surface
from users who just want "a clean Word document" or "an EPUB book" without
learning the CLI. This module is the single source of truth for those
profiles: each profile is a fixed list of Pandoc flags plus an
accessibility-friendly description the wizard's Summary page reads aloud.

The profiles are deliberately *Pandoc-flavoured*; they wrap Pandoc flags that
already exist rather than introducing a new QUILL-specific concept. The
mapping is conservative (no Pandoc flag that issue #262 calls out as risky
is enabled by default) and screen-reader-first (descriptions are plain
language, not flag names).

Pure logic. No ``wx`` imports. Strict-typed; always in scope for ``mypy``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConvertProfile:
    """One pre-bundled conversion profile.

    ``name`` is the internal key (used in settings persistence). ``label``
    is the display name shown in the wizard's profile picker. ``description``
    is the one-paragraph explanation the Summary page reads aloud via the
    screen reader. ``flags`` is the ordered list of Pandoc CLI flags that
    the runner appends to the user's chosen command. ``source_format`` /
    ``target_format`` are optional locks: when set, the wizard greys out the
    format picker and uses these directly.
    """

    name: str
    label: str
    description: str
    flags: tuple[str, ...]
    source_format: str | None = None
    target_format: str | None = None


# The seven profiles from issue #262. The flag lists are intentionally
# minimal and bias toward the "clean QUILL output" defaults; advanced flags
# belong in the Tier-2 "Advanced Pandoc Formats..." menu (a future issue).
PROFILES: tuple[ConvertProfile, ...] = (
    ConvertProfile(
        name="clean_word_document",
        label="Clean Word Document",
        description=(
            "Produce a Word document with QUILL's heading hierarchy as Word "
            "heading styles. Tables become Word tables. No theme, no macros, "
            "no embedded fonts. Best for sending a draft to a reviewer who "
            "uses Word."
        ),
        flags=("--standalone",),
        target_format="docx",
    ),
    ConvertProfile(
        name="accessible_html_page",
        label="Accessible HTML Page",
        description=(
            "Produce a single self-contained HTML page with semantic heading "
            "levels, alt text preserved on images, and table headers marked "
            "up for screen readers. Use this when you want one HTML file you "
            "can email or post online."
        ),
        flags=("--standalone", "--html-q-tags"),
        target_format="html",
    ),
    ConvertProfile(
        name="epub_book",
        label="EPUB Book",
        description=(
            "Produce an EPUB book with a table of contents from the document "
            "headings. Use this for long-form reading on tablets and e-readers."
        ),
        flags=(
            "--standalone",
            "--toc",
            "--toc-depth=2",
        ),
        target_format="epub",
    ),
    ConvertProfile(
        name="github_readme",
        label="GitHub README",
        description=(
            "Produce a GitHub-Flavored Markdown file with the same heading "
            "levels and code fences as the source. Best for posting into a "
            "repository's README.md."
        ),
        flags=(),
        target_format="gfm",
    ),
    ConvertProfile(
        name="print_pdf",
        label="Print PDF",
        description=(
            "Produce a PDF rendered from the Markdown. Requires a LaTeX "
            "engine to be installed on this computer; QUILL will use whichever "
            "one Pandoc finds first."
        ),
        flags=(),
        target_format="pdf",
    ),
    ConvertProfile(
        name="instructor_handout",
        label="Instructor Handout",
        description=(
            "Produce a Word document with line numbers on every line and "
            "table of contents from the headings. Useful when you are handing "
            "a draft out for inline comments."
        ),
        flags=("--standalone", "--number-lines"),
        target_format="docx",
    ),
    ConvertProfile(
        name="plain_text_for_screen_readers",
        label="Plain Text for Screen Readers",
        description=(
            "Produce a plain text file with no Markdown syntax. Headings, "
            "lists, and tables become plain-text equivalents. Use this when "
            "you want a flat file a screen reader can read straight through "
            "without interpreting any markup."
        ),
        flags=("--wrap=auto", "--strip-comments"),
        target_format="plain_text",
    ),
)


def get_profile(name: str | None) -> ConvertProfile | None:
    """Return the profile with ``name`` or ``None`` if ``name`` is falsy / unknown.

    A ``None`` name means "no profile" — the user wants Pandoc's plain
    defaults. The wizard passes ``None`` when the profile picker is set to
    "(no profile)".
    """

    if not name:
        return None
    for profile in PROFILES:
        if profile.name == name:
            return profile
    return None


def flags_for_profile(name: str | None) -> Sequence[str]:
    """Return the flags for ``name`` or an empty sequence if no profile.

    Convenience wrapper for the runner call site; reads cleanly in
    :func:`quill.core.batch_convert.run_batch`.
    """

    profile = get_profile(name)
    if profile is None:
        return ()
    return profile.flags

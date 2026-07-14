"""Markdown extension catalog and profile presets (issue #257).

QUILL's Markdown surface already renders headings, lists, fenced code, GFM
tables, and inline emphasis (see ``quill.core.browser_preview``), and already
has Insert commands for tables, footnotes, code blocks, and task lists (see
``quill.core.tagging``). What it lacked was a *named, friendly* way to talk
about that surface — a profile a user can pick instead of memorizing
extension names like ``toc`` or ``nl2br`` — and the table-of-contents and
line-break-preservation transforms themselves
(:mod:`quill.core.markdown_extensions`).

This module is the catalog: plain-language names and descriptions for each
extension (PRD principle 7.2, "Friendly Names Before Technical Names"), and
eight built-in profiles (PRD section 10 / guiding principle 7.3) that turn
groups of extensions on at once. Tagged under the ``"markdown"`` feature
category — never ``future.ai`` — because none of this calls a model.

No ``wx`` imports; pure data, fully unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MarkdownExtension:
    id: str
    friendly_name: str
    technical_name: str
    description: str
    accessibility_notes: str = ""
    implemented: bool = True


#: Extension catalog (PRD #257 section 11). ``implemented`` marks the
#: extensions QUILL applies today (table of contents, line-break
#: preservation); the rest are already supported natively by the editor's
#: Markdown renderer and Insert commands, so they are listed here for the
#: profile/extension dialog but are not separate toggleable transforms yet.
MARKDOWN_EXTENSIONS: dict[str, MarkdownExtension] = {
    "toc": MarkdownExtension(
        "toc",
        "Table of Contents",
        "toc",
        "Generates a table of contents from your document's headings.",
        "Greatly improves navigation for long documents; links match the "
        "heading IDs used by Browser Preview.",
    ),
    "nl2br": MarkdownExtension(
        "nl2br",
        "Preserve Single Line Breaks",
        "nl2br",
        "Keeps every line break as a line break, instead of collapsing it "
        "into a flowing paragraph. Useful for poetry, lyrics, and scripts.",
        "Not usually recommended for normal prose.",
    ),
    "tables": MarkdownExtension(
        "tables",
        "Markdown Tables",
        "tables",
        "Pipe-style tables, already supported by Insert > Insert Table and Browser Preview.",
        "Exports to semantic table markup.",
    ),
    "fenced_code": MarkdownExtension(
        "fenced_code",
        "Triple-Backtick Code Blocks",
        "fenced_code",
        "Fenced code blocks, already supported by Insert > Insert Code Block.",
        "Code blocks remain readable without relying on color.",
    ),
    "footnotes": MarkdownExtension(
        "footnotes",
        "Footnotes",
        "footnotes",
        "Notes referenced from the main text, already supported by Insert > Insert Footnote.",
        "Lets you cite details without interrupting the main reading flow.",
    ),
    "task_lists": MarkdownExtension(
        "task_lists",
        "Task Lists and Checkboxes",
        "tasklists",
        "Checklist items, already supported by Insert > Insert Task List.",
        "Important for project notes, meeting notes, and release checklists.",
    ),
    "strikethrough": MarkdownExtension(
        "strikethrough",
        "Strikethrough",
        "strikethrough",
        "``~~text~~`` for deleted or replaced text.",
        "Can convey revisions and status; should not be the only signal.",
    ),
    "def_list": MarkdownExtension(
        "def_list",
        "Definition Lists and Glossaries",
        "def_list",
        "Term-and-definition structures for glossary-style content.",
        "Exports to semantic definition list structures.",
    ),
}


@dataclass(frozen=True, slots=True)
class MarkdownProfile:
    id: str
    name: str
    description: str
    extensions: frozenset[str] = field(default_factory=frozenset)
    best_for: str = ""


#: Eight built-in profiles (PRD #257 guiding principle 7.3 / section 10).
MARKDOWN_PROFILES: dict[str, MarkdownProfile] = {
    "standard": MarkdownProfile(
        "standard",
        "Standard Markdown",
        "Basic, portable Markdown for maximum compatibility.",
        frozenset(),
        "Simple notes, portable Markdown, beginner users.",
    ),
    "github_style": MarkdownProfile(
        "github_style",
        "GitHub-Style Markdown",
        "Matches common expectations from GitHub README files, issues, and discussions.",
        frozenset({"tables", "fenced_code", "task_lists", "strikethrough"}),
        "README files, GitHub issues, project notes, release notes.",
    ),
    "documentation": MarkdownProfile(
        "documentation",
        "Documentation",
        "Supports manuals, guides, help files, and structured documentation.",
        frozenset({"toc", "tables", "fenced_code", "footnotes", "def_list"}),
        "User guides, developer documentation, help systems, PRDs.",
    ),
    "poetry_and_lyrics": MarkdownProfile(
        "poetry_and_lyrics",
        "Poetry and Lyrics",
        "Preserves intentional line breaks.",
        frozenset({"nl2br"}),
        "Poetry, lyrics, speeches, dramatic scripts, transcripts.",
    ),
    "accessible_publishing": MarkdownProfile(
        "accessible_publishing",
        "Accessible Publishing",
        "Creates clean, accessible HTML output, with heading and table checks.",
        frozenset({"toc", "tables", "footnotes", "def_list"}),
        "Web-ready documents that must hold up to a heading-structure audit.",
    ),
    "technical_writing": MarkdownProfile(
        "technical_writing",
        "Technical Writing",
        "Tables, fenced code, and footnotes for technical articles and manuals.",
        frozenset({"tables", "fenced_code", "footnotes", "def_list"}),
        "API references, technical articles, runbooks.",
    ),
    "prd_and_release_notes": MarkdownProfile(
        "prd_and_release_notes",
        "PRD and Release Notes",
        "Structured product documents, changelogs, and community-facing announcements.",
        frozenset({"toc", "tables", "task_lists", "footnotes", "strikethrough"}),
        "Product requirements documents, release notes, project plans, meeting notes.",
    ),
    "custom": MarkdownProfile(
        "custom",
        "Custom",
        "Your own combination of extensions.",
        frozenset(),
        "Advanced users who want to pick extensions individually.",
    ),
}

DEFAULT_MARKDOWN_PROFILE_ID = "standard"

#: Citation style for the Author or Student persona profile: either footnote
#: references (no new dependency) or full MLA/Chicago/APA bibliography
#: entries via the existing ``quill.core.citations`` module.
CITATION_STYLE_FOOTNOTES = "footnotes"
CITATION_STYLE_ACADEMIC = "academic"
CITATION_STYLES: tuple[tuple[str, str], ...] = (
    (CITATION_STYLE_FOOTNOTES, "Markdown footnotes"),
    (CITATION_STYLE_ACADEMIC, "Academic (MLA / Chicago / APA bibliography)"),
)


def extension_names(profile_id: str) -> list[str]:
    profile = MARKDOWN_PROFILES.get(profile_id)
    if profile is None:
        return []
    return [
        MARKDOWN_EXTENSIONS[ext_id].friendly_name
        for ext_id in profile.extensions
        if ext_id in MARKDOWN_EXTENSIONS
    ]


def describe_profile(profile_id: str) -> str:
    """Screen-reader-friendly summary (PRD #257 section 13.1)."""
    profile = MARKDOWN_PROFILES.get(profile_id)
    if profile is None:
        return f"No Markdown profile named {profile_id!r} was found."
    names = extension_names(profile_id)
    count = len(names)
    noun = "extension" if count == 1 else "extensions"
    return f"Markdown profile: {profile.name}. {count} {noun} enabled. {profile.description}"

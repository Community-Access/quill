"""build_docs.py -- Auto-generate docs/CONTROL_REFERENCE.md from topics.json.

Usage:
    python -m quill.tools.build_docs

The output file is overwritten on every run. Do not hand-edit
docs/CONTROL_REFERENCE.md; edit topics.json instead.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TOPICS_PATH = _REPO_ROOT / "quill" / "core" / "help" / "topics.json"
_OUTPUT_PATH = _REPO_ROOT / "docs" / "CONTROL_REFERENCE.md"

# Human-readable labels for user_guide_section slugs.
# Keys are the slug values from topics.json; values are the display title.
# Sections not listed here fall back to a title-cased version of the slug.
_SECTION_LABELS: dict[str, str] = {
    "the-main-window": "The Main Window",
    "writing-and-editing": "Writing and Editing",
    "editing": "Editing",
    "search-and-replace": "Search and Replace",
    "search-replace-and-deep-navigation": "Search, Replace, and Deep Navigation",
    "spelling": "Spell Checking",
    "ai-assistant": "AI Writing Assistance",
    "remote-access": "Remote File Editing",
    "read-aloud": "Read Aloud",
    "appearance": "Appearance",
    "general-preferences": "General Preferences",
    "keyboard-and-sound": "Keyboard and Sound",
    "profiles-keyboard-packs-and-customization": "Profiles, Keyboard Packs, and Customization",
    "feature-profiles": "Feature Profiles",
    "trust-recovery-sessions-and-safety": "Trust, Recovery, and Safety",
    "tools-for-reading-review-and-inspection": "Tools for Reading, Review, and Inspection",
    "working-with-different-document-types": "Working with Different Document Types",
    "help-learning-and-daily-confidence": "Help, Learning, and Daily Confidence",
    "checking-for-updates": "Checking for Updates",
    "glow-workflows-inside-quill": "GLOW Workflows Inside QUILL",
    "braille-mode": "Braille Mode",
}

# Desired display order for sections. Sections not listed appear at the end
# in alphabetical order.
_SECTION_ORDER: list[str] = [
    "the-main-window",
    "writing-and-editing",
    "editing",
    "search-and-replace",
    "search-replace-and-deep-navigation",
    "spelling",
    "ai-assistant",
    "remote-access",
    "read-aloud",
    "appearance",
    "general-preferences",
    "keyboard-and-sound",
    "profiles-keyboard-packs-and-customization",
    "feature-profiles",
    "trust-recovery-sessions-and-safety",
    "tools-for-reading-review-and-inspection",
    "working-with-different-document-types",
    "braille-mode",
    "help-learning-and-daily-confidence",
    "checking-for-updates",
    "glow-workflows-inside-quill",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_label(slug: str) -> str:
    """Return a human-readable heading for a user_guide_section slug."""
    if slug in _SECTION_LABELS:
        return _SECTION_LABELS[slug]
    # Fallback: replace hyphens and title-case.
    return slug.replace("-", " ").title()


def _sorted_sections(sections: dict[str, list[dict]]) -> list[tuple[str, list[dict]]]:
    """Return sections in display order, with unordered sections at the end."""
    ordered: list[tuple[str, list[dict]]] = []
    for slug in _SECTION_ORDER:
        if slug in sections:
            ordered.append((slug, sections[slug]))
    # Append any sections not in _SECTION_ORDER, alphabetically.
    for slug in sorted(sections):
        if slug not in _SECTION_ORDER:
            ordered.append((slug, sections[slug]))
    return ordered


def _render_keystrokes(keystrokes: list[str]) -> str:
    """Render a list of keystroke strings as a two-column Markdown table."""
    if not keystrokes:
        return ""
    lines: list[str] = [
        "",
        "| Key | Action |",
        "|---|---|",
    ]
    for entry in keystrokes:
        # Each entry is expected to be "Key - Description".
        if " - " in entry:
            key, action = entry.split(" - ", maxsplit=1)
        else:
            key, action = entry, ""
        lines.append(f"| {key.strip()} | {action.strip()} |")
    return "\n".join(lines)


def _render_topic(topic: dict) -> str:
    """Render a single topic as a Markdown subsection."""
    title = topic.get("title", topic.get("id", "Untitled"))
    body = topic.get("body", "").strip()
    keystrokes: list[str] = topic.get("keystrokes", [])
    see_also: list[str] = topic.get("see_also", [])

    parts: list[str] = [f"### {title}"]
    if body:
        parts.append("")
        parts.append(body)
    ks_table = _render_keystrokes(keystrokes)
    if ks_table:
        parts.append(ks_table)
    if see_also:
        refs = ", ".join(f"`{ref}`" for ref in see_also)
        parts.append("")
        parts.append(f"See also: {refs}")
    return "\n".join(parts)


def _generate_markdown(topics: list[dict]) -> str:
    """Group topics by user_guide_section and produce full Markdown content."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        "<!-- AUTO-GENERATED FILE. Do not hand-edit.\n"
        f"    Generated by quill/tools/build_docs.py on {timestamp}.\n"
        "    To update, edit quill/core/help/topics.json and re-run:\n"
        "        python -m quill.tools.build_docs\n"
        "-->\n\n"
        "# QUILL Control Reference\n\n"
        "This document describes every registered help topic in QUILL.\n"
        "Press F1 on any control to see its topic in-app.\n"
        "Press Ctrl+F1 to open the User Guide.\n\n"
        f"Topic count: {len(topics)}\n"
    )

    # Group topics by section.
    sections: dict[str, list[dict]] = defaultdict(list)
    for topic in topics:
        slug = topic.get("user_guide_section", "general")
        sections[slug].append(topic)

    section_parts: list[str] = []
    for slug, section_topics in _sorted_sections(sections):
        label = _section_label(slug)
        section_parts.append(f"\n## {label}\n")
        for topic in section_topics:
            section_parts.append(_render_topic(topic))
            section_parts.append("")

    return header + "\n".join(section_parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    if not _TOPICS_PATH.exists():
        print(f"ERROR: topics.json not found at {_TOPICS_PATH}", file=sys.stderr)
        return 1

    raw = _TOPICS_PATH.read_text(encoding="utf-8")
    try:
        topics: list[dict] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Failed to parse topics.json: {exc}", file=sys.stderr)
        return 1

    if not isinstance(topics, list):
        print("ERROR: topics.json must be a JSON array.", file=sys.stderr)
        return 1

    output = _generate_markdown(topics)

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"OK - wrote {len(topics)} topics to {_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

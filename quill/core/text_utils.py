"""Lightweight Markdown-to-plain-text flattener for dialog bodies.

Used by :meth:`quill.ui.main_frame.MainFrame._html_info` to render the
small Markdown subset emitted by the GLOW / Check-for-Updates flow
into a string suitable for a ``wx.MessageDialog``. Pure, no ``wx``
imports, safe to call from unit tests.

The About-Quill dialog rewrite (#260) deliberately removed the
equivalent ``_md_to_plain`` helper from :mod:`quill.ui.info_pages`
because flattening headings, lists, and links into a single
``TextCtrl`` made the dialog unreadable in JAWS Forms mode. The
Check-for-Updates dialog is a small informational box, not a
navigable document, so a flattener is still the right tool there.
"""

from __future__ import annotations

import re

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)")


def strip_md_to_plain(text: str) -> str:
    """Reduce the small Markdown subset used in update / GLOW dialogs
    to text suitable for a ``wx.MessageDialog`` body.

    Handles ``#``..``######`` headings (preserved with an underline so
    a JAWS / NVDA user still hears the heading cue), ``**bold**`` and
    inline ``code``, and ``[label](url)`` links. Anything else passes
    through unchanged so user-typed paragraphs and bullet lists
    survive. Fenced code blocks are not handled: the inline-backtick
    rule applies line-by-line, so the wrapping ``\\`\\`\\``` markers
    are stripped. The GLOW update notes and the Check-for-Updates
    dialog never emit fenced code, and a ``MessageDialog`` would
    render a fence poorly anyway.

    Used to live in :mod:`quill.ui.info_pages` as ``_md_to_plain``;
    moved out when the About dialog rewrite (#260) deleted the
    flattener, then revived here for the Check-for-Updates path (#605).
    """
    lines: list[str] = []
    for line in text.splitlines():
        m = _MD_HEADING.match(line)
        if m:
            heading = m.group(2).strip()
            underline = ("=" if len(m.group(1)) == 1 else "-") * min(len(heading), 60)
            lines.append(heading)
            lines.append(underline)
            continue
        lines.append(line)
    result = "\n".join(lines)
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", result)
    result = re.sub(r"`(.+?)`", r"\1", result)
    result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", result)
    return result.strip()

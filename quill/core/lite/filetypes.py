"""Which files QuillLite offers, and which of them are rich text.

Two decisions live here, in one wx-free place so the Open dialog, the Save As
dialog, the drag-and-drop path and the mode-switching logic cannot disagree
about them.

**What counts as rich text is the extension, and only ``.rtf``.** Not a sniff of
the first bytes, and not a preference: a file named ``.rtf`` opens in rich mode
and everything else opens as text. That is what Notepad and WordPad do, it is
what the user's file manager already told them, and a rule you can predict from
the name is worth more here than a rule that is right slightly more often.

**A text editor should open text.** The "all supported files" filter therefore
covers the extensions people actually keep prose, notes and configuration in,
rather than only ``.txt`` -- opening a ``.md`` or a ``.log`` should not require
finding the All Files filter first.
"""

from __future__ import annotations

__all__ = [
    "OPEN_WILDCARD",
    "RICH_SUFFIXES",
    "SAVE_WILDCARD_PLAIN",
    "SAVE_WILDCARD_RICH",
    "is_rich_path",
]

#: The one extension that means rich text.
RICH_SUFFIXES = frozenset({".rtf"})

#: The extensions the "all supported files" filter offers, as one wx pattern.
_TEXT_LIKE = "*.txt;*.rtf;*.md;*.log;*.csv;*.json;*.py;*.html"

OPEN_WILDCARD = (
    f"All supported files ({_TEXT_LIKE})|{_TEXT_LIKE}|"
    "Text files (*.txt)|*.txt|"
    "Rich Text (*.rtf)|*.rtf|"
    "Markdown (*.md)|*.md|"
    "All files (*.*)|*.*"
)

#: Save As offers the document's own kind first, so Enter does the obvious thing.
SAVE_WILDCARD_PLAIN = (
    "Text files (*.txt)|*.txt|Markdown (*.md)|*.md|Rich Text (*.rtf)|*.rtf|All files (*.*)|*.*"
)
SAVE_WILDCARD_RICH = "Rich Text (*.rtf)|*.rtf|Text files (*.txt)|*.txt|All files (*.*)|*.*"


def is_rich_path(name: str) -> bool:
    """True when a file of this name should be opened (or saved) as rich text."""
    lowered = str(name).lower()
    return any(lowered.endswith(suffix) for suffix in RICH_SUFFIXES)

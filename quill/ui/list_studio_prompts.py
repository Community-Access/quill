"""Small modal prompts for the Structured List Studio (kept out of the dialog).

Separated from ``list_studio_dialog`` so the dialog stays within its GATE-11 size
budget. The one prompt here implements §7.6/§21.3: when a Markdown definition list
has no profile configured for the document, ask the user how to generate it rather
than silently guessing a syntax their renderer may not support.
"""

from __future__ import annotations

from typing import Any

# Native (Pandoc-style) Markdown definition syntaxes offered in the second step,
# paired with the choice token render.render_definition_with_choice understands.
_NATIVE_PROFILES: list[tuple[str, str]] = [
    ("Pandoc", "pandoc"),
    ("Markdown Extra", "markdown_extra"),
    ("MultiMarkdown", "multimarkdown"),
]


def prompt_definition_fallback(wx: Any, parent: Any) -> str | None:
    """Ask how to render a definition list with no Markdown profile (§21.3).

    Uses native, keyboard-first ``wx.SingleChoiceDialog`` modals owned by *parent*.
    Embedded HTML is the recommended first semantic fallback; choosing a Markdown
    profile opens a second picker. Returns a choice token (a key of
    ``render.DEFINITION_FALLBACK_PROFILES``) or ``None`` on cancel.
    """
    actions = [
        "Generate embedded HTML (recommended)",
        "Choose a Markdown definition-list profile…",
        'Create a plain "Term: Definition" list',
    ]
    with wx.SingleChoiceDialog(
        parent,
        "Definition-list support is not configured for this Markdown document. "
        "How would you like to generate it?",
        "Definition List Format",
        actions,
    ) as dlg:
        if dlg.ShowModal() != wx.ID_OK:
            return None
        selection = dlg.GetSelection()
    if selection == 0:
        return "html"
    if selection == 2:
        return "plain"
    with wx.SingleChoiceDialog(
        parent,
        "Choose the Markdown definition-list syntax this document's renderer supports:",
        "Markdown Definition Profile",
        [label for label, _token in _NATIVE_PROFILES],
    ) as dlg:
        if dlg.ShowModal() != wx.ID_OK:
            return None
        return _NATIVE_PROFILES[dlg.GetSelection()][1]

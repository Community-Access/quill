"""QUILL Lite's side of the thesaurus and the dictionaries (2026-10-02).

The thesaurus and the AI dictionary are the family's
(:mod:`quill.ui.word_tools_commands`, reached through ``HostedAiMixin``); this
mixin answers the one question that module asks the host -- is the dictionary
area switched on -- with QUILL Lite's feature area, and adds the one row QUILL has
that is about the *spelling* dictionaries rather than the thesaurus:
**Dictionary Status**, which says how many words each dictionary holds, where
each file lives, and whether the thesaurus data is present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.lite import spelling as spelling_mod


class DocumentWordsMixin:
    """Thesaurus switch, and Tools > Spelling > Dictionary Status."""

    def _dictionary_enabled(self) -> bool:
        return bool(self.app.feature_enabled("dictionary"))  # type: ignore[attr-defined]

    def cmd_dictionary_status(self) -> None:
        """How many taught words, where they are kept, and whether the thesaurus is here."""
        from quill.core import thesaurus
        from quill.core.spellcheck import load_scope_dictionary

        app = self.app  # type: ignore[attr-defined]
        document_path: Path | None = getattr(self, "path", None)
        personal_dir = spelling_mod.dictionary_dir(app.settings, app.data_dir)
        shared = bool(getattr(app.settings, "share_quill_dictionary", False))
        lines: list[str] = []
        try:
            personal = len(load_scope_dictionary("personal", document_path, None, personal_dir))
        except Exception:  # noqa: BLE001 - an unreadable list is reported as empty
            personal = 0
        personal_file = personal_dir / "dictionaries" / "personal.json"
        owner = "QUILL's shared dictionary" if shared else "your QUILL Lite dictionary"
        lines.append(
            f"Personal ({owner}): {personal} word{'s' if personal != 1 else ''}, "
            f"kept at {personal_file}"
            + ("" if personal_file.exists() else " (not created yet; add a word to create it)")
        )
        if document_path is None:
            lines.append("This document: no dictionary until the document is saved.")
        else:
            try:
                document = len(load_scope_dictionary("document", document_path, None, personal_dir))
            except Exception:  # noqa: BLE001
                document = 0
            sidecar = document_path.with_suffix(document_path.suffix + ".quill-dict.json")
            lines.append(
                f"This document: {document} word{'s' if document != 1 else ''}, "
                f"kept beside the file at {sidecar.name}"
                + ("" if sidecar.exists() else " (not created yet)")
            )
        lines.append(
            "Thesaurus data: "
            + ("installed" if thesaurus.is_available() else "not installed")
            + f" ({thesaurus.data_path()})"
        )
        lines.append("")
        lines.append(
            "Words are taught from the Spelling Actions submenu on a word, or with "
            "Add Word to Dictionary (Ctrl+Alt+F9). Preferences chooses whether QUILL "
            "Lite shares QUILL's dictionary."
        )
        show_dictionary_status(self, lines, self._announce)  # type: ignore[attr-defined]


def show_dictionary_status(parent: Any, lines: list[str], announce: Any) -> None:
    """The read-only status window: one field, arrowable, and Close."""
    import wx

    from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

    dialog = wx.Dialog(parent, title="Dictionary Status")
    root = wx.BoxSizer(wx.VERTICAL)
    caption = wx.StaticText(dialog, label="&Status:")
    field = wx.TextCtrl(
        dialog,
        value="\n".join(lines),
        size=(560, 220),
        style=wx.TE_MULTILINE | wx.TE_READONLY,
    )
    field.SetHelpText(
        "How many words each dictionary holds and where each file is. Read only; "
        "arrow through it, and copy any line you need."
    )
    root.Add(caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    root.Add(field, 1, wx.EXPAND | wx.ALL, 8)
    close = wx.Button(dialog, wx.ID_CLOSE, label="Close")
    close.SetHelpText("Closes this window.")
    row = wx.BoxSizer(wx.HORIZONTAL)
    row.AddStretchSpacer()
    row.Add(close, 0, wx.ALL, 8)
    root.Add(row, 0, wx.EXPAND)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=close.GetId(), escape_id=close.GetId())
    close.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    wx.CallAfter(field.SetFocus)
    try:
        show_modal_dialog(dialog, "Dictionary Status", announce=announce)
    finally:
        dialog.Destroy()


__all__ = ["DocumentWordsMixin"]

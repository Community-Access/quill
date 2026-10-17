"""The password question for a locked PDF, one dialog for both editors.

QUILL asked for a PDF's password from ``MainFrame._ask_pdf_password``; QUILL
Lite needs the same question when it opens a PDF (2026-10-15), and two copies
of a password prompt are two places a password could start being remembered.
So this is the one, and its rules are short:

* **A native password box** (``wx.PasswordEntryDialog``): the field is a real
  password edit, so the screen reader says "password" and does not echo the
  characters, and Enter and Escape answer OK and Cancel.
* **The password is returned, never kept.** The caller uses it for one read of
  one file and drops it; nothing here writes it anywhere.
* **The question says which file and whether the last try failed**, from the
  shared sentences in :mod:`quill.core.pdf_open`, so a wrong password re-asks
  with "That password did not open ..." rather than the same words again.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.pdf_open import PASSWORD_DIALOG_TITLE, password_prompt

__all__ = ["ask_pdf_password"]

#: The F1 answer for the password box.
_HELP = (
    "Type the password for this PDF and press Enter. It is used once, to open "
    "this file, and is never saved. Escape cancels the open."
)


def ask_pdf_password(
    parent: Any,
    file_name: str,
    *,
    incorrect: bool,
    show_modal: Callable[[Any, str], int] | None = None,
) -> str | None:
    """Ask for *file_name*'s password. ``None`` on Cancel or an empty entry.

    *show_modal* is the host's modal runner (QUILL's ``_show_modal_dialog``);
    without one the shared :func:`~quill.ui.dialog_contract.show_modal_dialog`
    runs it, which is what QUILL Lite uses for every dialog.
    """
    import wx

    from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

    runner = show_modal or show_modal_dialog
    with wx.PasswordEntryDialog(
        parent, password_prompt(file_name, incorrect=incorrect), PASSWORD_DIALOG_TITLE
    ) as dialog:
        dialog.SetHelpText(_HELP)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        if runner(dialog, PASSWORD_DIALOG_TITLE) != wx.ID_OK:
            return None
        password = dialog.GetValue()
    return password or None

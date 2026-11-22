"""Convert Linked Document with Scribe for Documents... (PRD 8.6 Cast, 8.8 Social).

One command for both apps: the links Scribe can take (:mod:`quill.core.scribe.links`),
then the shared Convert dialog for the one chosen, which says what will be
sent before anything goes (URL input, direct file links only).

* **None:** one sentence, and nothing opens.
* **One:** straight to the Convert dialog; a list of one is a step for nothing.
* **Several:** a standard choice list, "Choose a Linked Document". Its message
  is the list's label (Windows names the list from the text before it), short
  and with the count: "Linked documents in this episode's show notes, 3:". The
  first row is selected, so the reader hears "<first row>, 1 of 3".
"""

from __future__ import annotations

from typing import Any

from quill.core.scribe.links import LinkedDocument, list_label, none_sentence, row_labels

TITLE = "Choose a Linked Document"


def choose(
    parent: Any,
    documents: list[LinkedDocument],
    *,
    where: str,
    modal: Any,
) -> LinkedDocument | None:
    """The document to convert, or ``None`` (cancelled, or a list of none).

    *where* names the place in the label ("this post"); *modal* is the app's
    modal contract, ``modal(dialog, title) -> int``.
    """
    if not documents:
        return None
    if len(documents) == 1:
        return documents[0]
    import wx

    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.SingleChoiceDialog(
        parent, list_label(len(documents), where), TITLE, row_labels(documents)
    )
    try:
        dialog.SetName("scribe_link_choice_dialog")  # F1 finds its topic by this name
        dialog.SetSelection(0)
        for child in dialog.GetChildren():
            if isinstance(child, wx.ListBox):
                child.SetName(list_label(len(documents), where).rstrip(":"))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        if modal(dialog, TITLE) != wx.ID_OK:
            return None
        return documents[max(0, dialog.GetSelection())]
    finally:
        dialog.Destroy()


def convert_linked(
    controller: Any,
    documents: list[LinkedDocument],
    *,
    parent: Any,
    where: str,
    subject: str,
    verb: str,
    say: Any,
    modal: Any,
) -> list[Any]:
    """The whole command: say there is nothing, or choose, then convert."""
    if not controller.check_available():
        return []
    if not documents:
        say(none_sentence(subject, verb=verb))
        return []
    chosen = choose(parent, documents, where=where, modal=modal)
    if chosen is None:
        return []
    return list(controller.convert_url(chosen.url, open_as="linked"))


__all__ = ["TITLE", "choose", "convert_linked"]

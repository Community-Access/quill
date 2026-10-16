"""Clipboard collector mode append logic (EDS-11), and what it says.

Clipboard collector mode appends every subsequent clipboard copy into
the document, separated by a divider. This wx-free helper holds the pure append
logic so the divider behaviour can be unit-tested without ``wx``.

It also holds the one decision both editors make after a clip lands
(``clipboard_collector_saves``, 2026-10-15): whether to save the document
quietly, and the sentence that says what happened. QUILL and QUILL Lite both
call these, so the two collectors cannot come to answer the same copy with
different words. The rules:

* Only a document **with a file name** is saved. An untitled one collects as
  it always did, and no Save As window ever opens -- a copy made in another
  program must never put a dialog in front of you.
* A clip that was saved says one sentence, ``"Collected and saved"``, not a
  collection sentence followed by a save sentence (the double announcement
  bad.md C4 removed).
* A save that could not happen is a failure, and failures are always spoken
  (``quill/core/action_feedback.py``): the clip is still in the document, the
  sentence says so, and collecting carries on.
"""

from __future__ import annotations

__all__ = [
    "COLLECTED",
    "COLLECTED_AND_SAVED",
    "DEFAULT_DIVIDER",
    "append_collected",
    "collected_but_not_saved",
    "disk_changed_reason",
    "encoding_reason",
    "saves_after_collect",
]

DEFAULT_DIVIDER = "\n\n----\n\n"

#: A clip collected into a document that is not saved by the collector.
COLLECTED = "Collected clipboard text"
#: A clip collected into a named document, which was then saved quietly.
COLLECTED_AND_SAVED = "Collected and saved"


def append_collected(document_text: str, clip_text: str, *, divider: str = DEFAULT_DIVIDER) -> str:
    """Return ``document_text`` with ``clip_text`` appended after a divider.

    An empty ``clip_text`` leaves the document unchanged. When the document is
    empty the clip is used as-is, with no leading divider.
    """
    if not clip_text:
        return document_text
    if not document_text:
        return clip_text
    return document_text + divider + clip_text


def saves_after_collect(setting_on: object, has_file_name: bool) -> bool:
    """Whether a collected clip is followed by a quiet save.

    *setting_on* is ``clipboard_collector_saves`` (on by default); a document
    with no file name is never saved, whatever the setting says.
    """
    return bool(setting_on) and bool(has_file_name)


def collected_but_not_saved(reason: str) -> str:
    """The one sentence for a clip that landed but could not be saved.

    *reason* is the plain explanation (it should end with a full stop); the
    sentence leads with what did happen, because the clip is safe in the
    document and the person should not go looking for it.
    """
    reason = reason.strip()
    return f"Collected, but not saved. {reason}" if reason else "Collected, but not saved."


def disk_changed_reason(name: str) -> str:
    """Why a quiet save stood back: another program changed the file.

    The collector never overwrites a change it has not seen and never asks in a
    window either, so the person is told and decides with an ordinary Save.
    """
    return (
        f"Another program changed {name} on disk. Save it yourself to choose which version to keep."
    )


def encoding_reason(name: str, encoding: str) -> str:
    """Why a quiet save stood back: the file's encoding cannot hold the clip.

    Saving anyway would turn those characters into question marks, which is a
    choice only the writer can make -- so the ordinary Save asks, and this
    says to use it.
    """
    return (
        f"{name} is saved as {encoding}, which cannot hold some of the collected "
        "characters. Save it yourself to choose what to do."
    )

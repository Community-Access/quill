"""Hand a transcript or show notes to QUILL as a document (FUX-02).

The UI half of :mod:`quill.core.editor_handoff`: write the document into the
app's folder in Documents, say once where it is, and open it in QUILL (or
QUILL Lite) through the family's launcher, the same way Scribe's Next Steps
open a result (:func:`quill.ui.scribe_app_host.open_in_editor`).

**When there is no editor** the document is still written, and the sentence
says where; nothing is copied to the clipboard behind the person's back and
nothing offers an installation first.

**Said once, before QUILL comes forward.** QUILL taking the focus makes the
screen reader read its window, which would cut off anything said after.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path


def documents_folder(source_app: str) -> Path:
    """The folder named after *source_app* in Documents: where a handed-over document is kept."""
    base = ""
    try:
        import wx

        base = wx.StandardPaths.Get().GetDocumentsDir()
    except Exception:  # noqa: BLE001 - no wx, or no answer: fall back below
        base = ""
    return Path(base or Path.home() / "Documents") / source_app


def _allow_foreground() -> None:
    """Let the QUILL that answers come to the front.

    Windows hands the foreground on only from the process that has it, which
    is this one; without this an already-running QUILL flashes on the taskbar
    behind Cast, right after Cast said it was opening it.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # type: ignore[attr-defined]  # ASFW_ANY
    except Exception:  # noqa: BLE001 - a focus courtesy must never block the handoff
        pass


def hand_to_editor(
    content: str,
    *,
    filename: str,
    kind: str,
    source_app: str,
    announce: Callable[[str], None],
    line: int | None = None,
    folder: Path | None = None,
) -> Path | None:
    """Write *content* as *filename* and open it in the editor.

    *kind* names the thing in the sentence ("the transcript"). Returns the
    document's path, or ``None`` when it could not be written.

    The sentence is short and leads with the folder: QUILL's window, which
    comes forward next, says the file's name in its title, and a long
    sentence would be cut off when it does.
    """
    from quill.core.editor_handoff import destination
    from quill.ui import scribe_app_host

    where = folder if folder is not None else documents_folder(source_app)
    place = f"in Documents, in the {where.name} folder"
    try:
        where.mkdir(parents=True, exist_ok=True)
        target = destination(where, filename, content)
        existed = target.exists()
        if not existed:
            target.write_text(content, encoding="utf-8", newline="\n")
    except OSError as error:
        announce(f"Could not save {kind} {place}: {error.strerror or error}.")
        return None
    editor = scribe_app_host.editor_name()
    if not editor:
        announce(
            f"Saved {kind} as {target.name} {place}. QUILL is not installed "
            "with this copy, so it was not opened."
        )
        return target
    saved = f"Already saved {place}." if existed else f"Saved {place}."
    at_top = " It opens at the top." if line and editor != "QUILL" else ""
    announce(f"{saved} Opening it in {editor}.{at_top}")
    _allow_foreground()
    if not scribe_app_host.open_in_editor(target, line=line):
        announce(f"{editor} could not be opened. {target.name} is saved {place}.")
    return target


def send_text(
    text: str,
    *,
    source_app: str,
    announce: Callable[[str], None],
    kind: str = "show notes",
    title: str = "",
    show: str = "",
    line: int | None = None,
    wrapped: bool = False,
    open_here: Callable[[str, int | None], None] | None = None,
) -> None:
    """The one way Cast's show notes and transcripts reach the editor.

    *text* is plain unless *wrapped* (the transcript reader's own document).
    Inside QUILL, *open_here* opens it as a new document, at *line*; elsewhere it is saved
    and handed over by :func:`hand_to_editor`.
    """
    from quill.core.editor_handoff import document_filename, text_document

    document = (
        text
        if wrapped
        else text_document(text, kind=kind, title=title, show=show, source_app=source_app)
    )
    if open_here is not None:
        open_here(document, line)
        return
    hand_to_editor(
        document,
        filename=document_filename(kind=kind, title=title, show=show),
        kind=f"the {kind}",
        source_app=source_app,
        announce=announce,
        line=line,
    )


__all__ = ["documents_folder", "hand_to_editor", "send_text"]

r"""The window is not renamed to the name it already has.

QUILL has skipped an unchanged retitle since it learned why
(``_refresh_title_bar``); QuillLite called ``SetTitle`` every time anything
touched the document. Retitling fires ``EVT_OBJECT_NAMECHANGE`` through MSAA and
UIA, so a screen reader is told the window was renamed -- and on an MDI child the
call reaches all the way up to the parent's caption, which is not free even when
nothing is listening.

``_set_modified`` is the hot path: it runs on the first change to a clean
document and on every save, and the mode switch lands here too.

The real method, bound to a holder, in the shape ``test_main_frame_undo_atomic``
uses for QUILL's: ``_update_title`` lives on ``DocumentFrame`` rather than on one
of the mixins, so the shared window stub cannot reach it.
"""

from __future__ import annotations

from quill.apps.lite_window import DocumentFrame
from quill.ui.richedit_editing import PLAIN, RICH


class _Editor:
    def __init__(self, mode: str = PLAIN) -> None:
        self.mode = mode


class _Holder:
    """The five things ``_update_title`` reads, and the one it calls."""

    _update_title = DocumentFrame._update_title
    document_name = DocumentFrame.document_name

    def __init__(self, *, number: int = 3, path=None, mode: str = PLAIN) -> None:
        self.number = number
        self.path = path
        self.modified = False
        self.editor = _Editor(mode)
        self.titles: list[str] = []

    def SetTitle(self, title: str) -> None:  # noqa: N802 - wx API shape
        self.titles.append(title)


def test_the_same_title_is_not_set_twice() -> None:
    holder = _Holder()
    holder._update_title()
    assert len(holder.titles) == 1

    holder._update_title()
    holder._update_title()
    assert len(holder.titles) == 1


def test_a_real_change_still_retitles() -> None:
    """The guard must not be able to stop the title telling the truth."""
    holder = _Holder()
    holder._update_title()
    holder.modified = True
    holder._update_title()
    assert len(holder.titles) == 2
    assert "*" in holder.titles[1]
    assert "*" not in holder.titles[0]


def test_the_mode_is_in_the_title_and_changes_it() -> None:
    holder = _Holder()
    holder._update_title()
    holder.editor.mode = RICH
    holder._update_title()
    assert "plain text" in holder.titles[0]
    assert "rich text" in holder.titles[1]


def test_the_number_leads_the_title() -> None:
    """It is the handle a person comes back by, and an MDI child is not in Alt+Tab."""
    holder = _Holder(number=7)
    holder._update_title()
    assert holder.titles[-1].startswith("7: ")

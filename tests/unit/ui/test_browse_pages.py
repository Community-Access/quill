"""Browse mode by misspelling (M) and by page (F), and the page said once.

QUILL's browse mode over a fake editor: no window is shown and no key reaches
a real one. The dispatch test runs MainFrame's own key-to-action method.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.navigation import PageLatch, page_starts, page_target
from quill.ui.main_frame_browse_pages import BrowsePagesMixin

PDF_TEXT = "Page one text.\fPage two text.\fPage three text.\n"


class _Editor:
    def __init__(self, text: str, caret: int = 0) -> None:
        self.text = text
        self.caret = caret
        self.selection = (caret, caret)

    def GetValue(self) -> str:  # noqa: N802 - wx API shape
        return self.text

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.caret

    def GetLastPosition(self) -> int:  # noqa: N802
        return len(self.text)

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.selection = (start, end)

    def SetFocus(self) -> None:  # noqa: N802
        pass


class _Browser(BrowsePagesMixin):
    def __init__(self, text: str, caret: int = 0) -> None:
        self.editor = _Editor(text, caret)
        self.document = object()
        self.settings = SimpleNamespace(browse_mode_wrap=True)
        self.said: list[str] = []
        self.announced: list[str] = []
        self._location_ring = SimpleNamespace(record=lambda _p: None)

    def _browse_text(self) -> str:
        return self.editor.text

    def _spell_dictionary(self) -> set[str]:
        return set()

    def _quill_feedback(self, message: str, **_kwargs: object) -> None:
        self.said.append(message)

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _record_location_before_jump(self) -> None:
        pass

    def _move_point(self, position: int) -> None:
        self.editor.caret = position

    def arrow_to(self, position: int) -> None:
        self.editor.caret = position
        self._maybe_announce_page_crossing()


# -- core ------------------------------------------------------------------------ #


def test_page_targets_go_to_the_top_of_a_page_first() -> None:
    starts = page_starts(PDF_TEXT)
    second = PDF_TEXT.index("Page two")
    assert page_target(starts, 0, forward=True) == second
    assert page_target(starts, second + 4, forward=False) == second  # top of this page
    assert page_target(starts, second, forward=False) == 0  # then the one before
    assert page_target(starts, starts[-1], forward=True) is None


def test_the_latch_says_a_page_once_and_not_on_opening() -> None:
    latch = PageLatch()
    doc = object()
    assert latch.crossed(1, doc) is False  # opening is not a crossing
    assert latch.crossed(2, doc) is True
    assert latch.crossed(2, doc) is False  # the next arrow key on page 2
    latch.settle(3, doc)
    assert latch.crossed(3, doc) is False
    assert latch.crossed(1, object()) is False  # another document starts fresh


# -- F and Shift+F ------------------------------------------------------------------ #


def test_f_goes_page_by_page_and_says_where() -> None:
    browser = _Browser(PDF_TEXT)
    browser._browse_page(reverse=False)
    assert browser.editor.caret == PDF_TEXT.index("Page two")
    assert browser.said == ["Page 2 of 3"]
    browser._browse_page(reverse=True)
    assert browser.editor.caret == 0 and browser.said[-1] == "Page 1 of 3"


def test_arrowing_across_a_break_says_the_page_once() -> None:
    browser = _Browser(PDF_TEXT)
    browser.arrow_to(1)  # first reading: nothing
    two = PDF_TEXT.index("Page two")
    browser.arrow_to(two - 1)
    assert browser.announced == []
    browser.arrow_to(two)
    browser.arrow_to(two + 1)
    browser.arrow_to(two + 2)
    assert browser.announced == ["Page 2 of 3"]


def test_f_settles_the_latch_so_the_page_is_not_said_twice() -> None:
    browser = _Browser(PDF_TEXT)
    browser.arrow_to(0)
    browser._browse_page(reverse=False)
    browser._maybe_announce_page_crossing()  # the key-up after F
    assert browser.said == ["Page 2 of 3"] and browser.announced == []


def test_a_document_without_page_breaks_says_so() -> None:
    browser = _Browser("No pages here.\n")
    browser._browse_page(reverse=False)
    assert browser.said == ["This document has no page breaks."]
    browser.arrow_to(3)
    assert browser.announced == []


# -- M and Shift+M ------------------------------------------------------------------ #


def test_m_finds_the_next_misspelling_and_says_the_word() -> None:
    text = "A good line.\nThe recieve form is here.\nAnd teh end.\n"
    browser = _Browser(text)
    browser._browse_misspelling(reverse=False)
    start = text.index("recieve")
    assert browser.editor.caret == start
    assert browser.editor.selection == (start, start + len("recieve"))
    assert browser.said == ["Misspelled: recieve, line 2"]
    browser._browse_misspelling(reverse=False)
    assert browser.said[-1] == "Misspelled: teh, line 3"
    browser._browse_misspelling(reverse=True)
    assert browser.said[-1] == "Misspelled: recieve, line 2"


def test_m_in_a_clean_document_says_there_is_nothing() -> None:
    browser = _Browser("A good line.\n")
    browser._browse_misspelling(reverse=False)
    assert browser.said == ["No misspelled words in this document."]


# -- the keys reach the actions ------------------------------------------------------ #


@pytest.mark.parametrize(
    ("key", "shift", "action"),
    [
        ("M", False, "browse.misspelling.next"),
        ("M", True, "browse.misspelling.previous"),
        ("F", False, "browse.page.next"),
        ("F", True, "browse.page.previous"),
    ],
)
def test_browse_mode_maps_m_and_f(key: str, shift: bool, action: str) -> None:
    import wx

    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.ui.keybinding_parse import KeybindingParseMixin
    from quill.ui.main_frame import MainFrame

    host = SimpleNamespace(_wx=wx, _binding_for=DEFAULT_KEYMAP.get)
    host._parse_keybinding = lambda binding: KeybindingParseMixin._parse_keybinding(host, binding)
    event = SimpleNamespace(
        GetKeyCode=lambda: ord(key),
        ShiftDown=lambda: shift,
        ControlDown=lambda: False,
        AltDown=lambda: False,
    )
    assert MainFrame._quill_key_action_for_event(host, event) == action


def test_no_two_browse_keys_share_a_letter() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    keys = [v.upper() for k, v in DEFAULT_KEYMAP.items() if k.startswith("quill.quick_nav.") and v]
    assert len(keys) == len(set(keys))

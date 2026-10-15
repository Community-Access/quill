"""Find in Open Documents: what it says, where it goes, and what Replace All does.

The window is shared by QUILL and QUILL Lite; these drive its logic through a
fake host, the way each editor's adapter drives it for real.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.find_model import FindQuery
from quill.core.open_documents_search import OpenDoc
from quill.ui import open_documents_find as odf


class _Host:
    def __init__(self, texts: list[str], *, editable: list[bool] | None = None) -> None:
        self.texts = list(texts)
        self.editable = editable or [True] * len(texts)
        self.front = 0
        self.sel = (0, 0)
        self.said: list[str] = []
        self.writes: list[tuple[int, str, list[tuple[int, int, str]]]] = []
        self.state = odf.OpenDocumentsState()
        self.parent = None

    def documents(self) -> list[OpenDoc]:
        return [
            OpenDoc(f"Doc {i + 1}", text, ok)
            for i, (text, ok) in enumerate(zip(self.texts, self.editable, strict=True))
        ]

    def current(self) -> int:
        return self.front

    def selection(self) -> tuple[int, int]:
        return self.sel

    def go_to(self, index: int, start: int, end: int) -> None:
        self.front, self.sel = index, (start, end)

    def write(self, index: int, new_text: str, spans: list[tuple[int, int, str]]) -> None:
        self.writes.append((index, new_text, spans))
        self.texts[index] = new_text

    def announce(self, text: str) -> None:
        self.said.append(text)

    def show_modal(self, dialog: Any, label: str) -> int:  # pragma: no cover - not reached
        raise AssertionError("no window in these tests")


def test_find_next_stays_in_the_document_and_reads_the_line() -> None:
    host = _Host(["one cat\ntwo cat"])
    assert odf._step(host, FindQuery("cat"), backwards=False)
    assert host.sel == (4, 7)
    assert host.said[-1] == "Line 1: one cat"  # no document name: it did not move


def test_moving_to_another_document_says_its_name() -> None:
    host = _Host(["no", "the cat sat"])
    odf._step(host, FindQuery("cat"), backwards=False)
    assert (host.front, host.sel) == (1, (4, 7))
    assert host.said[-1] == "Doc 2, line 1: the cat sat"


def test_coming_back_round_says_so() -> None:
    host = _Host(["cat", "dog"])
    host.sel = (3, 3)
    odf._step(host, FindQuery("cat"), backwards=False)
    assert host.said[-1].startswith("Back to the start. Doc 1, line 1")


def test_a_miss_counts_the_documents_it_looked_in() -> None:
    host = _Host(["a", "b", "c"])
    assert not odf._step(host, FindQuery("zebra"), backwards=False)
    assert host.said[-1] == 'No matches for "zebra" in 3 open documents.'


def test_f3_carries_on_only_after_a_search_here_and_not_after_ordinary_find() -> None:
    host = _Host(["x", "cat"])
    assert odf.find_again(host) is False  # nothing searched here yet
    host.state.query, host.state.active = FindQuery("cat"), True
    assert odf.find_again(host) is True
    assert host.front == 1
    host.state.end()
    assert odf.find_again(host) is False  # ordinary Find owns F3 again


def test_replace_all_asks_with_the_count_first_and_cancel_changes_nothing() -> None:
    host = _Host(["cat cat", "none", "cat"])
    asked: list[str] = []
    assert not odf._replace_all(host, FindQuery("cat"), "dog", lambda q: asked.append(q) or False)
    assert asked[0].startswith("3 matches in 2 of 3 open documents. Replace them all?")
    assert host.writes == []


def test_replace_all_writes_each_document_and_saves_nothing() -> None:
    host = _Host(["cat cat", "none", "cat"], editable=[True, True, False])
    assert odf._replace_all(host, FindQuery("cat"), "dog", lambda _q: True)
    assert [(i, text) for i, text, _spans in host.writes] == [(0, "dog dog")]
    assert host.writes[0][2] == [(4, 7, "dog"), (0, 3, "dog")]  # last first
    assert host.said[-1] == (
        "Replaced 2 in 1 documents. Nothing has been saved. Left 1 read-only documents alone."
    )


def test_a_bad_pattern_is_reported_not_swallowed() -> None:
    host = _Host(["text"])
    odf._step(host, FindQuery("(", mode="regex"), backwards=False)
    assert host.said and "No matches" not in host.said[-1]


class _Control:
    def __init__(self, text: str) -> None:
        self.text = text
        self.edits: list[tuple[int, int, str]] = []

    def GetValue(self) -> str:
        return self.text

    def SetSelection(self, start: int, end: int) -> None:
        self.sel = (start, end)

    def WriteText(self, text: str) -> None:
        start, end = self.sel
        self.edits.append((start, end, text))
        self.text = self.text[:start] + text + self.text[end:]


def test_plain_text_is_one_undo_step_for_the_whole_document() -> None:
    control = _Control("a cat and a cat")
    odf.replace_text_in(control, "a dog and a dog", [(12, 15, "dog"), (2, 5, "dog")], rich=False)
    assert control.text == "a dog and a dog"
    assert len(control.edits) == 1  # one write, one Ctrl+Z


def test_formatted_text_is_replaced_match_by_match_so_formatting_between_survives() -> None:
    control = _Control("a cat and a cat")
    odf.replace_text_in(control, "a dog and a dog", [(12, 15, "dog"), (2, 5, "dog")], rich=True)
    assert control.text == "a dog and a dog"
    assert control.edits == [(12, 15, "dog"), (2, 5, "dog")]  # " and a " never rewritten


# -- QUILL's adapter and its F3 ---------------------------------------------


def _quill_frame(texts: list[str]) -> Any:
    from quill.ui.main_frame_open_documents import OpenDocumentsFindMixin

    class _Search:
        def find_next(self) -> None:
            self.ordinary.append("next")

        def find_previous(self) -> None:
            self.ordinary.append("previous")

        def find_text(self) -> None:
            self.ordinary.append("find")

        def replace_text(self) -> None:
            self.ordinary.append("replace")

    class _Frame(OpenDocumentsFindMixin, _Search):
        pass

    frame = _Frame()
    frame.ordinary = []
    frame.said = []
    frame._announce = frame.said.append
    frame._document_tabs = []
    for i, text in enumerate(texts):
        control = _Control(text)
        control.GetSelection = lambda c=control: getattr(c, "sel", (0, 0))
        control.ShowPosition = lambda _pos: None
        frame._document_tabs.append(
            SimpleNamespace(
                editor=control,
                document=SimpleNamespace(name=f"Tab {i + 1}", set_text=lambda _t: None),
                editor_mode="markup",
            )
        )
    frame._active_tab_index = 0
    frame.editor = frame._document_tabs[0].editor

    def select_tab(index: int) -> None:
        frame._active_tab_index = index
        frame.editor = frame._document_tabs[index].editor

    frame._select_tab = select_tab
    return frame


def test_quill_f3_is_ordinary_until_a_search_across_tabs() -> None:
    frame = _quill_frame(["x", "the cat"])
    frame.find_next()
    assert frame.ordinary == ["next"]
    from quill.ui.main_frame_open_documents import _state

    _state(frame).query, _state(frame).active = FindQuery("cat"), True
    frame.find_next()
    assert frame._active_tab_index == 1
    assert frame.editor.sel == (4, 7)
    assert frame.said[-1] == "Tab 2, line 1: the cat"
    frame.find_text()  # Ctrl+F: an ordinary Find
    frame.find_next()
    assert frame.ordinary == ["next", "find", "next"]


def test_quill_lists_every_tab_including_untitled_and_skips_none() -> None:
    from quill.ui.main_frame_open_documents import QuillOpenDocuments

    frame = _quill_frame(["one", "two", "three"])
    frame._document_tabs[2].document.name = ""
    docs = QuillOpenDocuments(frame).documents()
    assert [doc.name for doc in docs] == ["Tab 1", "Tab 2", "Untitled"]

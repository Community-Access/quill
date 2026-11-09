"""The shared Word Prediction list (quill.ui.suggestion_list), driven through
QUILL's adapter (quill.ui.main_frame_intellisense) with wx left out.

Locked in: the key opens the list in every profile, "as you type" stays off
unless both the setting and the profile allow it, Escape never changes the
text, and inserting replaces only the fragment typed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.ui.main_frame_intellisense import IntellisensePopupMixin

_WX = SimpleNamespace(
    WXK_ESCAPE=27, WXK_RETURN=13, WXK_NUMPAD_ENTER=370, WXK_TAB=9, WXK_UP=315, WXK_DOWN=317
)


class _Editor:
    def __init__(self, text: str, caret: int) -> None:
        self.text, self.caret = text, caret

    def GetValue(self) -> str:  # noqa: N802 - wx spelling
        return self.text

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.caret

    def SetInsertionPoint(self, value: int) -> None:  # noqa: N802
        self.caret = value

    def SetSelection(self, start: int, _end: int) -> None:  # noqa: N802
        self.caret = start

    def Replace(self, start: int, end: int, text: str) -> None:  # noqa: N802
        self.text = self.text[:start] + text + self.text[end:]

    def SetFocus(self) -> None:  # noqa: N802
        pass

    def GetScreenPosition(self) -> Any:  # noqa: N802
        return SimpleNamespace(x=0, y=0)


class _Popup:
    def __init__(self) -> None:
        self.visible, self.suggestions, self.index = False, [], 0

    def update(self, suggestions: list, _status: str) -> None:
        self.suggestions, self.index = list(suggestions), 0

    def show(self, _position: Any) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def is_visible(self) -> bool:
        return self.visible

    def selection_index(self) -> int:
        return self.index

    def set_selection(self, index: int) -> None:
        self.index = max(0, min(index, len(self.suggestions) - 1))

    def selected_suggestion(self) -> Any:
        return self.suggestions[self.index] if self.suggestions else None


class _Host(IntellisensePopupMixin):
    def __init__(
        self, text: str, caret: int, *, as_you_type: bool = False, profile_on: bool = True
    ) -> None:
        self._wx = _WX
        self.editor = _Editor(text, caret)
        self.settings = SimpleNamespace(intellisense_as_you_type=as_you_type)
        self._intellisense_popup = _Popup()
        self.status: list[str] = []
        self._profile_on = profile_on

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _spell_dictionary(self) -> set[str]:
        return {"counter", "country", "county"}

    def _feature_enabled(self, _feature: str) -> bool:
        return self._profile_on


@pytest.fixture(autouse=True)
def _quiet(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    said: list[str] = []
    monkeypatch.setattr("quill.ui.main_frame_intellisense.announce", said.append)
    return said


def _key(code: int) -> Any:
    return SimpleNamespace(GetKeyCode=lambda: code)


def test_the_key_opens_the_list_even_in_a_profile_without_word_prediction(_quiet) -> None:
    host = _Host("the coun", 8, profile_on=False)
    assert host._show_intellisense_popup(manual=True)
    assert host._intellisense_popup.visible
    assert _quiet[-1].startswith(f"{len(host._intellisense_popup.suggestions)} prediction(s). ")


def test_as_you_type_needs_the_setting_and_the_profile() -> None:
    assert not _Host("coun", 4)._show_intellisense_popup(manual=False)
    assert not _Host("coun", 4, as_you_type=True, profile_on=False)._show_intellisense_popup(
        manual=False
    )
    assert _Host("coun", 4, as_you_type=True)._show_intellisense_popup(manual=False)


@pytest.mark.parametrize("caret", [4, 8, 2])
def test_escape_never_changes_the_text(caret: int) -> None:
    text = "the coun ty"
    host = _Host(text, caret)
    host._show_intellisense_popup(manual=True)
    assert (
        host._handle_intellisense_key_down(_key(_WX.WXK_DOWN))
        or not host._intellisense_popup.visible
    )
    host._handle_intellisense_key_down(_key(_WX.WXK_ESCAPE))
    assert host.editor.text == text
    assert not host._intellisense_popup.visible


def test_inserting_replaces_only_the_fragment_typed() -> None:
    host = _Host("the coun is here", 8)
    host._show_intellisense_popup(manual=True)
    chosen = host._intellisense_popup.selected_suggestion()
    assert host._handle_intellisense_key_down(_key(_WX.WXK_TAB))
    assert host.editor.text == f"the {chosen.inserted_text} is here"
    assert host.status[-1] == f'Inserted prediction "{chosen.label}".'


def test_closed_list_lets_every_key_through() -> None:
    host = _Host("text", 4)
    for code in (_WX.WXK_ESCAPE, _WX.WXK_RETURN, _WX.WXK_UP):
        assert not host._handle_intellisense_key_down(_key(code))


def test_in_a_code_file_the_list_is_the_files_names_with_kinds(_quiet) -> None:
    text = "def count_words(t):\n    pass\n\ncou"
    host = _Host(text, len(text))
    host.document = SimpleNamespace(path="tool.py")
    assert host._show_intellisense_popup(manual=True)
    assert _quiet[-1] == "1 suggestion. count_words, function"
    host._handle_intellisense_key_down(_key(_WX.WXK_DOWN))
    assert _quiet[-1] == "count_words, function"
    host._handle_intellisense_key_down(_key(_WX.WXK_RETURN))
    assert host.editor.text.endswith("\ncount_words")


def test_project_names_fill_the_list_after_a_background_walk(tmp_path, monkeypatch, _quiet) -> None:
    from quill.ui import suggestion_list

    monkeypatch.setattr(suggestion_list, "_PROJECT_INDEXES", {})
    monkeypatch.setattr(suggestion_list, "_PROJECT_BUILDS", set())
    (tmp_path / ".git").mkdir()
    (tmp_path / "shapes.py").write_text("def rectangle_area(r):\n    return r\n", encoding="utf-8")
    jobs: list = []

    class _ProjectHost(_Host):
        def _suggest_in_background(self, work, done) -> bool:
            jobs.append((work, done))
            return True

    text = "from shapes import rectangle_area\nrect"
    host = _ProjectHost(text, len(text))
    host.document = SimpleNamespace(path=str(tmp_path / "main.py"))
    host._show_intellisense_popup(manual=True)
    assert len(jobs) == 1, "the first press starts the walk, off the UI thread"
    work, done = jobs.pop()
    done(work())
    host._hide_intellisense_popup()
    text = "x = 1\nrect"
    host.editor = _Editor(text, len(text))
    assert host._show_intellisense_popup(manual=True)
    assert _quiet[-1] == "1 suggestion. rectangle_area, function"
    assert jobs == [], "a fresh index is reused, not rebuilt"


def test_no_background_runner_means_no_project_walk(tmp_path, monkeypatch) -> None:
    from quill.ui import suggestion_list
    from quill.ui.suggestion_list import SuggestionListMixin

    monkeypatch.setattr(suggestion_list, "_PROJECT_INDEXES", {})
    monkeypatch.setattr(suggestion_list, "_PROJECT_BUILDS", set())
    host = _Host("rect", 4)
    host.document = SimpleNamespace(path=str(tmp_path / "main.py"))
    assert SuggestionListMixin._suggest_in_background(host, lambda: None, lambda _r: None) is False
    host._suggest_in_background = lambda work, done: False  # type: ignore[method-assign]
    host._show_intellisense_popup(manual=True)
    assert suggestion_list._PROJECT_BUILDS == set()


# -- review 2026-11-09 -----------------------------------------------------------


class _UndoEditor(_Editor):
    """Records the select-and-write pair replace_as_one_undo uses."""

    def __init__(self, text: str, caret: int) -> None:
        super().__init__(text, caret)
        self.selection = (caret, caret)
        self.writes: list[tuple[int, int, str]] = []

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.selection, self.caret = (start, end), start

    def WriteText(self, text: str) -> None:  # noqa: N802
        from quill.core.text_units import text_index

        start, end = self.selection
        self.writes.append((start, end, text))
        # Positions are the control's UTF-16 units; the string is code points.
        first, last = text_index(self.text, start), text_index(self.text, end)
        self.text = self.text[:first] + text + self.text[last:]


def test_enter_inserts_for_the_word_at_the_caret_now_not_at_the_last_refresh() -> None:
    """QUILL 7: type-and-Enter before the list caught up gave "countern"."""
    host = _Host("the coun", 8)
    host._show_intellisense_popup(manual=True)
    chosen = host._intellisense_popup.selected_suggestion()
    host.editor.text, host.editor.caret = "the count", 9  # typed; no refresh yet
    host._handle_intellisense_key_down(_key(_WX.WXK_RETURN))
    assert host.editor.text == f"the {chosen.inserted_text}"


def test_a_caret_key_closes_the_list_and_still_moves_the_caret() -> None:
    """QUILL 7: Left, Home and the like are not typing."""
    wx_keys = SimpleNamespace(**vars(_WX), WXK_LEFT=314, WXK_HOME=313)
    host = _Host("the coun", 8)
    host._wx = wx_keys
    host._show_intellisense_popup(manual=True)
    assert host._handle_intellisense_key_down(_key(314)) is False, "the key goes on"
    assert not host._intellisense_popup.visible
    assert host.editor.text == "the coun"


def test_focus_leaving_the_text_closes_the_list(monkeypatch) -> None:
    """QUILL 7 / QUILL Lite 9: deactivation or focus elsewhere hides it."""
    host = _Host("the coun", 8)
    host._show_intellisense_popup(manual=True)
    focus: list[Any] = [host.editor]
    host._intellisense_popup.contains = lambda window: False
    host._suggest_wx = lambda: SimpleNamespace(  # type: ignore[method-assign]
        Window=SimpleNamespace(FindFocus=lambda: focus[0])
    )
    host._hide_unless_focus_is_ours()
    assert host._intellisense_popup.visible, "still in the text: stays"
    focus[0] = None  # another program is in front
    host._hide_unless_focus_is_ours()
    assert not host._intellisense_popup.visible


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="UTF-16 positions are wxMSW's")
def test_an_emoji_before_the_word_does_not_shift_the_insert() -> None:
    """QUILL 5 and QUILL 12: the right span, in the control's units, as one undo step."""
    text = "\U0001f600 the coun is here"
    host = _Host(text, 0)
    host.editor = _UndoEditor(text, len("\U0001f600 the coun".encode("utf-16-le")) // 2)
    host._show_intellisense_popup(manual=True)
    chosen = host._intellisense_popup.selected_suggestion()
    host._handle_intellisense_key_down(_key(_WX.WXK_TAB))
    assert host.editor.text == f"\U0001f600 the {chosen.inserted_text} is here"
    assert host.editor.writes == [(7, 11, chosen.inserted_text)], "one select-and-write"
    assert host.editor.caret == 7 + len(chosen.inserted_text)


def test_a_loose_file_starts_no_project_walk(tmp_path, monkeypatch) -> None:
    """QUILL Lite 12: no marker, no index of the folder around it."""
    from quill.ui import suggestion_list

    monkeypatch.setattr(suggestion_list, "_PROJECT_INDEXES", {})
    monkeypatch.setattr(suggestion_list, "_PROJECT_BUILDS", set())
    jobs: list[Any] = []
    host = _Host("rect", 4)
    host._suggest_in_background = lambda work, done: jobs.append(work) or True  # type: ignore[method-assign]
    host.document = SimpleNamespace(path=str(tmp_path / "main.py"))
    host._show_intellisense_popup(manual=True)
    assert jobs == []

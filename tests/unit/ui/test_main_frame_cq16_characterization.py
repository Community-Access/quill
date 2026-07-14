"""Characterization tests pinning MainFrame behavior ahead of CQ-1 (CQ-16).

These lock the observable behavior of four high-traffic areas — menus, the
QUILL key surface, selection, and the file lifecycle — so the planned
decomposition of the 22k-line ``main_frame`` module stays behavior-preserving.

The QUILL-key surface itself is pinned in ``test_main_frame_quill_key.py``; this
module focuses on the menu-state, selection, and file-lifecycle seams that had no
isolated coverage. Every test uses the established ``MainFrame.__new__`` harness
(no wx widget tree) and stubs only the attributes each method touches.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.ui.main_frame import MainFrame


def _bare() -> MainFrame:
    return MainFrame.__new__(MainFrame)


class _FakeEditor:
    def __init__(self, text: str = "", selection: tuple[int, int] = (0, 0)) -> None:
        self._text = text
        self._selection = selection
        self.insertion_point = selection[0]
        self.set_selection_calls: list[tuple[int, int]] = []
        self.focused = False

    def GetValue(self) -> str:
        return self._text

    def GetSelection(self) -> tuple[int, int]:
        return self._selection

    def GetInsertionPoint(self) -> int:
        return self.insertion_point

    def SetFocus(self) -> None:
        self.focused = True

    def SetSelection(self, start: int, end: int) -> None:
        self._selection = (start, end)
        self.set_selection_calls.append((start, end))


# ---------------------------------------------------------------------------
# MENUS
# ---------------------------------------------------------------------------


def test_menu_updates_are_blocked_while_a_menu_is_open() -> None:
    frame = _bare()
    # Default (attribute absent) is "allowed".
    assert frame._menu_updates_allowed() is True
    frame._menu_open_depth = 0
    assert frame._menu_updates_allowed() is True
    frame._menu_open_depth = 1
    assert frame._menu_updates_allowed() is False
    frame._menu_open_depth = 3
    assert frame._menu_updates_allowed() is False


def test_markup_context_prefers_extension_then_content() -> None:
    frame = _bare()

    frame.document = SimpleNamespace(path=Path("note.md"))
    frame.editor = _FakeEditor("plain words")
    assert frame._current_markup_context() == "markdown"

    frame.document = SimpleNamespace(path=Path("page.HTML"))
    assert frame._current_markup_context() == "html"

    # No extension hint: fall back to a content sniff.
    frame.document = SimpleNamespace(path=None)
    frame.editor = _FakeEditor("<html><body><p>hi</p></body></html>")
    assert frame._current_markup_context() == "html"

    frame.editor = _FakeEditor("# Title\n\n- one\n- two\n")
    assert frame._current_markup_context() == "markdown"

    frame.editor = _FakeEditor("just an ordinary sentence with no markup")
    assert frame._current_markup_context() == "plain"


# ---------------------------------------------------------------------------
# SELECTION
# ---------------------------------------------------------------------------


def test_has_active_selection_requires_a_nonempty_range() -> None:
    frame = _bare()

    frame.editor = _FakeEditor(selection=(4, 4))
    assert frame._has_active_selection() is False

    frame.editor = _FakeEditor(selection=(2, 7))
    assert frame._has_active_selection() is True

    # Defensive: a frame with no editor must not raise.
    frame.editor = None
    assert frame._has_active_selection() is False


def test_selection_action_specs_adapt_to_scope_and_surface() -> None:
    frame = _bare()

    word_plain = [label for label, _ in frame._selection_action_specs("word", None)]
    assert "Copy" in word_plain
    assert "Upper case" in word_plain
    assert "Expand selection" in word_plain
    # No markup surface -> no emphasis actions; single word -> no line actions.
    assert "Bold" not in word_plain
    assert "Italic" not in word_plain
    assert "Sort lines ascending" not in word_plain
    assert "Toggle line comment" not in word_plain

    line_markup = [label for label, _ in frame._selection_action_specs("line", "markdown")]
    assert "Bold" in line_markup
    assert "Italic" in line_markup
    assert "Sort lines ascending" in line_markup
    assert "Indent" in line_markup
    assert "Toggle line comment" in line_markup


def test_expand_then_shrink_selection_round_trips_through_the_stack() -> None:
    frame = _bare()
    frame.editor = _FakeEditor("hello world", selection=(0, 0))
    frame._selection_expand_stack = []
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]
    frame._announce_selection_scope = lambda *a, **k: None  # type: ignore[method-assign]

    frame.expand_selection()
    # The pre-expand range is pushed so shrink can restore it.
    assert frame._selection_expand_stack == [(0, 0)]
    expanded = frame.editor.GetSelection()
    assert expanded != (0, 0)

    frame.shrink_selection()
    assert frame._selection_expand_stack == []
    assert frame.editor.GetSelection() == (0, 0)

    # Shrinking with an empty stack is a no-op that announces, not an error.
    frame.shrink_selection()
    assert statuses[-1] == "No selection to shrink"


# ---------------------------------------------------------------------------
# FILE LIFECYCLE
# ---------------------------------------------------------------------------


def test_find_tab_index_matches_resolved_paths() -> None:
    frame = _bare()
    a = SimpleNamespace(document=SimpleNamespace(path=Path("alpha.txt")))
    b = SimpleNamespace(document=SimpleNamespace(path=Path("beta.txt")))
    untitled = SimpleNamespace(document=SimpleNamespace(path=None))
    frame._document_tabs = [a, untitled, b]

    assert frame._find_tab_index(None) == -1
    assert frame._find_tab_index(Path("beta.txt")) == 2
    assert frame._find_tab_index(Path("gamma.txt")) == -1


def test_title_subject_and_dirty_suffix_follow_settings() -> None:
    frame = _bare()
    frame.document = SimpleNamespace(name="note.md", path=Path("/tmp/note.md"), modified=False)
    frame.settings = SimpleNamespace(title_bar_path_mode="name", dirty_title_style="text")
    assert frame._title_subject() == "note.md"
    assert frame._dirty_title_suffix() == ""

    frame.settings.title_bar_path_mode = "full_path"
    assert frame._title_subject() == str(Path("/tmp/note.md"))

    frame.document.modified = True
    frame.settings.dirty_title_style = "asterisk"
    assert frame._dirty_title_suffix() == " *"
    frame.settings.dirty_title_style = "asterisk_text"
    assert frame._dirty_title_suffix() == " * [modified]"
    frame.settings.dirty_title_style = "text"
    assert frame._dirty_title_suffix() == " [modified]"


def test_prompt_to_save_active_document_decision_table() -> None:
    frame = _bare()
    frame._wx = SimpleNamespace(ID_CANCEL=5101, ID_YES=5103, ID_NO=5104)
    prompt_calls: list[tuple[Any, ...]] = []
    kwarg_calls: list[dict[str, Any]] = []

    def _prompt(*args: Any, **_kwargs: Any) -> int:
        prompt_calls.append(args)
        kwarg_calls.append(_kwargs)
        return frame._next_prompt_result

    frame._prompt_unsaved_changes_action = _prompt  # type: ignore[method-assign]
    frame.save_file = lambda: setattr(frame.document, "modified", False)  # type: ignore[method-assign]

    # Clean document: returns True and never prompts.
    frame.document = SimpleNamespace(modified=False)
    assert frame._prompt_to_save_active_document("closing") is True
    assert prompt_calls == []

    # Cancel: abort the action.
    frame.document = SimpleNamespace(modified=True)
    frame._next_prompt_result = frame._wx.ID_CANCEL
    assert frame._prompt_to_save_active_document("closing") is False

    # Save: saves, then reports success because the doc is now clean.
    frame.document = SimpleNamespace(modified=True)
    frame._next_prompt_result = frame._wx.ID_YES
    assert frame._prompt_to_save_active_document("closing") is True
    assert frame.document.modified is False

    # Don't Save: proceed without saving.
    frame.document = SimpleNamespace(modified=True)
    frame._next_prompt_result = frame._wx.ID_NO
    assert frame._prompt_to_save_active_document("closing") is True
    assert frame.document.modified is True

    # #619: the close path must pass restore_focus=False so the queued
    # editor.SetFocus does not fire after DeletePage destroys the TextCtrl.
    assert kwarg_calls, "the save prompt must have been invoked at least once"
    assert all(call.get("restore_focus") is False for call in kwarg_calls), (
        "#619: every close-path save prompt must pass restore_focus=False"
    )


def test_switch_document_wraps_around_and_guards_single_tab() -> None:
    frame = _bare()
    statuses: list[str] = []
    selected: list[int] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]
    frame._select_tab = selected.append  # type: ignore[method-assign]
    frame.document = SimpleNamespace(name="B.md")

    # Single tab: nothing to switch to.
    frame._document_tabs = [object()]
    frame._switch_document(reverse=False)
    assert selected == []
    assert statuses[-1] == "No other open document to switch to"

    # Three tabs, currently on index 0.
    frame._document_tabs = [object(), object(), object()]
    frame._current_tab_index = lambda: 0  # type: ignore[method-assign]
    frame._switch_document(reverse=False)
    assert selected[-1] == 1
    frame._switch_document(reverse=True)
    # From index 0 going back wraps to the last tab.
    assert selected[-1] == 2
    assert statuses[-1] == "Switched to B.md"


def test_write_document_to_disk_routes_by_extension(monkeypatch) -> None:
    import quill.io.export as export_module

    rtf_calls: list[tuple[object, Path | None]] = []
    verbatim_calls: list[tuple[object, Path | None]] = []
    monkeypatch.setattr(
        export_module,
        "write_rtf_document",
        lambda doc, target=None, **kwargs: rtf_calls.append((doc, target)),
    )
    monkeypatch.setattr(
        export_module,
        "write_text_document",
        lambda doc, target=None, **kwargs: verbatim_calls.append((doc, target)),
    )

    frame = _bare()

    # A .txt target is written verbatim — no Markdown stripping and no blank-line
    # collapsing (#649). (The explicit "Save as plain text" command still flattens
    # markup; Save / Save As by extension does not.)
    txt_doc = SimpleNamespace(path=Path("note.txt"))
    frame._write_document_to_disk(txt_doc)
    assert verbatim_calls[-1] == (txt_doc, Path("note.txt"))
    assert rtf_calls == []

    # A .md target is also written verbatim (already Markdown).
    md_doc = SimpleNamespace(path=Path("note.md"))
    frame._write_document_to_disk(md_doc)
    assert verbatim_calls[-1] == (md_doc, Path("note.md"))

    # A .rtf path routes through the RTF writer.
    rtf_doc = SimpleNamespace(path=Path("note.rtf"))
    frame._write_document_to_disk(rtf_doc)
    assert rtf_calls[-1] == (rtf_doc, Path("note.rtf"))

    # An explicit .rtf target overrides a non-rtf document path.
    other = SimpleNamespace(path=Path("note.txt"))
    frame._write_document_to_disk(other, Path("export.rtf"))
    assert rtf_calls[-1] == (other, Path("export.rtf"))

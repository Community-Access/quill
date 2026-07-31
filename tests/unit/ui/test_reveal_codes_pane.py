"""Interaction tests for the Reveal Codes pane's flowed (interactive) surface.

The pure caret math is covered in ``tests/unit/core/test_reveal_nav.py``; here we
lock in the thin wx layer: arrowing speaks the character/code with *no* repeated
"Reveal Codes" prefix (the original complaint), and F2 edits a bounded run back
into the editor buffer.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.ui.reveal_codes_pane import RevealCodesPane

wx = pytest.importorskip("wx")


@pytest.fixture
def app():
    application = wx.App(False)
    yield application
    application.Destroy()


class _FakeEvent:
    def __init__(self, key: int, *, ctrl: bool = False) -> None:
        self._key = key
        self._ctrl = ctrl
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._key

    def ControlDown(self) -> bool:
        return self._ctrl

    def Skip(self) -> None:
        self.skipped = True


def _make_host(frame, markup: str):
    editor = wx.TextCtrl(frame, style=wx.TE_MULTILINE)
    editor.SetValue(markup)
    editor.SetInsertionPoint(0)
    spoken: list[str] = []
    host = SimpleNamespace(
        editor=editor,
        settings=SimpleNamespace(
            reveal_codes_view="flowed",
            reveal_codes_verbosity="balanced",
            reveal_codes_visible=True,
        ),
        spoken=spoken,
    )
    host._announce = lambda msg, **kw: spoken.append(msg)  # type: ignore[attr-defined]
    host._set_status = lambda msg: spoken.append(("status", msg))  # type: ignore[attr-defined]
    host._set_status_quiet = lambda msg: None  # type: ignore[attr-defined]
    host._reveal_move_editor_caret = lambda off: editor.SetInsertionPoint(max(0, off))  # type: ignore[attr-defined]
    return host, editor, spoken


def test_plain_text_moves_are_silent_so_the_screen_reader_narrates(app) -> None:
    frame = wx.Frame(None)
    host, editor, spoken = _make_host(frame, "ab")
    pane = RevealCodesPane(wx, frame, host)
    pane.rebuild()
    pane._caret = 0

    pane._on_flow_key(_FakeEvent(wx.WXK_RIGHT))
    pane._on_flow_key(_FakeEvent(wx.WXK_RIGHT))

    # The flowed control is a real text control; the screen reader reads each
    # character move itself. QUILL stays quiet on text so nothing is said twice.
    assert spoken == []
    frame.Destroy()


def test_right_arrow_steps_over_a_code_atomically_and_only_the_code_speaks(app) -> None:
    frame = wx.Frame(None)
    host, editor, spoken = _make_host(frame, "a**b**c")
    pane = RevealCodesPane(wx, frame, host)
    pane.rebuild()
    pane._caret = 0  # on 'a'

    pane._on_flow_key(_FakeEvent(wx.WXK_RIGHT))  # -> [Bold On]: QUILL speaks it
    assert "bold on" in spoken[-1]
    assert "Reveal Codes" not in spoken[-1]  # bare phrase, no repeated prefix
    pane._on_flow_key(_FakeEvent(wx.WXK_RIGHT))  # -> 'b': text, so QUILL is silent
    assert spoken == [spoken[0]]  # nothing new was spoken for the character
    frame.Destroy()


def test_f2_edits_a_bounded_run_back_into_the_editor(app) -> None:
    frame = wx.Frame(None)
    host, editor, spoken = _make_host(frame, "**Hello** world")
    pane = RevealCodesPane(wx, frame, host)
    pane.rebuild()
    # Land the caret on a character inside the bold run.
    hello_cell = next(i for i, c in enumerate(pane._flow_view.cells) if c.char == "H")
    pane._caret = hello_cell

    pane._on_flow_key(_FakeEvent(wx.WXK_F2))
    assert pane._edit_region is not None
    assert pane._flow.GetValue() == "Hello"  # only the run is editable

    pane._flow.SetValue("Goodbye")
    pane._on_flow_key(_FakeEvent(wx.WXK_RETURN))

    assert pane._edit_region is None
    assert editor.GetValue() == "**Goodbye** world"  # codes preserved, run replaced
    frame.Destroy()


def test_f2_on_unbounded_text_declines(app) -> None:
    frame = wx.Frame(None)
    host, editor, spoken = _make_host(frame, "plain words")
    pane = RevealCodesPane(wx, frame, host)
    pane.rebuild()
    pane._caret = 0

    pane._on_flow_key(_FakeEvent(wx.WXK_F2))
    assert pane._edit_region is None
    assert any("Not inside a formatting code" in str(s) for s in spoken)
    frame.Destroy()


def test_f2_spans_the_whole_region_including_a_tab(app) -> None:
    frame = wx.Frame(None)
    host, editor, spoken = _make_host(frame, "**Hello\tworld**")
    pane = RevealCodesPane(wx, frame, host)
    pane.rebuild()
    # Land the caret on the tab code inside the bold run.
    tab_cell = next(i for i, c in enumerate(pane._flow_view.cells) if c.label == "[Tab]")
    pane._caret = tab_cell

    pane._on_flow_key(_FakeEvent(wx.WXK_F2))
    assert pane._edit_region is not None
    assert pane._flow.GetValue() == "Hello\tworld"  # the whole span, tab included

    pane._flow.SetValue("Hi\tthere")
    pane._on_flow_key(_FakeEvent(wx.WXK_RETURN))
    assert editor.GetValue() == "**Hi\tthere**"
    frame.Destroy()


def test_editor_caret_moves_keep_the_pane_in_sync_any_movement(app) -> None:
    frame = wx.Frame(None)
    host, editor, spoken = _make_host(frame, "**Hello** world")
    pane = RevealCodesPane(wx, frame, host)
    pane.rebuild()

    # Simulate arbitrary editor caret movement (arrow, mouse, jump — the pane only
    # sees the resulting offset): land inside the bold word, then out in " world".
    editor.SetInsertionPoint(4)  # inside "Hello"
    pane.sync_from_editor()
    assert pane._flow_view.cells[pane._caret].char in set("Hello")

    editor.SetInsertionPoint(12)  # inside " world"
    pane.sync_from_editor()
    assert pane._flow_view.cells[pane._caret].char in set(" world")
    frame.Destroy()

"""FUX-12: F8 and Shift+F8 move change by change through a read-only diff text."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.change_walk import change_starts, next_stop
from quill.core.diff_marks import render_texts

# An emoji before a change: Windows counts it as two positions.
REPORT = render_texts(
    "one \U0001f600\ntwo\nthree\nfour\nfive\nsix\nseven\neight\nnine\nten\n",
    "one \U0001f600\nTWO\nthree\nfour\nfive\nsix\nseven\neight\nnine\nTEN\n",
    "the copy on Site",
    "your copy",
)


def test_every_renderer_header_starts_a_change() -> None:
    text = "\n".join([
        "summary",
        "Difference 1 of 2. Text changed at line 3.",
        "Removed: a",
        "Lines 10 to 15:",
        "At line 4:",
        "A change:",
        "@@ -1,2 +1,2 @@",
        "Added: Lines 3 to 4: is not a header",
        "@@ not a hunk header",
    ])
    assert change_starts(text) == [1, 3, 4, 5, 6]


def test_next_and_previous_say_which_change_of_how_many() -> None:
    assert len(change_starts(REPORT)) == 2
    first = next_stop(REPORT, 0)
    assert first is not None and first.position == 1 and first.total == 2
    assert first.spoken().startswith("Change 1 of 2. ")
    second = next_stop(REPORT, first.line)
    assert second is not None and second.position == 2
    assert next_stop(REPORT, second.line) is None
    # Back from inside the second change goes to its own start first.
    back = next_stop(REPORT, second.line + 1, forward=False)
    assert back is not None and back.line == second.line
    assert next_stop(REPORT, first.line, forward=False) is None


def test_the_engines_count_and_place_are_said_not_its_quoted_lines() -> None:
    text = "x\nDifference 2 of 5. Lines inserted at line 4. Added: 'a' Added: 'b'\nAdded: a\n"
    stop = next_stop(text, 0)
    assert stop is not None
    assert stop.spoken() == "Difference 2 of 5. Lines inserted at line 4."


# -- in a real text box ------------------------------------------------------------


@pytest.fixture
def frame(wx_session_app):
    import wx

    made = wx.Frame(None)
    yield made
    made.Destroy()


@pytest.mark.parametrize("rich", [True, False])
def test_the_caret_moves_to_the_change_and_it_is_said(frame, rich: bool) -> None:
    import wx

    from quill.ui.change_walk_keys import walk

    style = wx.TE_MULTILINE | wx.TE_READONLY | (wx.TE_RICH2 if rich else 0)
    box = wx.TextCtrl(frame, value=REPORT, style=style)
    said: list[str] = []
    starts = change_starts(REPORT)
    lines = REPORT.split("\n")

    def caret_line() -> str:
        before = str(box.GetRange(0, box.GetInsertionPoint()))
        assert before.endswith("\n")  # at a line's start, not inside one
        return lines[before.count("\n")]

    assert walk(box, said.append, forward=True)
    assert caret_line() == lines[starts[0]]
    assert said[-1].startswith("Change 1 of 2. ")
    assert walk(box, said.append, forward=True)
    assert caret_line() == lines[starts[1]]
    assert said[-1].startswith("Change 2 of 2. ")
    assert not walk(box, said.append, forward=True)
    assert said[-1] == "No more changes."
    assert walk(box, said.append, forward=False)
    assert said[-1].startswith("Change 1 of 2. ")
    assert not walk(box, said.append, forward=False)
    assert said[-1] == "No earlier changes."
    box.SetValue("a new file, shown whole")
    assert not walk(box, said.append, forward=True)
    assert said[-1] == "No changes in this file."


def test_f8_is_bound_and_other_keys_pass_through(frame) -> None:
    import wx

    from quill.ui import change_walk_keys

    box = wx.TextCtrl(frame, value=REPORT, style=wx.TE_MULTILINE | wx.TE_READONLY)
    handlers: list[Any] = []
    box.Bind = lambda _evt, handler: handlers.append(handler)  # type: ignore[method-assign]
    said: list[str] = []
    change_walk_keys.bind_change_walk(box, said.append)

    def key(code: int, *, shift: bool = False, ctrl: bool = False) -> SimpleNamespace:
        skipped: list[bool] = []
        event = SimpleNamespace(
            GetKeyCode=lambda: code,
            ShiftDown=lambda: shift,
            ControlDown=lambda: ctrl,
            AltDown=lambda: False,
            MetaDown=lambda: False,
            Skip=lambda: skipped.append(True),
        )
        handlers[0](event)
        return SimpleNamespace(skipped=bool(skipped))

    assert not key(wx.WXK_F8).skipped
    assert said[-1].startswith("Change 1 of 2.")
    assert not key(wx.WXK_F8, shift=True).skipped
    assert key(wx.WXK_F8, ctrl=True).skipped
    assert key(wx.WXK_DOWN).skipped


def test_compare_configuration_marks_lines_in_words(frame, tmp_path, monkeypatch) -> None:
    from quill.core.github import review_preferences
    from quill.ui.github_config_compare_dialog import ConfigCompareDialog

    monkeypatch.setattr(review_preferences, "app_data_dir", lambda: tmp_path)
    found = SimpleNamespace(
        state="different",
        target_text="name: ci\non: push\n",
        source_text="name: ci\non: [push, pull_request]\n",
        can_update=True,
        sentence=lambda: "workflow ci.yml: different",
    )
    dialog = ConfigCompareDialog(frame, "me/app", "me/template", [found])
    try:
        text = dialog.diff.GetValue()
        assert "Removed: on: push" in text and "Added: on: [push, pull_request]" in text
        assert "+on:" not in text
    finally:
        dialog.dialog.Destroy()


def test_compare_with_site_report_walks_when_given_a_voice(frame, monkeypatch) -> None:
    from quill.ui import change_walk_keys, wordpress_dialogs

    bound: list[Any] = []
    monkeypatch.setattr(
        change_walk_keys, "bind_change_walk", lambda ctrl, announce: bound.append(ctrl)
    )
    shown: list[Any] = []

    def show_modal(dialog: Any, _title: str) -> int:
        shown.append(dialog.text)
        return 0

    wordpress_dialogs.show_report(frame, show_modal, title="R", text=REPORT, help_text="h")
    assert bound == []
    wordpress_dialogs.show_report(
        frame, show_modal, title="R", text=REPORT, help_text="h", announce=lambda _m: None
    )
    assert bound == [shown[-1]]


def test_compare_with_site_passes_the_hosts_voice() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = (root / "quill" / "ui" / "wordpress_commands.py").read_text(encoding="utf-8")
    body = source[source.index("def cmd_compare(") : source.index("def to_html(")]
    assert "announce=self.host.announce" in body

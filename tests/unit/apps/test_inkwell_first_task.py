"""Inkwell's emptied abbreviation list names how to make a first entry (FUX-09)."""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def inkwell(quill_data_dir: Path, wx_session_app):
    from quill.apps.inkwell import QuillInkwellFrame

    frame = QuillInkwellFrame(safe_mode=True)  # no keyboard hook
    try:
        yield frame
    finally:
        frame._preference_saver.flush()
        timer = getattr(frame, "_ipc_timer", None)
        if timer is not None:
            timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()


def test_a_new_library_has_its_built_ins_and_no_line(inkwell) -> None:
    assert inkwell._list.GetItemCount() > 0
    assert not inkwell._first_task_line.shown


def test_an_emptied_library_names_manage_and_clipboard_and_takes_focus(
    inkwell, monkeypatch
) -> None:
    inkwell._library.abbreviations.clear()
    inkwell._reload_list()
    line = inkwell._first_task_line
    assert line.text == (
        "No abbreviations yet. Manage Abbreviations (Ctrl+M) makes one, or New from "
        "Clipboard (Ctrl+Shift+N) saves the copied text as one."
    )
    focused: list[str] = []
    monkeypatch.setattr(line.ctrl, "SetFocus", lambda: focused.append("line"))
    monkeypatch.setattr(inkwell._list, "SetFocus", lambda: focused.append("list"))
    inkwell._focus_initial_control()
    assert focused == ["line"]
    children = list(inkwell._list.GetParent().GetChildren())
    assert children.index(line.ctrl) < children.index(inkwell._list)


def test_the_list_keeps_its_own_spoken_name_with_the_line_before_it(inkwell, monkeypatch) -> None:
    from quill.apps import inkwell as app

    named: list[str] = []
    monkeypatch.setattr(app, "set_spoken_name", lambda _c, n: named.append(n))
    inkwell._build_main_panel()
    assert "Abbreviations" in named

"""Lists that stay still in QUILL Lite (FUX-06), and in QUILL, which shares them.

"Recent files, recovered drafts and the Problems list never move the selected
row or focus when they refresh in the background." (QUILL Lite PRD, Family UX
pilot, 2026-11-19.)

Modelled on the lists-stay-still section of ``tests/unit/apps/test_cast_one_window.py``:
put the reader on a row, change the list the way something in the background
would (rows arrive above, another row goes), let the real refill run, then
check the same item is selected, it is on the same line of the screen, keyboard
focus did not move, and nothing was said. All three widgets are the shared
ones in ``quill/ui``, so QUILL's lists are held to the same rule by the same
tests. Real wx controls; no frame, no hotkeys, so not ``machine_global``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.problems.model import CheckReport, Problem
from quill.core.problems.pane import follow_row

wx = pytest.importorskip("wx")


def _pump() -> None:
    app = wx.GetApp()
    for _ in range(3):
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()


@pytest.fixture
def frame(wx_session_app: Any):
    window = wx.Frame(None, size=(600, 300))
    # Something else holds keyboard focus, as the editor does while a quiet
    # check refills the pane: the refill must not take it.
    window.elsewhere = wx.TextCtrl(window)  # type: ignore[attr-defined]
    window.Show()
    window.elsewhere.SetFocus()  # type: ignore[attr-defined]
    _pump()
    yield window
    window.Destroy()


# -- the Problems pane --------------------------------------------------------- #


def _problem(line: int, message: str, severity: str = "error") -> Problem:
    return Problem(line, 1, severity, message, "JSON")


def _report(*problems: Problem) -> CheckReport:
    return CheckReport(language="json", problems=problems, checked_with=("JSON",))


@pytest.fixture
def pane(frame):
    from quill.ui.problems_pane import ProblemsPane

    said: list[str] = []
    widget = ProblemsPane(
        wx,
        frame,
        go_to=lambda _i: None,
        back_to_editor=lambda: None,
        copy_text=lambda _t: None,
        say=said.append,
    )
    widget.panel.SetSize((560, 140))  # a few rows on screen, so the list scrolls
    widget.said = said  # type: ignore[attr-defined]
    return widget


def _many(prefix: str, count: int, start: int = 1) -> list[Problem]:
    return [_problem(start + i * 3, f"{prefix} {i}") for i in range(count)]


def test_a_quiet_check_keeps_the_readers_problem_when_rows_arrive_above(pane, frame) -> None:
    rows = _many("Old", 30, start=100)
    pane.show_report(_report(*rows))
    box = pane._list
    box.SetSelection(12)
    box.SetFirstItem(9)
    reader_on = rows[12]

    # Two new problems near the top of the file, one old one fixed lower down.
    fresh = [_problem(1, "New A"), _problem(2, "New B")]
    pane.show_report(_report(*fresh, *[p for p in rows if p is not rows[20]]))
    _pump()

    selected = box.GetSelection()
    assert pane._report.problems[pane._row_indices[selected]] == reader_on
    assert selected == 14
    assert box.GetTopItem() == 11, "the row stays on the line it was on"
    assert wx.Window.FindFocus() is frame.elsewhere, "focus never moves"
    assert pane.said == [], "the host says the count; the refill says nothing"


def test_a_problem_that_moved_down_a_line_is_still_the_readers(pane) -> None:
    pane.show_report(_report(_problem(3, "Missing comma"), _problem(9, "Trailing comma")))
    pane._list.SetSelection(1)
    # A line was typed above both: same problems, one line lower.
    pane.show_report(_report(_problem(4, "Missing comma"), _problem(10, "Trailing comma")))
    assert pane._list.GetSelection() == 1


def test_a_fixed_problem_leaves_the_reader_on_the_one_that_took_its_place(pane) -> None:
    pane.show_report(_report(_problem(1, "a"), _problem(2, "b"), _problem(3, "c")))
    pane._list.SetSelection(1)
    pane.show_report(_report(_problem(1, "a"), _problem(3, "c")))
    assert pane._list.GetString(pane._list.GetSelection()).endswith("c (JSON)")


def test_an_unchanged_report_rewrites_nothing(pane, monkeypatch) -> None:
    report = _report(*_many("Same", 5))
    pane.show_report(report)
    pane._list.SetSelection(3)
    calls: list[Any] = []
    monkeypatch.setattr(pane._list, "Set", lambda *a: calls.append(a))
    pane.show_report(_report(*_many("Same", 5)))
    assert calls == [] and pane._list.GetSelection() == 3


def test_follow_row_is_by_the_problem_not_its_place() -> None:
    a, b, c = _problem(1, "a"), _problem(5, "b"), _problem(9, "c")
    assert follow_row(b, 1, [_problem(0, "new"), a, b, c]) == 2
    assert follow_row(b, 1, [a, _problem(6, "b"), c]) == 1
    assert follow_row(b, 1, [a, c]) == 1
    assert follow_row(c, 2, [a]) == 0
    assert follow_row(None, 0, []) == -1


# -- the Recent Documents window ---------------------------------------------- #


@pytest.fixture
def recent_window(frame, tmp_path: Path):
    from quill.ui.recent_documents_dialog import RecentDocumentsWindow

    paths = []
    for index in range(30):
        path = tmp_path / f"doc{index:02d}.txt"
        path.write_text("x", encoding="utf-8")
        paths.append(str(path))
    said: list[str] = []
    window = RecentDocumentsWindow(
        frame, paths, [], limit=50, auto_clear_missing=False, announce=said.append
    )
    window.dialog.Show()
    frame.elsewhere.SetFocus()  # type: ignore[attr-defined]
    _pump()
    window.said = said  # type: ignore[attr-defined]
    window.paths = paths  # type: ignore[attr-defined]
    yield window
    window.dialog.Destroy()


def test_a_save_elsewhere_adds_its_row_without_moving_the_reader(
    recent_window, frame, tmp_path: Path
) -> None:
    from quill.ui.recent_documents_dialog import follow_recent_change

    box = recent_window.listbox
    box.SetSelection(10)
    box.SetFirstItem(8)
    reader_on = recent_window.selected().path
    focus_before = wx.Window.FindFocus()

    # A Word document finished saving in the background: it heads the list.
    saved = tmp_path / "report.docx"
    saved.write_text("x", encoding="utf-8")
    follow_recent_change([str(saved), *recent_window.paths])
    _pump()

    assert recent_window.selected().path == reader_on
    assert box.GetSelection() == 11
    assert box.GetTopItem() == 9, "the row stays on the line it was on"
    assert wx.Window.FindFocus() is focus_before, "focus never moves"
    assert recent_window.said == [], "the save already said what it did"
    assert recent_window.answer().recent[0] == str(saved), "closing keeps the new row"


def test_a_row_removed_here_is_not_brought_back_by_a_change_elsewhere(recent_window) -> None:
    removed = recent_window.paths[0]
    recent_window.listbox.SetSelection(0)
    recent_window.remove_selected()
    recent_window.follow(recent_window.paths)
    assert all(row.path != removed for row in recent_window._rows)


def test_a_closed_window_is_not_followed(frame) -> None:
    from quill.ui import recent_documents_dialog as rdd

    window = rdd.RecentDocumentsWindow(frame, [], [], limit=10, auto_clear_missing=False)
    window.dialog.Destroy()
    _pump()
    rdd.follow_recent_change(["C:/nowhere/x.txt"])
    assert window not in rdd._OPEN


# -- the recovered drafts --------------------------------------------------------- #


def test_discarding_drafts_keeps_the_rest_as_the_reader_left_them(
    frame, monkeypatch, tmp_path: Path
) -> None:
    """The one refill the Unsaved Work window has: the rows left keep their checks."""
    from quill.core import recovery_triage
    from quill.ui import recovery_dialog

    slots = [_slot(tmp_path, i) for i in range(4)]
    result = recovery_triage.Triage(offer=tuple(slots))
    seen: dict[str, Any] = {}
    outcomes = iter([recovery_dialog._ID_DISCARD_CHECKED, recovery_dialog._ID_RESTORE_CHECKED])

    def fake_modal(dialog, _title):
        boxes = [w for w in _all_children(dialog) if isinstance(w, wx.CheckBox)]
        if "first" not in seen:
            seen["first"] = True
            # Keep note0 and note2 (unchecked), discard note1 and note3.
            boxes[0].SetValue(False)
            boxes[2].SetValue(False)
        else:
            seen["boxes"] = [(b.GetLabel(), b.GetValue()) for b in boxes]
        return next(outcomes)

    monkeypatch.setattr(recovery_dialog, "show_modal_dialog", fake_modal)
    answer = recovery_dialog.ask_recovery(frame, result)

    labels = [label for label, _checked in seen["boxes"]]
    assert len(labels) == 2
    assert [checked for _label, checked in seen["boxes"]] == [False, False], (
        "a row the reader unchecked is not checked again behind their back"
    )
    assert answer.restore == ()
    assert {id(s) for s in answer.discard} == {id(slots[1]), id(slots[3])}


def _slot(tmp_path: Path, index: int) -> Any:
    from quill.core.lite import recovery as recovery_mod

    slot = recovery_mod.RecoverySlot(
        slot_id=f"s{index}",
        mode="plain",
        original_path=str(tmp_path / f"note{index}.txt"),
        content_path=tmp_path / f"s{index}.txt",
        meta_path=tmp_path / f"s{index}.json",
    )
    slot.content_path.write_text(f"draft {index}", encoding="utf-8")
    return slot


def _all_children(window: Any) -> list[Any]:
    found: list[Any] = []
    for child in window.GetChildren():
        found.append(child)
        found.extend(_all_children(child))
    return found

"""The shared windows behind Paste Copied Files, replace jobs and snippet blanks, built for real.

Each window is constructed on the session ``wx.App`` and "shown" through a fake
modal route that fills in the controls the way a person would and presses OK --
so what is checked is the real window's controls, labels, help and answer, not
a stand-in's.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.replace_jobs import ReplaceJob, ReplaceStep  # noqa: E402
from quill.core.snippets import extract_placeholders  # noqa: E402
from quill.ui import replace_jobs_windows as replace_jobs  # noqa: E402
from quill.ui.paste_file import choose_paste_kind  # noqa: E402
from quill.ui.replace_jobs_windows import (  # noqa: E402
    choose_replace_job,
    edit_replace_step,
)
from quill.ui.snippet_prompts import ask_snippet_values  # noqa: E402


@pytest.fixture(autouse=True)
def _help_provider(wx_session_app) -> None:
    """SetHelpText stores nothing without a provider, as at app activation."""
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)


def _controls(dialog: Any, kind: type) -> list[Any]:
    return [child for child in dialog.GetChildren() if isinstance(child, kind)]


def _labels(dialog: Any) -> list[str]:
    return [child.GetLabel() for child in dialog.GetChildren() if isinstance(child, wx.Button)]


def _assert_contract(dialog: Any) -> None:
    """Every control explains itself (F1), and OK, Cancel, Close carry no access key."""
    for child in dialog.GetChildren():
        if isinstance(child, wx.StaticText):
            continue
        assert child.GetHelpText(), f"{type(child).__name__} {child.GetLabel()!r} has no help"
    for label in _labels(dialog):
        if label.replace("&", "") in {"OK", "Cancel", "Close"}:
            assert "&" not in label


def _blanks(body: str) -> list[Any]:
    return [p for p in extract_placeholders(body) if p.kind in {"input", "choice"}]


def test_snippet_blanks_are_asked_in_the_shared_fill_in_form(wx_session_app) -> None:
    blanks = _blanks("${input:topic} ${choice:NVDA|JAWS|Narrator}")

    def show(dialog: Any, _title: str) -> int:
        text = _controls(dialog, wx.TextCtrl)[0]
        choice = _controls(dialog, wx.Choice)[0]
        text.SetValue("Budget")
        choice.SetSelection(1)
        labels = [c.GetLabel() for c in _controls(dialog, wx.StaticText)]
        assert labels == ["Topic:", "NVDA, JAWS or Narrator:"]
        return wx.ID_OK

    answers = ask_snippet_values(None, "Snippet: test", blanks, show)

    assert answers == {"input:topic": "Budget", "choice:NVDA|JAWS|Narrator": "JAWS"}


def test_snippet_blanks_cancelled_answer_none(wx_session_app) -> None:
    blanks = _blanks("${input:topic}")

    assert ask_snippet_values(None, "Snippet", blanks, lambda *_a: wx.ID_CANCEL) is None


def test_paste_file_offers_text_or_paths(wx_session_app) -> None:
    def show(dialog: Any, _title: str) -> int:
        _assert_contract(dialog)
        listbox = _controls(dialog, wx.ListBox)[0]
        assert listbox.GetStrings() == ["Each file's text", "Each file's full path"]
        listbox.SetSelection(1)
        return wx.ID_OK

    assert choose_paste_kind(None, ["a.txt", "b.docx"], show) == "path"


def test_run_replace_job_lists_the_jobs_and_says_where_it_runs(wx_session_app) -> None:
    jobs = [ReplaceJob("One", [ReplaceStep("a")]), ReplaceJob("Two", [ReplaceStep("a")] * 2)]

    def show(dialog: Any, _title: str) -> int:
        _assert_contract(dialog)
        listbox = _controls(dialog, wx.ListBox)[0]
        assert listbox.GetStrings() == ["One, 1 step", "Two, 2 steps"]
        labels = [c.GetLabel() for c in _controls(dialog, wx.StaticText)]
        assert "&Job to run on the selection:" in labels
        listbox.SetSelection(1)
        return wx.ID_OK

    assert choose_replace_job(None, jobs, show, in_selection=True) == 1


def test_a_step_with_a_bad_pattern_is_refused_and_explained(wx_session_app) -> None:
    told: list[str] = []

    def show(dialog: Any, title: str) -> int:
        if isinstance(dialog, wx.MessageDialog):
            told.append(dialog.GetMessage())
            return wx.ID_OK
        _assert_contract(dialog)
        find, replace = _controls(dialog, wx.TextCtrl)
        regex, _case = _controls(dialog, wx.CheckBox)
        find.SetValue("(")
        regex.SetValue(True)
        ok = dialog.FindWindow(wx.ID_OK)
        ok.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, wx.ID_OK))
        assert told and "not valid" in told[-1]  # refused: the window stays open
        find.SetValue("cat")
        replace.SetValue("dog")
        return wx.ID_OK

    assert edit_replace_step(None, None, show) == ReplaceStep("cat", "dog", regex=True)


def test_the_job_editor_adds_moves_and_removes_steps(wx_session_app, monkeypatch) -> None:
    new_steps = iter([ReplaceStep("b", "B"), ReplaceStep("c", "C")])
    monkeypatch.setattr(replace_jobs, "edit_replace_step", lambda *_a: next(new_steps))
    editor = replace_jobs._JobEditor(
        None, ReplaceJob("Mine", [ReplaceStep("a", "A")]), [], -1, lambda *_a: wx.ID_OK
    )
    try:
        _assert_contract(editor.dialog)
        editor.add_step()  # after "a"
        editor.add_step()  # after "b"
        assert [s.find for s in editor.steps] == ["a", "b", "c"]
        editor.move(-1)
        assert [s.find for s in editor.steps] == ["a", "c", "b"]
        editor.remove_step()
        assert [s.find for s in editor.steps] == ["a", "b"]
        assert editor.problem() == ""
        editor.name.SetValue("")
        assert editor.problem() == "Give the job a name."
    finally:
        editor.dialog.Destroy()


def test_the_job_editor_refuses_a_name_already_taken(wx_session_app) -> None:
    others = [ReplaceJob("Tidy", [ReplaceStep("a")])]
    editor = replace_jobs._JobEditor(None, ReplaceJob("tidy"), others, -1, lambda *_a: wx.ID_OK)
    try:
        assert editor.problem().startswith("There is already a job called tidy")
    finally:
        editor.dialog.Destroy()


def test_the_manager_renames_and_deletes_after_asking(wx_session_app, monkeypatch) -> None:
    answers = iter([wx.ID_NO, wx.ID_YES])
    monkeypatch.setattr(replace_jobs, "_ask_name", lambda *_a: "Renamed")
    jobs = [ReplaceJob("One", [ReplaceStep("a")]), ReplaceJob("Two", [ReplaceStep("b")])]
    manager = replace_jobs._JobManager(None, jobs, lambda *_a: next(answers))
    try:
        _assert_contract(manager.dialog)
        assert set(_labels(manager.dialog)) == {
            "&New...",
            "&Edit...",
            "&Rename...",
            "&Delete",
            "Close",
        }
        manager.rename()
        assert manager.jobs[0].name == "Renamed"
        manager.delete()  # answered No
        assert len(manager.jobs) == 2
        manager.delete()  # answered Yes
        assert [job.name for job in manager.jobs] == ["Two"]
        assert manager.changed
        assert jobs[0].name == "One"  # the caller's list is untouched until saved
    finally:
        manager.dialog.Destroy()

"""Undo, Redo, Retry Failed, Mixed and emptied fields through the real Workbench (complete.md 1.3).

The engine half is proved field by field in
``tests/unit/core/workbench/test_github_field_matrix.py``; this file drives
the same paths from the frame, as a person would: Ctrl+Z and Ctrl+Y in the
list, the results list's Retry Failed, a combined sheet left Mixed, and a
title box emptied.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.change_log import ChangeLog  # noqa: E402
from quill.core.github.rest_transport import GitHubRestError  # noqa: E402
from quill.ui.workbench_properties_sheet import PropertiesSheet  # noqa: E402
from tests.unit.ui import test_github_workbench_properties as base  # noqa: E402

_check, _pick, _script = base._check, base._pick, base._script
bench = base.bench  # the same frame over the same recorded API


def _add_bug(bench, monkeypatch) -> None:
    def edit(sheet: PropertiesSheet) -> None:
        _check(sheet, "labels", "bug")
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.properties")


def test_redo_makes_the_change_again_and_it_can_be_undone_again(bench, monkeypatch) -> None:
    _add_bug(bench, monkeypatch)
    api = bench.provider.api
    bench.list.SetFocus()
    bench.run("github.workbench.undo_change")
    assert api.writes()[-1] == ("DELETE", "/repos/owner/repo/issues/1/labels/bug", None)
    bench.run("github.workbench.redo_change")
    assert api.writes()[-1] == ("POST", "/repos/owner/repo/issues/1/labels", {"labels": ["bug"]})
    assert any(text.startswith("Redone.") for text in bench.said)
    assert not ChangeLog.load().entries[-1].undone, "a redone change is undoable again"
    bench.run("github.workbench.undo_change")
    assert api.writes()[-1] == ("DELETE", "/repos/owner/repo/issues/1/labels/bug", None)
    assert ChangeLog.load().entries[-1].undone


def test_undo_twice_with_nothing_left_says_so(bench, monkeypatch) -> None:
    _add_bug(bench, monkeypatch)
    bench.list.SetFocus()
    bench.run("github.workbench.undo_change")
    count = len(bench.provider.api.writes())
    bench.run("github.workbench.undo_change")
    assert len(bench.provider.api.writes()) == count
    assert bench.said[-1] == "Nothing to undo."


def test_an_emptied_title_is_left_as_it_is_and_says_why(bench, monkeypatch) -> None:
    def edit(sheet: PropertiesSheet) -> None:
        sheet.controls["title"].SetValue("")
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.properties")
    assert bench.provider.api.writes() == []
    assert "Title cannot be empty on GitHub, so it was left as it is." in bench.said


def test_a_combined_sheet_left_mixed_sends_only_what_was_touched(bench, monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.github_workbench_results.show_results", lambda *a, **kw: None)

    def edit(sheet: PropertiesSheet) -> None:
        assert sheet.controls["title"].GetValue() == "Mixed"  # Issue 1 and Issue 2
        _check(sheet, "labels", "bug")
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    _pick(bench, 2, add=True)
    bench.run("github.workbench.properties")
    writes = bench.provider.api.writes()
    assert writes and all(body is None or "title" not in body for _m, _p, body in writes)


def test_retry_failed_reads_each_failed_row_again_and_finishes_it(bench, monkeypatch) -> None:
    retries: list[Any] = []
    texts: list[str] = []

    def show(_parent, _title, text, **kw: Any) -> None:
        texts.append(text)
        retries.append(kw.get("retry"))

    monkeypatch.setattr("quill.ui.github_workbench_results.show_results", show)
    api = bench.provider.api
    answer = api.on_write
    broken = {"on": True}

    def flaky(method: str, path: str, body: Any) -> None:
        if broken["on"] and path == "/repos/owner/repo/issues/2/labels":
            raise GitHubRestError("Server Error", status=502)
        answer(method, path, body)

    api.on_write = flaky

    def edit(sheet: PropertiesSheet) -> None:
        _check(sheet, "labels", "bug")
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    _pick(bench, 2, add=True)
    bench.run("github.workbench.properties")
    assert texts[0].endswith("1 done, 0 skipped, 1 failed")
    assert retries[0] is not None, "Retry Failed is offered when something failed"
    broken["on"] = False
    reads = len([c for c in api.calls if c[:2] == ("GET", "/repos/owner/repo/issues/2")])
    retries[0]()
    assert texts[1].endswith("1 done, 0 skipped, 0 failed")
    after = len([c for c in api.calls if c[:2] == ("GET", "/repos/owner/repo/issues/2")])
    assert after == reads + 2, "the retry read the row afresh, saved it, then read it again"
    assert retries[1] is None, "nothing left to retry"

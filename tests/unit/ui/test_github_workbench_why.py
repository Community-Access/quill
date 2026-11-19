"""GH-R-108: Why? on what the GitHub Workbench did on its own (GitHub PRD D13).

A watch that spoke, a notification in the inbox and a filter that only covers
the loaded rows each explain themselves. Shift+F1 lists Why? first, and the
watch and notification rows carry it on their context menu.
"""

# ruff: noqa: F811 - the shared bench fixture is imported, then named by each test

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.watches import Watch, WatchStore  # noqa: E402
from quill.core.github.why import why_filter, why_notification, why_watch  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.test_github_workbench_phase13 import (  # noqa: E402,F401
    _account_key,
    _go,
    bench,
)

# -- the words --------------------------------------------------------------------


def test_a_watch_says_what_it_looks_for_how_often_and_what_it_found() -> None:
    watch = Watch("w1", "release", "owner/repo", primed=True, last_result="New release: Two.")
    said = why_watch(watch, 15, now=None)
    assert said.startswith("This watch, New releases in owner/repo, looks for a new release.")
    assert "checked every 15 minutes while this window is open" in said
    assert "found something it had not seen before: New release: Two." in said
    assert "never marks a notification read" in said


def test_a_new_or_paused_or_quiet_watch_says_so() -> None:
    assert "only learns what is there already" in why_watch(Watch("a", "run", "o/r"), 15)
    assert "It is paused" in why_watch(Watch("b", "run", "o/r", paused=True), 15)
    quiet = why_watch(Watch("c", "comment", "o/r", number=4, primed=True), 15)
    assert "Nothing new has turned up" in quiet


def test_a_notification_says_why_github_sent_it() -> None:
    said = why_notification(
        "Issue: Crash\nRepository: o/r\nWhy you got it: you were mentioned", "o/r"
    )
    assert said.startswith("GitHub sent you this because of this reason: you were mentioned.")
    assert "how you watch on o/r" in said


def test_a_filter_says_whether_it_covers_github_or_only_what_is_loaded() -> None:
    assert why_filter("", remote=False, loaded=30, complete=False) == ""
    assert "sent to GitHub as a search" in why_filter("bug", remote=True, loaded=30, complete=False)
    partial = why_filter("bug", remote=False, loaded=30, complete=False)
    assert "Only 30 rows are loaded" in partial and "Load More, Alt+PageDown" in partial
    assert "nothing is missed" in why_filter("bug", remote=False, loaded=12, complete=True)


# -- in the window -----------------------------------------------------------------------


def test_shift_f1_lists_why_first_on_a_watch_and_it_is_on_the_row(bench, monkeypatch) -> None:
    store = WatchStore.load(_account_key())
    watch = store.add("release", "owner/repo")
    store.replace(Watch(watch.id, "release", "owner/repo", primed=True, last_result="New: Two."))
    store.save()
    _go(bench, NodeRef("", "watches"))
    bench.list.Select(0)
    shown: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.workbench_help_dialogs.ActionListDialog.show",
        lambda dialog: shown.append(dialog.rows) or dialog.dialog.Destroy(),
    )
    bench.what_can_i_do()
    first = shown[0][0]
    assert first.text == "Why?"
    first.run()
    assert bench.said[-1].startswith("This watch, New releases in owner/repo")
    first_rows, other_rows = bench.row_actions(bench.selected_row())
    assert "Why?" in [row.label for row in (*first_rows, *other_rows)]
    bench.run("github.workbench.why")
    assert bench.said[-1].startswith("This watch, New releases in owner/repo")


def test_with_nothing_automatic_there_is_no_why(bench, monkeypatch) -> None:
    _go(bench, NodeRef("", "watches"))
    assert bench.provider.why_text() == ""
    assert not bench.can_run("github.workbench.why")

"""GH-R-107: Walk Me Through It and Do It on the Workbench's help tasks (GitHub PRD D12).

A walk says the first step of a Do Something task, then the next step each
time a command is done. F1 says the step again, Shift+F1 lists the steps and
Escape stops. Do It runs the one command a task comes down to, where it
belongs, and is greyed on tasks that are more than one command.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.github import workbench_help as catalogue  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.workbench_glossary import TASKS  # noqa: E402
from quill.core.workbench.walk import Walk, steps_of  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.test_github_workbench_help import REPO, _go, _inline, _Items  # noqa: E402

# -- the walk itself --------------------------------------------------------------


def test_a_task_is_cut_into_one_action_a_step() -> None:
    assert steps_of(
        "Press Ctrl+1 for Inbox. Arrow down the list; Enter opens a row; Delete marks it done."
    ) == (
        "Press Ctrl+1 for Inbox.",
        "Arrow down the list.",
        "Enter opens a row.",
        "Delete marks it done.",
    )
    assert steps_of(
        "Press Ctrl+Shift+1 for Issues, then Ctrl+N. Type a title, press Enter, "
        "then say what it is about."
    ) == (
        "Press Ctrl+Shift+1 for Issues.",
        "Ctrl+N.",
        "Type a title, press Enter.",
        "Say what it is about.",
    )


def test_every_task_has_steps() -> None:
    for _id, title, text, _place in TASKS:
        assert steps_of(text), title


def test_an_arrow_step_is_passed_over_by_the_command_that_follows_it() -> None:
    walk = Walk(
        "Find what needs me",
        ("Press Ctrl+1.", "Arrow down the list.", "Enter opens it.", "Delete marks it done."),
    )
    assert walk.advance() == "Step 2 of 4: Arrow down the list."
    # Enter ran a command: the arrowing was done, and so was Enter.
    assert walk.advance() == "Step 4 of 4: Delete marks it done."
    assert walk.advance() == "That was the last step of Find what needs me."
    assert walk.finished


def test_the_listing_marks_where_you_are() -> None:
    walk = Walk("T", ("One.", "Two."), index=1)
    assert walk.listing() == "T, 2 steps. Step 1: One. Step 2, you are here: Two."


# -- in the window ---------------------------------------------------------------------


@pytest.fixture
def bench(wx_session_app, quill_data_dir, wx_call_after):
    wx_call_after()
    said: list[str] = []
    provider = GitHubWorkbenchProvider(
        _Items([GitHubItem(1, "Crash", "open", "https://github.com/o/r/issues/1", False)]),
        REPO,
        announce=said.append,
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _task(bench: WorkbenchFrame, title: str) -> None:
    _go(bench, NodeRef("", "help_tasks"))
    index = next(i for i, row in enumerate(bench.rows) if row.label == title)
    for other in range(bench.list.GetItemCount()):
        bench.list.Select(other, False)
    bench.list.Select(index)
    assert bench.selected_row().label == title


def test_walk_me_through_it_goes_there_and_says_one_step_at_a_time(bench) -> None:
    _task(bench, "Find what needs me")
    bench.run("github.workbench.walk_me_through")
    assert bench.walk is not None
    assert bench.said[-1].startswith(
        "Walking through Find what needs me. Step 1 of 5: Press Ctrl+1 for Inbox."
    )
    assert "Escape stops" in bench.said[-1]
    bench.show_layered_help()  # F1 says the step again, and opens nothing
    assert bench.said[-1] == "Step 1 of 5: Press Ctrl+1 for Inbox."
    bench.what_can_i_do()  # Shift+F1 lists them
    assert bench.said[-1].startswith("Find what needs me, 5 steps. Step 1, you are here:")
    bench.run("github.workbench.go_inbox")  # Ctrl+1: the step is done
    assert bench.said[-1] == "Step 2 of 5: Arrow down the list."


def test_escape_stops_the_walk_before_it_does_anything_else(bench) -> None:
    _task(bench, "File an issue")
    bench.run("github.workbench.walk_me_through")
    assert bench.stop_walk() is True
    assert bench.walk is None
    assert bench.said[-1] == "Stopped walking through File an issue."
    assert bench.stop_walk() is False


def test_do_it_is_offered_only_where_the_answer_is_one_command(bench) -> None:
    _task(bench, "Fix a failed run")
    assert not bench.can_run("github.workbench.do_it")
    _task(bench, "Open another repository")
    assert bench.can_run("github.workbench.do_it")
    assert set(catalogue.DO_IT) <= {task_id for task_id, *_rest in TASKS}


def test_do_it_runs_the_command_where_it_belongs(bench, monkeypatch) -> None:
    ran: list[str] = []
    real = bench.run

    def run(command_id: str) -> None:
        ran.append(command_id)
        if command_id != "github.workbench.new_issue":
            real(command_id)

    monkeypatch.setattr(bench, "run", run)
    _task(bench, "File an issue")
    real("github.workbench.do_it")
    assert ran == ["github.workbench.new_issue"]
    assert bench.current == NodeRef("repository", "issues", REPO)


def test_the_help_rows_offer_all_four(bench) -> None:
    _task(bench, "File an issue")
    first, _rest = bench.row_actions(bench.selected_row())
    labels = [row.label for row in (*first, *_rest)]
    for label in ("Take Me There", "Walk Me Through It", "Do It"):
        assert label in labels


def test_the_frame_walk_is_shared_by_every_workbench() -> None:
    from quill.ui.workbench_frame_help import WorkbenchHelpMixin

    assert WorkbenchHelpMixin.walk is None
    assert callable(WorkbenchHelpMixin.start_walk)

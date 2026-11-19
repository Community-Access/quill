"""GH-R-106: Help and Learning has every node of D11, Tutorials and Tips included.

Tutorials lists the GitHub lessons with your progress, opens one in the
editor's Tutorials window, and walks it here on request. Tips holds
QUILLBert's tips, and every key a tip names is one the Workbench binds.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github import workbench_learning as learning  # noqa: E402
from quill.core.github.workbench_tree import GITHUB_TREE  # noqa: E402
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS  # noqa: E402
from quill.core.tutorials.github_lessons import github_lessons  # noqa: E402
from quill.core.tutorials.model import Progress  # noqa: E402
from quill.core.tutorials.progress import TutorialProgressStore  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.test_github_workbench_help import REPO, _go, _inline, _Items  # noqa: E402

_CHORD = re.compile(r"\b(?:(?:Ctrl|Alt|Shift)\+)+(?:F\d+|PageDown|PageUp|Enter|[A-Z0-9])\b")


def test_help_and_learning_has_every_node_of_d11_in_order() -> None:
    labels = [
        node.label for _template, node in GITHUB_TREE.all_nodes() if node.key.startswith("help_")
    ]
    assert labels == [
        "Do Something",
        "The Guide",
        "Words",
        "Keys",
        "Tutorials",
        "What Changed",
        "Tips",
        "Ask a Person",
    ]


def test_every_key_a_tip_teaches_is_bound() -> None:
    bound = set(WORKBENCH_KEYS.values()) | {"Ctrl+Enter", "Alt+Enter"}
    for tip in learning.TIPS:
        for chord in _CHORD.findall(tip):
            if chord in ("Alt+1", "Alt+9"):  # "Alt+1 to Alt+9", the readouts' family
                continue
            assert chord in bound, f"{chord} in {tip!r}"


def test_tutorial_rows_say_where_you_are_and_how_many_are_done() -> None:
    lessons = github_lessons()
    store = TutorialProgressStore()
    store.entries[lessons[0].slug] = Progress(lessons[0].slug, done=True)
    store.entries[lessons[1].slug] = Progress(lessons[1].slug, step=2)
    rows = learning.tutorial_rows(lessons, store)
    assert rows[0][0] == f"{lessons[0].title}: done"
    assert rows[1][0] == f"{lessons[1].title}: step 3 of {len(lessons[1].steps)}"
    assert rows[2][0].endswith("minutes, not started")
    assert rows[0][2] == f"tutorial:{lessons[0].slug}"
    assert learning.tutorials_note(lessons, store) == f"1 of {len(lessons)} done."
    assert learning.tutorials_note(lessons, None) == f"0 of {len(lessons)} done."


def test_a_lesson_walks_with_the_keys_as_bound_now() -> None:
    lesson = next(t for t in github_lessons() if t.slug == "github-practice-start")
    steps = learning.lesson_steps(lesson, lambda command: "Ctrl+Alt+Shift+P" if command else "")
    assert len(steps) == len(lesson.steps)
    practice = next(step for step in steps if step.startswith("Make the practice repository."))
    assert "Keys: Ctrl+Alt+Shift+P" in practice  # the bound key first, as the window says it
    assert "You should hear:" in practice


class _Editor:
    def __init__(self) -> None:
        self.opened: list[str] = []

    def open_quill_tutorials(self, slug: str = "") -> None:
        self.opened.append(slug)


def _bench(product: str, editor: Any = None) -> WorkbenchFrame:
    said: list[str] = []
    provider = GitHubWorkbenchProvider(
        _Items([]), REPO, announce=said.append, guide_product=product
    )
    frame = WorkbenchFrame(provider, editor=editor, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    return frame


def _select(frame: WorkbenchFrame, index: int) -> None:
    for other in range(frame.list.GetItemCount()):
        frame.list.Select(other, False)
    frame.list.Select(index)


def test_enter_on_a_tutorial_opens_it_in_the_editor(wx_session_app, quill_data_dir) -> None:
    editor = _Editor()
    frame = _bench("quill", editor)
    try:
        _go(frame, NodeRef("", "help_tutorials"))
        assert len(frame.rows) == len(github_lessons())
        assert frame.provider.local_note.endswith(f"of {len(github_lessons())} done.")
        _select(frame, 0)
        frame.default_action()
        assert editor.opened == [github_lessons()[0].slug]
    finally:
        frame.frame.Destroy()


def test_in_quill_lite_a_tutorial_is_walked_here(wx_session_app, quill_data_dir) -> None:
    frame = _bench("quilllite", _Editor())
    try:
        _go(frame, NodeRef("", "help_tutorials"))
        _select(frame, 0)
        frame.default_action()
        assert frame.walk is not None
        assert frame.said[-1].startswith(f"Walking through {github_lessons()[0].title}. Step 1 of")
        frame.run("github.workbench.take_me_there")
        assert frame.said[-1] == "This topic is not about one place."
    finally:
        frame.frame.Destroy()


def test_tips_are_a_list_you_read_at_your_own_pace(wx_session_app, quill_data_dir) -> None:
    frame = _bench("quill")
    try:
        _go(frame, NodeRef("", "help_tips"))
        assert [row.label for row in frame.rows] == list(learning.TIPS)
        assert frame.rows[0].detail.startswith(f"QUILLBert's tip 1 of {len(learning.TIPS)}:")
    finally:
        frame.frame.Destroy()

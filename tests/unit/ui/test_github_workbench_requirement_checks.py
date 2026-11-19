"""Tests for GitHub Workbench requirements that were built but had no test.

The 2026-11-18 requirement audit (PRD Part E) found these working in the code
with nothing proving it: Switch to Editor (GH-R-006), "Me" and "has none" in
the filter (GH-R-052), Or groups (GH-R-054), no letter as a command
(GH-R-092), rebinding (GH-R-093), the access matrix and bulk access
(GH-R-068, GH-R-142) and the read-only role views (GH-R-069).
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github import access  # noqa: E402
from quill.core.github import filter_builder as fb  # noqa: E402
from quill.core.github.permissions import WriteTier  # noqa: E402
from quill.core.github.workbench_window_menu import WINDOW_MENU, WORKBENCH_KEYS  # noqa: E402
from quill.core.workbench.menus import all_rows  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import WorkbenchFrame  # noqa: E402
from tests.unit.ui.test_github_workbench_window import REPO, _inline, _Items  # noqa: E402


class _Editor:
    def __init__(self, *, closed: bool = False) -> None:
        self.closed = closed
        self.raised = self.focused = 0

    def Raise(self) -> None:  # noqa: N802 - wx's name
        if self.closed:
            raise RuntimeError("wrapped C/C++ object has been deleted")
        self.raised += 1

    def SetFocus(self) -> None:  # noqa: N802 - wx's name
        self.focused += 1


def _frame(editor: Any = None) -> tuple[WorkbenchFrame, list[str]]:
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    frame = WorkbenchFrame(provider, editor=editor, announce=said.append, run_background=_inline)
    return frame, said


# -- GH-R-006: Switch to Editor --------------------------------------------------


def test_switch_to_editor_raises_and_focuses_the_editor_that_opened_it(
    wx_session_app, quill_data_dir
) -> None:
    editor = _Editor()
    frame, said = _frame(editor)
    try:
        frame.switch_to_editor()
        assert (editor.raised, editor.focused) == (1, 1)
        assert said == []  # the focus move says it (GATE-13)
    finally:
        frame.frame.Destroy()


def test_switch_to_editor_says_so_when_the_editor_has_closed(
    wx_session_app, quill_data_dir
) -> None:
    frame, said = _frame(_Editor(closed=True))
    try:
        frame.switch_to_editor()
        assert said == ["The editor that opened this window is closed."]
    finally:
        frame.frame.Destroy()


# -- GH-R-052 and GH-R-054: the filter ---------------------------------------------


def test_every_person_and_list_attribute_offers_has_none_and_has_any() -> None:
    for item in fb.ATTRIBUTES:
        if item.kind in ("person", "list"):
            assert {"has none", "has any"} <= set(fb.OPERATORS[item.kind]), item.key


def test_me_is_sent_as_at_me_and_read_back_as_me() -> None:
    row = fb.BuilderRow("assignee", "is", ("Me",))
    assert fb.render_row(row) == "assignee:@me"
    assert fb.describe_row(fb.BuilderRow("assignee", "is", ("@me",))) == "Assignee is Me"


def test_has_none_and_has_any_on_a_list_attribute() -> None:
    assert fb.render_row(fb.BuilderRow("label", "has none")) == "no:label"
    assert fb.render_row(fb.BuilderRow("label", "has any")) == "-no:label"


def test_or_groups_are_bracketed_and_joined_by_or() -> None:
    rows = [
        fb.BuilderRow("label", "is", ("bug",), group=0),
        fb.BuilderRow("assignee", "is", ("Me",), group=0),
        fb.BuilderRow("label", "is", ("docs",), group=1),
    ]
    assert fb.render_query(rows) == "(label:bug assignee:@me) OR (label:docs)"
    assert fb.describe_row(rows[2]) == "Label is docs (group 2)"


def test_one_group_needs_no_brackets() -> None:
    assert fb.render_query([fb.BuilderRow("label", "is", ("bug",))]) == "label:bug"


# -- GH-R-092 and GH-R-093: keys ---------------------------------------------------


def test_no_workbench_key_is_a_letter_or_digit_on_its_own() -> None:
    bare = re.compile(r"(Shift\+)?[A-Za-z0-9]")
    claimed = [
        (command, key) for command, key in WORKBENCH_KEYS.items() if key and bare.fullmatch(key)
    ]
    assert claimed == []  # typing always moves through the tree and lists


def test_a_rebound_key_is_the_one_the_menu_shows(
    wx_session_app, quill_data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    command, default = next(
        (row.command_id, row.key) for _spec, row in all_rows(WINDOW_MENU) if row.key
    )
    chosen = "Ctrl+Alt+Shift+F11"
    assert chosen not in WORKBENCH_KEYS.values()
    monkeypatch.setattr("quill.core.keymap.load_keymap", lambda: {command: chosen})
    frame, _said = _frame()
    try:
        assert frame._keys[command] == chosen
        item = frame._menu_items[command]
        assert item.GetItemLabel().split("\t")[-1] == chosen
        assert default not in item.GetItemLabel()
    finally:
        frame.frame.Destroy()


def test_a_broken_keymap_file_leaves_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui.workbench_frame_commands import bound_keys

    def broken() -> dict[str, str]:
        raise ValueError("not JSON")

    monkeypatch.setattr("quill.core.keymap.load_keymap", broken)
    assert bound_keys("github", {"a": "Ctrl+1"}) == {"a": "Ctrl+1"}


# -- GH-R-068 and GH-R-142: the access matrix and bulk changes -----------------------


def test_the_access_matrix_is_one_sorted_row_per_person_and_repository() -> None:
    found = access.matrix_rows({
        "o/web": [access.AccessRow("zoe", role="write"), access.AccessRow("ann", role="admin")],
        "o/api": [access.AccessRow("ann", "team", "read", "through docs")],
    })
    assert found == [
        ("ann", "o/api", "read", "through docs"),
        ("ann", "o/web", "admin", "direct"),
        ("zoe", "o/web", "write", "direct"),
    ]
    table = list(csv.reader(io.StringIO(access.matrix_csv(found))))
    assert table[0] == ["person", "repository", "role", "source"]
    assert len(table) == 4


def test_bulk_access_gives_a_team_a_role_on_each_repository_with_an_undo() -> None:
    changes = access.bulk_plan(
        "repository", "docs", "team", "write", [{"repo": "o/web"}, {"repo": "o/api"}]
    )
    assert [(c.method, c.path, c.body) for c in changes] == [
        ("PUT", "/orgs/o/teams/docs/repos/o/web", {"permission": "push"}),
        ("PUT", "/orgs/o/teams/docs/repos/o/api", {"permission": "push"}),
    ]
    assert all(c.undo and c.undo[0] == "DELETE" for c in changes)


def test_bulk_team_membership_and_its_removal() -> None:
    added = access.bulk_plan(
        "team",
        "kelly",
        "person",
        "member",
        [{"org": "o", "team": "docs"}, {"org": "o", "team": "web"}],
    )
    assert [c.path for c in added] == [
        "/orgs/o/teams/docs/memberships/kelly",
        "/orgs/o/teams/web/memberships/kelly",
    ]
    removed = access.bulk_plan(
        "team", "kelly", "person", "maintainer", [{"org": "o", "team": "docs"}], remove=True
    )
    assert removed[0].method == "DELETE"
    assert removed[0].tier == WriteTier.DESTRUCTIVE  # a maintainer is tier 3


# -- GH-R-069: roles, read-only ------------------------------------------------------


def test_view_as_role_includes_every_lower_role() -> None:
    read, write = access.view_as_role("read"), access.view_as_role("write")
    assert set(read) < set(write)
    assert "merge pull requests" in write and "merge pull requests" not in read


def test_compare_roles_names_only_what_the_higher_adds() -> None:
    added = access.compare_roles("triage", "write")
    assert "push to branches" in added
    assert "apply labels" not in added


def test_why_cant_they_names_the_role_needed_and_who_can_change_it() -> None:
    text = access.why_cant_they("kelly", "triage", "merge pull requests", "o/web")
    assert text == (
        "kelly has triage access to o/web; merge pull requests needs write. An admin of "
        "o/web can change their role on its Access page, or give a team they are on write."
    )


def test_why_cant_they_points_at_rules_when_the_role_is_enough() -> None:
    text = access.why_cant_they("kelly", "admin", "merge pull requests", "o/web")
    assert "a ruleset or branch protection may block it" in text


def test_why_cant_they_says_when_it_does_not_know() -> None:
    assert access.why_cant_they("kelly", "read", "fly", "o/web") == (
        "QUILL does not know what fly needs on o/web."
    )


# -- GH-R-004: size and pane size are kept with the place ----------------------------


def test_size_and_pane_size_round_trip_and_bad_values_are_dropped(tmp_path) -> None:
    from quill.core.github.navigation_state import (
        WorkbenchPlace,
        load_workbench_place,
        save_workbench_place,
    )

    path = tmp_path / "context.json"
    save_workbench_place("acct", WorkbenchPlace(size=(1200, 800), sash=340), path)
    assert load_workbench_place("acct", path).size == (1200, 800)
    assert load_workbench_place("acct", path).sash == 340
    save_workbench_place("acct", WorkbenchPlace(size=(50, 50), sash=9), path)
    place = load_workbench_place("acct", path)
    assert (place.size, place.sash) == (None, 0)  # too small to be a real window


def test_saving_the_place_keeps_the_size_and_saving_the_size_keeps_the_place(
    wx_session_app, quill_data_dir
) -> None:
    from quill.core.github.navigation_state import load_workbench_place
    from quill.ui.workbench_frame import NodeRef

    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=lambda _t: None)
    provider.remember_layout((1100, 760), 300)
    provider.remember_place(([], NodeRef("repository", "runs", REPO)))
    place = load_workbench_place(provider._account_key())
    assert place.size == (1100, 760) and place.sash == 300
    assert place.last == ("repository", "runs", REPO)
    provider.remember_layout((1000, 700), 0)
    assert load_workbench_place(provider._account_key()).last == ("repository", "runs", REPO)


def test_the_window_opens_at_last_times_size_and_remembers_it_on_close(
    wx_session_app, quill_data_dir
) -> None:
    frame, _said = _frame()
    try:
        frame.provider.remember_layout((1111, 777), 333)
        frame.restore_layout()
        size = frame.frame.ToDIP(frame.frame.GetSize())
        assert (size.GetWidth(), size.GetHeight()) == (1111, 777)
        frame.frame.SetSize(frame.frame.FromDIP(wx.Size(1050, 720)))
        frame.remember_layout()
        assert frame.provider.recall_layout()[0] == (1050, 720)
    finally:
        frame.frame.Destroy()

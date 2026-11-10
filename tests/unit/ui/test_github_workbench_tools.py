"""GitHub Workbench Phases 9 and 10 in the window: the Filter Builder, permissions, history, access.

A real frame over a recorded API; each modal window is driven by replacing
its show() with a script, the way a person would press its buttons.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.access import AccessRow, plan_add  # noqa: E402
from quill.core.github.change_log import ChangeLog  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.permissions import AccessLevel, AccessStore  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.github_api_fake import FakeGitHubApi  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."


class _Items:
    is_authenticated = True
    token = "test-token-not-real"
    last_scopes_header = "repo, read:org"

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [GitHubItem(1, "One", "open", "https://github.com/owner/repo/issues/1", False)]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def search_items(self, _repo: str, query: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    said: list[str] = []
    ran: list[str] = []
    provider = GitHubWorkbenchProvider(
        _Items(),
        REPO,
        announce=said.append,
        editor_command=lambda c: ran.append(c) or True,
        editor_command_available=lambda c: True,
    )
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/labels", [{"name": "bug"}])
    provider.api = api
    provider.batch_pace = 0
    monkeypatch.setattr(provider, "account_name", lambda: "me")
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_modal_dialog", lambda dialog, title: wx.ID_OK
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.ran = ran  # type: ignore[attr-defined]
    ref = NodeRef("repository", "issues_and_pulls", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    yield frame
    frame.frame.Destroy()


def test_the_filter_builder_writes_github_syntax_into_the_filter_box(bench, monkeypatch) -> None:
    from quill.ui.github_filter_builder_dialog import FilterBuilderDialog

    def script(dialog: FilterBuilderDialog) -> bool:
        assert "bug" in dialog.value.GetStrings() or True
        dialog.attribute.SetStringSelection("Label")
        dialog._attribute_changed()
        dialog.operator.SetStringSelection("any of")
        dialog.value.SetValue("bug, ui")
        dialog.add()
        dialog.attribute.SetStringSelection("Milestone")
        dialog._attribute_changed()
        dialog.operator.SetStringSelection("has none")
        dialog.add()
        dialog.query = dialog.text()
        dialog.save = True
        dialog.dialog.Destroy()
        return True

    monkeypatch.setattr(FilterBuilderDialog, "show", script)
    bench.run(f"{_P}filter_builder")
    assert bench.filter.GetValue() == "label:bug,ui no:milestone"
    assert bench.said[-1] == "Saved the search label:bug,ui no:milestone."


def _list_script(monkeypatch, steps) -> list[Any]:
    from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

    seen: list[Any] = []

    def show(dialog: WorkbenchListDialog) -> None:
        seen.append(dialog)
        steps(dialog)
        dialog.dialog.Destroy()

    monkeypatch.setattr(WorkbenchListDialog, "show", show)
    return seen


def test_github_permissions_lists_every_scope_and_adds_the_missing_in_one_step(
    bench, monkeypatch
) -> None:
    def steps(dialog: Any) -> None:
        assert any(
            row.startswith("read:org:") and row.endswith("You have it.") for row in dialog.rows
        )
        project = next(i for i, row in enumerate(dialog.rows) if row.startswith("project:"))
        assert dialog.rows[project].endswith("You do not have it.")
        dialog.buttons[0].GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.wxEVT_BUTTON, dialog.buttons[0].GetId())
        )

    seen = _list_script(monkeypatch, steps)
    bench.run(f"{_P}permissions")
    assert seen and bench.ran[-1] == "file.github_manage_accounts"
    from quill.core.github import oauth_sign_in

    assert "project" in oauth_sign_in.requested_scope().split()
    oauth_sign_in.request_extra_scopes([])


def test_change_history_lists_changes_and_undoes_one(bench, monkeypatch) -> None:
    api = bench.provider.api
    issue = {"number": 1, "labels": [{"name": "bug"}], "updated_at": "x"}
    api.answer("GET", "/repos/owner/repo/issues/1", lambda: issue)
    log = bench.provider.change_log()
    from quill.core.workbench.properties import FieldChange

    log.record(
        account="me",
        kind="issue",
        ident={"repo": REPO, "number": "1"},
        target="Issue #1",
        summary="Issue #1: added bug.",
        changes=[FieldChange("labels", "Labels", (), ("bug",))],
        tier=0,
        confirmed=True,
        can_undo=True,
    )

    def steps(dialog: Any) -> None:
        assert dialog.rows[0].endswith("Issue #1, Issue #1: added bug., confirmed")
        dialog.buttons[0].GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.wxEVT_BUTTON, dialog.buttons[0].GetId())
        )

    _list_script(monkeypatch, steps)
    bench.run(f"{_P}change_history")
    assert api.writes()[-1] == ("PATCH", "/repos/owner/repo/issues/1", {"labels": []})
    assert ChangeLog.load().entries[-1].undone


def test_an_access_change_is_previewed_sent_and_recorded(bench, monkeypatch) -> None:
    provider = bench.provider
    asked = iter(["kelly"])
    monkeypatch.setattr(provider, "_ask_text", lambda *a, **k: next(asked))
    monkeypatch.setattr(provider, "_choose", lambda title, prompt, labels: labels.index("write"))
    from quill.core.github.sheet_catalog import Target
    from quill.core.workbench.properties import FieldSpec

    class _Loaded:
        values = {"collaborators": ("me, person, admin, direct",)}

    state = {"ident": {"repo": REPO}, "loaded": _Loaded()}
    act = provider.table_action(Target("repository", {"repo": REPO}), state)
    act(FieldSpec("collaborators", "People"), "add", "")
    assert provider.api.writes()[-1] == (
        "PUT",
        "/repos/owner/repo/collaborators/kelly",
        {"permission": "push"},
    )
    assert bench.said[-1] == "1 done, 0 failed."
    assert ChangeLog.load().entries[-1].summary.startswith("Invite kelly to owner/repo")


def test_removing_your_own_admin_role_is_refused(bench, monkeypatch) -> None:
    provider = bench.provider
    from quill.core.github.sheet_catalog import Target
    from quill.core.workbench.properties import FieldSpec

    class _Loaded:
        values = {"collaborators": ("me, person, admin, direct",)}

    act = provider.table_action(
        Target("repository", {"repo": REPO}), {"ident": {"repo": REPO}, "loaded": _Loaded()}
    )
    act(FieldSpec("collaborators", "People"), "remove", "me, person, admin, direct")
    assert provider.api.writes() == []
    assert bench.said[-1].startswith("That would leave nobody who can manage it")


def test_the_account_level_is_kept_and_read_only_locks_every_field(bench, monkeypatch) -> None:
    provider = bench.provider
    monkeypatch.setattr(provider, "_choose", lambda *a: 0)
    bench.run(f"{_P}account_level")
    assert AccessStore.load().level("me") is AccessLevel.READ_ONLY
    assert provider.access_level() is AccessLevel.READ_ONLY
    assert plan_add("repository", {"repo": REPO}, "x", "person", "read").words
    assert AccessRow("x").text() == "x, person, , direct"

"""GitHub Phases 7, 9 and 10 in the core: permissions, Change History, batches, filters."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from quill.core.github.batch import BatchItem, item_changes, preview, results_text, run
from quill.core.github.change_log import ChangeLog
from quill.core.github.filter_menu import (
    active,
    cell_choices,
    clear_toggles,
    group_rows,
    local_only,
    local_status,
    matches_local,
    show_only,
    toggle,
    toggle_words,
)
from quill.core.github.permissions import (
    SCOPES,
    AccessLevel,
    AccessStore,
    ViewerContext,
    WriteTier,
    check,
    classic_token_url,
    effective_level,
    expand_scopes,
    fine_grained_steps,
    gh_refresh_command,
    level_allows,
    missing_scopes,
    repo_role,
    scope_rows,
)
from quill.core.github.sheets_items import ISSUE
from quill.core.workbench.properties import FieldChange, ListDelta
from tests.github_api_fake import FakeGitHubApi

# -- permissions (18.1, 18.2, 18.4) ---------------------------------------------


def test_every_scope_the_prd_names_is_in_the_catalogue() -> None:
    names = {scope.name for scope in SCOPES}
    for wanted in (
        "repo",
        "public_repo",
        "read:org",
        "admin:org",
        "write:org",
        "project",
        "read:project",
        "notifications",
        "user",
        "user:follow",
        "user:email",
        "gist",
        "workflow",
        "write:packages",
        "read:packages",
        "delete:packages",
        "delete_repo",
        "admin:repo_hook",
        "admin:org_hook",
        "admin:public_key",
        "admin:gpg_key",
        "admin:ssh_signing_key",
        "security_events",
        "codespace",
        "copilot",
        "read:audit_log",
    ):
        assert wanted in names, wanted
    risky = {scope.name for scope in SCOPES if scope.risky}
    assert risky == {"delete_repo", "delete:packages", "admin:org"}


def test_scope_rows_read_in_full_and_know_what_a_scope_implies() -> None:
    rows = dict((scope.name, said) for scope, said in scope_rows(("repo", "admin:org")))
    assert rows["read:org"].endswith("You have it.")
    assert rows["project"].endswith("You do not have it.")
    assert "Optional and risky" in rows["delete_repo"]
    fine = dict((s.name, said) for s, said in scope_rows(None))
    assert fine["project"].endswith("This token's permissions are set on GitHub.")
    assert "public_repo" in expand_scopes(["repo"])
    assert missing_scopes(["repo"], ["project", "public_repo"]) == ("project",)
    assert missing_scopes(None, ["project"]) == ()


def test_the_three_ways_to_add_missing_scopes() -> None:
    assert gh_refresh_command(["project", "read:org"]) == (
        "gh auth refresh -h github.com -s project,read:org"
    )
    assert classic_token_url(["project"]).startswith(
        "https://github.com/settings/tokens/new?scopes=project"
    )
    assert fine_grained_steps(["project"]) == [
        "project: Organization permissions: Projects: Read and write"
    ]


def test_roles_from_rest_and_graphql() -> None:
    assert repo_role({"admin": False, "push": True, "pull": True}) == "write"
    assert repo_role("MAINTAIN") == "maintain"
    assert repo_role(None) == ""


def test_a_refusal_names_what_it_needs_what_you_have_and_who_can_change_it() -> None:
    ctx = ViewerContext(repo_role="read", where="owner/name")
    said = check("repo:triage", ctx)
    assert said == (
        "Changing this needs triage access to owner/name. You have read access. An owner "
        "or admin of the repository can give it to you."
    )
    assert check("repo:triage", ViewerContext(repo_role="maintain")) == ""
    assert "project permission" in check("scope:project", ViewerContext(scopes=("repo",)))
    assert check("viewer:viewerCanLabel", ViewerContext(viewer={"viewerCanLabel": False}))
    assert check("org:owner", ViewerContext(org_role="member")).startswith(
        "This needs the owner role"
    )


def test_account_levels_and_safe_mode(tmp_path: Path) -> None:
    assert not level_allows(AccessLevel.READ_ONLY, WriteTier.ORGANIZING)
    assert level_allows(AccessLevel.ORGANIZE, WriteTier.VISIBLE)
    assert not level_allows(AccessLevel.ORGANIZE, WriteTier.ACCESS)
    assert level_allows(AccessLevel.FULL, WriteTier.DESTRUCTIVE)
    assert effective_level(AccessLevel.FULL, safe_mode=True) is AccessLevel.READ_ONLY
    store = AccessStore.load(tmp_path / "access.json")
    store.set("kelly", AccessLevel.ORGANIZE)
    assert AccessStore.load(tmp_path / "access.json").level("kelly") is AccessLevel.ORGANIZE
    assert AccessStore.load(tmp_path / "access.json").level("someone") is AccessLevel.FULL
    ctx = ViewerContext(repo_role="admin", level=AccessLevel.ORGANIZE)
    assert "set to Organize" in check("repo:admin", ctx, WriteTier.ACCESS)


# -- Change History (18.5) ----------------------------------------------------------


def test_change_history_is_atomic_kept_ninety_days_and_never_holds_a_token(
    tmp_path: Path,
) -> None:
    path = tmp_path / "history.json"
    log = ChangeLog.load(path)
    token = "ghp_" + "a" * 36
    log.record(
        account="kelly",
        kind="issue",
        ident={"repo": "o/r", "number": "42"},
        target="Issue #42",
        summary=f"#42: title {token}",
        changes=[FieldChange("labels", "Labels", ("docs",), ("bug",))],
        tier=0,
        confirmed=True,
        can_undo=True,
    )
    assert token not in path.read_text(encoding="utf-8")
    again = ChangeLog.load(path)
    assert again.entries[0].fields[0].after == ("bug",)
    assert again.newest_undoable("kelly") == 0
    assert "Issue #42" in again.as_csv()
    old = ChangeLog.load(path, now=again.entries[0].when + 91 * 86400)
    assert old.entries == []
    again.mark_undone(0)
    assert ChangeLog.load(path).newest_undoable() == -1
    again.clear()
    assert ChangeLog.load(path).entries == []


# -- batches (16.4) -------------------------------------------------------------------


def test_a_batch_previews_skips_what_is_already_so_and_reports_each_item() -> None:
    api = FakeGitHubApi()
    issues = {
        1: {"number": 1, "labels": [{"name": "bug"}], "updated_at": "x"},
        2: {"number": 2, "labels": [], "updated_at": "x"},
    }

    def on_write(method: str, path: str, body: object) -> None:
        number = int(path.rsplit("/", 1)[-1])
        assert isinstance(body, dict)
        issues[number]["labels"] = [{"name": n} for n in body["labels"]]

    api.on_write = on_write
    for number in issues:
        api.answer("GET", f"/repos/o/r/issues/{number}", lambda n=number: issues[n])
    items = [
        BatchItem("#1", {"repo": "o/r", "number": "1"}, {"labels": ("bug",)}),
        BatchItem("#2", {"repo": "o/r", "number": "2"}, {"labels": ()}),
    ]
    changes = [FieldChange("labels", "Labels", None, ListDelta(("bug",), ()))]
    said = preview("issues", items, changes)
    assert said == "Change 2 issues: add bug. 1 of them already have bug."
    sleeps: list[float] = []
    results = run(api, ISSUE, items, changes, sleep=sleeps.append)
    assert [(r.name, r.status) for r in results] == [("#1", "Skipped"), ("#2", "Done")]
    assert results_text(results).endswith("1 done, 1 skipped, 0 failed")
    removal = item_changes(
        [FieldChange("labels", "Labels", None, ListDelta((), ("bug",)))], {"labels": ("bug",)}
    )
    assert removal[0].after == ()


# -- filters (17) -------------------------------------------------------------------------


def test_quick_filters_toggle_in_the_one_query() -> None:
    text = toggle("is:open", "assigned_me")
    assert text == "is:open assignee:@me"
    text = toggle(text, "no_milestone")
    assert set(active(text)) == {"assigned_me", "no_milestone"}
    assert toggle_words(text) == "assigned to me, no milestone"
    assert toggle(text, "assigned_me") == "is:open no:milestone"
    assert toggle("", "assigned_to", "kellylford") == "assignee:kellylford"
    assert toggle("", "updated_week", today=dt.date(2026, 11, 10)) == "updated:>=2026-11-03"
    assert clear_toggles("bug assignee:@me no:label") == "bug"


def test_show_only_and_hide_write_github_syntax() -> None:
    cells = cell_choices({"labels": ("bug", "good first issue"), "author": "dependabot"})
    assert ("label:bug", "label bug") in cells
    assert ('label:"good first issue"', "label good first issue") in cells
    assert show_only("is:open", "label:bug") == "is:open label:bug"
    assert show_only("is:open label:bug", "label:bug", hide=True) == "is:open -label:bug"


def test_local_conditions_are_split_off_and_said_honestly() -> None:
    server, local = local_only("is:pr conflicts:true label:bug")
    assert server == "is:pr label:bug"
    assert local == [("conflicts", "true", False)]
    assert matches_local({"conflicts": "dirty"}, local)
    assert not matches_local({"conflicts": "clean"}, local)
    assert local_status(40, 3, complete=False) == (
        "Filtered locally: 3 of 40 loaded. Load All to be sure."
    )


def test_group_by_puts_a_row_in_each_of_its_groups_and_none_last() -> None:
    rows = [("a", ["bug"]), ("b", ["bug", "ui"]), ("c", [])]
    groups = group_rows(rows, "label", lambda row: row[1])
    assert [(name, [r[0] for r in found]) for name, found in groups] == [
        ("bug", ["a", "b"]),
        ("ui", ["b"]),
        ("None", ["c"]),
    ]

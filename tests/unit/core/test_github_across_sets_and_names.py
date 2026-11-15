"""GH-E: Repository Sets, honest outcomes, issue fields, by-name changes and the Fleet.

All against a recorded fake of the Workbench's GitHubApi; nothing reaches GitHub.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from quill.core.github import across
from quill.core.github.across_actions import ACROSS_ROWS, KEYLESS, LIST_KEYS
from quill.core.github.across_by_name import find_uses_query, survey
from quill.core.github.across_changes import (
    apply,
    plan_close,
    plan_copy_missing,
    plan_delete,
    plan_make_same,
    plan_merge,
    plan_rename,
    results_summary,
)
from quill.core.github.across_fleet import read_fleet
from quill.core.github.across_issue_fields import match, read_issue_extras
from quill.core.github.repository_sets import DEFAULT_SET, RepositorySets
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS


class FakeApi:
    """``rest`` answers from a table keyed by (method, path); writes are recorded."""

    def __init__(self, answers: dict[tuple[str, str], Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        if method != "GET":
            self.sent.append((method, path, body))
        answer = self.answers.get((method, path))
        if answer is None and method != "GET":
            answer = {}
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            answer = answer(query or {})
        if answer is None:
            raise RuntimeError(f"404 Not Found: {method} {path}")
        return SimpleNamespace(status=200, data=answer, headers={})


def _repo(push: bool = True, branch: str = "main") -> dict[str, Any]:
    return {"default_branch": branch, "permissions": {"push": push, "admin": False}}


# -- Repository Sets --------------------------------------------------------------


def test_sets_are_named_chosen_renamed_filtered_and_deleted(tmp_path) -> None:
    sets = RepositorySets.load("octo", data_dir=tmp_path)
    assert sets.current_name == DEFAULT_SET
    assert sets.set_repositories("Docs sites", ["a/one", "A/One", "x"]) == ["x"]
    assert sets.repositories("Docs sites") == ["a/one"]  # adding a listed one keeps one copy
    sets.set_filter("QuillVille", "org:Community-Access topic:quillville")
    assert sets.choose("QuillVille") and sets.current_name == "QuillVille"
    assert sets.rename("QuillVille", "docs sites").startswith("There is already")
    assert sets.rename("QuillVille", "Family") == ""
    assert sets.current_name == "Family" and sets.filter_for() == (
        "org:Community-Access topic:quillville"
    )
    sets.save()
    again = RepositorySets.load("octo", data_dir=tmp_path)
    assert again.current_name == "Family" and "made by the filter" in again.describe()
    assert again.delete("Family") and again.current_name == "Docs sites"


def test_a_version_one_file_still_loads(tmp_path) -> None:
    sets = RepositorySets.load("octo", data_dir=tmp_path)
    sets.path.write_text(json.dumps({"version": 1, "sets": {"Work": ["a/one"]}}), "utf-8")
    old = RepositorySets.load("octo", data_dir=tmp_path)
    assert old.names() == ["Work"] and old.current_name == "Work"
    assert old.repositories() == ["a/one"]


# -- outcomes, pages ----------------------------------------------------------------


def test_every_repository_state_has_its_own_sentence() -> None:
    failures = {"a/off": "403 Discussions are disabled", "a/no": "403 Forbidden", "a/bad": "500"}

    def fetch(repo: str, limit: int) -> list[Any]:
        if repo in failures:
            raise RuntimeError(failures[repo])
        return (
            [SimpleNamespace(title=str(n)) for n in range(40)][:limit] if repo == "a/full" else []
        )

    result = across.fetch_across(
        None,
        "discussions",
        ["a/full", "a/none", "a/off", "a/no", "a/bad"],
        per_repo_limits={"a/full": across.more_limit(30)},
        fetchers={key: fetch for key, _label in across.CATEGORIES},
    )
    states = {o.repository: o.state for o in result.outcomes}
    assert states == {
        "a/full": "complete",
        "a/none": "empty",
        "a/off": "disabled",
        "a/no": "no_access",
        "a/bad": "error",
    }
    full = next(o for o in result.outcomes if o.repository == "a/full")
    assert full.limit == 60 and full.count == 40
    said = {o.repository: o.sentence() for o in result.outcomes}
    assert said["a/off"] == "a/off: Discussions are off, so it has none to list"
    assert said["a/no"] == "a/no: could not be read, no access"
    assert "had none" in result.summary() and "3 could not be read" in result.summary()
    assert across.more_limit(90) == across.MAX_PER_REPO


# -- issue type and fields -------------------------------------------------------------


def test_issue_types_and_fields_keep_their_states_apart() -> None:
    api = FakeApi({
        ("GET", "/repos/o/r/issues"): [
            {"number": 1, "type": {"name": "Bug"}},
            {"number": 2, "type": None},
        ],
        ("GET", "/orgs/o/issue-fields"): [
            {"id": 10, "name": "Priority", "data_type": "single_select"},
            {"id": 11, "name": "Notes", "data_type": "text"},
            {"id": 12, "name": "Odd", "data_type": "hologram"},
        ],
        ("GET", "/repos/o/r/issues/1/issue-field-values"): [
            {"issue_field_id": 10, "single_select_option": {"name": "High"}},
            {"issue_field_id": 11, "value": ""},
            {"issue_field_id": 12, "value": "x"},
        ],
        ("GET", "/repos/o/r/issues/2/issue-field-values"): RuntimeError("403 Forbidden"),
    })
    found = read_issue_extras(api, "o/r", [1, 2], organization="o")
    one, two = found[1], found[2]
    assert one.type_state == "set" and one.issue_type == "Bug"
    states = {f.name: f.state for f in one.fields}
    assert states == {"Priority": "value", "Notes": "empty", "Odd": "unsupported"}
    assert "Field Priority (single choice, field 10): High" in one.detail_lines()
    assert two.type_state == "none" and two.fields_state == "hidden"
    assert match(one, [("type", "bug", False), ("field", "Priority=High", False)]) is True
    assert match(one, [("field", "Notes=", False)]) is True
    assert match(two, [("field", "Priority=High", False)]) is None  # unknown, not "no"
    hidden = read_issue_extras(api, "o/r", [1], organization="o", can_see_fields=False)
    assert hidden[1].fields_state == "hidden"


# -- by name: survey, plans, results ------------------------------------------------------


def _label_api() -> FakeApi:
    return FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/ro"): _repo(push=False),
        ("GET", "/repos/a/gone"): RuntimeError("404 Not Found"),
        ("GET", "/repos/a/one/labels"): [
            {"name": "bug", "color": "D73A4A", "description": "Broken"},
            {"name": "defect", "color": "000000", "description": ""},
        ],
        ("GET", "/repos/a/two/labels"): [{"name": "Bug", "color": "ff0000", "description": ""}],
        ("GET", "/repos/a/ro/labels"): [{"name": "bug", "color": "ff0000", "description": ""}],
        ("GET", "/repos/a/one/labels/bug"): {"color": "d73a4a", "description": "Broken"},
        ("GET", "/repos/a/two/labels/Bug"): {"color": "00ff00", "description": ""},
        ("GET", "/repos/a/one/labels/defect"): {"color": "000000", "description": ""},
    })


def test_labels_by_name_show_variants_missing_and_unread() -> None:
    api = _label_api()
    found = survey(api, "labels", ["a/one", "a/two", "a/ro", "a/gone"], read_at="12:00 UTC")
    bug = found.row("BUG")
    assert bug is not None and bug.name == "bug"
    assert [repos for _props, repos in bug.variants()] == [["a/two", "a/ro"], ["a/one"]]
    assert bug.sentence() == (
        "bug: in 3 of 3 repositories, 2 colours, 2 descriptions, 1 could not be read"
    )
    defect = found.row("defect")
    assert defect is not None and defect.missing == ("a/two", "a/ro")
    assert "a/gone" not in defect.missing and defect.unread == (
        ("a/gone", "not found, or no access"),
    )
    assert find_uses_query("labels", "bug", ["a/one"]) == 'label:"bug" repo:a/one'


def test_a_change_previews_permission_and_conflict_then_reports_each_repository() -> None:
    api = _label_api()
    found = survey(api, "labels", ["a/one", "a/two", "a/ro"])
    bug = found.row("bug")
    assert bug is not None
    winner = bug.variants()[1][0]  # a/one's colour and description win
    plan = plan_make_same(found, bug, winner)
    preview = plan.preview()
    assert "a/one: no change" in preview
    assert "a/ro: will not change, you may not change a label there" in preview
    results = apply(api, plan)
    by_repo = {r.repository: r for r in results}
    # a/two changed on GitHub since the survey (00ff00), so it is skipped, not overwritten.
    assert by_repo["a/two"].said == "it was changed on GitHub since you looked"
    assert not by_repo["a/ro"].ok and by_repo["a/one"].ok
    assert results_summary(results).startswith("0 of 3 repositories changed. 1 already right.")
    assert not [s for s in api.sent if s[0] == "PATCH"]


def test_rename_clash_merge_delete_and_add_missing() -> None:
    api = _label_api()
    found = survey(api, "labels", ["a/one", "a/two"])
    defect = found.row("defect")
    bug = found.row("bug")
    assert defect is not None and bug is not None
    clash = plan_rename(found, defect, "bug")
    assert "it already has bug" in clash.steps[0].blocked
    merge = plan_merge(found, defect, "bug")
    assert merge.steps[0].action == "relabel"
    api.answers[("GET", "/repos/a/one/issues")] = lambda q: (
        [{"number": 5}] if q.get("page") == "1" else []
    )
    (result,) = apply(api, merge)
    assert result.ok and "moved 1 items to bug" in result.said
    assert ("POST", "/repos/a/one/issues/5/labels", {"labels": ["bug"]}) in api.sent
    assert ("DELETE", "/repos/a/one/labels/defect", None) in api.sent
    add = plan_copy_missing(found, defect, defect.variants()[0][0])
    assert [s.repository for s in add.runnable] == ["a/two"]
    api.answers[("GET", "/repos/a/two/labels/defect")] = None  # still missing: no conflict
    (added,) = apply(api, add)
    assert added.ok and api.sent[-1][0:2] == ("POST", "/repos/a/two/labels")
    gone = plan_delete(found, bug)
    assert {s.action for s in gone.steps} == {"delete"}


def test_milestones_align_close_and_rules_read() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/one/milestones"): [
            {
                "title": "2027.1",
                "number": 3,
                "due_on": "2027-01-31T00:00:00Z",
                "description": "",
                "state": "open",
                "open_issues": 2,
                "closed_issues": 8,
            },
        ],
        ("GET", "/repos/a/two/milestones"): [
            {
                "title": "2027.1",
                "number": 7,
                "due_on": None,
                "description": "",
                "state": "closed",
                "open_issues": 0,
                "closed_issues": 5,
            },
        ],
        ("GET", "/repos/a/one/milestones/3"): {
            "due_on": "2027-01-31T00:00:00Z",
            "description": "",
            "state": "open",
        },
    })
    found = survey(api, "milestones", ["a/one", "a/two"])
    row = found.row("2027.1")
    assert row is not None and "13 of 15 items closed" in row.sentence()
    close = plan_close(found, row)
    assert [s.action for s in close.steps] == ["close", "skip"]
    results = apply(api, close)
    assert results[0].said == "closed" and results[1].ok
    assert ("PATCH", "/repos/a/one/milestones/3", {"state": "closed"}) in api.sent
    rules = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/one/rulesets"): [
            {"name": "Main rules", "enforcement": "active", "target": "branch"}
        ],
        ("GET", "/repos/a/one/branches/main/protection"): RuntimeError("404 Not Found"),
    })
    read = survey(rules, "rules", ["a/one"])
    names = [r.name for r in read.rows]
    assert names == ["Branch protection on main", "Main rules"]
    assert read.rows[0].copies[0].props == (("protected", "no"),)


# -- the Fleet ----------------------------------------------------------------------------


def test_the_fleet_names_its_revision_and_keeps_failed_repositories() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/one/commits/main"): {
            "sha": "3f2a9c1aaaa",
            "commit": {"committer": {"date": "2026-11-12T10:00:00Z"}},
        },
        ("GET", "/repos/a/one/commits/3f2a9c1aaaa/status"): {"state": "success", "total_count": 2},
        ("GET", "/repos/a/one/pulls"): [{}, {}, {}, {}],
        ("GET", "/repos/a/one/releases/latest"): {"tag_name": "3.2.0"},
        ("GET", "/repos/a/one/dependabot/alerts"): RuntimeError(
            "403 Dependabot alerts are disabled for this repository."
        ),
        ("GET", "/repos/a/gone"): RuntimeError("404 Not Found"),
    })
    one, gone = read_fleet(api, ["a/one", "a/gone"], read_at="2026-11-13 12:00 UTC")
    assert one.sentence() == (
        "a/one: main at 3f2a9c1 from 2026-11-12, checks passing, 4 open pull requests, "
        "latest release 3.2.0, Dependabot alerts are off; read at 2026-11-13 12:00 UTC"
    )
    assert gone.failed and "not found, or no access" in gone.sentence()


# -- rule 8 for the across commands --------------------------------------------------------


def test_every_across_command_has_a_key_or_a_written_reason() -> None:
    commands = {
        row.command_id
        for rows in ACROSS_ROWS.values()
        for row in rows
        if row.command_id.removeprefix("github.workbench.").startswith(("across", "next", "prev"))
    }
    keyed = set(WORKBENCH_KEYS) | set(LIST_KEYS)
    assert sorted(c for c in commands if c not in keyed and c not in KEYLESS) == []
    assert all(reason.strip() for reason in KEYLESS.values())

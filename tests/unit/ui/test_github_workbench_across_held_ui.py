"""GH-R-151 in the window: milestone rename and delete, environment Add to Missing, Delete
Where Merged, Draft Releases Together and Dismiss Everywhere, each from its row, through the
preview and a result per repository; and New Ruleset and New Environment in one repository.

A real frame over a recorded fake of the Workbench's GitHubApi; nothing leaves the machine.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.core.github.notifications import GitHubSecurityAlert  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.core.test_github_across_held_writes import FakeApi  # noqa: E402
from tests.unit.ui.test_github_workbench_across_more_ui import (  # noqa: E402
    _choose,
    _go,
    _inline,
    _Items,
)


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    from quill.ui.github_workbench_window import GitHubWorkbenchProvider
    from quill.ui.workbench_frame import WorkbenchFrame

    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), "", announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _repo(admin: bool = True) -> dict[str, Any]:
    return {"id": 1, "default_branch": "main", "permissions": {"push": True, "admin": admin}}


def _previews(provider: Any, monkeypatch: Any, answer: bool = True) -> list[dict[str, Any]]:
    """Record each preview's plan and how it was asked; answer it."""
    shown: list[dict[str, Any]] = []

    def preview(title: str, plan: Any, yes: str, **kw: Any) -> bool:
        shown.append({"title": title, "plan": plan, "yes": yes, **kw})
        return answer

    monkeypatch.setattr(provider, "_across_preview", preview)
    return shown


def _milestones() -> FakeApi:
    one = {"number": 1, "title": "v1", "state": "open", "open_issues": 1, "closed_issues": 0}
    two = {"number": 2, "title": "v1", "state": "open", "open_issues": 0, "closed_issues": 4}
    return FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/two"): _repo(),
        ("GET", "/repos/o/one/milestones"): [one],
        ("GET", "/repos/o/two/milestones"): [two],
        ("GET", "/repos/o/one/milestones/1"): one,
        ("GET", "/repos/o/two/milestones/2"): two,
    })


def test_a_milestone_is_deleted_everywhere_after_a_preview_that_starts_on_cancel(
    bench, monkeypatch
) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = _milestones()
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_milestones"))
    (row,) = bench.rows
    assert provider._fits_across_rename_name(row) and provider._fits_across_delete_name(row)
    shown = _previews(provider, monkeypatch, answer=False)
    provider._do_across_delete_name(None, row)
    (asked,) = shown
    assert asked["destructive"] is True and asked["yes"] == "Delete"
    assert api.sent == []  # Cancel sent nothing
    shown = _previews(provider, monkeypatch)
    provider._do_across_delete_name(None, row)
    assert [p for m, p, _b in api.sent] == [
        "/repos/o/one/milestones/1",
        "/repos/o/two/milestones/2",
    ]
    assert bench.details.GetValue().startswith("2 of 2 repositories changed.")
    assert "o/one: deleted v1; its 1 open item and 0 closed items stay" in bench.details.GetValue()


def test_a_milestone_renamed_everywhere_is_in_change_history_to_undo(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = _milestones()
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_milestones"))
    (row,) = bench.rows
    monkeypatch.setattr(provider, "_ask_text", lambda *_a, **_kw: "v1.0")
    _previews(provider, monkeypatch)
    provider._do_across_rename_name(None, row)
    assert ("PATCH", "/repos/o/one/milestones/1", {"title": "v1.0"}) in api.sent
    entries = provider.change_log().entries[-2:]
    assert [e.kind for e in entries] == ["milestone", "milestone"]
    assert all(e.can_undo for e in entries)


def test_the_destructive_preview_names_the_count_and_every_repository(bench, monkeypatch) -> None:
    from quill.core.github.across_changes import Plan, Step

    provider = bench.provider
    asked: dict[str, Any] = {}
    monkeypatch.setattr(
        "quill.ui.wordpress_workbench_dialogs.ask_preview",
        lambda *_a, **kw: asked.update(kw) or False,
    )
    plan = Plan(
        "milestones",
        "v1",
        "Delete",
        (Step("o/one", "delete", after="gone"), Step("o/two", "delete", after="gone")),
    )
    provider._across_preview("Delete: v1", plan, "Delete", destructive=True)
    assert asked["summary"] == (
        "Delete the milestone v1: 2 of 2 repositories will change. They are: o/one and o/two."
    )
    assert asked["destructive"] is True and asked["undoable"] is False


def test_an_environment_is_offered_add_to_missing(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/two"): _repo(),
        ("GET", "/repos/o/one/environments"): {"environments": [{"name": "production"}]},
        ("GET", "/repos/o/two/environments"): {"environments": []},
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_environments"))
    (row,) = bench.rows
    assert provider._fits_across_add_missing(row)
    monkeypatch.setattr(provider, "_choose_many", lambda _t, _p, labels, _c: labels)
    _previews(provider, monkeypatch)
    provider._do_across_add_missing(None, row)
    assert [(m, p) for m, p, _b in api.sent] == [("PUT", "/repos/o/two/environments/production")]


def test_delete_where_merged_reads_first_then_previews_on_cancel(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/two"): _repo(),
        ("GET", "/repos/o/one/pulls"): [],
        ("GET", "/repos/o/two/pulls"): [],
        ("GET", "/repos/o/one/branches"): [{"name": "main"}, {"name": "done"}],
        ("GET", "/repos/o/two/branches"): [{"name": "main"}, {"name": "done"}],
        ("GET", "/repos/o/one/branches/done"): {"commit": {"sha": "1111111aaa"}},
        ("GET", "/repos/o/two/branches/done"): {"commit": {"sha": "2222222bbb"}},
        ("GET", "/repos/o/one/compare/main...done"): {"ahead_by": 0},
        ("GET", "/repos/o/two/compare/main...done"): {"ahead_by": 4},
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_branches"))
    row = next(r for r in bench.rows if r.title == "done")
    assert provider._fits_across_delete_merged(row) and not provider._fits_across_delete_name(row)
    shown = _previews(provider, monkeypatch)
    provider._do_across_delete_merged(None, row)
    (asked,) = shown
    assert asked["destructive"] is True
    assert [s.repository for s in asked["plan"].runnable] == ["o/one"]
    assert [p for _m, p, _b in api.sent] == ["/repos/o/one/git/refs/heads/done"]
    said = bench.details.GetValue()
    assert said.startswith("1 of 2 repositories changed. Not changed: o/two: 4 commits on it")
    assert "o/one: deleted; its last commit was 1111111" in said
    assert "o/two: not changed, 4 commits on it" in said


def test_draft_releases_together_from_a_tag_row(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/two"): _repo(),
        ("GET", "/repos/o/one/tags"): [{"name": "v3", "commit": {"sha": "abc"}}],
        ("GET", "/repos/o/two/tags"): [{"name": "v3", "commit": {"sha": "def"}}],
        ("GET", "/repos/o/one/releases"): [],
        ("GET", "/repos/o/two/releases"): [],
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_tags"))
    (row,) = bench.rows
    assert provider._fits_across_draft_releases(row)
    offered: list[Any] = []
    monkeypatch.setattr(
        provider, "_choose_many", lambda _t, _p, _l, checked: offered.append(checked) or checked
    )
    monkeypatch.setattr(provider, "_ask_text", lambda *_a, **_kw: "Fixes for {repository}")
    monkeypatch.setattr(provider, "_choose", lambda *_a: 0)
    shown = _previews(provider, monkeypatch)
    provider._do_across_draft_releases(None, row)
    assert offered == [["o/one", "o/two"]] and "destructive" not in shown[0]
    assert [b["body"] for _m, _p, b in api.sent] == ["Fixes for o/one", "Fixes for o/two"]
    assert all(b["draft"] is True for _m, _p, b in api.sent)


def _alert_row(provider: Any, alert_type: str = "Dependabot") -> ExploreRow:
    model = GitHubSecurityAlert(
        3, "open", "high", "lodash", "Prototype pollution", alert_type=alert_type
    )
    row = ExploreRow("o/one: alert 3", "", "", "o/one", "across_item", "alert-key")
    provider._across()["sources"][row.key] = ("alerts", "o/one", model)
    return row


def test_dismiss_everywhere_previews_on_cancel_and_each_alert_can_be_undone(
    bench, monkeypatch
) -> None:
    provider = bench.provider
    row = _alert_row(provider)
    assert provider._fits_across_dismiss_alerts(row)
    assert not provider._fits_across_dismiss_alerts(_alert_row(provider, "Secret scanning"))
    row = _alert_row(provider)
    advisory = {"ghsa_id": "GHSA-1", "summary": "Prototype pollution"}
    api = FakeApi({
        ("GET", "/repos/o/one/dependabot/alerts"): [{"number": 3, "security_advisory": advisory}],
        ("GET", "/repos/o/two/dependabot/alerts"): [{"number": 8, "security_advisory": advisory}],
        ("PATCH", "/repos/o/one/dependabot/alerts/3"): {"state": "dismissed"},
        ("PATCH", "/repos/o/two/dependabot/alerts/8"): {"state": "dismissed"},
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    monkeypatch.setattr(provider, "across_scope", lambda: (["o/one", "o/two"], ""))
    monkeypatch.setattr(provider, "_choose", lambda *_a: 4)  # risk is tolerable
    monkeypatch.setattr(provider, "_ask_optional", lambda *_a: "")
    shown = _previews(provider, monkeypatch)
    provider._do_across_dismiss_alerts(None, row)
    (asked,) = shown
    assert asked["destructive"] is True and asked["undoable"] is True
    assert [p for _m, p, _b in api.sent] == [
        "/repos/o/one/dependabot/alerts/3",
        "/repos/o/two/dependabot/alerts/8",
    ]
    entries = provider.change_log().entries[-2:]
    assert [e.kind for e in entries] == ["security_alert", "security_alert"]
    assert all(e.can_undo for e in entries)
    assert bench.details.GetValue().startswith("2 of 2 repositories changed.")


def test_a_comment_longer_than_github_keeps_is_refused_before_anything_is_read(
    bench, monkeypatch
) -> None:
    provider = bench.provider
    row = _alert_row(provider)
    api = FakeApi({})
    monkeypatch.setattr(provider, "github_api", lambda: api)
    monkeypatch.setattr(provider, "_choose", lambda *_a: 0)
    monkeypatch.setattr(provider, "_ask_optional", lambda *_a: "x" * 300)
    provider._do_across_dismiss_alerts(None, row)
    assert api.queries == [] and "at most 280. Nothing was dismissed." in bench.said[-1]


def test_the_preview_dialog_starts_on_cancel_and_says_when_undo_can_reverse_it(
    wx_session_app,
) -> None:
    from quill.ui.wordpress_workbench_dialogs import PreviewDialog

    frame = wx.Frame(None)
    try:
        for undoable, words in ((True, "Change History can undo it"), (False, "cannot be undone")):
            dialog = PreviewDialog(
                frame,
                title="Dismiss",
                summary="s",
                lines=["a"],
                yes="Dismiss",
                destructive=True,
                undoable=undoable,
            )
            assert words in dialog.GetHelpText()
            assert dialog.GetDefaultItem() is dialog.FindWindow(wx.ID_CANCEL)
            dialog.Destroy()
    finally:
        frame.Destroy()


# -- New Ruleset and New Environment in one repository --------------------------------


class _Window:
    """The two New Here handlers over stubbed questions; nothing is shown."""

    signed_in = True

    def __init__(self, node: str, picks: list[int], texts: list[str], api: FakeApi) -> None:
        self.picks, self.texts, self.api = list(picks), list(texts), api
        self.said: list[str] = []
        self.asked: list[str] = []
        self.frame = SimpleNamespace(
            current=SimpleNamespace(key=node), reload=lambda: self.said.append("(reloaded)")
        )

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, *_a: Any) -> int:
        return self.picks.pop(0)

    def _confirm(self, _title: str, question: str) -> bool:
        self.asked.append(question)
        return True

    def _ask_text(self, *_a: Any, **_kw: Any) -> str:
        return self.texts.pop(0)

    def _check_rules(self, *_a: Any) -> list[int]:
        return [0, 1]

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def _new_ruleset_window(**kw: Any) -> Any:
    from quill.ui.github_workbench_new_ruleset import GitHubWorkbenchNewRulesetMixin

    class Window(_Window, GitHubWorkbenchNewRulesetMixin):
        def _check_rules(self, *_a: Any) -> list[int]:
            return [0, 1]

    return Window(**kw)


def test_new_ruleset_asks_says_the_whole_ruleset_then_makes_it() -> None:
    api = FakeApi({("GET", "/repos/o/r/rulesets"): []})
    window = _new_ruleset_window(
        node="repo_rulesets", picks=[0, 0, 0], texts=["Protect main", "2"], api=api
    )
    assert window._fits_new_ruleset(None)
    window._do_new_ruleset(SimpleNamespace(instance="o/r"), None)
    (question,) = window.asked
    assert question.startswith("The ruleset Protect main in o/r. On the default branch: ")
    assert question.endswith("Make it now?")
    ((method, path, body),) = api.sent
    assert (method, path) == ("POST", "/repos/o/r/rulesets")
    assert [r["type"] for r in body["rules"]] == ["pull_request", "non_fast_forward"]
    assert body["rules"][0]["parameters"]["required_approving_review_count"] == 2
    assert window.said[0] == "Made the ruleset Protect main in o/r, as described."
    assert window.said[-1] == "(reloaded)"


def test_new_ruleset_says_why_before_sending_a_bad_answer() -> None:
    api = FakeApi({})
    window = _new_ruleset_window(node="repo_rulesets", picks=[0, 0], texts=["x", "many"], api=api)
    window._do_new_ruleset(SimpleNamespace(instance="o/r"), None)
    assert window.said == ["Approvals are a whole number, 0 to 10. Nothing was made."]
    assert api.sent == []


def test_new_environment_from_environments() -> None:
    from quill.ui.github_workbench_environments import GitHubWorkbenchEnvironmentsMixin

    class Window(_Window, GitHubWorkbenchEnvironmentsMixin):
        pass

    api = FakeApi({("PUT", "/repos/o/r/environments/staging"): {"name": "staging"}})
    window = Window("environments", [1], ["staging", "0"], api)
    assert window._fits_new_environment(None)
    window._do_new_environment(SimpleNamespace(instance="o/r"), None)
    assert api.sent[0][2]["deployment_branch_policy"]["protected_branches"] is True
    assert window.said == [
        "Made the environment staging in o/r: any branch may deploy to it, with no wait.",
        "(reloaded)",
    ]
    window = Window("environments", [0], ["staging", "lots"], FakeApi({}))
    window._do_new_environment(SimpleNamespace(instance="o/r"), None)
    assert window.said == ["The wait is a whole number of minutes, 0 to 43200. Nothing was made."]


def test_every_new_verb_is_registered_and_new_here() -> None:
    from quill.core.github.item_shortcuts import NEW_HERE
    from quill.ui.github_workbench_across import ACROSS_VERBS
    from quill.ui.github_workbench_development import DEVELOPMENT_VERBS

    assert {"across_delete_merged", "across_draft_releases", "across_dismiss_alerts"} <= set(
        ACROSS_VERBS
    )
    assert {"new_ruleset", "new_environment"} <= set(DEVELOPMENT_VERBS)
    assert NEW_HERE["repo_rulesets"] == "github.workbench.new_ruleset"
    assert NEW_HERE["environments"] == "github.workbench.new_environment"


def test_no_across_method_is_shadowed_in_the_window() -> None:
    """The across preview was once named _preview, which the plain-language batch's own
    _preview shadowed in the window, so every by-name change failed before its preview."""
    from quill.ui import (
        github_workbench_across,
        github_workbench_across_more,
        github_workbench_across_names,
        github_workbench_across_ops,
    )
    from quill.ui.github_workbench_window import GitHubWorkbenchProvider

    mixins = (
        github_workbench_across.GitHubWorkbenchAcrossMixin,
        github_workbench_across_names.GitHubWorkbenchAcrossNamesMixin,
        github_workbench_across_more.GitHubWorkbenchAcrossMoreMixin,
        github_workbench_across_ops.GitHubWorkbenchAcrossOpsMixin,
    )
    stubs = {"github_api", "across_scope"}
    for mixin in mixins:
        for name, value in vars(mixin).items():
            if callable(value) and not name.startswith("__") and name not in stubs:
                owner = next(c for c in GitHubWorkbenchProvider.__mro__ if name in vars(c))
                assert owner is mixin, f"{mixin.__name__}.{name} is {owner.__name__}'s"

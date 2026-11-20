"""The Access buttons and the organization commands in the window: typed names, no lockout.

complete.md 1.3: organization members are converted or removed only after
their name is typed, and no new destructive membership or permission action
can take away your own way of managing something. A real frame over a
recorded API.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.access import OUTSIDE  # noqa: E402
from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.core.github.quick_tables import QUICK  # noqa: E402
from quill.core.github.sheet_catalog import Target  # noqa: E402
from quill.core.workbench.properties import FieldSpec  # noqa: E402
from tests.unit.ui.test_github_workbench_tools import bench as tools_bench  # noqa: E402, F401

_QUICK = {q.verb: q for q in QUICK}


@pytest.fixture
def bench(request):
    """The window and recorded API of the Phase 9 and 10 tests (their fixture, bench)."""
    return request.getfixturevalue("tools_bench")


class _Loaded:
    def __init__(self, **values: Any) -> None:
        self.values = values


def _answers(monkeypatch, provider, *, typed: list[str], choose: str = "") -> None:
    queue = list(typed)
    monkeypatch.setattr(provider, "_ask_text", lambda *a, **k: queue.pop(0) if queue else "")
    monkeypatch.setattr(provider, "_confirm", lambda *a: True)
    if choose:
        monkeypatch.setattr(provider, "_choose", lambda _t, _p, labels: labels.index(choose))


_MEMBERS = (
    "me, person, owner, direct, two-factor on",
    "ana, person, owner, direct, two-factor on",
    "kim, person, member, direct, two-factor off",
)


def test_a_member_becomes_an_outside_collaborator_only_with_the_name_typed(
    bench, monkeypatch
) -> None:
    provider = bench.provider
    org = Target("organization", {"org": "acme"})
    state = {"ident": {"org": "acme"}, "loaded": _Loaded(members=_MEMBERS)}
    act = provider.table_action(org, state)
    _answers(monkeypatch, provider, typed=["kin"], choose=OUTSIDE)
    act(FieldSpec("members", "Members"), "change", _MEMBERS[2])
    assert provider.api.writes() == []
    assert bench.said[-1] == "The name did not match. Nothing changed."
    _answers(monkeypatch, provider, typed=["kim"], choose=OUTSIDE)
    act(FieldSpec("members", "Members"), "change", _MEMBERS[2])
    assert provider.api.writes() == [("PUT", "/orgs/acme/outside_collaborators/kim", {})]
    assert bench.said[-1] == "1 done, 0 failed."


def test_you_cannot_make_yourself_an_outside_collaborator(bench, monkeypatch) -> None:
    provider = bench.provider
    state = {"ident": {"org": "acme"}, "loaded": _Loaded(members=_MEMBERS)}
    act = provider.table_action(Target("organization", {"org": "acme"}), state)
    _answers(monkeypatch, provider, typed=["me"], choose=OUTSIDE)
    act(FieldSpec("members", "Members"), "change", _MEMBERS[0])
    assert provider.api.writes() == []
    assert bench.said[-1].startswith("That takes you out of the organization")


def test_removing_an_outside_collaborator_is_tier_three(bench, monkeypatch) -> None:
    provider = bench.provider
    rows = ("zed, person, outside collaborator, repositories only",)
    state = {"ident": {"org": "acme"}, "loaded": _Loaded(members=_MEMBERS, outside=rows)}
    act = provider.table_action(Target("organization", {"org": "acme"}), state)
    _answers(monkeypatch, provider, typed=["zed"])
    act(FieldSpec("outside", "Outside collaborators"), "remove", rows[0])
    assert provider.api.writes() == [("DELETE", "/orgs/acme/outside_collaborators/zed", None)]


def test_the_last_maintainer_of_a_team_cannot_remove_themselves(bench, monkeypatch) -> None:
    provider = bench.provider
    state = {
        "ident": {"org": "acme", "team": "docs"},
        "loaded": _Loaded(maintainers=("me, maintainer",), members=("kim, member",)),
    }
    act = provider.table_action(Target("team", {"org": "acme", "team": "docs"}), state)
    _answers(monkeypatch, provider, typed=["me"])
    act(FieldSpec("maintainers", "Maintainers"), "remove", "me, maintainer")
    assert provider.api.writes() == []
    assert bench.said[-1].startswith("That would leave nobody who can manage it")


def test_a_teams_admin_on_a_repository_is_kept_when_it_is_your_way_in(bench, monkeypatch) -> None:
    provider = bench.provider
    api = provider.api
    api.answer("GET", "/user", {"login": "me"})
    api.answer("GET", "/orgs/acme/members", [{"login": "ana"}])  # the owners
    api.answer("GET", "/orgs/acme/teams/docs/memberships/me", {"state": "active"})
    api.answer("GET", "/repos/acme/site/collaborators", [])
    row = "acme/site, repository, admin, team"
    state = {"ident": {"org": "acme", "team": "docs"}, "loaded": _Loaded(team_repos=(row,))}
    act = provider.table_action(Target("team", {"org": "acme", "team": "docs"}), state)
    _answers(monkeypatch, provider, typed=["acme/site"])
    act(FieldSpec("team_repos", "Repositories"), "remove", row)
    assert api.writes() == []
    assert bench.said[-1].startswith("That takes away your own admin access to acme/site")
    _answers(monkeypatch, provider, typed=[], choose="maintain")
    act(FieldSpec("team_repos", "Repositories"), "change", row)
    assert api.writes() == []
    _answers(monkeypatch, provider, typed=["acme/quill"], choose="write")
    act(FieldSpec("team_repos", "Repositories"), "add", "")
    assert api.writes() == [
        ("PUT", "/orgs/acme/teams/docs/repos/acme/quill", {"permission": "push"})
    ]


def test_make_outside_collaborator_asks_for_the_name_and_refuses_yourself(
    bench, monkeypatch
) -> None:
    provider = bench.provider
    api = provider.api
    api.answer("GET", "/user", {"login": "me"})
    api.answer("GET", "/orgs/acme/members", [{"login": "me"}])
    quick = _QUICK["make_outside_collaborator"]
    _answers(monkeypatch, provider, typed=["kim", "kin"])
    provider.quick_start(quick, {"org": "acme"})
    assert api.writes() == []
    assert bench.said[-1] == "The name did not match. Nothing changed."
    _answers(monkeypatch, provider, typed=["me", "me"])
    provider.quick_start(quick, {"org": "acme"})
    assert api.writes() == []
    assert bench.said[-1].startswith("That takes you out of the organization")
    _answers(monkeypatch, provider, typed=["kim", "kim"])
    provider.quick_start(quick, {"org": "acme"})
    assert api.writes() == [("PUT", "/orgs/acme/outside_collaborators/kim", {})]
    assert bench.said[-1] == "kim is an outside collaborator now."


def test_removing_a_member_from_the_members_list_is_typed_and_guarded(bench, monkeypatch) -> None:
    provider = bench.provider
    api = provider.api
    api.answer("GET", "/user", {"login": "me"})
    api.answer("GET", "/orgs/acme/members", [{"login": "me"}])  # the only owner
    ref = type("Ref", (), {"instance": "acme"})()
    me = ExploreRow("me, owner.", "", "", "acme", "resource", "org_members:me")
    _answers(monkeypatch, provider, typed=["me"])
    provider._do_resource_delete(ref, me)
    assert api.writes() == []
    assert "leave nobody who can manage it" in bench.said[-1]
    kim = ExploreRow("kim, member.", "", "", "acme", "resource", "org_members:kim")
    _answers(monkeypatch, provider, typed=["kim"])
    monkeypatch.setattr(bench, "reload", lambda: None)
    provider._do_resource_delete(ref, kim)
    assert api.writes() == [("DELETE", "/orgs/acme/members/kim", None)]

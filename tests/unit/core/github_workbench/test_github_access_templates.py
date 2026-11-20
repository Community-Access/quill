"""Access templates: named sets of access, applied to a person in one batch (GH-R-068)."""

from __future__ import annotations

from pathlib import Path

from quill.core.github.access_templates import AccessTemplates, parse_grants, template_plan
from quill.core.github.permissions import WriteTier
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS

CONTRIBUTOR = "write on o/web\nwrite on o/api\nmember of o/docs"


def test_each_line_is_one_grant_and_what_is_not_one_is_said() -> None:
    grants, rejected = parse_grants(
        "Write on o/web; triage on o/api\nmaintainer of o/docs\nowner of o\n"
        "push on o/web\nmember of\nwrite on not-a-repository"
    )
    assert [g.text() for g in grants] == [
        "write on o/web",
        "triage on o/api",
        "maintainer of o/docs",
        "owner of o",
    ]
    assert rejected == ["push on o/web", "member of", "write on not-a-repository"]


def test_one_role_a_place_the_last_line_wins() -> None:
    grants, _ = parse_grants("read on o/web\nadmin on O/Web")
    assert [g.text() for g in grants] == ["admin on O/Web"]


def test_the_batch_joins_the_organization_then_teams_then_repositories() -> None:
    grants, _ = parse_grants(CONTRIBUTOR + "\nmember of o")
    plan = template_plan(grants, "@kelly")
    assert [(c.method, c.path, c.body) for c in plan] == [
        ("PUT", "/orgs/o/memberships/kelly", {"role": "member"}),
        ("PUT", "/orgs/o/teams/docs/memberships/kelly", {"role": "member"}),
        ("PUT", "/repos/o/api/collaborators/kelly", {"permission": "push"}),
        ("PUT", "/repos/o/web/collaborators/kelly", {"permission": "push"}),
    ]
    assert all(c.tier == WriteTier.ACCESS and c.undo for c in plan)
    assert plan[2].words == (
        "Invite kelly to o/api with write access. GitHub sends them an invitation."
    )


def test_templates_are_kept_per_account_renamed_and_deleted(tmp_path: Path) -> None:
    mine = AccessTemplates.load("account-a", data_dir=tmp_path)
    assert mine.set_template("  Contributor ", CONTRIBUTOR) == ("", [])
    mine.save()

    again = AccessTemplates.load("account-a", data_dir=tmp_path)
    assert again.names() == ["Contributor"]
    assert again.text("Contributor") == CONTRIBUTOR
    assert again.describe("Contributor") == (
        "Contributor: write on o/web; write on o/api; member of o/docs"
    )
    assert AccessTemplates.load("account-b", data_dir=tmp_path).names() == []

    assert again.set_template("Reviewer", "triage on o/web") == ("", [])
    assert (
        again.rename("Reviewer", "contributor") == "There is already a template called contributor."
    )
    assert again.rename("Reviewer", "Triager") == ""
    assert again.delete("Triager") and not again.delete("Triager")


def test_a_template_needs_a_name_and_one_grant() -> None:
    store = AccessTemplates(Path("unused.json"))
    assert store.set_template(" ", CONTRIBUTOR)[0] == "A template needs a name."
    problem, rejected = store.set_template("Empty", "push on o/web")
    assert problem.startswith("A template needs at least one line")
    assert rejected == ["push on o/web"]
    assert store.names() == []


def test_applying_is_an_access_write_and_managing_is_local() -> None:
    assert COMMAND_REQUIREMENTS["github.workbench.apply_access_template"] == (
        "repo:admin",
        WriteTier.ACCESS,
    )
    assert COMMAND_REQUIREMENTS["github.workbench.access_templates"][0] == "local"

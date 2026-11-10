"""GitHub Phase 8: every object's sheet, against recorded answers (Appendix C, 16.6, 18.3.1)."""

from __future__ import annotations

import json

from quill.core.github.rulesets import classic_as_rules, ruleset_body, summary
from quill.core.github.sheet_catalog import SHEETS, Target, target_for
from quill.core.github.sheet_engine import load, plan, save
from quill.core.github.sheets_deploy import seal_secret
from quill.core.github.sheets_projects import parse_fields, project_item_sheet
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

RULESET = {
    "id": 9,
    "name": "main",
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "bypass_actors": [{"actor_type": "RepositoryRole", "actor_id": 2, "bypass_mode": "always"}],
    "rules": [
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": 2,
                "require_code_owner_review": True,
            },
        },
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": "build"}, {"context": "test"}]},
        },
        {"type": "non_fast_forward"},
    ],
}


def test_a_ruleset_reads_as_one_plain_sentence() -> None:
    assert summary(RULESET) == (
        "On the default branch: changes need a pull request with 2 approvals including a "
        "code owner; checks build and test must pass; force pushes are blocked; "
        "maintainers, always may bypass."
    )


def test_a_ruleset_sheet_edits_rules_and_sends_the_whole_ruleset_back() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/repos/o/r/rulesets/9", RULESET)
    ident = {"repo": "o/r", "id": "9"}
    loaded = load(api, SHEETS["ruleset"], ident)
    assert loaded.values["approvals"] == 2
    assert "block force pushes" in loaded.values["rules"]
    changes = [
        FieldChange("approvals", "Approvals needed", 2, 1),
        FieldChange(
            "rules",
            "Rules",
            loaded.values["rules"],
            ("require a pull request", "require status checks", "require signed commits"),
        ),
    ]
    save(api, SHEETS["ruleset"], ident, changes, loaded=loaded.values, check_conflicts=False)
    method, path, body = api.writes()[0]
    assert (method, path) == ("PUT", "/repos/o/r/rulesets/9")
    kinds = [rule["type"] for rule in body["rules"]]
    assert "non_fast_forward" not in kinds and "required_signatures" in kinds
    pr = next(rule for rule in body["rules"] if rule["type"] == "pull_request")
    assert pr["parameters"]["required_approving_review_count"] == 1
    assert body["bypass_actors"] == RULESET["bypass_actors"]


def test_classic_protection_reads_through_the_same_summary() -> None:
    protection = {
        "required_pull_request_reviews": {"required_approving_review_count": 1},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
        "enforce_admins": {"enabled": True},
    }
    said = summary(classic_as_rules(protection, "main"))
    assert said.startswith("On main: changes need a pull request with 1 approval;")
    body = ruleset_body(RULESET, {"enforcement": "evaluate"})
    assert body["enforcement"] == "evaluate"


def test_an_environment_saves_whole_with_its_reviewers_kept() -> None:
    raw = {
        "name": "production",
        "can_admins_bypass": True,
        "protection_rules": [
            {"type": "wait_timer", "wait_timer": 5},
            {
                "type": "required_reviewers",
                "prevent_self_review": False,
                "reviewers": [{"type": "User", "reviewer": {"login": "kelly", "id": 7}}],
            },
        ],
        "deployment_branch_policy": None,
    }
    api = FakeGitHubApi()
    api.answer("GET", "/repos/o/r/environments/production", raw)
    ident = {"repo": "o/r", "name": "production"}
    loaded = load(api, SHEETS["environment"], ident)
    assert loaded.values["reviewers"] == ("kelly, user",)
    from quill.core.github.sheet_engine import adopted

    (request,) = plan(
        SHEETS["environment"],
        adopted(SHEETS["environment"], ident, loaded.values),
        [FieldChange("wait_timer", "Wait timer", 5, 10)],
    )
    assert request.method == "PUT"
    assert request.body is not None
    assert request.body["wait_timer"] == 10
    assert request.body["reviewers"] == [{"type": "User", "id": 7}]


def test_a_secret_is_sealed_and_never_said_or_re_read() -> None:
    from nacl import encoding, public

    private = public.PrivateKey.generate()
    key = private.public_key.encode(encoding.Base64Encoder).decode("ascii")
    sealed = seal_secret(key, "hunter2")
    assert public.SealedBox(private).decrypt(__import__("base64").b64decode(sealed)) == b"hunter2"
    api = FakeGitHubApi()
    api.answer("GET", "/repos/o/r/actions/secrets/TOKEN", {"name": "TOKEN"})
    api.answer("GET", "/repos/o/r/actions/secrets/public-key", {"key_id": "k1", "key": key})
    ident = {"repo": "o/r", "name": "TOKEN"}
    loaded = load(api, SHEETS["secret"], ident)
    outcome = save(
        api,
        SHEETS["secret"],
        ident,
        [FieldChange("secret_value", "New value", "", "hunter2")],
        loaded=loaded.values,
        check_conflicts=False,
    )
    assert [(c.key, c.after) for c in outcome.done] == [("secret_value", "(set)")]
    method, _path, body = api.writes()[0]
    assert method == "PUT" and body["key_id"] == "k1" and "hunter2" not in json.dumps(body)


def test_team_code_review_is_one_mutation_with_every_setting() -> None:
    sheet = SHEETS["team"]
    ident = {
        "org": "acme",
        "team": "docs",
        "node_id": "T_1",
        "review_enabled": "False",
        "review_algorithm": "round robin",
        "review_count": "1",
        "review_notify": "True",
    }
    found = plan(
        sheet,
        ident,
        [
            FieldChange("review_enabled", "Assign", False, True),
            FieldChange("review_algorithm", "How", "round robin", "load balance"),
        ],
    )
    (request,) = found
    assert "updateTeamReviewAssignment" in request.graphql
    assert request.body == {
        "id": "T_1",
        "enabled": True,
        "algorithm": "LOAD_BALANCE",
        "count": 1,
        "notify": True,
    }


def test_a_project_item_sheet_has_one_control_per_field_by_type() -> None:
    data = {
        "node": {
            "fields": {
                "nodes": [
                    {
                        "id": "F1",
                        "name": "Status",
                        "dataType": "SINGLE_SELECT",
                        "options": [
                            {"id": "o1", "name": "Todo"},
                            {"id": "o2", "name": "In progress"},
                        ],
                    },
                    {"id": "F2", "name": "Due", "dataType": "DATE"},
                    {
                        "id": "F3",
                        "name": "Sprint",
                        "dataType": "ITERATION",
                        "configuration": {
                            "iterations": [
                                {
                                    "id": "i4",
                                    "title": "Iteration 4",
                                    "startDate": "2026-11-04",
                                    "duration": 14,
                                }
                            ]
                        },
                    },
                ]
            }
        }
    }
    fields = parse_fields(data)
    sheet = project_item_sheet(fields)
    assert sheet.sheet.field("f_F3").choices == ("Iteration 4, from 2026-11-04 for 14 days",)
    ident = {"project_id": "P", "item_id": "I"}
    (request,) = plan(sheet, ident, [FieldChange("f_F1", "Status", "Todo", "In progress")])
    assert request.body == {
        "project": "P",
        "item": "I",
        "field": "F1",
        "value": {"singleSelectOptionId": "o2"},
    }
    (clear,) = plan(sheet, ident, [FieldChange("f_F2", "Due", "2026-11-20", "")])
    assert "clearProjectV2ItemFieldValue" in clear.graphql


def test_rows_of_every_kind_name_their_object() -> None:
    from quill.core.github.explore_models import ExploreRow
    from quill.core.github.items_provider import GitHubBranch, GitHubRelease

    assert target_for(GitHubBranch("main", "abc"), "o/r") == Target(
        "branch", {"repo": "o/r", "branch": "main"}
    )
    assert target_for(GitHubRelease("v1", "One"), "o/r") == Target(
        "release", {"repo": "o/r", "tag": "v1"}
    )
    alert = ExploreRow("x", "", "", "o/r", "security", "dependabot:7")
    found = target_for(alert)
    assert found is not None and found.ident["alert_path"] == "dependabot/alerts"
    person = ExploreRow("kelly", "", "", "", "person", "kelly")
    assert target_for(person) == Target("person", {"login": "kelly"})

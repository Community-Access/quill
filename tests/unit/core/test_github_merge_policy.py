"""Merge-policy reads keep branch scope and partial results explicit."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.merge_policy import fetch_merge_policy


class _GithubError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class _Requester:
    def __init__(self, listed: list[dict], details: dict[int, dict]) -> None:
        self.listed = listed
        self.details = details
        self.calls: list[tuple[str, str, dict | None]] = []
        self.fail_status: int | None = None

    def requestJsonAndCheck(self, method: str, url: str, *, parameters: dict | None = None):
        self.calls.append((method, url, parameters))
        if self.fail_status:
            raise _GithubError(self.fail_status, "policy permission missing")
        if url.endswith("/rulesets"):
            return {}, self.listed
        ruleset_id = int(url.rsplit("/", 1)[-1])
        return {}, self.details[ruleset_id]


class _Repo:
    url = "https://api.github.com/repos/owner/repo"
    default_branch = "main"

    def __init__(self) -> None:
        self.requester = _Requester(
            [
                {
                    "id": 10,
                    "name": "Main branch requirements",
                    "target": "branch",
                    "conditions": {
                        "ref_name": {
                            "include": ["refs/heads/main"],
                            "exclude": ["refs/heads/main-old"],
                        }
                    },
                },
                {
                    "id": 11,
                    "name": "Development only",
                    "target": "branch",
                    "conditions": {"ref_name": {"include": ["refs/heads/dev*"]}},
                },
            ],
            {
                10: {
                    "id": 10,
                    "name": "Main branch requirements",
                    "target": "branch",
                    "conditions": {
                        "ref_name": {
                            "include": ["refs/heads/main"],
                            "exclude": ["refs/heads/main-old"],
                        }
                    },
                    "enforcement": "active",
                    "rules": [
                        {
                            "type": "required_status_checks",
                            "parameters": {"required_status_checks": [{"context": "api-tests"}]},
                        },
                        {
                            "type": "pull_request",
                            "parameters": {
                                "required_approving_review_count": 3,
                                "require_code_owner_review": True,
                            },
                        },
                        {"type": "merge_queue", "parameters": {}},
                    ],
                },
                11: {
                    "id": 11,
                    "name": "Development only",
                    "target": "branch",
                    "conditions": {"ref_name": {"include": ["refs/heads/dev*"]}},
                    "enforcement": "active",
                    "rules": [{"type": "required_status_checks", "parameters": {}}],
                },
            },
        )
        self._protection = SimpleNamespace(
            required_pull_request_reviews=SimpleNamespace(
                required_approving_review_count=2,
                require_code_owner_reviews=True,
            ),
            required_status_checks=SimpleNamespace(
                contexts=["build"],
                checks=[SimpleNamespace(context="lint")],
                strict=True,
            ),
            required_conversation_resolution=SimpleNamespace(enabled=True),
        )
        self.codeowners_found = True

    def get_branch(self, _branch: str):
        return SimpleNamespace(get_protection=lambda: self._protection)

    def get_contents(self, path: str, *, ref: str):
        assert ref == "main"
        if path == ".github/CODEOWNERS" and self.codeowners_found:
            return SimpleNamespace(type="file", size=80, name="CODEOWNERS")
        raise _GithubError(404, "not found")

    @property
    def _requester(self):
        return self.requester


class _Provider:
    def __init__(self, repo: _Repo) -> None:
        self.repo = repo

    def _repo(self, _full_name: str):
        return self.repo


def test_merge_policy_combines_legacy_protection_and_matching_rulesets() -> None:
    repo = _Repo()

    policy = fetch_merge_policy(_Provider(repo), "owner/repo", "main")

    assert policy.complete
    assert policy.branch_protection_enabled
    assert policy.active_required_approvals == 3
    assert policy.active_required_checks == ("build", "lint", "api-tests")
    assert policy.active_codeowners_required
    assert policy.active_merge_queue_required
    assert policy.codeowners_path == ".github/CODEOWNERS"
    assert [ruleset.name for ruleset in policy.active_rulesets] == ["Main branch requirements"]
    assert repo.requester.calls[0][2] == {
        "includes_parents": "true",
        "targets": "branch",
        "per_page": 100,
        "page": 1,
    }
    assert "merge queue" in policy.summary_text().casefold()


def test_merge_policy_does_not_apply_another_branch_ruleset() -> None:
    repo = _Repo()

    policy = fetch_merge_policy(_Provider(repo), "owner/repo", "release/1.0")

    assert policy.rulesets == ()


def test_merge_policy_reports_ruleset_permission_errors_as_incomplete() -> None:
    repo = _Repo()
    repo.requester.fail_status = 403

    policy = fetch_merge_policy(_Provider(repo), "owner/repo", "main")

    assert not policy.complete
    assert any("rulesets could not be read" in warning for warning in policy.warnings)


def test_missing_legacy_protection_is_distinct_from_a_failed_read() -> None:
    repo = _Repo()
    repo._protection = None
    repo.get_branch = lambda _branch: SimpleNamespace(
        get_protection=lambda: (_ for _ in ()).throw(_GithubError(404, "no protection"))
    )
    repo.requester.listed = []
    repo.codeowners_found = False

    policy = fetch_merge_policy(_Provider(repo), "owner/repo", "main")

    assert policy.complete
    assert policy.branch_protection_available
    assert policy.branch_protection_enabled is False
    assert "no legacy branch protection reported" in policy.summary_text()

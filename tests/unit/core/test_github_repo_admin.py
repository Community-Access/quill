"""Unit tests for the wx-free GitHub repo-admin provider.

PyGithub is mocked with lightweight stubs, mirroring the pattern in
test_github_items_provider.py, so create/rename/visibility/default-branch/
protection/fork/multi-file-commit are all testable without wx or network.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import repo_admin
from quill.core.github.repo_admin import GitHubRepoAdminError, GitHubRepoAdminProvider


class _FakeGithubException(Exception):
    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.data = {"message": message}


class _FakeGitRef:
    def __init__(self, sha: str) -> None:
        self.object = SimpleNamespace(sha=sha)
        self.edited_to: str | None = None
        self.deleted = False

    def edit(self, sha: str) -> None:
        self.edited_to = sha

    def delete(self) -> None:
        self.deleted = True


class _FakeBranch:
    def __init__(self) -> None:
        self.protection_calls: list[dict[str, Any]] = []
        self.protection_removed = False

    def edit_protection(self, **kwargs: Any) -> None:
        self.protection_calls.append(kwargs)

    def remove_protection(self) -> None:
        self.protection_removed = True


class _FakeGitTree:
    def __init__(self, sha: str = "tree-sha") -> None:
        self.sha = sha


class _FakeGitCommit:
    def __init__(self, sha: str = "commit-sha", tree: _FakeGitTree | None = None) -> None:
        self.sha = sha
        self.tree = tree or _FakeGitTree()


class _FakeRepo:
    def __init__(
        self,
        *,
        full_name: str = "owner/repo",
        html_url: str = "https://github.com/owner/repo",
        private: bool = False,
        default_branch: str = "main",
        raise_on_edit: Exception | None = None,
    ) -> None:
        self.full_name = full_name
        self.html_url = html_url
        self.private = private
        self.default_branch = default_branch
        self.description = ""
        self.owner = SimpleNamespace(login=full_name.split("/")[0])
        self.edits: list[dict[str, Any]] = []
        self._raise_on_edit = raise_on_edit
        self._branch = _FakeBranch()
        self._git_ref = _FakeGitRef("base-sha")
        self.forked: _FakeRepo | None = None
        self.tree_elements: list[Any] | None = None
        self.commit_message: str | None = None

    def edit(self, **kwargs: Any) -> None:
        if self._raise_on_edit:
            raise self._raise_on_edit
        self.edits.append(kwargs)
        for key in ("name", "private", "default_branch"):
            if key in kwargs:
                if key == "name":
                    self.full_name = f"{self.owner.login}/{kwargs['name']}"
                elif key == "private":
                    self.private = kwargs["private"]
                elif key == "default_branch":
                    self.default_branch = kwargs["default_branch"]

    def create_fork(self, organization: Any = None) -> _FakeRepo:
        owner = organization.login if organization is not None else "me"
        self.forked = _FakeRepo(full_name=f"{owner}/{self.full_name.split('/')[1]}")
        return self.forked

    def get_branch(self, _name: str) -> _FakeBranch:
        return self._branch

    def get_git_ref(self, _ref: str) -> _FakeGitRef:
        return self._git_ref

    def get_git_commit(self, sha: str) -> _FakeGitCommit:
        return _FakeGitCommit(sha=sha)

    def create_git_tree(self, elements: Any, _base_tree: Any) -> _FakeGitTree:
        self.tree_elements = elements
        return _FakeGitTree()

    def create_git_commit(self, message: str, _tree: Any, _parents: Any) -> _FakeGitCommit:
        self.commit_message = message
        return _FakeGitCommit(sha="new-commit-sha")

    def generate_release_notes(self, tag_name: str, **_kwargs: Any) -> Any:
        return SimpleNamespace(body=f"Generated notes for {tag_name}")

    def create_git_release(self, tag: str, name: Any, body: Any, **kwargs: Any) -> Any:
        self.release_calls = getattr(self, "release_calls", [])
        self.release_calls.append({"tag": tag, "name": name, "body": body, **kwargs})
        return SimpleNamespace(
            tag_name=tag,
            title=name if isinstance(name, str) else "",
            html_url=f"https://github.com/{self.full_name}/releases/tag/{tag}",
            draft=kwargs.get("draft", False),
            prerelease=kwargs.get("prerelease", False),
        )


class _FakeUser:
    def __init__(self, repo: _FakeRepo) -> None:
        self._repo = repo
        self.created: dict[str, Any] | None = None
        self.orgs: list[Any] = []

    def create_repo(self, name: str, **kwargs: Any) -> _FakeRepo:
        self.created = {"name": name, **kwargs}
        self._repo.full_name = f"me/{name}"
        self._repo.private = bool(kwargs.get("private", False))
        self._repo.description = str(kwargs.get("description", ""))
        return self._repo

    def get_orgs(self) -> list[Any]:
        return self.orgs


class _FakeOrg:
    def __init__(self, login: str, repo: _FakeRepo) -> None:
        self.login = login
        self._repo = repo
        self.created: dict[str, Any] | None = None
        self.repos: list[_FakeRepo] = []

    def create_repo(self, name: str, **kwargs: Any) -> _FakeRepo:
        self.created = {"name": name, **kwargs}
        self._repo.full_name = f"{self.login}/{name}"
        self._repo.private = bool(kwargs.get("private", False))
        self._repo.description = str(kwargs.get("description", ""))
        return self._repo

    def get_repos(self) -> list[_FakeRepo]:
        return self.repos or [self._repo]


class _FakeGithubClient:
    def __init__(self, repo: _FakeRepo) -> None:
        self._repo = repo
        self.user = _FakeUser(repo)
        self._orgs: dict[str, _FakeOrg] = {}

    def get_repo(self, full_name: str) -> _FakeRepo:
        return self._repo

    def get_user(self) -> _FakeUser:
        return self.user

    def get_organization(self, login: str) -> _FakeOrg:
        if login not in self._orgs:
            self._orgs[login] = _FakeOrg(login, self._repo)
        return self._orgs[login]

    def close(self) -> None:
        pass


def _install_fake_github(monkeypatch: pytest.MonkeyPatch, repo: _FakeRepo) -> None:
    fake_module = SimpleNamespace(
        Github=lambda auth=None: _FakeGithubClient(repo),
        Auth=SimpleNamespace(Token=lambda token: ("token", token)),
        GithubException=_FakeGithubException,
        GithubObject=SimpleNamespace(NotSet=None),
    )
    monkeypatch.setitem(sys.modules, "github", fake_module)
    monkeypatch.setattr(repo_admin, "_get_gh_module", lambda: fake_module)


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


@pytest.fixture
def provider(repo: _FakeRepo, monkeypatch: pytest.MonkeyPatch) -> GitHubRepoAdminProvider:
    _install_fake_github(monkeypatch, repo)
    return GitHubRepoAdminProvider(token="tok")


# ---------------------------------------------------------------------------


def test_requires_a_token() -> None:
    with pytest.raises(GitHubRepoAdminError, match="signed-in"):
        GitHubRepoAdminProvider(token="")


def test_create_repository_for_the_authenticated_user(
    provider: GitHubRepoAdminProvider, repo: _FakeRepo
) -> None:
    result = provider.create_repository("new-repo", private=True, description="hi")
    assert result.full_name == "me/new-repo"
    assert result.is_private is True
    assert result.description == "hi"


def test_create_repository_under_an_org(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    result = provider.create_repository("new-repo", org="acme")
    assert result.full_name == "acme/new-repo"


def test_fork_repository(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    result = provider.fork_repository("owner/repo")
    assert result.full_name == "me/repo"
    assert repo.forked is not None


def test_fork_repository_into_an_org(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    result = provider.fork_repository("owner/repo", org="acme")
    assert result.full_name == "acme/repo"


def test_rename_repository(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    result = provider.rename_repository("owner/repo", "renamed")
    assert result.full_name == "owner/renamed"
    assert repo.edits == [{"name": "renamed"}]


def test_set_visibility(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    result = provider.set_visibility("owner/repo", private=True)
    assert result.is_private is True


def test_set_default_branch(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    result = provider.set_default_branch("owner/repo", "develop")
    assert result.default_branch == "develop"


def test_set_branch_protection(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    provider.set_branch_protection(
        "owner/repo",
        "main",
        required_approving_review_count=2,
        required_status_checks=("ci",),
        enforce_admins=True,
    )
    assert repo._branch.protection_calls == [
        {
            "strict": True,
            "contexts": ["ci"],
            "enforce_admins": True,
            "required_approving_review_count": 2,
        }
    ]


def test_remove_branch_protection(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    provider.remove_branch_protection("owner/repo", "main")
    assert repo._branch.protection_removed is True


def test_delete_branch(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    provider.delete_branch("owner/repo", "stale-branch")
    assert repo._git_ref.deleted is True


def test_commit_files_builds_a_tree_and_moves_the_ref(
    provider: GitHubRepoAdminProvider, repo: _FakeRepo
) -> None:
    sha = provider.commit_files(
        "owner/repo",
        "main",
        [("a.txt", b"hello"), ("b.txt", b"world")],
        "two files",
    )
    assert sha == "new-commit-sha"
    assert repo.commit_message == "two files"
    assert repo._git_ref.edited_to == "new-commit-sha"
    assert repo.tree_elements is not None
    assert len(repo.tree_elements) == 2
    assert repo.tree_elements[0]["path"] == "a.txt"
    assert repo.tree_elements[0]["content"] == "hello"


def test_commit_files_rejects_empty_file_list(provider: GitHubRepoAdminProvider) -> None:
    with pytest.raises(GitHubRepoAdminError, match="no files"):
        provider.commit_files("owner/repo", "main", [], "empty")


def test_commit_files_rejects_binary_content(provider: GitHubRepoAdminProvider) -> None:
    with pytest.raises(GitHubRepoAdminError, match="UTF-8"):
        provider.commit_files("owner/repo", "main", [("a.bin", b"\xff\xfe")], "binary")


def test_translates_404_to_not_found(
    provider: GitHubRepoAdminProvider, repo: _FakeRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_404(_full_name: str) -> _FakeRepo:
        raise _FakeGithubException(404, "Not Found")

    monkeypatch.setattr(provider._gh, "get_repo", raise_404)
    with pytest.raises(GitHubRepoAdminError, match="not found"):
        provider.rename_repository("owner/repo", "x")


def test_translates_403_to_scope_hint(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    repo._raise_on_edit = _FakeGithubException(403, "Forbidden")
    with pytest.raises(GitHubRepoAdminError, match="delete_repo"):
        provider.rename_repository("owner/repo", "x")


def test_translates_422_to_name_taken_hint(
    provider: GitHubRepoAdminProvider, repo: _FakeRepo
) -> None:
    repo._raise_on_edit = _FakeGithubException(422, "name already exists")
    with pytest.raises(GitHubRepoAdminError, match="already be taken"):
        provider.rename_repository("owner/repo", "x")


def test_close_is_best_effort(provider: GitHubRepoAdminProvider) -> None:
    provider.close()  # must not raise


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


def test_list_organizations(provider: GitHubRepoAdminProvider) -> None:
    provider._gh.user.orgs = [SimpleNamespace(login="acme"), SimpleNamespace(login="widgets")]
    assert provider.list_organizations() == ["acme", "widgets"]


def test_list_org_repositories(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    other = _FakeRepo(full_name="acme/other")
    org = provider._gh.get_organization("acme")
    org.repos = [repo, other]
    names = [r.full_name for r in provider.list_org_repositories("acme")]
    assert names == ["owner/repo", "acme/other"]


def test_list_org_repositories_respects_limit(
    provider: GitHubRepoAdminProvider, repo: _FakeRepo
) -> None:
    org = provider._gh.get_organization("acme")
    org.repos = [repo, _FakeRepo(full_name="acme/b"), _FakeRepo(full_name="acme/c")]
    names = [r.full_name for r in provider.list_org_repositories("acme", limit=2)]
    assert len(names) == 2


# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------


def test_generate_release_notes(provider: GitHubRepoAdminProvider) -> None:
    body = provider.generate_release_notes("owner/repo", "v1.0.0")
    assert body == "Generated notes for v1.0.0"


def test_create_release(provider: GitHubRepoAdminProvider, repo: _FakeRepo) -> None:
    info = provider.create_release(
        "owner/repo", "v1.0.0", name="Version 1.0.0", body="notes", draft=True
    )
    assert info.tag == "v1.0.0"
    assert info.name == "Version 1.0.0"
    assert info.draft is True
    assert repo.release_calls[0]["tag"] == "v1.0.0"

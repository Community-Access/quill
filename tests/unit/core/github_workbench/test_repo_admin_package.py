"""Repository administration: merge defaults, Sponsor links, Pages, New Repository,
Transfer with a new name and teams, and Repository > Packages (complete.md 1.3).

Fakes only: every request is recorded, none reaches GitHub.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import packages as pk
from quill.core.github import repo_create as rc
from quill.core.github import repo_transfer as rt
from quill.core.github.across_scope_matrix import classify
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheet_engine import SheetSaveError, plan
from quill.core.github.sheets_repo_more import merge_defaults, pages_source
from quill.core.workbench.properties import FieldChange
from quill.core.workbench.tree import Need

REPO = SHEETS["repository"]
IDENT = {"repo": "jeff/site"}


def _change(key: str, before: object, after: object) -> FieldChange:
    spec = next(f for p in REPO.sheet.pages for f in p.fields if f.key == key)
    return FieldChange(key, spec.label, before, after)  # type: ignore[arg-type]


# -- the Merging page: title and message saved as GitHub's pair ---------------------


def test_merge_defaults_read_as_the_words_of_githubs_settings_page() -> None:
    found = merge_defaults({
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
        "merge_commit_title": "MERGE_MESSAGE",
        "merge_commit_message": "PR_TITLE",
    })
    assert found == {
        "squash_default": "pull request title and description",
        "merge_default": "default message",
    }
    odd = merge_defaults({"merge_commit_title": "PR_TITLE", "merge_commit_message": "PR_TITLE"})
    assert odd["merge_default"] == "title PR_TITLE, message PR_TITLE"


def test_changing_one_default_sends_its_title_and_message_together_with_other_flags() -> None:
    requests = plan(
        REPO,
        IDENT,
        [
            _change("squash_default", "default message", "pull request title"),
            _change("allow_auto_merge", False, True),
        ],
    )
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.path) == ("PATCH", "/repos/jeff/site")
    assert request.body == {
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "BLANK",
        "allow_auto_merge": True,
    }


def test_a_default_github_does_not_name_is_refused_in_words() -> None:
    with pytest.raises(SheetSaveError, match="not one of GitHub's choices"):
        plan(REPO, IDENT, [_change("merge_default", "default message", "anything")])


# -- Features: the Sponsor links read, and say why they only read ---------------------


def test_sponsor_links_read_only_with_the_reason() -> None:
    field = next(f for p in REPO.sheet.pages for f in p.fields if f.key == "sponsor_links")
    assert field.readonly and "cannot change" in field.help
    assert "sponsor_links" not in REPO.writes
    read = next(r for r in REPO.reads if "fundingLinks" in r.graphql)
    assert read.optional and read.extract is not None
    links = {"repository": {"fundingLinks": [{"platform": "GITHUB", "url": "https://x/y"}]}}
    assert read.extract(links) == {"sponsor_links": "github: https://x/y"}
    assert read.extract({"repository": {"fundingLinks": []}})["sponsor_links"].startswith("none")


# -- Pages: build type, branch and folder, latest build -------------------------------


def test_pages_branch_and_folder_parse_or_refuse() -> None:
    assert pages_source("main") == {"branch": "main", "path": "/"}
    assert pages_source("gh-pages docs") == {"branch": "gh-pages", "path": "/docs"}
    for bad in ("", "main /src", "a b c"):
        with pytest.raises(SheetSaveError):
            pages_source(bad)


def test_pages_settings_are_one_put_with_source_and_build_type() -> None:
    requests = plan(
        REPO,
        IDENT,
        [
            _change("pages_source", "main /", "main /docs"),
            _change("pages_build_type", "by a workflow", "from a branch"),
            _change("pages_https", False, True),
        ],
    )
    assert [(r.method, r.path) for r in requests] == [("PUT", "/repos/jeff/site/pages")]
    assert requests[0].body == {
        "source": {"branch": "main", "path": "/docs"},
        "build_type": "legacy",
        "https_enforced": True,
    }


def test_pages_page_reads_status_build_type_and_the_latest_build() -> None:
    pages = next(r for r in REPO.reads if r.path == "/repos/{repo}/pages")
    latest = next(r for r in REPO.reads if r.path.endswith("/pages/builds/latest"))
    assert pages.extract is not None and latest.extract is not None
    site = pages.extract({
        "html_url": "https://jeff.github.io/site",
        "status": "built",
        "build_type": "workflow",
        "source": {"branch": "main", "path": "/"},
    })
    assert site["pages_build_type"] == "by a workflow"
    assert site["pages_status"] == "built" and site["pages_source"] == "main /"
    said = latest.extract({"status": "errored", "error": {"message": "Page build failed."}})
    assert said == {"pages_latest": "errored: Page build failed."}
    keys = [f.key for f in next(p for p in REPO.sheet.pages if p.key == "pages").fields]
    assert keys[:5] == [
        "pages_url",
        "pages_status",
        "pages_latest",
        "pages_build_type",
        "pages_source",
    ]


# -- New Repository: every option, checked first --------------------------------------


@pytest.mark.parametrize(
    ("new", "words"),
    [
        (rc.NewRepository(""), "Type a name"),
        (rc.NewRepository("a b"), "is not a repository name"),
        (rc.NewRepository("r", visibility="internal"), "Choose private or public"),
        (rc.NewRepository("r", template="nope"), "type it as owner/name"),
        (rc.NewRepository("r", template="o/t", auto_init=True), "brings its own files"),
        (rc.NewRepository("r", template="o/t", license="mit"), "brings its own files"),
        (rc.NewRepository("r", include_all_branches=True), "is for a repository made from"),
        (rc.NewRepository("r", license="wtfpl"), "not one of GitHub's licence keys"),
    ],
)
def test_problems_are_said_before_anything_is_sent(new: rc.NewRepository, words: str) -> None:
    assert words in rc.problem(new)


def test_a_full_new_repository_sends_only_what_was_chosen() -> None:
    new = rc.NewRepository(
        "site",
        owner="acme",
        description=" Docs ",
        homepage="https://acme.example",
        gitignore="Python",
        license="MIT",
    )
    assert rc.problem(new) == ""
    assert rc.create_kwargs(new) == {
        "private": True,
        "description": "Docs",
        "homepage": "https://acme.example",
        "gitignore_template": "Python",
        "license_template": "mit",
        "auto_init": True,
    }
    assert rc.create_kwargs(rc.NewRepository("r", visibility="public")) == {"private": False}


def test_a_template_copy_takes_owner_privacy_and_all_branches() -> None:
    new = rc.NewRepository("r", owner="acme", template="o/t", include_all_branches=True)
    assert rc.problem(new) == ""
    assert rc.template_kwargs(new) == {
        "owner": "acme",
        "description": "",
        "private": True,
        "include_all_branches": True,
    }


# -- Transfer: a new name, and teams by name for an organization ----------------------


class TransferApi:
    def __init__(self, teams: dict[str, int] | None = None) -> None:
        self.teams = teams or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        if "/teams/" in path:
            slug = path.rsplit("/", 1)[1]
            if slug not in self.teams:
                raise GitHubRestError("no", status=404)
            return RestResponse(200, {}, {"id": self.teams[slug]})
        return RestResponse(202, {}, {"full_name": "acme/site"})

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_transfer_renames_and_resolves_team_names_to_ids() -> None:
    api = TransferApi({"docs-writers": 7, "core": 9})
    said = rt.transfer_repository(
        api, "jeff/r", "acme", new_name="site", teams=["Docs Writers", " core ", ""]
    )
    assert said == "Transferred jeff/r; it is now acme/site. The old address redirects."
    assert api.sent[-1] == (
        "POST",
        "/repos/jeff/r/transfer",
        {"new_owner": "acme", "new_name": "site", "team_ids": [7, 9]},
    )


def test_transfer_keeps_the_name_unsent_and_refuses_unknown_teams_before_moving() -> None:
    api = TransferApi()
    rt.transfer_repository(api, "jeff/r", "acme", new_name="r")
    assert api.sent == [("POST", "/repos/jeff/r/transfer", {"new_owner": "acme"})]
    api = TransferApi()
    with pytest.raises(rt.TransferError, match="no team called ghost"):
        rt.transfer_repository(api, "jeff/r", "sam", teams=["ghost"])
    assert not any(method == "POST" for method, _p, _b in api.sent)
    with pytest.raises(rt.TransferError, match="not a repository name"):
        rt.transfer_repository(TransferApi(), "jeff/r", "acme", new_name="a b")


# -- Repository > Packages ------------------------------------------------------------

_PACKAGE = {
    "name": "engine",
    "package_type": "container",
    "repository": {"full_name": "acme/site"},
}
_OTHER = {"name": "other", "package_type": "npm", "repository": {"full_name": "acme/else"}}


class PackagesApi:
    def __init__(self, owner_type: str, me: str = "jeff") -> None:
        self.owner_type, self.me = owner_type, me
        self.sent: list[str] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append(path)
        if path.startswith("/users/") and not path.endswith("/packages"):
            return RestResponse(200, {}, {"type": self.owner_type})
        if path == "/user":
            return RestResponse(200, {}, {"login": self.me})
        if query and query.get("package_type") == "container":
            return RestResponse(200, {}, [_PACKAGE, _OTHER])
        return RestResponse(200, {}, [])

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


@pytest.mark.parametrize(
    ("owner_type", "repo", "listed", "key"),
    [
        ("Organization", "acme/site", "/orgs/acme/packages", "@acme/container/engine"),
        ("User", "jeff/site", "/user/packages", "container/engine"),
        ("User", "sam/site", "/users/sam/packages", "~sam/container/engine"),
    ],
)
def test_a_repositorys_packages_are_its_owners_published_from_it(
    owner_type: str, repo: str, listed: str, key: str
) -> None:
    rows_of = {**_PACKAGE, "repository": {"full_name": repo}}
    api = PackagesApi(owner_type)
    original = api.rest

    def rest(method: str, path: str, **kw: Any) -> Any:
        found = original(method, path, **kw)
        if isinstance(found.data, list) and found.data:
            return RestResponse(200, {}, [rows_of, _OTHER])
        return found

    api.rest = rest  # type: ignore[method-assign]
    rows = pk.fetch_repository_packages(api, repo)
    assert listed in api.sent
    assert [row.key for row in rows] == [key]
    assert all(row.repo == repo for row in rows)


def test_repository_packages_node_and_the_across_cell_say_where_it_lives() -> None:
    from quill.core.github.workbench_tree import GITHUB_TREE

    node = GITHUB_TREE.template_node("repository", "repo_packages")
    assert node.loader == "explore:repo_packages" and node.row_type == "package"
    assert Need.SIGN_IN in node.needs
    cell = classify("by_name", "packages_pages", "repository_set", "list")
    assert cell.supported and "Pages is one site per repository" in cell.reason
    write = classify("by_name", "packages_pages", "repository_set", "make_same")
    assert not write.supported and "change a package's visibility" in write.reason

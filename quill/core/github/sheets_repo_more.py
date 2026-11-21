"""The repository sheet's merge message defaults, Sponsor links and Pages page.

Kept apart so :mod:`quill.core.github.sheets_repo` stays under its size
budget. Three things live here:

- **Merge message defaults.** GitHub's ``PATCH /repos/{o}/{r}`` takes a
  squash or merge commit's title and message as a pair (the title is required
  with the message, and only some pairs are allowed), so each is one choice,
  in the words of GitHub's own settings page, saved as the pair.
- **Sponsor links.** The Sponsor button's links come from
  ``.github/FUNDING.yml`` (GraphQL ``fundingLinks``); whether the button shows
  is a setting GitHub's API cannot change, so the field only reads.
- **Pages.** The site's address, status and latest build, and the four
  settings ``PUT /repos/{o}/{r}/pages`` changes: how it is built, the branch
  and folder it is built from, the custom domain and HTTPS.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetSaveError, Write
from quill.core.github.sheet_fields import dig, ed, page, patch, ro, when
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, Value

__all__ = [
    "BUILD_TYPES",
    "MERGE_DEFAULTS",
    "MERGE_DEFAULT_FIELDS",
    "MORE_READS",
    "MORE_WRITES",
    "PAGES_PAGE",
    "SPONSOR_FIELD",
    "SPONSOR_WHY",
    "SQUASH_DEFAULTS",
    "merge_defaults",
    "pages_source",
]

_K = FieldKind
_REPO = "/repos/{repo}"
_ADMIN = "repo:admin"
_A = WriteTier.ACCESS

#: A squash merge's default commit, as GitHub's settings page words it: (title, message).
SQUASH_DEFAULTS: dict[str, tuple[str, str]] = {
    "default message": ("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"),
    "pull request title": ("PR_TITLE", "BLANK"),
    "pull request title and commit details": ("PR_TITLE", "COMMIT_MESSAGES"),
    "pull request title and description": ("PR_TITLE", "PR_BODY"),
}
#: A merge commit's default, the same way.
MERGE_DEFAULTS: dict[str, tuple[str, str]] = {
    "default message": ("MERGE_MESSAGE", "PR_TITLE"),
    "pull request title": ("PR_TITLE", "BLANK"),
    "pull request title and description": ("PR_TITLE", "PR_BODY"),
}

#: How GitHub builds the site, in words, and the API's word for it.
BUILD_TYPES: dict[str, str] = {"from a branch": "legacy", "by a workflow": "workflow"}

SPONSOR_WHY = (
    "The links come from the repository's .github/FUNDING.yml file. Whether the Sponsor "
    "button shows is a setting GitHub's API cannot change, so turn it on or off on "
    "GitHub's settings page: Open on GitHub, Shift+Enter, goes there."
)

_FUNDING_QUERY = (
    "query($owner:String!,$name:String!){repository(owner:$owner,name:$name)"
    "{fundingLinks{platform url}}}"
)


def _variables(ident: Ident) -> dict[str, object]:
    owner, _, name = ident["repo"].partition("/")
    return {"owner": owner, "name": name}


def _word_for(pairs: Mapping[str, tuple[str, str]], title: str, message: str) -> str:
    for word, pair in pairs.items():
        if pair == (title, message):
            return word
    if not title and not message:
        return ""
    # A pair GitHub allows but its settings page does not name: say it as it is.
    return f"title {title or 'unset'}, message {message or 'unset'}"


def merge_defaults(data: Mapping[str, Any]) -> dict[str, Value]:
    """The two defaults, in words, from a repository's REST answer."""
    return {
        "squash_default": _word_for(
            SQUASH_DEFAULTS,
            str(data.get("squash_merge_commit_title") or ""),
            str(data.get("squash_merge_commit_message") or ""),
        ),
        "merge_default": _word_for(
            MERGE_DEFAULTS,
            str(data.get("merge_commit_title") or ""),
            str(data.get("merge_commit_message") or ""),
        ),
    }


def _pair_encode(pairs: Mapping[str, tuple[str, str]], prefix: str) -> Any:
    def encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
        found = pairs.get(str(value or ""))
        if found is None:
            raise SheetSaveError(
                f"{value} is not one of GitHub's choices: " + ", ".join(pairs) + "."
            )
        return {f"{prefix}_title": found[0], f"{prefix}_message": found[1]}

    return encode


MERGE_DEFAULT_FIELDS: tuple[FieldSpec, ...] = (
    ed(
        "squash_default",
        "Squash merge commit message",
        _K.CHOICE,
        "What a squash merge's commit says unless the person merging changes it.",
        choices=tuple(SQUASH_DEFAULTS),
    ),
    ed(
        "merge_default",
        "Merge commit message",
        _K.CHOICE,
        "What a merge commit says unless the person merging changes it.",
        choices=tuple(MERGE_DEFAULTS),
    ),
)


def _funding(data: Mapping[str, Any]) -> dict[str, Value]:
    links = dig(data, "repository", "fundingLinks")
    said = [
        f"{str(link.get('platform') or '').replace('_', ' ').lower()}: {link.get('url') or ''}"
        for link in links or ()
        if isinstance(link, Mapping)
    ]
    return {"sponsor_links": "; ".join(said) if said else "none: the repository has no FUNDING.yml"}


SPONSOR_FIELD = ro("sponsor_links", "Sponsor button links", help=SPONSOR_WHY)


def pages_source(text: str) -> dict[str, str]:
    """``"main /docs"`` as GitHub's ``source``: a branch, and the folder ``/`` or ``/docs``."""
    words = text.split()
    if not words:
        raise SheetSaveError(
            "Type the branch to build from, then the folder: main / or main /docs."
        )
    folder = words[1] if len(words) > 1 else "/"
    if folder == "docs":
        folder = "/docs"
    if len(words) > 2 or folder not in ("/", "/docs"):
        raise SheetSaveError(
            f"{text} is not a branch and a folder: GitHub builds from / or /docs, as main /docs."
        )
    return {"branch": words[0], "path": folder}


def _source_encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    return {"source": pages_source(str(value or ""))}


def _build_encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    word = BUILD_TYPES.get(str(value or ""))
    if word is None:
        raise SheetSaveError("Choose from a branch, or by a workflow.")
    return {"build_type": word}


def _pages(data: Mapping[str, Any]) -> dict[str, Value]:
    build = str(data.get("build_type") or "")
    return {
        "pages_url": str(data.get("html_url") or ""),
        "pages_status": str(data.get("status") or "not built yet"),
        "pages_build_type": next((w for w, api in BUILD_TYPES.items() if api == build), build),
        "pages_source": " ".join(
            str(dig(data, "source", part) or "") for part in ("branch", "path")
        ).strip(),
        "pages_cname": str(data.get("cname") or ""),
        "pages_https": bool(data.get("https_enforced")),
    }


def _latest(data: Mapping[str, Any]) -> dict[str, Value]:
    status = str(data.get("status") or "unknown")
    message = str(dig(data, "error", "message") or "")
    stamp = when(data.get("created_at"))
    said = status + (f", {stamp}" if stamp else "") + (f": {message}" if message else "")
    return {"pages_latest": said}


PAGES_PAGE: PageSpec = page(
    "pages",
    "Pages",
    ro("pages_url", "Site address", _K.LINK),
    ro("pages_status", "Status", help="Built, building or errored, as GitHub last reported it."),
    ro(
        "pages_latest",
        "Latest build",
        help="Its status, when it started, and GitHub's message when it failed. "
        "Rebuild, on the GitHub Pages node, asks for a new one.",
    ),
    ed(
        "pages_build_type",
        "Build",
        _K.CHOICE,
        "From a branch, or by a GitHub Actions workflow that deploys the site.",
        choices=tuple(BUILD_TYPES),
    ),
    ed(
        "pages_source",
        "Branch and folder",
        help="The branch, a space, then / or /docs: main / or gh-pages /docs. "
        "A workflow-built site ignores it.",
    ),
    ed("pages_cname", "Custom domain"),
    ed("pages_https", "Enforce HTTPS", _K.CHECK),
)

MORE_READS: tuple[Read, ...] = (
    Read(graphql=_FUNDING_QUERY, variables=_variables, extract=_funding, optional=True),
    Read(_REPO + "/pages", _pages, optional=True),
    Read(_REPO + "/pages/builds/latest", _latest, optional=True),
)

_PAGES_PUT = _REPO + "/pages"

MORE_WRITES: dict[str, Write] = {
    "squash_default": patch(
        _REPO, _ADMIN, _A, encode=_pair_encode(SQUASH_DEFAULTS, "squash_merge_commit")
    ),
    "merge_default": patch(_REPO, _ADMIN, _A, encode=_pair_encode(MERGE_DEFAULTS, "merge_commit")),
    "pages_build_type": patch(_PAGES_PUT, _ADMIN, _A, encode=_build_encode, method="PUT"),
    "pages_source": patch(_PAGES_PUT, _ADMIN, _A, encode=_source_encode, method="PUT"),
    "pages_cname": patch(_PAGES_PUT, _ADMIN, _A, "cname", method="PUT"),
    "pages_https": patch(_PAGES_PUT, _ADMIN, _A, "https_enforced", method="PUT"),
}

"""Repository > Wiki: whether a repository has a wiki, and how to work on its pages (GX12).

GitHub has no API for wiki pages. A wiki is a git repository of its own,
``owner/name.wiki``, so the Workbench's **Wiki** node says whether the wiki is
on and points at the two ways in: **Open on GitHub** reads it, and **Clone
Wiki...** (``Ctrl+Alt+W``) copies its pages to a folder with the same clone
QUILL uses for any repository, where they are Markdown files to edit in the
editor and push back with git. A repository with its wiki turned off says so,
and that the switch is in Properties.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["WikiError", "fetch_wiki", "wiki_address"]


class WikiError(CodedError):
    """The repository could not be read; the message is said."""

    code = "QUILL-GITHUB-WIKI"


def wiki_address(repository: str) -> str:
    """What to give the clone: the wiki's own repository, ``owner/name.wiki``."""
    return f"{repository}.wiki"


def fetch_wiki(api: GitHubApi, repository: str) -> list[ExploreRow]:
    try:
        data = api.rest("GET", f"/repos/{repository}").data
    except GitHubRestError as exc:
        raise WikiError(f"Could not read {repository}: {exc}") from exc
    page = f"https://github.com/{repository}/wiki"
    if not isinstance(data, Mapping) or not data.get("has_wiki"):
        label = (
            f"{repository}'s wiki is turned off. Its administrators turn it on in "
            "Properties, on the Features page."
        )
        return [
            ExploreRow(label, label, f"https://github.com/{repository}", repository, "wiki", "off")
        ]
    rows = [
        ExploreRow(
            f"{repository} has a wiki. Enter opens it on GitHub.",
            f"The wiki is on.\n{page}",
            page,
            repository,
            "wiki",
            "on",
        ),
        ExploreRow(
            "To edit its pages here, Clone Wiki (Ctrl+Alt+W) copies them to a folder as "
            f"Markdown files: the git repository {wiki_address(repository)}.",
            "Each page is one .md file, named after its title. Edit them in the editor, "
            "then commit and push with git; GitHub shows the change at once.\n" + page,
            page,
            repository,
            "wiki",
            "clone",
        ),
    ]
    return rows

"""New Repository's every option, checked before anything is sent (GitHub PRD 14.1).

Create Repository... asks for the owner, the name, a description and a
website, the visibility (private or public; internal repositories belong to
GitHub Enterprise Cloud, which the Workbench leaves to GitHub),
and how the repository starts: empty, with a README, a .gitignore template
and a licence (``POST /user/repos`` or ``POST /orgs/{org}/repos``), or as a
copy of a template repository, optionally with all its branches
(``POST /repos/{template}/generate``). :class:`NewRepository` holds those
answers; :func:`problem` says in one sentence why GitHub would refuse a
combination, so the dialog can say it before anything is sent;
:func:`create_kwargs` and :func:`template_kwargs` are what the two existing
calls take, and :func:`create` sends it through whichever one fits. wx-free
and strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.github.models import RemoteRepository

__all__ = [
    "GITIGNORE_TEMPLATES",
    "LICENSE_TEMPLATES",
    "VISIBILITIES",
    "NewRepository",
    "create",
    "create_kwargs",
    "generate_from_template",
    "problem",
    "template_kwargs",
]

VISIBILITIES = ("private", "public")

#: GitHub's commonest .gitignore templates (``GET /gitignore/templates`` has them all;
#: any name it lists may be typed).
GITIGNORE_TEMPLATES = (
    "Python",
    "Node",
    "Java",
    "C++",
    "C",
    "CSharp",
    "VisualStudio",
    "Go",
    "Rust",
    "Ruby",
    "Swift",
    "Kotlin",
    "Dart",
    "Android",
    "Unity",
    "Jekyll",
    "TeX",
)

#: GitHub's licence keys (``GET /licenses``), with the name a person knows.
LICENSE_TEMPLATES: dict[str, str] = {
    "mit": "MIT License",
    "apache-2.0": "Apache License 2.0",
    "gpl-3.0": "GNU General Public License v3.0",
    "agpl-3.0": "GNU Affero General Public License v3.0",
    "lgpl-3.0": "GNU Lesser General Public License v3.0",
    "bsd-2-clause": "BSD 2-Clause License",
    "bsd-3-clause": "BSD 3-Clause License",
    "mpl-2.0": "Mozilla Public License 2.0",
    "epl-2.0": "Eclipse Public License 2.0",
    "bsl-1.0": "Boost Software License 1.0",
    "cc0-1.0": "Creative Commons Zero v1.0 Universal",
    "unlicense": "The Unlicense",
}

_NAME = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_REPO = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class NewRepository:
    """Everything Create Repository... asks; *owner* "" is your own account."""

    name: str
    owner: str = ""
    description: str = ""
    homepage: str = ""
    visibility: str = "private"
    template: str = ""
    include_all_branches: bool = False
    auto_init: bool = False
    gitignore: str = ""
    license: str = ""

    @property
    def private(self) -> bool:
        return self.visibility != "public"


def problem(new: NewRepository) -> str:
    """Why GitHub would refuse *new*, in one sentence, or "" when it would not."""
    name = new.name.strip()
    if not name:
        return "Type a name for the new repository."
    if not _NAME.match(name) or name in (".", ".."):
        return (
            f"{name} is not a repository name: use letters, digits, hyphens, "
            "underscores and full stops, up to 100."
        )
    if new.visibility not in VISIBILITIES:
        return "Choose private or public."
    if new.template.strip():
        if not _REPO.match(new.template.strip()):
            return f"{new.template.strip()} is not a template repository: type it as owner/name."

        if new.auto_init or new.gitignore.strip() or new.license.strip():
            return (
                "A template brings its own files, so a README, .gitignore or licence "
                "cannot be added as well; clear them or the template."
            )
    elif new.include_all_branches:
        return "Include all branches is for a repository made from a template."
    if new.license.strip() and new.license.strip().lower() not in LICENSE_TEMPLATES:
        return f"{new.license.strip()} is not one of GitHub's licence keys, such as mit."
    return ""


def create_kwargs(new: NewRepository) -> dict[str, object]:
    """What ``create_repo`` takes for *new*: only the options that were chosen."""
    found: dict[str, object] = {"private": new.private}

    for key, value in (
        ("description", new.description.strip()),
        ("homepage", new.homepage.strip()),
        ("gitignore_template", new.gitignore.strip()),
        ("license_template", new.license.strip().lower()),
    ):
        if value:
            found[key] = value
    if new.auto_init or new.gitignore.strip() or new.license.strip():
        # GitHub adds a .gitignore or licence only in a first commit, so ask for one.
        found["auto_init"] = True
    return found


def template_kwargs(new: NewRepository) -> dict[str, object]:
    """What ``create_from_template`` takes for *new*."""
    return {
        "owner": new.owner.strip(),
        "description": new.description.strip(),
        "private": new.private,
        "include_all_branches": new.include_all_branches,
    }


def generate_from_template(token: str, new: NewRepository) -> RemoteRepository:
    """Make *new* from its template, through the one generate route (``repo_actions``)."""
    from quill.core.github.items_errors import GitHubItemsError
    from quill.core.github.repo_actions import GitHubRepoActions
    from quill.core.github.repo_admin import GitHubRepoAdminError

    try:
        full_name, url = GitHubRepoActions(token).create_from_template(
            new.template.strip(),
            new.name.strip(),
            owner=new.owner.strip(),
            description=new.description.strip(),
            private=new.private,
            include_all_branches=new.include_all_branches,
        )
    except GitHubItemsError as exc:
        raise GitHubRepoAdminError(str(exc)) from exc
    return RemoteRepository(
        provider="github", full_name=full_name, is_private=new.private, html_url=url
    )


def create(token: str, new: NewRepository) -> RemoteRepository:
    """Create *new*: from its template, or fresh with every option chosen.

    Raises :class:`~quill.core.github.repo_admin.GitHubRepoAdminError` with
    GitHub's refusal in words.
    """
    if new.template.strip():
        return generate_from_template(token, new)
    from quill.core.github.repo_admin import GitHubRepoAdminProvider

    provider = GitHubRepoAdminProvider(token)
    try:
        return provider.create_repository(new.name, org=new.owner, options=create_kwargs(new))
    finally:
        provider.close()

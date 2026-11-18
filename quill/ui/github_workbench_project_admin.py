"""Looking after a Project from its row in the GitHub Workbench (GitHub PRD section 19).

The work is in :mod:`quill.core.github.project_admin`; this mixin asks and
says. On a project row: Add Draft Issue, New Field, Delete Field, Post Status
Update, Link to Repository, Unlink from Repository, Mark as Template (a
toggle), Copy Project, and Delete Project. Deleting asks for the project's
title typed out, because it cannot be undone.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["PROJECT_ADMIN_REASONS", "PROJECT_ADMIN_VERBS", "GitHubWorkbenchProjectAdminMixin"]

_PROJECT = frozenset({"project"})

PROJECT_ADMIN_VERBS: dict[str, frozenset[str]] = {
    verb: _PROJECT
    for verb in (
        "project_draft",
        "project_field",
        "project_field_delete",
        "project_status",
        "project_link_repo",
        "project_unlink_repo",
        "project_template",
        "project_copy",
        "project_delete",
    )
}

PROJECT_ADMIN_REASONS: dict[str, str] = {
    verb: "This is for a Project's row, while you are signed in with the project scope."
    for verb in PROJECT_ADMIN_VERBS
}


def _title(row: ExploreRow) -> str:
    return (row.title or row.label).rsplit(" (#", 1)[0]


class GitHubWorkbenchProjectAdminMixin:
    frame: Any
    items: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def _project(self, row: object) -> ExploreRow | None:
        if isinstance(row, ExploreRow) and row.kind == "project" and row.key:
            return row
        return None

    def _fits_project(self, row: object) -> bool:
        return self.signed_in and self._project(row) is not None

    _fits_project_draft = _fits_project
    _fits_project_field = _fits_project
    _fits_project_field_delete = _fits_project
    _fits_project_status = _fits_project
    _fits_project_link_repo = _fits_project
    _fits_project_unlink_repo = _fits_project
    _fits_project_template = _fits_project
    _fits_project_copy = _fits_project
    _fits_project_delete = _fits_project

    def _token(self) -> str:
        return str(getattr(self.items, "token", "") or "")

    def _then(self, said: object) -> None:
        self._say(str(said))
        self.frame.reload()

    def _do_project_draft(self, _ref: Any, row: object) -> None:
        from quill.core.github.project_admin import add_draft_issue

        project = self._project(row)
        if project is None:
            return
        title = self._ask_text("Add Draft Issue", "Draft issue title:")
        if not title:
            return
        body = self._ask_text("Add Draft Issue", "Body (optional):", multiline=True)
        name = _title(project)
        self._background(
            "add the draft issue",
            lambda: (
                add_draft_issue(self._token(), project.key, title, body),
                f"Draft issue {title!r} added to {name}.",
            )[1],
            self._then,
        )

    def _do_project_field(self, _ref: Any, row: object) -> None:
        from quill.core.github.project_admin import FIELD_TYPES, create_field

        project = self._project(row)
        if project is None:
            return
        name = self._ask_text("New Field", "Field name:")
        if not name:
            return
        kind = self._choose(
            "New Field", f"What kind of field is {name}?", [w for _c, w in FIELD_TYPES]
        )
        if kind < 0:
            return
        code = FIELD_TYPES[kind][0]
        options: list[str] = []
        if code == "SINGLE_SELECT":
            typed = self._ask_text("New Field", "Choices, separated by commas:")
            options = [o.strip() for o in typed.split(",") if o.strip()]
            if not options:
                self._say("A single select field needs at least one choice.")
                return

        def work() -> str:
            made = create_field(self._token(), project.key, name, code, options)
            return f"Field {made} added to {_title(project)}."

        self._background("add the field", work, self._then)

    def _do_project_field_delete(self, _ref: Any, row: object) -> None:
        from quill.core.github.project_admin import delete_field
        from quill.core.github.projects import fetch_project

        project = self._project(row)
        if project is None:
            return
        token = self._token()

        def choose(board: Any) -> None:
            # Only fields a person made can go; Title, Status and the like belong to GitHub.
            fields = [
                f
                for f in board.fields
                if f.kind
                not in (
                    "TITLE",
                    "ASSIGNEES",
                    "LABELS",
                    "REPOSITORY",
                    "MILESTONE",
                    "LINKED_PULL_REQUESTS",
                    "REVIEWERS",
                    "PARENT_ISSUE",
                    "SUB_ISSUES_PROGRESS",
                    "TRACKS",
                    "TRACKED_BY",
                )
            ]
            if not fields:
                self._say(f"{_title(project)} has no fields of its own to delete.")
                return
            index = self._choose("Delete Field", "Delete which field?", [f.name for f in fields])
            if index < 0:
                return
            field = fields[index]
            if not self._confirm(
                "Delete Field",
                f"Delete the field {field.name!r} from {_title(project)}? Every item's value in "
                "it goes too, and this cannot be undone.",
            ):
                return
            self._background(
                "delete the field",
                lambda: (delete_field(token, field.node_id), f"Field {field.name} deleted.")[1],
                self._then,
            )

        self._background("read the fields", lambda: fetch_project(token, project.key), choose)

    def _do_project_status(self, _ref: Any, row: object) -> None:
        from quill.core.github.project_admin import STATUS_CHOICES, post_status_update

        project = self._project(row)
        if project is None:
            return
        index = self._choose(
            "Post Status Update", "How is it going?", [w for _c, w in STATUS_CHOICES]
        )
        if index < 0:
            return
        body = self._ask_text("Post Status Update", "What to say (optional):", multiline=True)
        target = self._ask_text("Post Status Update", "Target date, YYYY-MM-DD (optional):")
        code, words = STATUS_CHOICES[index]
        self._background(
            "post the status update",
            lambda: (
                post_status_update(self._token(), project.key, code, body, target_date=target),
                f"{_title(project)}: status update posted, {words}.",
            )[1],
            self._then,
        )

    def _link(self, row: object, link: bool) -> None:
        from quill.core.github.project_admin import link_repository

        project = self._project(row)
        if project is None:
            return
        title = "Link to Repository" if link else "Unlink from Repository"
        repo = self._ask_text(
            title, "Repository (owner/name):", value=project.repo if "/" in project.repo else ""
        )
        if not repo:
            return
        verb = "linked to" if link else "unlinked from"
        self._background(
            "change the link",
            lambda: (
                link_repository(self._token(), project.key, repo, link=link),
                f"{_title(project)} {verb} {repo}.",
            )[1],
            self._then,
        )

    def _do_project_link_repo(self, _ref: Any, row: object) -> None:
        self._link(row, True)

    def _do_project_unlink_repo(self, _ref: Any, row: object) -> None:
        self._link(row, False)

    def _do_project_template(self, _ref: Any, row: object) -> None:
        from quill.core.github.project_admin import set_template

        project = self._project(row)
        if project is None:
            return
        choice = self._choose(
            "Template",
            f"{_title(project)}: a template is offered when someone in the organization "
            "makes a new project.",
            ["Mark as a template", "Stop being a template"],
        )
        if choice < 0:
            return
        mark = choice == 0
        said = "is now a template" if mark else "is no longer a template"
        self._background(
            "change the template setting",
            lambda: (set_template(self._token(), project.key, mark), f"{_title(project)} {said}.")[
                1
            ],
            self._then,
        )

    def _do_project_copy(self, _ref: Any, row: object) -> None:
        from quill.core.github.project_admin import copy_project

        project = self._project(row)
        if project is None:
            return
        owner_guess = project.repo.split("/", 1)[0]
        owner = self._ask_text(
            "Copy Project", "Copy to which user or organization?", value=owner_guess
        )
        if not owner:
            return
        title = self._ask_text(
            "Copy Project", "Title of the copy:", value=f"{_title(project)} (copy)"
        )
        if not title:
            return
        drafts = self._confirm(
            "Copy Project",
            "Copy its draft issues too? Fields, views and workflows are always copied; issues and "
            "pull requests are not.",
        )

        def work() -> str:
            url = copy_project(self._token(), project.key, owner, title, include_drafts=drafts)
            return f"Copied to {owner} as {title}: {url}"

        self._background("copy the project", work, self._then)

    def _do_project_delete(self, _ref: Any, row: object) -> None:
        from quill.core.github.project_admin import delete_project

        project = self._project(row)
        if project is None:
            return
        name = _title(project)
        typed = self._ask_text(
            "Delete Project",
            f"Deleting {name} cannot be undone. Its issues and pull requests stay. "
            "Type the project's title to delete it:",
        )
        if not typed:
            return
        if typed.strip() != name:
            self._say("That is not the project's title, so nothing was deleted.")
            return
        self._background(
            "delete the project",
            lambda: (delete_project(self._token(), project.key), f"{name} deleted.")[1],
            self._then,
        )

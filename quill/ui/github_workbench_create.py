"""New... beside a GitHub sheet's pickers: make the thing and use it at once (GH-R-035).

New Label..., New Milestone..., New Project..., New Issue Type... and New
Branch.... Each returns the name to select, or None after saying why not. A
name that already exists is used rather than made twice, because two things
of one name cannot be told apart by ear.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.sheet_catalog import Target
from quill.core.github.workbench_api import fill_path
from quill.core.workbench.properties import FieldSpec

__all__ = ["GitHubWorkbenchCreateMixin"]


class GitHubWorkbenchCreateMixin:
    """The create half of the properties sheets; the host gives github_api and _say."""

    github_api: Any
    _say: Any
    _ask_text: Any

    def _create(
        self,
        target: Target,
        spec: FieldSpec,
        choices: dict[str, dict[str, object]],
        values: Mapping[str, object] | None = None,
    ) -> str | None:
        """New Label..., New Milestone...: make it on GitHub and use it at once (GH-R-035)."""
        name = self._ask_text(spec.create.rstrip("."), f"{spec.create.rstrip('.')}: name")  # type: ignore[attr-defined]
        if not name:
            return None
        repo = target.ident.get("repo", "")
        values = values or {}
        if spec.key == "projects":
            return self._create_project(repo, name, choices)
        if spec.key == "base":
            return self._create_branch(repo, name, str(values.get("base") or ""), choices)
        path, body = {
            "labels": (f"/repos/{repo}/labels", {"name": name, "color": "ededed"}),
            "milestone": (f"/repos/{repo}/milestones", {"title": name}),
            "issue_type": (
                f"/orgs/{repo.partition('/')[0]}/issue-types",
                {"name": name, "is_enabled": True},
            ),
        }.get(spec.key, ("", {}))
        if not path:
            choices.setdefault(spec.key, {})[name] = name
            return name
        api = self.github_api()
        try:
            answer = api.rest("POST", path, body=body)
        except Exception as exc:  # noqa: BLE001
            from quill.core.github.rest_transport import is_already_exists

            if not is_already_exists(exc):
                self._say(f"Could not create {name}: {exc}")
                return None
            # It is there already: use it, which is what the person wanted.
            value = self._existing_choice(api, spec.key, repo, name)
            if value is None:
                self._say(f"{name} already exists, but GitHub did not say where to find it.")
                return None
            choices.setdefault(spec.key, {})[name] = value
            self._say(f"{name} already exists; using it.")
            return name
        data = answer.data if isinstance(answer.data, dict) else {}
        choices.setdefault(spec.key, {})[name] = data.get("number", name)
        self._say(f"Created {name}.")
        return name

    def _create_branch(
        self, repo: str, name: str, start: str, choices: dict[str, dict[str, object]]
    ) -> str | None:
        """New Branch...: made from the branch it merges into now, or the default branch.

        A name already in the list is used rather than made again; GitHub
        refuses the second one anyway.
        """
        known = choices.setdefault("base", {})
        if name in known:
            self._say(f"{name} already exists; using it.")
            return name
        api = self.github_api()
        try:
            if not start:
                about = api.rest("GET", f"/repos/{repo}").data
                start = (
                    str((about or {}).get("default_branch") or "")
                    if isinstance(about, dict)
                    else ""
                )
            head = api.rest(
                "GET",
                fill_path("/repos/{repo}/git/ref/heads/{start}", {"repo": repo, "start": start}),
            ).data
            sha = (
                str(((head or {}).get("object") or {}).get("sha") or "")
                if isinstance(head, dict)
                else ""
            )
            if not sha:
                self._say(
                    f"Could not create {name}: GitHub did not say where "
                    f"{start or 'the default branch'} is."
                )
                return None
            api.rest(
                "POST", f"/repos/{repo}/git/refs", body={"ref": f"refs/heads/{name}", "sha": sha}
            )
        except Exception as exc:  # noqa: BLE001 - said, never raised into the sheet
            self._say(f"Could not create {name}: {exc}")
            return None
        known[name] = name
        self._say(f"Created {name} from {start}.")
        return name

    def _create_project(
        self, repo: str, name: str, choices: dict[str, dict[str, object]]
    ) -> str | None:
        """New Project...: a Project (version 2) owned by the repository's owner, linked to it.

        Checked at once on the sheet, so OK adds the item to it. A title already
        in the list is used rather than made twice (GitHub allows duplicates,
        which nobody can tell apart by ear).
        """
        from quill.core.github.sheets_items import CREATE_PROJECT, PROJECT_OWNER_QUERY

        known = choices.setdefault("projects", {})
        if name in known:
            self._say(f"{name} already exists; using it.")
            return name
        owner, _, short = repo.partition("/")
        api = self.github_api()
        try:
            found = api.graphql(PROJECT_OWNER_QUERY, {"owner": owner, "name": short})
            repository = found.get("repository") or {}
            owner_id = str((repository.get("owner") or {}).get("id") or "")
            made = api.graphql(
                CREATE_PROJECT,
                {"owner": owner_id, "title": name, "repository": repository.get("id")},
            )
        except Exception as exc:  # noqa: BLE001 - said, never raised into the sheet
            self._say(f"Could not create {name}: {exc}")
            return None
        project = (made.get("createProjectV2") or {}).get("projectV2") or {}
        if not project.get("id"):
            self._say(f"Could not create {name}: GitHub did not say it was made.")
            return None
        known[name] = project["id"]
        self._say(f"Created {name}.")
        return name

    @staticmethod
    def _existing_choice(api: Any, key: str, repo: str, name: str) -> object | None:
        """The value an existing label (its name) or milestone (its number) is chosen by."""
        if key in ("labels", "issue_type"):
            return name
        answer = api.rest(
            "GET", f"/repos/{repo}/milestones", query={"state": "all", "per_page": "100"}
        )
        rows = answer.data if isinstance(answer.data, list) else []
        found = next((r for r in rows if isinstance(r, dict) and r.get("title") == name), None)
        return found.get("number") if found else None

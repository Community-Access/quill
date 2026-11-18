"""A repository's environments: their secrets and variables, and deleting one (PRD section 19).

Secrets and variables go through the resource engine, with the environment
as its target; this mixin lists them in a chooser with "Add one" first, then
asks for each answer with the resource mixin's own questions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["ENVIRONMENT_REASONS", "ENVIRONMENT_VERBS", "GitHubWorkbenchEnvironmentsMixin"]

_ROW = frozenset({"environment"})

ENVIRONMENT_VERBS: dict[str, frozenset[str]] = {
    "environment_secrets": _ROW,
    "environment_variables": _ROW,
    "environment_branch_policies": _ROW,
    "environment_protection_rules": _ROW,
    "environment_delete": _ROW,
}

ENVIRONMENT_REASONS: dict[str, str] = {
    "environment_secrets": "Secrets is for an environment, while you are signed in.",
    "environment_variables": "Variables is for an environment, while you are signed in.",
    "environment_branch_policies": "Branch Policies is for an environment, while signed in.",
    "environment_protection_rules": "Protection Rules is for an environment, while signed in.",
    "environment_delete": "Delete is for an environment, while you are signed in.",
}


class GitHubWorkbenchEnvironmentsMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_fields: Callable[[str, tuple[Any, ...]], dict[str, str] | None]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _environment(row: object) -> tuple[str, str] | None:
        if isinstance(row, ExploreRow) and row.kind == "environment" and row.key and row.repo:
            return row.repo, row.key
        return None

    def _fits_environment(self, row: object) -> bool:
        return self.signed_in and self._environment(row) is not None

    _fits_environment_secrets = _fits_environment
    _fits_environment_variables = _fits_environment
    _fits_environment_delete = _fits_environment
    _fits_environment_branch_policies = _fits_environment
    _fits_environment_protection_rules = _fits_environment

    def _do_environment_branch_policies(self, _ref: Any, row: object) -> None:
        self._manage(row, "environment_branch_policies")

    def _do_environment_protection_rules(self, _ref: Any, row: object) -> None:
        self._manage(row, "environment_protection_rules")

    def _do_environment_secrets(self, _ref: Any, row: object) -> None:
        self._manage(row, "environment_secrets")

    def _do_environment_variables(self, _ref: Any, row: object) -> None:
        self._manage(row, "environment_variables")

    def _manage(self, row: object, key: str) -> None:
        from quill.core.github import resource_engine as engine
        from quill.core.github.resource_specs_env import environment_spec, environment_target

        found, spec = self._environment(row), environment_spec(key)
        if found is None or spec is None:
            return
        repo, name = found
        target, api = environment_target(repo, name), self.github_api()
        title = f"{name}: {spec.label.split()[-1]}"

        def listed(rows: Any) -> None:
            rows = list(rows)
            labels = [f"Add a {spec.noun}...", *(one.label for one in rows)]
            picked = self._choose(title, f"The {spec.noun}s of {name}:", labels)
            if picked < 0:
                return
            if picked == 0 and key == "environment_protection_rules":
                self._add_protection_app(api, spec, target, name)
                return
            if picked == 0:
                answers = self._ask_fields(f"New {spec.noun}", spec.create)
                if answers is not None:
                    self._background(
                        f"add the {spec.noun}",
                        lambda: engine.create(api, spec, target, answers),
                        lambda said: self._say(str(said)),
                    )
                return
            item = rows[picked - 1]
            _key, item_id = engine.row_spec_and_id(item.key)
            actions = (["Change its value..."] if spec.edit else []) + ["Delete..."]
            act = self._choose(title, item.label, actions)
            if act < 0:
                return
            if spec.edit and act == 0:
                answers = self._ask_fields(f"Change {spec.noun}", spec.edit)
                if answers is not None:
                    self._background(
                        f"change the {spec.noun}",
                        lambda: engine.edit(api, spec, target, item_id, answers),
                        lambda said: self._say(str(said)),
                    )
                return
            if self._confirm(f"Delete {spec.noun}", f"Delete {item_id} from {name}?"):
                self._background(
                    f"delete the {spec.noun}",
                    lambda: engine.delete(api, spec, target, item_id),
                    lambda said: self._say(str(said)),
                )

        self._background(
            f"list {name}'s {spec.noun}s", lambda: engine.fetch(api, spec, target), listed
        )

    def _do_environment_delete(self, _ref: Any, row: object) -> None:
        from quill.core.github.environments import delete_environment

        found = self._environment(row)
        if found is None:
            return
        repo, name = found
        if not self._confirm(
            "Delete Environment",
            f"Delete the environment {name} from {repo}, with its secrets, variables and "
            "protection rules? Workflows that deploy to it make a new, unprotected one.",
        ):
            return
        api = self.github_api()
        self._background(
            f"delete {name}",
            lambda: delete_environment(api, repo, name),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _add_protection_app(self, api: Any, spec: Any, target: str, name: str) -> None:
        """Offer the GitHub Apps that can guard deployments, rather than ask for a number."""
        from quill.core.github import resource_engine as engine
        from quill.core.github.resource_specs_env_more import protection_apps

        def chosen(apps: Any) -> None:
            apps = list(apps)
            if not apps:
                self._say(
                    "No GitHub App that protects deployments is installed for this repository. "
                    "Install one from GitHub Marketplace first."
                )
                return
            picked = self._choose(
                f"{name}: Add Protection Rule",
                "Which app must approve each deployment?",
                [slug for _id, slug in apps],
            )
            if picked < 0:
                return
            app_id, slug = apps[picked]
            self._background(
                "add the protection rule",
                lambda: engine.create(api, spec, target, {"integration_id": app_id}),
                lambda _said: self._say(f"{slug} must now approve each deployment to {name}."),
            )

        self._background(
            "list the apps that can protect deployments",
            lambda: protection_apps(api, target),
            chosen,
        )

"""Codespaces in the GitHub Workbench: make, start, stop, export, publish, delete (PRD section 19).

The code is in :mod:`quill.core.github.codespaces`; this mixin asks and says.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubItem

__all__ = ["CODESPACE_REASONS", "CODESPACE_VERBS", "GitHubWorkbenchCodespacesMixin"]

_ROW = frozenset({"codespace"})

CODESPACE_VERBS: dict[str, frozenset[str]] = {
    "codespace_new": frozenset({"view"}),
    "codespace_start": _ROW,
    "codespace_stop": _ROW,
    "codespace_machine": _ROW,
    "codespace_export": _ROW,
    "codespace_publish": _ROW,
    "codespace_delete": _ROW,
    "pull_codespace": frozenset({"item"}),
}

_RUNS = "It costs money for every hour it runs, until it stops."
_KEPT = "It costs money for every hour it runs, and for its storage until you delete it."

_ON_ROW = "is for one of your codespaces, while you are signed in."
CODESPACE_REASONS: dict[str, str] = {
    "codespace_new": "New Codespace is Ctrl+N in a repository's Codespaces.",
    "codespace_start": f"Start {_ON_ROW}",
    "codespace_stop": f"Stop {_ON_ROW}",
    "codespace_machine": f"Change Machine {_ON_ROW}",
    "codespace_export": f"Export to a Branch {_ON_ROW}",
    "codespace_publish": f"Publish to a New Repository {_ON_ROW}",
    "codespace_delete": f"Delete {_ON_ROW}",
    "pull_codespace": "Open in a Codespace is for an open pull request.",
}


class GitHubWorkbenchCodespacesMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _codespace(row: object) -> str:
        if isinstance(row, ExploreRow) and row.kind == "codespace" and row.key:
            return row.key
        return ""

    def _on_row(self, row: object) -> bool:
        return self.signed_in and bool(self._codespace(row))

    _fits_codespace_start = _on_row
    _fits_codespace_stop = _on_row
    _fits_codespace_machine = _on_row
    _fits_codespace_export = _on_row
    _fits_codespace_publish = _on_row
    _fits_codespace_delete = _on_row

    def _fits_codespace_new(self, _row: object) -> bool:
        current = getattr(getattr(self.frame, "current", None), "key", "")
        return self.signed_in and current == "repo_codespaces"

    def _fits_pull_codespace(self, row: object) -> bool:
        return (
            self.signed_in
            and isinstance(row, GitHubItem)
            and row.is_pr
            and row.state.casefold() == "open"
        )

    def _said_and_reload(self, said: object) -> None:
        self._say(str(said))
        self.frame.reload()

    def _if_paid_for(self, title: str, question: str, payer: str) -> bool:
        """Ask before GitHub starts billing; No is the default, so Enter spends nothing."""
        return self._confirm(title, f"{question} GitHub bills {payer}.")

    # -- one codespace ---------------------------------------------------------------------

    def _do_codespace_start(self, _ref: Any, row: object) -> None:
        from quill.core.github.codespaces import billing_owner, start

        name, api = self._codespace(row), self.github_api()

        def asked(payer: Any) -> None:
            if self._if_paid_for("Start Codespace", f"Start the codespace {name}? {_RUNS}", payer):
                self._background(f"start {name}", lambda: start(api, name), self._said_and_reload)

        self._background(f"read who pays for {name}", lambda: billing_owner(api, name=name), asked)

    def _do_codespace_stop(self, _ref: Any, row: object) -> None:
        from quill.core.github.codespaces import stop

        name, api = self._codespace(row), self.github_api()
        self._background(f"stop {name}", lambda: stop(api, name), self._said_and_reload)

    def _do_codespace_delete(self, _ref: Any, row: object) -> None:
        from quill.core.github.codespaces import delete

        name = self._codespace(row)
        if not self._confirm(
            "Delete Codespace",
            f"Delete the codespace {name}? Changes you have not pushed or exported are lost.",
        ):
            return
        api = self.github_api()
        self._background(f"delete {name}", lambda: delete(api, name), self._said_and_reload)

    def _do_codespace_machine(self, _ref: Any, row: object) -> None:
        from quill.core.github.codespaces import machines, set_machine

        name, api = self._codespace(row), self.github_api()

        def chosen(found: Any) -> None:
            found = list(found)
            if not found:
                self._say(f"GitHub offers no other machine for {name}.")
                return
            picked = self._choose(
                "Change Machine", f"Which machine should {name} use?", [m.label for m in found]
            )
            if picked < 0:
                return
            machine = found[picked]
            self._background(
                "change the machine", lambda: set_machine(api, name, machine), self._said_and_reload
            )

        self._background(f"list the machines for {name}", lambda: machines(api, name), chosen)

    def _do_codespace_export(self, _ref: Any, row: object) -> None:
        from quill.core.github.codespaces import export, export_status

        name, api = self._codespace(row), self.github_api()

        def started(result: Any) -> None:
            said, export_id = result
            self._say(said)
            self._background(
                "read the export's progress",
                lambda: export_status(api, name, export_id),
                lambda status: self._say(str(status)),
            )

        self._background(f"export {name}", lambda: export(api, name), started)

    def _do_codespace_publish(self, _ref: Any, row: object) -> None:
        from quill.core.github.codespaces import publish

        name = self._codespace(row)
        title = "Publish to a New Repository"
        repository = self._ask_text(title, "Name for the new repository (blank for GitHub's):")
        visibility = self._choose(title, "Who may see it?", ["Private", "Public"])
        if visibility < 0:
            return
        api = self.github_api()
        self._background(
            f"publish {name}",
            lambda: publish(api, name, repository, visibility == 0),
            self._said_and_reload,
        )

    # -- making one ------------------------------------------------------------------------

    def _do_codespace_new(self, ref: Any, _row: object) -> None:
        from quill.core.github.codespaces import create, new_choices

        repo = ref.instance
        title = f"New Codespace: {repo}"
        branch = self._ask_text(title, "Make it on which branch?", value="main")
        if not branch:
            return
        api = self.github_api()

        def chosen(found: Any) -> None:
            if not found.allowed:
                self._say(
                    "This dev container asks for permissions you have not accepted. Open the "
                    "repository's Codespaces on GitHub once to accept them, then try again."
                )
                return
            machine = ""
            if found.machines:
                picked = self._choose(
                    title, "Which machine?", [one.label for one in found.machines]
                )
                if picked < 0:
                    return
                machine = found.machines[picked].value
            container = found.default_container
            if len(found.containers) > 1:
                labels = [one.label for one in found.containers]
                picked = self._choose(title, "Which dev container?", labels)
                if picked < 0:
                    return
                container = found.containers[picked].value
            question = f"Make a codespace for {repo} on {branch}? {_KEPT}"
            if not self._if_paid_for(title, question, found.payer):
                return
            self._background(
                "make the codespace",
                lambda: create(api, repo, branch, machine, container),
                self._said_and_reload,
            )

        self._background(
            f"read what a codespace for {repo} can use",
            lambda: new_choices(api, repo, branch),
            chosen,
        )

    def _do_pull_codespace(self, ref: Any, row: object) -> None:
        from quill.core.github.codespaces import billing_owner, for_pull

        if not isinstance(row, GitHubItem):
            return
        api, repo, number = self.github_api(), ref.instance, row.number

        def asked(payer: Any) -> None:
            question = f"Make a codespace for pull request #{number}? {_KEPT}"
            if not self._if_paid_for("Open in a Codespace", question, payer):
                return
            self._background(
                f"make a codespace for #{number}",
                lambda: for_pull(api, repo, number),
                lambda said: self._say(str(said)),
            )

        self._background(
            f"read who pays for a codespace in {repo}", lambda: billing_owner(api, repo=repo), asked
        )

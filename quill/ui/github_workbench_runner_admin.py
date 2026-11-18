"""Repository > Actions > Runners: adding, labelling and removing runners (GitHub PRD 14.2).

The list is the Explore view ``runners``. **New Runner...** (``Ctrl+N``
there) copies the setup commands for the machine's system to the clipboard,
with a one-hour token in them that is never said. **Runner Labels...** adds
or removes a label; **Remove Runner...** forgets a runner after asking.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["RUNNER_ADMIN_REASONS", "RUNNER_ADMIN_VERBS", "GitHubWorkbenchRunnerAdminMixin"]

RUNNER_ADMIN_VERBS: dict[str, frozenset[str]] = {
    "new_runner": frozenset({"view"}),
    "runner_labels": frozenset({"runner"}),
    "remove_runner": frozenset({"runner"}),
}

RUNNER_ADMIN_REASONS: dict[str, str] = {
    "new_runner": "New Runner is Ctrl+N in a repository's Runners, for its administrators.",
    "runner_labels": "Runner Labels is for a self-hosted runner.",
    "remove_runner": "Remove Runner is for a self-hosted runner.",
}


class GitHubWorkbenchRunnerAdminMixin:
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
    def _runner(row: object) -> ExploreRow | None:
        found = isinstance(row, ExploreRow) and row.kind == "runner" and bool(row.key)
        return row if found and isinstance(row, ExploreRow) else None

    def _fits_new_runner(self, _row: object) -> bool:
        key = getattr(getattr(self.frame, "current", None), "key", "")
        return self.signed_in and key == "runners"

    def _fits_runner_labels(self, row: object) -> bool:
        return self.signed_in and self._runner(row) is not None

    _fits_remove_runner = _fits_runner_labels

    def _do_new_runner(self, ref: Any, _row: object) -> None:
        from quill.core.github.runner_admin import fetch_downloads

        api, repository = self.github_api(), ref.instance
        self._background(
            "read the runner downloads",
            lambda: fetch_downloads(api, repository),
            lambda found: self._pick_download(repository, list(found)),
        )

    def _pick_download(self, repository: str, downloads: list[Any]) -> None:
        from quill.core.github.runner_admin import setup_commands

        if not downloads:
            self._say("GitHub listed no runner downloads.")
            return
        picked = self._choose(
            "New Runner",
            "Which system does the machine run?",
            [download.label for download in downloads],
        )
        if picked < 0:
            return
        download = downloads[picked]
        api = self.github_api()
        self._background(
            "get a runner token",
            lambda: setup_commands(api, repository, download),
            lambda commands: self._copy_commands(str(commands), download.label),
        )

    def _copy_commands(self, commands: str, system: str) -> None:
        self.frame.copy_text(commands)
        self._say(
            f"Copied the setup commands for {system}. Paste them into a terminal on that "
            "machine within the hour; the token in them then stops working."
        )

    def _do_runner_labels(self, ref: Any, row: object) -> None:
        from quill.core.github.runner_admin import custom_labels

        found = self._runner(row)
        if found is None:
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "read the labels",
            lambda: custom_labels(api, repository, found.key),
            lambda labels: self._change_label(repository, found, list(labels)),
        )

    def _change_label(self, repository: str, found: ExploreRow, labels: list[str]) -> None:
        from quill.core.github.runner_admin import add_label, remove_label

        choices = ["Add a label...", *(f"Remove {label}" for label in labels)]
        picked = self._choose("Runner Labels", f"Labels of {found.title or found.key}:", choices)
        if picked < 0:
            return
        api = self.github_api()
        if picked == 0:
            label = self._ask_text("Runner Labels", "The label to add, such as gpu:")
            if not label:
                return
            work: Callable[[], Any] = lambda: add_label(api, repository, found.key, label)  # noqa: E731
        else:
            label = labels[picked - 1]
            work = lambda: remove_label(api, repository, found.key, label)  # noqa: E731
        self._background(
            "change the labels", work, lambda said: (self._say(str(said)), self.frame.reload())
        )

    def _do_remove_runner(self, ref: Any, row: object) -> None:
        from quill.core.github.runner_admin import remove_runner

        found = self._runner(row)
        if found is None:
            return
        name = found.title or found.key
        if not self._confirm(
            "Remove Runner",
            f"Remove the runner {name}? GitHub forgets it, and the program on that machine "
            "gets no more jobs. Setting it up again needs a new token.",
        ):
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "remove the runner",
            lambda: remove_runner(api, repository, found.key, name),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

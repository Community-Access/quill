"""Tools > Dry Run in the GitHub Workbench, and how a stopped or failed write is said.

Dry Run (GitHub PRD 22.8) is :data:`quill.core.github.dry_run.DRY_RUN`: while
it is on, every command still asks and previews, and the write itself stops
at the door with "Dry run: QUILL would ... Nothing was changed." It lasts
until it is turned off or QUILL closes, and the Account cell of the status bar
says so while it is on.

:func:`failure_sentence` is what the Workbench says when background work
fails: a Dry Run stop as itself, anything else as "Could not ..." and the
reason, without the support code a coded error carries in brackets.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["DRY_RUN_REASONS", "DRY_RUN_VERBS", "GitHubWorkbenchDryRunMixin", "failure_sentence"]

DRY_RUN_VERBS: dict[str, frozenset[str]] = {"dry_run": frozenset({"view"})}
DRY_RUN_REASONS: dict[str, str] = {"dry_run": "Dry Run is always available."}


def failure_sentence(name: str, error: object) -> str:
    from quill.core.github.dry_run import DryRunStop

    if isinstance(error, DryRunStop):
        return error.sentence
    args = getattr(error, "args", None)
    reason = (str(args[0]) if args else str(error)) or "no reason was given"
    return f"Could not {name}: {reason}"


class GitHubWorkbenchDryRunMixin:
    _say: Callable[[str], None]

    def _do_dry_run(self, _ref: Any, _row: object) -> None:
        from quill.core.github.dry_run import DRY_RUN

        DRY_RUN.set(not DRY_RUN.on)
        if DRY_RUN.on:
            self._say(
                "Dry Run is on. Commands still ask and preview, then stop before sending "
                "anything to GitHub, and say what they would have sent. It lasts until you "
                "turn it off or close QUILL."
            )
        else:
            self._say("Dry Run is off. Writes go to GitHub again.")

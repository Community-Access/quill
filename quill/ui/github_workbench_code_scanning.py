"""Copilot Autofix, every place an alert was found, and uploading SARIF (GitHub PRD section 19).

The code is in :mod:`quill.core.github.code_scanning_tools`; this mixin asks
the questions and says the answers.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["CODE_SCANNING_REASONS", "CODE_SCANNING_VERBS", "GitHubWorkbenchCodeScanningMixin"]

CODE_SCANNING_VERBS: dict[str, frozenset[str]] = {
    "autofix_alert": frozenset({"security"}),
    "alert_instances": frozenset({"security"}),
    "upload_sarif": frozenset({"view"}),
}

CODE_SCANNING_REASONS: dict[str, str] = {
    "autofix_alert": "Copilot Autofix is for a code scanning alert, while you are signed in.",
    "alert_instances": "Show Every Place is for a code scanning alert.",
    "upload_sarif": "Upload SARIF File is in a repository's Code Scanning Analyses.",
}


class GitHubWorkbenchCodeScanningMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _show_text: Callable[[str, str], None]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _code_alert(row: object) -> tuple[str, int] | None:
        from quill.core.github.alert_triage import parse_alert_key

        if not isinstance(row, ExploreRow):
            return None
        parsed = parse_alert_key(row.key)
        if parsed is None or parsed[0].key != "code-scanning":
            return None
        return row.repo, parsed[1]

    def _fits_autofix_alert(self, row: object) -> bool:
        return self.signed_in and self._code_alert(row) is not None

    def _fits_alert_instances(self, row: object) -> bool:
        return self.signed_in and self._code_alert(row) is not None

    def _fits_upload_sarif(self, _row: object) -> bool:
        current = getattr(getattr(self.frame, "current", None), "key", "")
        return self.signed_in and current == "code_scanning_analyses"

    # -- Copilot Autofix -------------------------------------------------------------------

    def _do_autofix_alert(self, _ref: Any, row: object) -> None:
        from quill.core.github.code_scanning_tools import autofix

        found = self._code_alert(row)
        if found is None:
            return
        repo, number = found
        api = self.github_api()
        self._background(
            f"read the fix for alert #{number}",
            lambda: autofix(api, repo, number),
            lambda fix: self._autofix_next(repo, number, fix),
        )

    def _autofix_next(self, repo: str, number: int, fix: Any) -> None:
        from quill.core.github.code_scanning_tools import autofix, commit_autofix

        title = f"Copilot Autofix: alert #{number}"
        api = self.github_api()
        if fix.status in ("none", "outdated", "error"):
            if self._confirm(title, f"{fix.sentence()} Ask Copilot Autofix for a fix now?"):
                self._background(
                    "ask Copilot Autofix for a fix",
                    lambda: autofix(api, repo, number, ask=True),
                    lambda made: self._say(made.sentence()),
                )
            return
        if not fix.ready:
            self._say(fix.sentence())
            return
        if self._choose(title, fix.sentence(), ["Commit the fix to a branch...", "Not now"]) != 0:
            return
        branch = self._ask_text(title, "Commit the fix to which branch?")
        if not branch:
            return
        message = self._ask_text(title, "Commit message (optional):")
        self._background(
            f"commit the fix to {branch}",
            lambda: commit_autofix(api, repo, number, branch, message),
            lambda said: self._say(str(said)),
        )

    # -- every place it was found --------------------------------------------------------

    def _do_alert_instances(self, _ref: Any, row: object) -> None:
        from quill.core.github.code_scanning_tools import instances

        found = self._code_alert(row)
        if found is None:
            return
        repo, number = found
        api = self.github_api()

        def shown(places: Any) -> None:
            if not places:
                self._say(f"GitHub lists no places for alert #{number}.")
                return
            count = len(places)
            heading = f"Alert #{number} was found in {count} place{'s' if count != 1 else ''}."
            self._show_text(f"Every Place: alert #{number}", "\n".join([heading, "", *places]))

        self._background(
            f"list where alert #{number} was found", lambda: instances(api, repo, number), shown
        )

    # -- uploading results -----------------------------------------------------------------

    def _pick_sarif(self) -> Path | None:
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self.frame._wx
        title = "Choose the SARIF file"
        with wx.FileDialog(
            self.frame.frame,
            title,
            wildcard="SARIF results (*.sarif;*.json)|*.sarif;*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as box:
            if show_modal_dialog(box, title) != wx.ID_OK:
                return None
            return Path(box.GetPath())

    def _do_upload_sarif(self, ref: Any, _row: object) -> None:
        from quill.core.github.code_scanning_tools import sarif_status, upload_sarif

        path = self._pick_sarif()
        if path is None:
            return
        branch = self._ask_text("Upload SARIF File", "Results are for which branch?", value="main")
        if not branch:
            return
        api, repo = self.github_api(), ref.instance

        def sent(result: Any) -> None:
            said, upload = result
            self._say(said)
            if upload:
                self._background(
                    "read the upload's progress",
                    lambda: sarif_status(api, repo, upload),
                    lambda status: self._say(str(status)),
                )
            self.frame.reload()

        self._background(f"upload {path.name}", lambda: upload_sarif(api, repo, path, branch), sent)

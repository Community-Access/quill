"""Repository > Security > Advisories: reporting, drafting, publishing (GitHub PRD 14.1, GX11).

The lists are Explore views (:mod:`quill.core.github.security_advisories`).
This mixin adds **New Here** in Advisories, which reports a vulnerability
privately or drafts an advisory; **Publish or Close Advisory...**,
where publishing wants the GHSA id typed because it cannot be undone; and
**Request CVE...**.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["ADVISORY_REASONS", "ADVISORY_VERBS", "GitHubWorkbenchAdvisoriesMixin"]

ADVISORY_VERBS: dict[str, frozenset[str]] = {
    "new_advisory": frozenset({"view"}),
    "advisory_state": frozenset({"advisory"}),
    "request_cve": frozenset({"advisory"}),
}

ADVISORY_REASONS: dict[str, str] = {
    "new_advisory": "New Here in Advisories reports a vulnerability, while you are signed in.",
    "advisory_state": "Publish or Close Advisory is for a repository's advisory.",
    "request_cve": "Request CVE is for a repository's draft advisory with no CVE yet.",
}

_KINDS = ("Report a vulnerability privately to the maintainers", "Draft an advisory (maintainers)")
_STATES = (
    ("Publish it: public, and in the Advisory Database", "published"),
    ("Close it", "closed"),
    ("Make it a draft again", "draft"),
)


class GitHubWorkbenchAdvisoriesMixin:
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
    def _advisory(row: object) -> ExploreRow | None:
        found = isinstance(row, ExploreRow) and row.kind == "advisory" and "/" in row.repo
        return row if found and isinstance(row, ExploreRow) else None

    def _fits_new_advisory(self, _row: object) -> bool:
        current = getattr(self.frame, "current", None)
        return self.signed_in and getattr(current, "key", "") == "advisories"

    def _fits_advisory_state(self, row: object) -> bool:
        return self.signed_in and self._advisory(row) is not None

    def _fits_request_cve(self, row: object) -> bool:
        found = self._advisory(row)
        return self.signed_in and found is not None and "CVE-" not in found.label

    def _ask_report(self, title: str) -> tuple[str, str, str] | None:
        from quill.core.github.security_advisories import SEVERITIES

        summary = self._ask_text(title, "A one-line summary of the vulnerability:")
        if not summary:
            return None
        description = self._ask_text(
            title,
            "What it is, how to reproduce it, and what it lets an attacker do:",
            multiline=True,
        )
        if not description:
            return None
        labels = [*(word.capitalize() for word in SEVERITIES), "Not sure"]
        picked = self._choose(title, "How severe is it?", labels)
        if picked < 0:
            return None
        return summary, description, SEVERITIES[picked] if picked < len(SEVERITIES) else ""

    def _do_new_advisory(self, ref: Any, _row: object) -> None:
        from quill.core.github.security_advisories import draft_advisory, report_vulnerability

        repository = ref.instance
        kind = self._choose("New Here", f"In {repository}'s advisories:", list(_KINDS))
        if kind < 0:
            return
        title = "Report a Vulnerability" if kind == 0 else "Draft an Advisory"
        answers = self._ask_report(title)
        if answers is None:
            return
        summary, description, severity = answers
        api = self.github_api()
        if kind == 0:
            work: Callable[[], Any] = lambda: report_vulnerability(  # noqa: E731
                api, repository, summary, description, severity
            )
        else:
            package = self._ask_text(
                title, "The affected package's name, or leave it empty to add it later:"
            )
            ecosystem = (
                self._ask_text(title, f"Which ecosystem is {package} in, such as npm or pip?")
                if package
                else ""
            )
            work = lambda: draft_advisory(  # noqa: E731
                api,
                repository,
                summary,
                description,
                severity,
                ecosystem=ecosystem,
                package=package,
            )
        self._background("send it", work, lambda said: (self._say(str(said)), self.frame.reload()))

    def _do_advisory_state(self, _ref: Any, row: object) -> None:
        from quill.core.github.security_advisories import set_state
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        found = self._advisory(row)
        if found is None:
            return
        picked = self._choose(
            "Advisory", f"What to do with {found.key}?", [label for label, _s in _STATES]
        )
        if picked < 0:
            return
        state = _STATES[picked][1]
        if state == "published":
            if not TypedConfirmDialog(
                self.frame.frame,
                title="Publish Advisory",
                message=(
                    f"Publish {found.key}? Everyone can read it, it goes into GitHub's "
                    "Advisory Database and alerts the repositories that depend on the package, "
                    "and it cannot be unpublished. Type its GHSA id to confirm."
                ),
                expected=found.key,
                confirm_label="Publish",
            ).show():
                self._say("Cancelled; the advisory was not published.")
                return
        elif not self._confirm("Advisory", f"{_STATES[picked][0]}: {found.key}?"):
            return
        api, repository = self.github_api(), found.repo
        self._background(
            "change the advisory",
            lambda: set_state(api, repository, found.key, state),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_request_cve(self, _ref: Any, row: object) -> None:
        from quill.core.github.security_advisories import request_cve

        found = self._advisory(row)
        if found is None or not self._confirm(
            "Request CVE", f"Ask GitHub for a CVE number for {found.key}?"
        ):
            return
        api = self.github_api()
        self._background(
            "request a CVE", lambda: request_cve(api, found.repo, found.key), self._say
        )

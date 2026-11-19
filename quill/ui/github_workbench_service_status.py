"""Help > GitHub Service Status...: is it GitHub, or is it me? (complete.md 1.3).

Asks once before the first read, then reads GitHub's public status page off
the UI thread and shows what it says. The work is
:mod:`quill.core.github.service_status`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["SERVICE_STATUS_REASONS", "SERVICE_STATUS_VERBS", "GitHubWorkbenchServiceStatusMixin"]

SERVICE_STATUS_VERBS: dict[str, frozenset[str]] = {"service_status": frozenset({"view"})}
SERVICE_STATUS_REASONS: dict[str, str] = {
    "service_status": "GitHub's status page is read only when you ask, and never in Safe Mode.",
}


class GitHubWorkbenchServiceStatusMixin:
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _show_text: Callable[[str, str], None]

    def _fits_service_status(self, _row: object) -> bool:
        import os

        return os.environ.get("QUILL_SAFE_MODE") != "1"  # H-SAFE-1: no network in Safe Mode

    def _do_service_status(self, _ref: Any, _row: object) -> None:
        from quill.core.github import service_status as ss

        if not ss.consented():
            if not self._confirm(
                "GitHub Service Status",
                "Read GitHub's public status page, www.githubstatus.com? QUILL sends only the "
                "request: nothing about you, your accounts or your repositories. It asks this "
                "once, and reads the page only when you choose this command.",
            ):
                return
            ss.record_consent()
        self._background(
            "read GitHub's status page",
            ss.read_status,
            lambda status: self._show_text("GitHub Service Status", status.sentences()),
        )

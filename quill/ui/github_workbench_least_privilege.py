"""Account > Roles and Access > Least Privilege Advice, a report that changes nothing.

It reads this account's token scopes afresh (``GET /user``, whose
``X-OAuth-Scopes`` names a classic token's scopes and is absent for a
fine-grained one), then hands what QUILL saw on this computer
(:data:`quill.core.github.observed_use.OBSERVED_USE`), Change History and the
account's Workbench level to :func:`quill.core.github.least_privilege.advise`,
and shows :func:`~quill.core.github.least_privilege.report` in the
Workbench's results window to read and copy. No token is changed, and nothing
is sent but that one read.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["GitHubWorkbenchLeastPrivilegeMixin"]


class GitHubWorkbenchLeastPrivilegeMixin:
    """Least Privilege Advice, for the GitHub provider."""

    items: Any
    frame: Any
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]

    def _tool_least_privilege(self) -> None:
        from quill.core.github.least_privilege import advise, report
        from quill.core.github.observed_use import OBSERVED_USE
        from quill.core.github.token_health import parse_scopes

        api = self.github_api()  # type: ignore[attr-defined]
        token = getattr(self.items, "token", None)
        login = self.account_name()  # type: ignore[attr-defined]
        level = self.access_level()  # type: ignore[attr-defined]
        history = list(self.change_log().entries)  # type: ignore[attr-defined]

        def read() -> str:
            answer = api.rest("GET", "/user")
            header = answer.header("x-oauth-scopes") if "x-oauth-scopes" in answer.headers else None
            scopes = parse_scopes(header)
            data = answer.data if isinstance(answer.data, dict) else {}
            who = login or str(data.get("login") or "")
            use = OBSERVED_USE.use_for(token)
            return report(advise(login=who, use=use, scopes=scopes, history=history, level=level))

        def done(text: str) -> None:
            from quill.ui.github_workbench_results import show_results

            show_results(
                self.frame.frame, "Least Privilege Advice", text, copy_text=self.frame.copy_text
            )

        self._background("read what this account used", read, done)

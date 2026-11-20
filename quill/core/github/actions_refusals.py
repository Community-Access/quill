"""Why an Actions request failed, in one plain sentence (complete.md 1.3, Actions lifecycle).

Turning a workflow on or off, starting or re-running one, reading a job's log
and downloading an artifact each reach GitHub by a different road (the
Workbench's REST door, PyGithub, or a hand-rolled download that never sends
the token to a redirect), and each used to pass GitHub's own words on raw:
"HTTP Error 410: Gone", "Resource not accessible by integration". One
sentence per status instead, said the same way on every road:

* 401: the sign-in is no longer accepted;
* 403: GitHub refused, and what it needs;
* 404 and 410: nothing there, with *gone* saying why that happens
  (a log or artifact past its retention, a run deleted);
* 409 and 422: not in its present state, with GitHub's reason when it gave one.

wx-free and strict-typed.
"""

from __future__ import annotations

from typing import Any

__all__ = ["actions_refusal", "status_of"]

_GONE = "it was deleted, or this account cannot see it"


def status_of(exc: Any) -> int | None:
    """The HTTP status a REST, PyGithub or urllib failure carries, if any."""
    for name in ("status", "code"):
        value = getattr(exc, name, None)
        if isinstance(value, int):
            return value
    return None


def _detail(exc: Any) -> str:
    data = getattr(exc, "data", None)
    message = data.get("message", "") if isinstance(data, dict) else ""
    return str(message or "").strip().rstrip(".")


def actions_refusal(
    doing: str,
    exc: Any,
    *,
    needs: str = "write access to Actions in this repository",
    gone: str = _GONE,
) -> str:
    """One sentence for a failure to *doing* (``"turn the workflow off"``)."""
    status = status_of(exc)
    if status == 401:
        return f"Could not {doing}: GitHub no longer accepts this sign-in. Sign in again."
    if status in (403, 429):
        from quill.core.github.auth_diagnostics import github_exception_hint

        hint = github_exception_hint(exc) or ""
        if hint and not hint.startswith("Access denied"):
            return f"Could not {doing}: {hint}"  # a rate limit or single sign-on
        return f"GitHub refused to {doing}. It needs {needs}."
    if status in (404, 410):
        return f"GitHub found nothing to {doing}: {gone}."
    if status in (409, 422):
        detail = _detail(exc)
        return f"GitHub could not {doing} in its present state" + (
            f": {detail}." if detail else "."
        )
    if status is not None and status >= 500:
        return f"Could not {doing}: GitHub had a server error. Wait a moment and try again."
    return f"Could not {doing}: {_detail(exc) or exc}"

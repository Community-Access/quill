"""Add an account by reusing the GitHub CLI's sign-in (``gh auth token``).

Someone who already signed in to ``gh`` should not have to sign in again.
QUILL asks ``gh`` for the token it holds for one host, by running exactly
``gh auth token --hostname HOST`` -- never by reading ``gh``'s own files or
keyring -- then checks with GitHub whose token it is, asks the person, and
saves it the way every other account is saved (``accounts.save_github_account``,
in the OS credential store). From then on it is QUILL's own copy: signing out
of ``gh`` later does not sign QUILL out, and removing the account in QUILL
does not touch ``gh``.

The boundary, frozen by ``tests/unit/core/test_github_gh_sign_in.py``:

* the executable is the ``gh`` that :func:`quill.core.git_binaries.resolve_gh`
  finds, which only ever answers a file named ``gh`` or ``gh.exe`` (the git and
  gh allowlist there). The external-engine allowlist is not widened;
* the arguments are :data:`GH_ARGUMENTS` and nothing else, with the host
  checked by :func:`quill.core.github.hosts.normalize_host` first, so no typed
  text becomes an argument of its own;
* it runs through ``safe_subprocess`` (argv, no shell, :data:`TIMEOUT_SECONDS`).
  ``gh auth token`` reads ``gh``'s local store and makes no network call; the
  identity check that follows goes through the Workbench's own transport, to
  the account's own host.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "GH_ARGUMENTS",
    "TIMEOUT_SECONDS",
    "GhSignInError",
    "confirm_question",
    "gh_arguments",
    "read_gh_token",
]

#: The one ``gh`` command this path runs; ``{host}`` is the checked host name.
GH_ARGUMENTS: tuple[str, ...] = ("auth", "token", "--hostname", "{host}")

TIMEOUT_SECONDS = 15.0

#: The shapes of token ``gh`` holds: OAuth (gho_), classic (ghp_), fine-grained
#: (github_pat_), the app tokens (ghu_, ghs_), and the 40 hexadecimal digits an
#: older Enterprise Server still issues. Anything else is not a token.
_TOKEN_RE = re.compile(
    r"^(?:gh[opsu]_[A-Za-z0-9]{20,255}|github_pat_[A-Za-z0-9_]{20,255}|[0-9a-f]{40})$"
)

Runner = Callable[..., Any]


class GhSignInError(CodedError):
    """The GitHub CLI could not give QUILL a sign-in for that host."""

    code = "QUILL-GITHUB-GHSIGNIN-FAILED"


def confirm_question(login: str, host: str, store: str) -> str:
    """The question asked before a reused ``gh`` sign-in is saved, naming whose it is."""
    return (
        f"The GitHub CLI is signed in to {host} as {login}. Add {login} on {host} to QUILL "
        f"with that sign-in?\n\nQUILL keeps its own copy in the {store}. Signing out of the "
        "GitHub CLI later does not sign QUILL out, and removing the account in QUILL does "
        "not touch the GitHub CLI."
    )


def gh_arguments(host: str) -> list[str]:
    """``GH_ARGUMENTS`` with the host filled in, after the host is checked."""
    from quill.core.github.hosts import GitHubHostError, normalize_host

    try:
        checked = normalize_host(host)
    except GitHubHostError as exc:
        raise GhSignInError(str(exc)) from exc
    return [part.replace("{host}", checked) for part in GH_ARGUMENTS]


def read_gh_token(
    host: str,
    *,
    gh_path: str | None = None,
    runner: Runner | None = None,
) -> str:
    """The token ``gh`` holds for *host*, or a :class:`GhSignInError` saying why not.

    *gh_path* and *runner* are for tests; by default the ``gh`` that
    ``resolve_gh`` finds, run by ``run_subprocess_safely``.
    """
    arguments = gh_arguments(host)
    if gh_path is None:
        from quill.core.git_binaries import resolve_gh

        found = resolve_gh()
        if found is None:
            raise GhSignInError(
                "QUILL did not find the GitHub CLI (gh). Sign In with GitHub works without it."
            )
        gh_path = str(found)
    if runner is None:
        from quill.stability.safe_subprocess import run_subprocess_safely

        runner = run_subprocess_safely
    try:
        result = runner([gh_path, *arguments], timeout_seconds=TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - a timeout or a launch failure, said plainly
        raise GhSignInError(f"The GitHub CLI did not answer: {exc}") from exc
    returncode = int(getattr(result, "returncode", 1))
    output = str(getattr(result, "stdout", "") or "").strip()
    checked = arguments[-1]
    if returncode != 0 or not output:
        raise GhSignInError(
            f"The GitHub CLI is not signed in to {checked}. Run gh auth login there first, "
            "or use Sign In with GitHub."
        )
    token = output.splitlines()[0].strip()
    if not _TOKEN_RE.fullmatch(token):
        raise GhSignInError("The GitHub CLI answered with something that is not a GitHub token.")
    return token

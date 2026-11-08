"""Clone Repository: ``git clone`` with the signed-in account's token (2026-11-08).

GitHub > Clone Repository... (and File > Open from Remote > Clone Repository...
in QUILL, File > Clone Repository... in QUILL Lite) asks for ``owner/name`` or a
URL and a folder, and runs ``git clone`` -- the user's own git, or a bundled
MinGit when one ships (:func:`quill.core.git_binaries.find_git`).

**The token.** A private repository needs the signed-in account's token, and
that token must never land anywhere it outlives the command: not in
``.git/config``, not in the remote URL (where ``git remote -v`` would print it
for ever), not on the command line (which any process on the machine can read,
and which the log records), and not in the log. So it travels in the child's
*environment*, as git's ``GIT_CONFIG_COUNT`` / ``GIT_CONFIG_KEY_n`` /
``GIT_CONFIG_VALUE_n`` trio, which sets ``http.<github>.extraheader`` for that
one process and is written nowhere. It is scoped to ``https://github.com/``, so
a submodule or redirect elsewhere never receives it. The token and the header
are remembered with :func:`quill.stability.redaction.remember_secret`, so any
line that ever quotes them is scrubbed, and git's own error text is scrubbed
again before anybody hears it.

``GIT_TERMINAL_PROMPT=0`` keeps git from waiting on a password prompt nobody can
see: without a token, a private repository fails at once with git's own
message, rather than hanging.

wx-free and strict-typed. The runner is injected (``run_subprocess_safely`` in
the app, a fake in the tests), as in :mod:`quill.core.local_git`.
"""

from __future__ import annotations

import base64
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from quill.core.error_codes import CodedError

__all__ = [
    "CLONE_TIMEOUT_SECONDS",
    "GIT_DOWNLOAD_URL",
    "CloneError",
    "CloneSource",
    "clone_command",
    "clone_environment",
    "clone_repository",
    "parse_clone_source",
    "target_folder",
]

#: Where Git for Windows comes from, offered when no git is found.
GIT_DOWNLOAD_URL = "https://git-scm.com/download/win"

#: A large repository over a slow line takes a while; ten minutes, then stop.
CLONE_TIMEOUT_SECONDS = 600.0

_GITHUB_PREFIX = "https://github.com/"
_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class CloneError(CodedError):
    """A clone could not start or did not finish. The message is safe to speak."""

    code = "QUILL-GITHUB-CLONE-FAILED"
    user_hint = "Check the repository name and your connection, then try again."


@dataclass(frozen=True, slots=True)
class CloneSource:
    """What to clone: the URL git is given, and the repository's own name."""

    url: str
    name: str
    #: ``owner/name`` when the repository is on github.com, else ``""``.
    full_name: str = ""

    @property
    def on_github(self) -> bool:
        return bool(self.full_name)


def parse_clone_source(text: str) -> CloneSource:
    """``owner/name``, a GitHub page or clone URL, or another https or ssh URL.

    Raises :class:`CloneError` with a sentence a person can act on.
    """
    raw = (text or "").strip()
    if not raw:
        raise CloneError("Type a repository as owner/name, or paste its address.")
    if raw.startswith("git@github.com:"):
        owner_name = raw.removeprefix("git@github.com:").removesuffix(".git").strip("/")
        return _github_source(owner_name, url=raw)
    if "://" not in raw:
        return _github_source(raw.removesuffix(".git").strip("/"))
    parts = urlsplit(raw)
    if parts.scheme not in {"https", "ssh"}:
        raise CloneError("Only https and ssh addresses can be cloned.")
    if parts.username or parts.password:
        # A user name or password in the address would be written into
        # .git/config for good, which is exactly what this module exists to avoid.
        raise CloneError("Paste the address without a user name or password in it.")
    host = (parts.hostname or "").lower()
    segments = [segment for segment in parts.path.split("/") if segment]
    if host in {"github.com", "www.github.com"} and parts.scheme == "https":
        if len(segments) < 2:
            raise CloneError("That GitHub address does not name a repository.")
        return _github_source(f"{segments[0]}/{segments[1].removesuffix('.git')}")
    if not segments:
        raise CloneError("That address does not name a repository.")
    name = segments[-1].removesuffix(".git")
    if not _NAME_RE.match(name):
        raise CloneError("That address does not name a repository.")
    return CloneSource(url=raw, name=name)


def _github_source(owner_name: str, *, url: str = "") -> CloneSource:
    owner, _, name = owner_name.partition("/")
    if not owner or not name or "/" in name or not (_NAME_RE.match(owner) and _NAME_RE.match(name)):
        raise CloneError("Type the repository as owner/name, for example octocat/hello-world.")
    full_name = f"{owner}/{name}"
    return CloneSource(
        url=url or f"{_GITHUB_PREFIX}{full_name}.git", name=name, full_name=full_name
    )


def target_folder(parent: Path | str, source: CloneSource) -> Path:
    """The folder the clone lands in: *parent* / the repository's name.

    Raises :class:`CloneError` when *parent* is not a folder or the target is a
    folder that already has something in it (git would refuse, less clearly).
    """
    base = Path(parent)
    if not base.is_dir():
        raise CloneError(f"The folder {base} does not exist.")
    target = base / source.name
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise CloneError(f"{target} already exists. Choose another folder.")
    return target


def clone_command(git: Path | str, source: CloneSource, target: Path | str) -> list[str]:
    """The argv: no shell, the URL after ``--`` so it can never read as an option."""
    return [str(git), "clone", "--", source.url, str(target)]


def _auth_header(token: str) -> str:
    """The header git sends: Basic, with GitHub's ``x-access-token`` user name."""
    pair = base64.b64encode(f"x-access-token:{token}".encode()).decode("ascii")
    return f"AUTHORIZATION: basic {pair}"


def clone_environment(
    token: str,
    source: CloneSource,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """The child's environment: *base* (default ``os.environ``) plus the token.

    The token goes in only for a github.com https clone, and only as the
    ``GIT_CONFIG_*`` entry after any the person already set, so their own
    environment settings still apply.
    """
    env = dict(os.environ if base is None else base)
    env["GIT_TERMINAL_PROMPT"] = "0"
    secret = (token or "").strip()
    if not secret or not source.on_github or not source.url.startswith(_GITHUB_PREFIX):
        return env
    from quill.stability.redaction import remember_secret

    header = _auth_header(secret)
    remember_secret(secret)
    remember_secret(header.split(" ", 2)[-1])
    try:
        index = max(0, int(env.get("GIT_CONFIG_COUNT", "0") or "0"))
    except ValueError:
        index = 0
    env[f"GIT_CONFIG_KEY_{index}"] = f"http.{_GITHUB_PREFIX}.extraheader"
    env[f"GIT_CONFIG_VALUE_{index}"] = header
    env["GIT_CONFIG_COUNT"] = str(index + 1)
    return env


def _scrub(text: str) -> str:
    from quill.stability.redaction import (
        redact_known_secrets,
        redact_source_tokens,
        redact_url_userinfo,
    )

    return redact_url_userinfo(redact_source_tokens(redact_known_secrets(text)))


def _git_said(stderr: str) -> str:
    """git's last meaningful line, scrubbed: ``fatal: repository not found``."""
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    meaningful = [line for line in lines if not line.lower().startswith("cloning into")]
    last = meaningful[-1] if meaningful else ""
    return _scrub(last.removeprefix("fatal: ").removeprefix("error: "))


def clone_repository(
    git: Path | str,
    source: CloneSource,
    target: Path | str,
    *,
    token: str,
    runner: Callable[..., Any],
    timeout_seconds: float = CLONE_TIMEOUT_SECONDS,
) -> Path:
    """Run the clone; return the new folder. Raises :class:`CloneError`.

    *runner* is called as ``runner(argv, cwd=..., timeout_seconds=..., env=...)``.
    """
    folder = Path(target)
    argv = clone_command(git, source, folder)
    env = clone_environment(token, source)
    try:
        result = runner(argv, cwd=str(folder.parent), timeout_seconds=timeout_seconds, env=env)
    except Exception as error:  # noqa: BLE001 - a timeout or a launch failure, said plainly
        name = type(error).__name__
        if name == "TimeoutExpired":
            raise CloneError(f"Cloning {source.name} took too long and was stopped.") from None
        raise CloneError(f"Git could not be started: {_scrub(str(error))}") from None
    if int(getattr(result, "returncode", 1)) != 0:
        said = _git_said(str(getattr(result, "stderr", "") or ""))
        detail = f" Git said: {said.rstrip('.')}." if said else ""
        raise CloneError(f"Could not clone {source.name}.{detail}")
    return folder

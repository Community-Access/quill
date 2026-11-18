"""Dry Run: every GitHub write stops at the door and says what it would have sent (PRD 22.8).

A switch for the whole GitHub Workbench. While it is on, each command still
asks its questions and shows its preview, exactly as it would, and then, at
the one moment it would change something on GitHub, :func:`stop_if_dry`
raises :class:`DryRunStop` with the sentence "Dry run: QUILL would ...
Nothing was changed." Reads are untouched, so lists, sheets and previews keep
working.

The switch is checked at the three doors every GitHub write goes through:
:func:`quill.core.github.rest_transport.request_json` (REST, and GraphQL
mutations, which it carries), the review window's own GraphQL transport, and
``GitHubItemsProvider._require_write_access`` (everything sent through
PyGithub). Local Git (worktrees, clone) does not touch GitHub and is not
stopped.

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping

from quill.core.error_codes import CodedError

__all__ = [
    "DRY_RUN",
    "DryRunStop",
    "describe_request",
    "is_mutation",
    "stop_if_dry",
    "stop_request_if_dry",
]


class DryRunStop(CodedError):
    """A write that Dry Run stopped before it was sent; the message is said as it is."""

    code = "QUILL-GITHUB-DRY-RUN"

    @property
    def sentence(self) -> str:
        return str(self.args[0]) if self.args else "Dry run: nothing was changed."


class _Switch:
    def __init__(self) -> None:
        self._on = False
        self._lock = threading.Lock()

    @property
    def on(self) -> bool:
        with self._lock:
            return self._on

    def set(self, on: bool) -> None:
        with self._lock:
            self._on = bool(on)


#: The one switch, shared by every GitHub door in this process.
DRY_RUN = _Switch()

_READS = frozenset({"GET", "HEAD", "OPTIONS"})


def is_mutation(query: str) -> bool:
    """Whether a GraphQL document changes something (``mutation``), not only reads."""
    stripped = "\n".join(
        line for line in query.splitlines() if not line.lstrip().startswith("#")
    ).lstrip()
    return stripped.startswith("mutation")


def _mutation_name(query: str) -> str:
    after = query.split("{", 2)
    body = after[1] if len(after) > 1 else ""
    name = body.strip().split("(", 1)[0].split()[0] if body.strip() else ""
    return name or "a change"


def describe_request(method: str, path: str, body: Mapping[str, object] | None = None) -> str:
    """ "send PATCH /repos/o/r/issues/7 (state, state_reason)", or the GraphQL mutation's name."""
    if path == "/graphql" and body is not None:
        query = str(body.get("query") or "")
        return f"ask GitHub for {_mutation_name(query)}"
    fields = f" ({', '.join(sorted(str(key) for key in body))})" if body else ""
    return f"send {method.upper()} {path}{fields}"


def stop_if_dry(what: str) -> None:
    """Raise :class:`DryRunStop` naming *what* when Dry Run is on; otherwise nothing."""
    if DRY_RUN.on:
        raise DryRunStop(f"Dry run: QUILL would {what}. Nothing was changed.")


def stop_request_if_dry(method: str, path: str, body: Mapping[str, object] | None) -> None:
    """The REST door: a write method, or a GraphQL mutation, stops while Dry Run is on."""
    if not DRY_RUN.on:
        return
    if path == "/graphql":
        if body is not None and is_mutation(str(body.get("query") or "")):
            stop_if_dry(describe_request(method, path, body))
        return
    if method.upper() not in _READS:
        stop_if_dry(describe_request(method, path, body))

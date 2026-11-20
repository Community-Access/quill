"""Every page of a GitHub list, stoppable, with the count said once at the end (GX11).

GitHub sends a list a page at a time (at most 100 rows) and names the next
page in the ``Link`` header, as a cursor (``after=``) for the organization
alert lists and as a page number elsewhere. :func:`read_every_page` follows
that link until there is none, so a count over the list is a count over all
of it, never over its first hundred.

* **Stoppable.** :class:`Paging` carries a ``should_cancel`` the caller's
  Cancel button sets; it is asked before every page, and a stop raises
  :class:`PagingStopped` with how far it got. A part of a count is never
  handed back as if it were the whole.
* **Quiet until the end.** ``progress`` is for a visual gauge only. The
  number of rows and pages is in :class:`Paging` afterwards, for the one
  sentence the caller says when it is done.
* **Only GitHub's own host.** A ``next`` link to anywhere but
  ``https://api.github.com`` is not followed, so the token never goes
  elsewhere (the transport would refuse it too).

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from quill.core.error_codes import CodedError

__all__ = ["Paging", "PagingStopped", "next_page", "read_every_page"]

_API_HOST = "api.github.com"
_NEXT = re.compile(r'<([^>]+)>\s*;\s*rel="?next"?')


def _never() -> bool:
    return False


def _ignore(_rows: int) -> None:
    return None


@dataclass
class Paging:
    """How a long read is stopped and how far it got."""

    should_cancel: Callable[[], bool] = field(default=_never)
    progress: Callable[[int], None] = field(default=_ignore)  # rows so far; a gauge, not speech
    pages: int = 0
    rows: int = 0


class PagingStopped(CodedError):
    """The person stopped a long read; ``rows`` and ``pages`` say how far it got."""

    code = "QUILL-GITHUB-PAGING-STOPPED"

    def __init__(self, rows: int, pages: int) -> None:
        super().__init__(f"Stopped after {rows} {'row' if rows == 1 else 'rows'}.")
        self.rows = rows
        self.pages = pages


def next_page(link: str) -> tuple[str, dict[str, str]] | None:
    """The ``rel="next"`` page as ``(path, query)``, or None when there is none.

    Only a link on ``https://api.github.com`` is followed.
    """
    for part in (link or "").split(","):
        found = _NEXT.search(part)
        if found is None:
            continue
        target = urlsplit(found.group(1))
        if target.scheme != "https" or target.hostname != _API_HOST or not target.path:
            return None
        return target.path, dict(parse_qsl(target.query))
    return None


def _header(response: Any, name: str) -> str:
    getter = getattr(response, "header", None)
    if callable(getter):
        return str(getter(name) or "")
    return ""


def read_every_page(
    api: Any, path: str, query: Mapping[str, str], paging: Paging | None = None
) -> list[Any]:
    """Every row of the list at *path*, following GitHub's ``next`` links.

    GitHub's refusal (``GitHubRestError``) is raised as it came; a stop
    raises :class:`PagingStopped`.
    """
    state = paging if paging is not None else Paging()
    rows: list[Any] = []
    where, asked = path, dict(query)
    while True:
        if state.should_cancel():
            raise PagingStopped(state.rows, state.pages)
        response = api.rest("GET", where, query=asked)
        data = getattr(response, "data", None)
        page = data if isinstance(data, list) else []
        rows.extend(page)
        state.pages += 1
        state.rows += len(page)
        state.progress(state.rows)
        following = next_page(_header(response, "Link"))
        if following is None or not page:
            return rows
        where, asked = following

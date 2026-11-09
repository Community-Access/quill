"""Layer 4 in the editors: language servers behind the keys you already use.

Shared by QUILL and QUILL Lite. The servers are :mod:`quill.core.lsp`; this
module is when they are asked and what is said. Nothing here starts a server
at launch, and nothing waits for one on the UI thread: every request runs
through the editor's background runner (``_suggest_in_background``) and comes
back through it.

What a listener gets:

* **Ctrl+.** in a file a server serves: the server's completions first, each
  with its kind, then the file's own names and the project's (layers 1 and 2)
  to fill the list. The first press in a project starts the server in the
  background and answers from layers 1 and 2 at once; once the server is
  running, the list waits for it (at most three seconds) and falls back to
  layers 1 and 2 when it has nothing.
* **Check This File** and the Problems pane: the server's problems beside the
  built-in checkers' and the outside tools'.
* **Quick Fix** on a Problems pane row: the server's fixes for that problem,
  as a list; Enter applies one, as one undo step.
* **Parameter Hints** (Edit menu): inside a call's brackets, "Parameter 2 of
  3, seconds", then the signature. With Parameter Hints As You Type on (off by
  default), typing an opening bracket or a comma says it too.

Every part has its own switch, and each server has its own: the Language
Servers window (Tools) sets them, and the settings are shared by name between
the two editors.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.lsp.pool import shared_pool
from quill.core.lsp.servers import (
    LANGUAGE_SERVERS,
    resolve_server,
    server_for_path,
    server_present,
)
from quill.core.problems.model import Problem
from quill.core.project_names import project_root_for
from quill.core.text_units import text_index

__all__ = [
    "FEATURE_SETTINGS",
    "LanguageServerMixin",
    "server_status",
]

#: The per-feature switches: ``(setting, label, help)``. All default to on
#: except Parameter Hints As You Type, which speaks while you type.
FEATURE_SETTINGS: tuple[tuple[str, str, str], ...] = (
    (
        "language_server_completions",
        "Suggestions from language servers",
        "Word Prediction (Ctrl+.) asks the language server for the file's language first.",
    ),
    (
        "language_server_problems",
        "Problems from language servers",
        "Check This File and the Problems pane include the language server's problems.",
    ),
    (
        "parameter_hints_as_you_type",
        "Parameter hints as you type",
        "Typing an opening bracket or a comma inside a call says which parameter you are on.",
    ),
)

#: How long, after the last use, a server is left running.
IDLE_STOP_SECONDS = 15 * 60


def server_status(spec: Any) -> str:
    """ "bundled", "installed" or "not found", as the Language Servers window says it."""
    if resolve_server(spec) is None:
        return "not found"
    return "bundled with QUILL" if spec.origin == "bundled" else "installed on this computer"


class LanguageServerMixin:
    """The language-server parts of both editors. Hooks: ``_ls_settings`` below."""

    _ls_last_used: float = 0.0

    # -- switches ------------------------------------------------------------- #

    def _ls_settings(self) -> Any:
        """The settings object holding the language-server switches."""
        raise NotImplementedError

    def _ls_wanted(self, path: Any, feature: str) -> bool:
        """True when *feature* is on and a server for *path* is on and present."""
        settings = self._ls_settings()
        if not getattr(settings, "language_servers_enabled", True):
            return False
        if not getattr(settings, feature, feature != "parameter_hints_as_you_type"):
            return False
        spec = server_for_path(path)
        if spec is None or spec.name in set(getattr(settings, "language_servers_off", []) or []):
            return False
        return server_present(spec)

    def _ls_root(self, path: Any) -> Path | None:
        return project_root_for(path) if path is not None else None

    # -- completions ------------------------------------------------------------ #

    def _ls_completions_ready(self, path: Any) -> bool:
        """True when a running server can answer Ctrl+. now; otherwise warm one up."""
        if path is None or not self._ls_wanted(path, "language_server_completions"):
            return False
        root = self._ls_root(path)
        spec = server_for_path(path)
        pool = shared_pool()
        if spec is not None and spec.name in pool.running():
            return True
        if root is not None:
            # The first press in a project starts the server for the next one.
            self._ls_background(lambda: pool.client_for(Path(path), root), lambda _client: None)
        return False

    def _ls_request_completions(
        self,
        path: Any,
        text: str,
        offset: int,
        fragment: str,
        done: Callable[[list[Any]], None],
    ) -> bool:
        root = self._ls_root(path)
        if root is None:
            return False
        pool = shared_pool()
        self._ls_last_used = time.monotonic()
        return self._ls_background(
            lambda: pool.complete(Path(path), root, text, offset, fragment), done
        )

    # -- problems --------------------------------------------------------------- #

    def _ls_problems_for(self, path: Any, text: str) -> list[Problem] | None:
        """The server's problems for *text*; meant for a background check."""
        if path is None or not self._ls_wanted(path, "language_server_problems"):
            return None
        root = self._ls_root(path)
        if root is None:
            return None
        self._ls_last_used = time.monotonic()
        return shared_pool().problems(Path(path), root, text)

    def _ls_serves(self, path: Any) -> bool:
        return path is not None and self._ls_wanted(path, "language_server_problems")

    # -- Quick Fix ---------------------------------------------------------------- #

    def _ls_quick_fixes(
        self, path: Any, text: str, problem: Problem, done: Callable[[list[Any]], None]
    ) -> bool:
        root = self._ls_root(path)
        if root is None or path is None:
            return False
        pool = shared_pool()
        return self._ls_background(lambda: pool.fixes(Path(path), root, text, problem), done)

    # -- parameter hints ------------------------------------------------------------ #

    def _ls_parameter_hints(self, *, quiet: bool = False) -> None:
        """Edit > Parameter Hints: which parameter the caret is on, said."""
        path = self._suggest_path()  # type: ignore[attr-defined]
        if path is None or not self._ls_wanted(path, "language_server_completions"):
            if not quiet:
                self._suggest_say("No parameter hints: no language server for this file")  # type: ignore[attr-defined]
            return
        root = self._ls_root(path)
        text = self._suggest_text()  # type: ignore[attr-defined]
        # The server's offsets are code points; the control's are UTF-16 units.
        offset = text_index(text, self._suggest_caret())  # type: ignore[attr-defined]
        pool = shared_pool()

        def done(sentence: str) -> None:
            if not self._suggest_window_alive():  # type: ignore[attr-defined]
                return  # the window closed while the server answered (Lite 3)
            if sentence:
                self._suggest_announce(sentence)  # type: ignore[attr-defined]
            elif not quiet:
                self._suggest_say("No parameter hints here")  # type: ignore[attr-defined]

        self._ls_background(lambda: pool.signature(Path(path), root, text, offset), done)

    def _ls_after_char(self) -> None:
        """After a key reached the text: the character before the caret decides.

        Only that character is read, and only once the setting and a server
        say a hint could follow: QUILL calls this after every pause in
        typing, and reading the whole text each time was the cost (review
        2026-11-09, QUILL 9).
        """
        path = self._suggest_path()  # type: ignore[attr-defined]
        if path is None or not self._ls_wanted(path, "parameter_hints_as_you_type"):
            return
        self._ls_typed(self._suggest_char_before_caret())  # type: ignore[attr-defined]

    def _ls_typed(self, character: str) -> None:
        """After a key reached the text: speak a hint on "(" or "," if asked to."""
        if not character or character not in "(,":
            return
        path = self._suggest_path()  # type: ignore[attr-defined]
        if path is None or not self._ls_wanted(path, "parameter_hints_as_you_type"):
            return
        self._ls_parameter_hints(quiet=True)

    # -- background ------------------------------------------------------------------ #

    def _ls_background(self, work: Callable[[], Any], done: Callable[[Any], None]) -> bool:
        runner = getattr(self, "_suggest_in_background", None)
        return bool(runner(work, done)) if callable(runner) else False


def server_names() -> tuple[str, ...]:
    """Every allowlisted server, in the order the window lists them."""
    return tuple(spec.name for spec in LANGUAGE_SERVERS)

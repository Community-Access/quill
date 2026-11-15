"""Watches in the GitHub Workbench (PRD 22.5): the node, its commands and its timer.

The ``watches`` node lists this account's watches
(:mod:`quill.core.github.watches`), each row saying its rule, whether it is
paused and when it was last checked ("checked 3 minutes ago"). Ctrl+N there
adds one, Enter edits it, Delete removes it, and its context menu pauses or
resumes it and checks every watch now.

While the Workbench is open a one-minute timer asks whether a round is due,
on the GitHub notification check's own interval from Workbench Options
(:func:`quill.core.github.workbench_prefs.github_monitor_policy`), and only
after the GitHub network consent and while signed in. A round runs off the UI
thread; what it finds is said through the window, so it is spoken and
brailled and F9 says it again. It reads runs, reviews, releases and comments
only: the notifications inbox is never read or marked by a watch.

Adding, editing, pausing and removing change only this device's list
(``local``, organizing tier); nothing is written to GitHub.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = [
    "WATCH_PREFIX",
    "WATCH_REASONS",
    "WATCH_VERBS",
    "GitHubWorkbenchWatchesMixin",
    "watch_rows",
]

WATCH_PREFIX = "watches:"
_TIMER_MS = 60_000

#: Workbench verbs for watches, and the row kinds each needs ("view": anywhere).
WATCH_VERBS: dict[str, frozenset[str]] = {
    "add_watch": frozenset({"view"}),
    "check_watches": frozenset({"view"}),
    "edit_watch": frozenset({"watch"}),
    "pause_watch": frozenset({"watch"}),
    "remove_watch": frozenset({"watch"}),
}

WATCH_REASONS: dict[str, str] = {
    "check_watches": "Sign in to GitHub first: Account, Manage GitHub Accounts.",
}

_KIND_ORDER = ("run", "review", "release", "comment")
_PROMPTS = {
    "run": "Repository, and a branch after a space if you want only that branch "
    "(owner/name or owner/name main):",
    "review": "The pull request, as owner/name#42 or its link:",
    "release": "The repository, as owner/name or its link:",
    "comment": "The issue or pull request, as owner/name#42 or its link:",
}


def _store(items: Any) -> Any:
    from quill.core.github.navigation_state import account_key_for_token
    from quill.core.github.watches import WatchStore

    return WatchStore.load(account_key_for_token(getattr(items, "token", None)))


def watch_rows(store: Any, now: float | None = None) -> list[ExploreRow]:
    """The node's rows: one Explore row per watch, keyed by its id."""
    return [
        ExploreRow(
            watch.label(now),
            watch.detail(now),
            watch.url(),
            watch.repository,
            "watch",
            watch.id,
            "",
            watch.describe(),
        )
        for watch in store.watches
    ]


def _target_text(watch: Any) -> str:
    if watch.kind in ("review", "comment"):
        return f"{watch.repository}#{watch.number}"
    return f"{watch.repository} {watch.branch}".strip()


class GitHubWorkbenchWatchesMixin:
    """Loading the watches node, its five commands and the round timer."""

    items: Any
    frame: Any
    local_note: str
    signed_in: bool
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    github_api: Callable[[], Any]
    _current_repository: Callable[[], str]
    _watch_timer: Any = None
    _watching: bool = False

    # -- the node ------------------------------------------------------------------

    def load_watches(self) -> list[object]:
        from quill.core.github.workbench_prefs import github_monitor_policy

        store = _store(self.items)
        minutes = github_monitor_policy().poll_interval_minutes
        active = sum(not w.paused for w in store.watches)
        self.local_note = (
            f"{len(store.watches)} watches, {active} active. Checked every {minutes} "
            "minutes while this window is open. Ctrl+N adds one."
        )
        return list(watch_rows(store))

    # -- the commands --------------------------------------------------------------

    def _watch_target(self, kind: str, value: str) -> tuple[str, str, int] | None:
        from quill.core.github.watches import parse_target

        while True:
            text = self._ask_text("Watch", _PROMPTS[kind], value=value)
            if not text:
                return None
            try:
                return parse_target(kind, text)
            except ValueError as exc:
                self._say(str(exc))
                value = text

    def _do_add_watch(self, _ref: Any, _row: object) -> None:
        from quill.core.github.watches import KINDS

        index = self._choose("Add Watch", "Tell me when:", [KINDS[kind] for kind in _KIND_ORDER])
        if index < 0:
            return
        kind = _KIND_ORDER[index]
        target = self._watch_target(kind, self._current_repository())
        if target is None:
            return
        store = _store(self.items)
        watch = store.add(kind, *target)
        store.save()
        self._say(f"Watching: {watch.describe()}. The first check learns what is there now.")
        self._reload_if_watches()

    def _picked_watch(self, row: object) -> tuple[Any, Any] | None:
        store = _store(self.items)
        watch = store.find(row.key) if isinstance(row, ExploreRow) else None
        if watch is None:
            self._say("That watch is no longer in the list.")
            self._reload_if_watches()
            return None
        return store, watch

    def _do_edit_watch(self, _ref: Any, row: object) -> None:
        from dataclasses import replace

        found = self._picked_watch(row)
        if found is None:
            return
        store, watch = found
        target = self._watch_target(watch.kind, _target_text(watch))
        if target is None:
            return
        repository, branch, number = target
        if (repository, branch, number) == (watch.repository, watch.branch, watch.number):
            return
        # A new target starts afresh: its first check learns, it does not announce history.
        store.replace(
            replace(
                watch,
                repository=repository,
                branch=branch,
                number=number,
                primed=False,
                seen=(),
                last_checked=0.0,
                last_result="",
            )
        )
        store.save()
        self._say(f"Watch changed: {store.find(watch.id).describe()}.")
        self._reload_if_watches()

    def _do_pause_watch(self, _ref: Any, row: object) -> None:
        from dataclasses import replace

        found = self._picked_watch(row)
        if found is None:
            return
        store, watch = found
        store.replace(replace(watch, paused=not watch.paused))
        store.save()
        self._say(f"{'Resumed' if watch.paused else 'Paused'}: {watch.describe()}.")
        self._reload_if_watches()

    def _do_remove_watch(self, _ref: Any, row: object) -> None:
        found = self._picked_watch(row)
        if found is None:
            return
        store, watch = found
        store.remove(watch.id)
        store.save()
        self._say(f"Watch removed: {watch.describe()}.")
        self._reload_if_watches()

    def _fits_check_watches(self, _row: object) -> bool:
        return bool(self.signed_in)

    def _do_check_watches(self, _ref: Any, _row: object) -> None:
        self.run_watch_round(forced=True)

    # -- the round -----------------------------------------------------------------

    def _reload_if_watches(self) -> None:
        current = self.frame.current if self.frame is not None else None
        if current is not None and current.key == "watches":
            self.frame.reload()

    def watch_round_blocked(self) -> str:
        """Why no round may run now, or "" when one may."""
        from quill.core.github.consent import load_github_consent_complete

        if not self.signed_in:
            return "Sign in to GitHub first: Account, Manage GitHub Accounts."
        if not load_github_consent_complete():
            return "GitHub network access has not been allowed yet; open GitHub from the editor."
        return ""

    def run_watch_round(self, *, forced: bool = False) -> bool:
        """One round, when due (or *forced*); True when one started."""
        from quill.core.github.watches import check_round, due
        from quill.core.github.workbench_prefs import github_monitor_policy

        blocked = self.watch_round_blocked()
        if blocked:
            if forced:
                self._say(blocked)
            return False
        if self._watching or self.frame is None:
            return False
        store = _store(self.items)
        active = sum(not w.paused for w in store.watches)
        if forced and not active:
            self._say("There are no active watches. Ctrl+N in Watches adds one.")
            return False
        if not forced and not due(store, github_monitor_policy().poll_interval_minutes):
            return False
        api = self.github_api()
        self._watching = True

        def work() -> list[str]:
            said = check_round(api, store)
            store.save()
            return said

        def done(said: list[str]) -> None:
            self._watching = False
            for sentence in said:
                self._say(sentence)
            if forced and not said:
                self._say(f"Checked {active} watches. Nothing new.")
            self._reload_if_watches()

        def failed(error: BaseException) -> None:
            self._watching = False
            if forced:
                self._say(f"Could not check watches: {error}")

        self.frame._run_background("Workbench Watches", work, done, failed)
        return True

    def start_watch_timer(self) -> None:
        """The one-minute timer that asks whether a round is due, owned by the window."""
        frame = self.frame
        if frame is None or self._watch_timer is not None:
            return
        wx = frame._wx
        timer = wx.Timer(frame.frame)
        frame.frame.Bind(wx.EVT_TIMER, lambda _event: self.run_watch_round(), timer)
        timer.Start(_TIMER_MS)
        self._watch_timer = timer

    def stop_watch_timer(self) -> None:
        timer, self._watch_timer = self._watch_timer, None
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - the window may already be gone
                pass

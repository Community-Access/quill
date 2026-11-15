"""One check for every write, and one history entry for every change (how.md review 1 and 3).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.

- **Every write is checked.** :meth:`unlisted_refusal` answers for a command
  that is not on the selected row's own context menu: the menu bar's Empty
  Spam and imports, a node's New Here, Delete on a person. Its tier comes from
  :func:`quill.core.wordpress.workbench_tiers.tier_of`, and the sites it
  touches from the row, the node or, on an Across Sites row, every site the
  row names. Workbench Access, Safe Mode and View As Role then refuse it in
  the same sentence a context-menu row gets. :meth:`access_refusal` is the
  same check for a write sent from outside a command (the REST Console).
- **Every change is in Change History.** Each site's client is wrapped
  (:class:`_WriteWatch`) so a background task notes when it sent a change. A
  task of a writing command that sent one and recorded nothing records
  "cannot be undone" itself, so Ctrl+Z never reaches past it to an older,
  unrelated change on another site. A reading command (tier 0) records
  nothing, whatever it sends: some reads are POSTs.
- **The tier is known while a command runs**, through its background tasks
  too, so :func:`quill.ui.wordpress_workbench_dialogs.ask_preview` can start
  on Cancel for a destructive one.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.workbench_permissions import tier_allowed
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_tiers import tier_of
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.core.workbench.menus import all_rows
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["Running", "WorkbenchGuard"]

_LOCAL = threading.local()
_WRITES = frozenset({"post", "delete", "upload", "batch"})
_READS = frozenset({"GET", "HEAD", "OPTIONS"})


def _noted() -> None:
    marks = getattr(_LOCAL, "marks", None)
    if marks is not None:
        marks["wrote"] = True


class _WriteWatch:
    """A site's client that notes, for the task sending it, each change it sends."""

    __slots__ = ("_api",)

    def __init__(self, api: Any) -> None:
        object.__setattr__(self, "_api", api)

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._api, name)
        if name == "request" and callable(value):

            def request(method: str, *args: Any, **kwargs: Any) -> Any:
                if str(method).upper() not in _READS:
                    _noted()
                return value(method, *args, **kwargs)

            return request
        if name in _WRITES and callable(value):

            def write(*args: Any, **kwargs: Any) -> Any:
                _noted()
                return value(*args, **kwargs)

            return write
        return value

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._api, name, value)

    def __repr__(self) -> str:
        return repr(self._api)


def watch_writes(api: Any) -> Any:
    return api if isinstance(api, _WriteWatch) else _WriteWatch(api)


@dataclass(frozen=True)
class Running:
    """The command a task belongs to: its label, its tier and the site it started on."""

    command_id: str
    label: str
    tier: Tier
    site: str


class WorkbenchGuard:
    """Tier checks for commands off the row's menu, and a history entry for every write."""

    actions: Any
    menu: Any
    history: Any
    safe_mode: bool
    access_for: Callable[[str], Any]
    _access_sentence: Callable[[str], str]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    _running: Running | None = None

    # -- the check ----------------------------------------------------------------

    def access_refusal(self, site: str, tier: Tier) -> str:
        """Why a *tier* change on *site* is refused by Workbench access ("" when it is not)."""
        if tier_allowed(tier, self.access_for(site)):
            return ""
        return self._access_sentence(site)

    def unlisted_refusal(self, command_id: str, row: WbRow | None, ref: Any) -> str:
        """Why *command_id*, not on *row*'s own menu, may not run ("" when it may)."""
        tier = tier_of(command_id, self.actions)
        if tier is None or tier <= Tier.READ:
            return ""
        sites = self._sites_touched(row, ref)
        if not sites and self.safe_mode:
            return "Safe Mode is on, so the Workbench only reads."
        for site in sites:
            said = self.access_refusal(site, tier)
            if said:
                return said
        return ""

    def _sites_touched(self, row: WbRow | None, ref: Any) -> list[str]:
        if row is not None and row.site:
            return [row.site]
        if row is not None and row.raw:
            named = [*(row.raw.get("objects") or {}), *(row.raw.get("missing") or [])]
            if named:
                return list(dict.fromkeys(str(site) for site in named))
        site = self.site_of(ref) if ref is not None else ""
        site = site or self.current_site()
        return [site] if site else []

    # -- what is running ------------------------------------------------------------

    def label_for(self, command_id: str) -> str:
        """The words a menu or a context menu gives *command_id*, without the access key."""
        found = next((r.label for _m, r in all_rows(self.menu) if r.command_id == command_id), "")
        for kind in () if found else self.actions.row_types_offering(command_id):
            found = next(r.label for r in self.actions.rows_for(kind) if r.command_id == command_id)
            break
        verb = command_id.rsplit(".", 1)[-1].replace("_", " ")
        return (found or verb.capitalize()).replace("&", "").removesuffix("...")

    def running_for(self, command_id: str, label: str, site: str) -> Running:
        return Running(command_id, label, tier_of(command_id, self.actions) or Tier.READ, site)

    @contextmanager
    def running(self, command: Running | None) -> Iterator[None]:
        """While *command* runs (or a task of it finishes), its tier is the preview's."""
        before = self._running
        self._running = command
        wdlg.set_running_tier(command.tier if command is not None else None)
        try:
            yield
        finally:
            self._running = before
            wdlg.set_running_tier(before.tier if before is not None else None)

    def watched(
        self, work: Callable[[], Any], done: Callable[[Any], None]
    ) -> tuple[Callable[[], Any], Callable[[Any], None], Callable[[], None]]:
        """*work* and *done* that note a change sent and record it if nothing else did.

        The third callable is for a task that failed: a change sent before the
        failure is recorded all the same.
        """
        command = self._running
        marks = {"wrote": False}
        before = self.history.recorded

        def work_watched() -> Any:
            earlier = getattr(_LOCAL, "marks", None)
            _LOCAL.marks = marks
            try:
                return work()
            finally:
                _LOCAL.marks = earlier

        def settle() -> None:
            if command is None or command.tier < Tier.ORGANIZE or not marks["wrote"]:
                return
            if self.history.recorded != before:
                return
            where = f" on {command.site}" if command.site else ""
            name = command.label or "A change"
            self.history.record(Change(command.site, f"{name}{where}.", undo=None))

        def done_watched(result: Any) -> None:
            with self.running(command):
                done(result)
            settle()

        return work_watched, done_watched, settle

"""A file worker asks the UI for current permission, even after a pool backlog."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from time import monotonic, perf_counter
from typing import Any

from quill.core.podcasts.storage_maintenance import (
    Deletion,
    DownloadTarget,
    delete_files,
    path_key,
)
from quill.ui.podcasts.storage_snapshot import (
    ITEMS_PER_TURN,
    TURN_BUDGET_SECONDS,
    generation,
    owner_alive,
)
from quill.ui.surface_lifetime import lifetime_for

logger = logging.getLogger(__name__)


class DeletionGate:
    def __init__(
        self,
        host: Any,
        targets: tuple[DownloadTarget, ...],
        authorize: Callable[[DeletionGate], None],
    ) -> None:
        self.host = host
        self.targets = targets
        self.authorize = authorize
        self.lifetime = getattr(host, "_cast_ui_lifetime", None) or lifetime_for(host.frame)
        self.dispatch = getattr(host._wx, "CallAfter", None)
        self.ready = threading.Event()
        self.cancelled = threading.Event()
        self.finished = threading.Event()
        self.approved: tuple[DownloadTarget, ...] = ()
        self.error: BaseException | None = None
        self.revision: object = None
        self.later: Any = None
        self.check: Callable[[], Iterator[bool]] | None = None
        self.checks: Iterator[bool] | None = None

    def cancel(self) -> None:
        self.cancelled.set()
        self.ready.set()
        if self.later is not None:
            self.later.Stop()
            self.later = None

    def fail(self, error: BaseException) -> None:
        logger.error("Could not authorize podcast file removal", exc_info=error)
        self.error = error
        self.ready.set()

    def allow(
        self, targets: tuple[DownloadTarget, ...], check: Callable[[], Iterator[bool]]
    ) -> None:
        if self.cancelled.is_set() or not owner_alive(self.host):
            self.cancel()
            return
        self.approved = targets
        self.revision = generation(self.host)
        self.check = check
        self._watch()
        self.ready.set()

    def _watch(self) -> None:
        self.later = None
        if self.finished.is_set() or self.cancelled.is_set():
            return
        if not owner_alive(self.host) or generation(self.host) != self.revision:
            self.cancel()
            return
        if self.checks is None:
            if self.check is None:
                self.fail(RuntimeError("Podcast removal has no permission checks"))
                self.cancel()
                return
            self.checks = self.check()
        deadline = perf_counter() + TURN_BUDGET_SECONDS
        for index in range(ITEMS_PER_TURN):
            if index and perf_counter() >= deadline:
                break
            try:
                safe = next(self.checks)
            except StopIteration:
                self.checks = None
                break
            except Exception as error:
                self.fail(error)
                self.cancel()
                return
            if not safe:
                self.cancel()
                return
        later = getattr(self.host._wx, "CallLater", None)
        if callable(later):
            self.later = later(1, self._watch)
        elif callable(self.dispatch):
            self.dispatch(self._watch)

    def perform(self) -> tuple[Deletion, ...]:
        """Worker-side: no live model/window reads, just dispatch and event tokens."""
        try:
            if not callable(self.dispatch):
                raise RuntimeError("File removal needs a UI authorization dispatcher")
            self.dispatch(self.authorize, self)
            deadline = monotonic() + 60
            while not self.ready.wait(0.05):
                if not self.lifetime.is_alive:
                    self.cancelled.set()
                    return tuple(Deletion(target, "changed") for target in self.targets)
                if monotonic() >= deadline:
                    raise TimeoutError("The UI did not authorize podcast file removal")
            if self.error is not None:
                raise self.error
            approved = {path_key(target.path) for target in self.approved}
            results = delete_files(self.approved, cancelled=self.cancelled.is_set)
            return results + tuple(
                Deletion(target, "changed")
                for target in self.targets
                if path_key(target.path) not in approved
            )
        finally:
            self.finished.set()

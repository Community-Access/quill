"""Never lose a word: autosaves, unconfirmed sends and the offline queue (wordpress.md 5.10, 9.3).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands` (through
:class:`~quill.ui.wordpress_page_commands.WordPressPageCommands`), shared by
QUILL and QUILL Lite.

One repeating timer from the host (``start_repeating``) drives two jobs, every
two minutes, from the moment a WordPress document is first opened or started
in a window until that window closes (the timer belongs to the window):

* **Autosave.** When the WordPress document in front has changed since the
  last autosave, its text goes into the local working copy and, once it is on
  the site, into the account's autosave (``/<type>/<id>/autosaves``) -- what
  the block editor itself does. Silent when it works; one spoken line the first
  time it does not, and not again until one has worked.
* **The queue.** A send that could not reach the site waits in
  :class:`~quill.core.wordpress.offline.OfflineQueue` and is tried again. Every
  retry runs the same conflict check as Publish from the menu, and a new item
  is first looked for on the site, so nothing is published over a newer change
  and nothing is created twice.

A send that fails on the way (a time-out, a lost connection) may still have
arrived, so before Try Again is offered the site is re-read (5.10).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import offline as off
from quill.core.wordpress import schedule as sch
from quill.core.wordpress import site as wp
from quill.core.wordpress.api import WordPressApiError
from quill.ui import wordpress_dialogs as dlg

_log = logging.getLogger(__name__)

#: How often the autosave and the queue run (wordpress.md 9.3: every two minutes).
REPEAT_SECONDS = 120


@dataclass
class _Watch:
    stop: Callable[[], None] | None = None
    autosaved: dict[str, str] = field(default_factory=dict)
    autosaving: bool = False
    autosave_failed: bool = False
    retrying: bool = False


def _now_gmt() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def _failure(exc: BaseException) -> str:
    from quill.ui.wordpress_commands import failure_sentence

    return failure_sentence(exc)


class WordPressOfflineCommands:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # the timer

    def _watch(self) -> _Watch:
        state = getattr(self, "_watch_state", None)
        if state is None:
            state = _Watch()
            self._watch_state = state
        return state

    def watch_documents(self) -> None:
        """Start the two-minute autosave and queue timer, once per window."""
        state = self._watch()
        if state.stop is not None:
            return
        start = getattr(self.host, "start_repeating", None)
        if start is None:
            return
        state.stop = start(REPEAT_SECONDS, self.tick)

    def stop_watching(self) -> None:
        state = self._watch()
        if state.stop is not None:
            state.stop()
            state.stop = None

    def tick(self) -> None:
        # A timer handler that raises would surface as a crash report every two
        # minutes; a missed autosave is logged and the next tick tries again.
        for job in (self.autosave_now, self.retry_queue):
            try:
                job()
            except Exception:  # noqa: BLE001
                _log.exception("WordPress %s failed", job.__name__)

    # ------------------------------------------------------------------ #
    # autosaves (9.3)

    def autosave_now(self) -> None:
        state = self._watch()
        if state.autosaving:
            return
        copy = self.local.copy_for_path(self.host.current_path())
        if copy is None:
            return
        text = self.host.current_text()
        if text == state.autosaved.get(copy.key, copy.text):
            return
        copy.text = text
        self.local.save(copy)  # the working copy beside the file; the file is Save's
        state.autosaved[copy.key] = text
        if not copy.remote_id:
            return
        profile = self.sites().get(copy.site_id)  # type: ignore[attr-defined]
        if profile is None:
            return
        item = wp.Item(
            id=copy.remote_id,
            kind=copy.kind,
            title=copy.title,
            content=self.to_html(copy)[0],  # type: ignore[attr-defined]
            status=copy.status,
            excerpt=str(copy.properties.get("excerpt", "")),
        )
        api = self.api(profile)  # type: ignore[attr-defined]

        def saved(_result: object) -> None:
            state.autosaving = False
            state.autosave_failed = False

        def failed(exc: BaseException) -> None:
            state.autosaving = False
            if state.autosave_failed:
                return
            state.autosave_failed = True
            self.host.announce(
                f"QUILL could not keep an autosave on {profile.name}. {_failure(exc)} "
                "Your text is still kept on this computer."
            )

        state.autosaving = True
        self.host.run_task(
            f"WordPress: autosave to {profile.name}",
            lambda: wp.save_autosave(api, item),
            saved,
            failed,
        )

    # ------------------------------------------------------------------ #
    # sends that never got an answer (5.10)

    def send_in_background(
        self,
        copy: lc.WorkingCopy,
        profile: Any,
        publish: bool,
        work: Callable[[], Any],
        done: Callable[[Any], None],
    ) -> None:
        """Run a send; a failure on the way re-reads the site before anything else."""
        since = _now_gmt()

        def failed(exc: BaseException) -> None:
            if off.is_unreachable(exc):
                self._unconfirmed(copy, profile, publish, since)
                return
            self.host.announce(_failure(exc))

        self.host.run_task(f"WordPress: sending to {profile.name}", work, done, failed)

    def _unconfirmed(self, copy: lc.WorkingCopy, profile: Any, publish: bool, since: str) -> None:
        api = self.api(profile)  # type: ignore[attr-defined]
        html = self.to_html(copy)[0]  # type: ignore[attr-defined]

        def work() -> wp.Item | None:
            return sch.find_landed(
                api,
                kind=copy.kind,
                title=copy.title,
                slug=str(copy.properties.get("slug", "")),
                since_gmt=since,
                item_id=copy.remote_id,
                content=html if copy.remote_id else "",
            )

        def done(found: wp.Item | None) -> None:
            if found is not None:
                self._sent(copy, profile, found)  # type: ignore[attr-defined]
                return
            if dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Not Sent",
                message=(
                    f"'{copy.title or 'untitled'}' did not reach {profile.name}. QUILL checked "
                    "the site and nothing was changed there. Your copy is kept on this computer. "
                    "Try again now?"
                ),
                yes_label="Try Again",
            ):
                self.send_copy(copy, profile, publish)

        def failed(exc: BaseException) -> None:
            if off.is_unreachable(exc):
                self.queue_send(copy, profile, publish, since)
                return
            self.host.announce(_failure(exc))

        self.host.run_task(f"WordPress: checking {profile.name}", work, done, failed)

    def send_copy(self, copy: lc.WorkingCopy, profile: Any, publish: bool) -> None:
        """Send a saved working copy again, with the same checks as the menu's send."""
        fresh = self._reload(copy.key) or copy
        api = self.api(profile)  # type: ignore[attr-defined]

        def done(result: tuple[str, Any]) -> None:
            kind, value = result
            if kind == "conflict":
                self._conflict(fresh, profile, value, publish)  # type: ignore[attr-defined]
                return
            self._sent(fresh, profile, value)  # type: ignore[attr-defined]

        self.send_in_background(
            fresh,
            profile,
            publish,
            lambda: self.send_work(api, fresh, publish),  # type: ignore[attr-defined]
            done,
        )

    # ------------------------------------------------------------------ #
    # the offline queue (15, item 9)

    def offline_queue(self) -> off.OfflineQueue:
        return off.OfflineQueue(self.local.root)

    def queue_send(self, copy: lc.WorkingCopy, profile: Any, publish: bool, since: str) -> None:
        self.offline_queue().add(
            key=copy.key,
            site_id=profile.id,
            title=copy.title,
            publish=publish,
            since_gmt=since if not copy.remote_id else "",
        )
        self.watch_documents()
        self.host.announce(
            f"{profile.name} cannot be reached, so '{copy.title or 'untitled'}' is queued. "
            "QUILL sends it when the site answers again; your copy is kept on this computer."
        )

    def _reload(self, key: str) -> lc.WorkingCopy | None:
        copy = self.local.load(key)
        if copy is None:
            return None
        path = self.local.document_path(copy)
        name = copy.properties.get("document_file")
        if name:
            path = path.with_name(str(name))
        return self.local.copy_for_path(path) or copy

    def retry_queue(self) -> None:
        state = self._watch()
        entries = self.offline_queue().entries()
        if not entries or state.retrying:
            return
        store = self.sites()  # type: ignore[attr-defined]
        groups: dict[str, list[off.QueuedSend]] = {}
        for entry in entries:
            groups.setdefault(entry.site_id, []).append(entry)
        pending = [len(groups)]

        def finished() -> None:
            pending[0] -= 1
            if pending[0] <= 0:
                state.retrying = False

        state.retrying = True
        for site_id, group in groups.items():
            profile = store.get(site_id)
            if profile is None:
                for entry in group:
                    self.offline_queue().drop(entry.key)
                    self.host.announce(
                        f"'{entry.title or 'untitled'}' was waiting for a site that is no longer "
                        "connected. It stays on this computer; Open Local Draft finds it."
                    )
                finished()
                continue
            api = self.api(profile)  # type: ignore[attr-defined]

            def done(results: list[tuple[off.QueuedSend, str, Any]], p: Any = profile) -> None:
                finished()
                self._queue_results(p, results)

            def failed(exc: BaseException) -> None:
                finished()

            self.host.run_task(
                f"WordPress: sending queued work to {profile.name}",
                lambda g=group, a=api: self._send_queued(a, g),
                done,
                failed,
            )

    def _send_queued(
        self, api: Any, group: list[off.QueuedSend]
    ) -> list[tuple[off.QueuedSend, str, Any]]:
        """Runs off the UI thread: each queued copy, oldest first, until the site fails."""
        results: list[tuple[off.QueuedSend, str, Any]] = []
        for entry in group:
            copy = self._reload(entry.key)
            if copy is None:
                results.append((entry, "gone", None))
                continue
            try:
                if not copy.remote_id and entry.since_gmt:
                    landed = sch.find_landed(
                        api,
                        kind=copy.kind,
                        title=copy.title,
                        slug=str(copy.properties.get("slug", "")),
                        since_gmt=entry.since_gmt,
                    )
                    if landed is not None:
                        results.append((entry, "saved", landed))
                        continue
                kind, value = self.send_work(api, copy, entry.publish)  # type: ignore[attr-defined]
                results.append((entry, kind, value))
            except WordPressApiError as exc:
                if off.is_unreachable(exc):
                    results.append((entry, "offline", None))
                    break  # still away: the rest wait for the next try
                results.append((entry, "failed", exc))
        return results

    def _queue_results(self, profile: Any, results: list[tuple[off.QueuedSend, str, Any]]) -> None:
        queue = self.offline_queue()
        drafts = published = 0
        for entry, kind, value in results:
            title = entry.title or "untitled"
            if kind == "offline":
                continue
            queue.drop(entry.key)
            if kind == "saved":
                copy = self._reload(entry.key)
                if copy is not None:
                    self.record_sent(copy, value)
                if value.status in ("publish", "future"):
                    published += 1
                else:
                    drafts += 1
            elif kind == "conflict":
                self.host.announce(
                    f"'{title}' was waiting to go to {profile.name}. "
                    + value.spoken(profile.name)
                    + " Open it and send again to compare the two."
                )
            elif kind == "failed":
                self.host.announce(
                    f"'{title}' could not be sent to {profile.name} from the queue. "
                    f"{_failure(value)} It is still on this computer."
                )
        if drafts or published:
            self.host.announce(off.back_online_sentence(profile.name, drafts, published))

    def record_sent(self, copy: lc.WorkingCopy, saved: wp.Item) -> None:
        """Remember what the site now has, with no window and nothing spoken."""
        if not copy.remote_id:
            self.local.rekey(copy, saved.id)
        copy.base_modified_gmt = saved.modified_gmt
        copy.link = saved.link
        copy.status = saved.status
        self.local.save(copy)
        if saved.status == "publish":
            self.local.add_version(copy, lc.REASON_PUBLISHED)

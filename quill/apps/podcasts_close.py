"""How QUILL Cast closes, and what closing costs (list.md 5.4).

Split out of ``quill/apps/podcasts.py`` under GATE-11, and a clean seam: this
is the whole of the window's ending -- the three answers to closing, the probe
for what is at stake, the confirm, and the teardown that runs last.

**The change 5.4 made.** Cast had one answer to closing (exit) and one narrow
escape from it (the Alt+F4-to-tray checkbox), so the titlebar X ended playback
with no way to say otherwise. Quill Radio has carried Ask / Exit / Minimize to
Tray for as long as it has had a tray icon; same window model, same audience,
and one of them lost an hour of listening to a reflex.

**Why the confirm never runs from inside EVT_CLOSE.** ``ShowModal`` from a
close handler on wxMSW can return without ever displaying -- notably with a
screen reader's keyboard hook active -- and the close is then silently vetoed.
``AppShellFrame.handle_app_close`` vetoes and re-runs the confirm deferred; the
Quill Radio bug that taught us this was "Alt+F4 does nothing while a station
plays".

**Why "protected" matters.** With nothing playing and nothing downloading,
Ask closes straight away rather than interrupting a deliberate Alt+F4 to ask
whether it was deliberate.
"""

from __future__ import annotations

import wx

__all__ = [
    "CastCloseMixin",
    "_CLOSE_ACTION_LABELS",
    "_CLOSE_ACTION_VALUES",
    "_close_action_index",
    "_close_action_value",
]


#: PodcastHistory.close_action's Preferences combo box. The same three
#: answers, in the same order, as Quill Radio's -- two apps that behave the
#: same on close should read the same in Preferences (see also
#: CastCloseConfirmDialog, which writes this field via "Don't ask me again").
_CLOSE_ACTION_LABELS = ("Ask every time", "Exit", "Minimize to Tray")
_CLOSE_ACTION_VALUES = ("ask", "exit", "minimize")


def _close_action_index(value: str) -> int:
    """The combo row for a stored answer; unreadable reads as Exit.

    Never raises and never guesses "ask": a junk value that selected Ask would
    start interrupting Alt+F4 with a question nobody chose.
    """
    try:
        return _CLOSE_ACTION_VALUES.index(str(value or "").strip().lower())
    except ValueError:
        return 1


def _close_action_value(index: int) -> str:
    """The stored answer for a combo row; out of range is Exit."""
    return _CLOSE_ACTION_VALUES[index] if 0 <= index < len(_CLOSE_ACTION_VALUES) else "exit"


class CastCloseMixin:
    """Closing QUILL Cast: the answer, the stakes, the confirm, the teardown."""

    def _on_cast_app_close(self, event: wx.CloseEvent) -> None:
        # Three answers rather than one (list.md 5.4), through the same shared
        # flow all the companion apps use. "protected" is what makes the
        # question worth asking at all: with nothing playing and nothing
        # downloading, Ask closes straight away rather than interrupting a
        # deliberate Alt+F4 to say "are you sure you meant that".
        self.handle_app_close(
            event,
            close_action=str(getattr(self._podcast_history, "close_action", "exit")),
            protected=self._cast_close_is_protected(),
            confirm=self._run_cast_close_confirm,
            shutdown=self._cast_shutdown,
        )

    def _cast_close_is_protected(self) -> bool:
        """Whether there is anything closing would actually cost."""
        return bool(self._cast_close_stakes() != (False, 0))

    def _cast_close_stakes(self) -> tuple[bool, int]:
        """``(playing, downloads in flight)``, defensively.

        Every lookup is a getattr with a fallback: this runs on the way out,
        and a close handler that raises is a window that cannot be closed.
        """
        playing = False
        downloads = 0
        try:
            playing = bool(self._podcast_controller.is_playing())
        except Exception:  # noqa: BLE001 - a close must never fail on a probe
            playing = False
        queue = getattr(self, "_podcast_download_queue", None)
        counter = getattr(queue, "active_count", None)
        if callable(counter):
            try:
                downloads = int(counter())
            except Exception:  # noqa: BLE001
                downloads = 0
        return playing, downloads

    def _run_cast_close_confirm(self) -> str | None:
        """Exit / Minimize to Tray / Cancel, with "Don't ask me again".

        Run deferred by the shared close flow, never from inside EVT_CLOSE:
        ShowModal from a close handler on wxMSW can return without ever
        displaying, and the close is then silently vetoed (the Quill Radio
        "Alt+F4 does nothing while a station plays" bug).
        """
        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history
        from quill.ui.podcasts.close_confirm_dialog import CastCloseConfirmDialog

        playing, downloads = self._cast_close_stakes()
        result = CastCloseConfirmDialog(
            self.frame, playing=playing, downloads=downloads, announce_cb=self._announce
        ).show()
        if result is None:
            return None  # Cancel: stay open, nothing to remember.
        action, dont_ask_again = result
        if dont_ask_again:
            self._podcast_history.close_action = action
            podcast_history.save_history(app_data_dir(), self._podcast_history)
        return action

    def _cast_shutdown(self) -> None:
        """Teardown just before the window closes. Every step is guarded and
        classed (qc.md F-06): a failed final write is kept for the next launch,
        which says so once; anything else is logged. Close always completes."""
        from quill.core.paths import app_data_dir
        from quill.core.shutdown_report import (
            BACKGROUND,
            BEST_EFFORT,
            MUST_RECORD,
            ShutdownReport,
        )

        report = ShutdownReport("cast", "QUILL Cast")
        # Lambdas, not bound methods: the lookup must happen inside the guard.
        report.step("quillins", BEST_EFFORT, lambda: self._app_host.shutdown())
        # Forced writes rather than the coalescing path: this is the last
        # chance, and a pending timer will never fire.
        report.step("listening_stats", MUST_RECORD, lambda: self._podcast_flush_stats())
        report.step("podcast_library", MUST_RECORD, lambda: self._flush_podcast_library())
        for name, action in (
            ("scan_hold", getattr(getattr(self, "_scan_hold", None), "shutdown", None)),
            ("player", getattr(getattr(self, "_podcast_controller", None), "shutdown", None)),
            ("transfers", getattr(self, "_shutdown_podcast_transfers", None)),
        ):
            report.step(name, BEST_EFFORT, action)
        report.step("tasks", BACKGROUND, lambda: self._task_manager.shutdown(wait=False))
        report.step("media_keys", BEST_EFFORT, lambda: self._unregister_media_keys())
        report.step("global_hotkeys", BEST_EFFORT, lambda: self._unregister_global_hotkeys())
        report.step("tray", BEST_EFFORT, lambda: self._remove_tray_icon())
        report.persist(app_data_dir())

    def _cast_launch_notices(self) -> None:
        """At launch, after the window is up: media health, then the previous
        session's closing failure if it left one (F-06), with its Retry."""
        from quill.ui.shutdown_notice import register_shutdown_retry, surface_previous_shutdown

        self.surface_cast_media_health()
        register_shutdown_retry(self._retry_cast_final_writes)
        surface_previous_shutdown(self, "cast")

    def _retry_cast_final_writes(self) -> str:
        """Recent Problems' Retry on a "Closing" row: the same two writes, now."""
        self._podcast_flush_stats()
        self._flush_podcast_library()
        return "Saved your podcast library and listening statistics now."

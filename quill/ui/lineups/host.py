"""What the Lineups window needs from the app it runs in.

:class:`LineupsHost` is a small adapter over the app frame. The defaults work
for both apps (announce, background work, modal dialogs, undo); each app
overrides only how a row plays and where its start Lineup is remembered.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.merge import Catalogue
from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import ItemRef


class LineupsHost:
    """The app behind a Lineups window. Subclassed once per app."""

    #: "radio" or "cast": which settings record and help catalogue apply.
    app_key = ""
    #: How sentences name the app: "Quill Radio".
    app_name = ""

    def __init__(self, app: Any) -> None:
        self.app = app

    # -- the app frame ---------------------------------------------------------------

    @property
    def frame(self) -> Any:
        return getattr(self.app, "frame", None)

    @property
    def windows(self) -> Any:
        return getattr(self.app, "_windows", None)

    @property
    def data_dir(self) -> Path:
        from quill.core.paths import app_data_dir

        return Path(app_data_dir())

    def announce(self, text: str) -> None:
        speak = getattr(self.app, "_announce", None)
        if callable(speak) and text:
            speak(text)

    def say_outcome(self, text: str) -> None:
        """An action's result: the listener's sound-or-speech choice applies.

        Failures and counts go through :meth:`announce` instead -- they are
        always spoken, because no tone carries a number.
        """
        self.announce(text)

    #: Milliseconds to wait before a sentence that follows a focus move, so the
    #: screen reader's own focus announcement does not cut it off.
    AFTER_FOCUS_MS = 150

    def announce_soon(self, text: str) -> None:
        """:meth:`announce`, after the focus move the same command just made."""
        self._later(self.announce, text)

    def say_outcome_soon(self, text: str) -> None:
        """:meth:`say_outcome`, after the focus move the same command just made."""
        self._later(self.say_outcome, text)

    def _later(self, speak: Callable[[str], None], text: str) -> None:
        if not text:
            return
        try:
            import wx

            if wx.GetApp() is not None:
                wx.CallLater(self.AFTER_FOCUS_MS, speak, text)
                return
        except Exception:  # noqa: BLE001 - no event loop: say it now rather than never
            pass
        speak(text)

    def submit(
        self,
        name: str,
        work: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_failure: Callable[[BaseException], None],
    ) -> None:
        """Run *work* off the UI thread; inline when the app has no task manager."""
        manager = getattr(self.app, "_task_manager", None)
        if manager is None:
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001 - reported, never raised into wx
                on_failure(exc)
                return
            on_success(result)
            return
        manager.submit(
            name,
            lambda **_kwargs: work(),
            on_success=lambda _op, result: on_success(result),
            on_failure=lambda _op, error: on_failure(error),
        )

    def show_modal_dialog(self, dialog: Any, label: str) -> int:
        """Every modal dialog through the app's announcing helper (the dialog contract)."""
        shower = getattr(self.app, "_show_modal_dialog", None)
        if callable(shower):
            return int(shower(dialog, label))
        from quill.ui import dialog_contract

        return int(dialog_contract.show_modal_dialog(dialog, label))

    def remember_undo(
        self, verb: str, subject: str, restores: str, undo: Callable[[], None]
    ) -> bool:
        from quill.ui import undo_last_ui

        return undo_last_ui.remember(verb, subject, restores, undo)

    def offer_undo(self, sentence: str) -> str:
        from quill.ui import undo_last_ui

        return undo_last_ui.offer(sentence)

    def undo_last(self) -> bool:
        undo = getattr(self.app, "undo_last_action", None)
        if callable(undo):
            undo()
            return True
        return False

    # -- per app ------------------------------------------------------------------------

    def install_menus(self, win: Any, menu_bar: Any, refs: list[Any]) -> None:
        """Add the app's own menus beside the window's (the Window menu at least)."""
        windows = self.windows
        if windows is not None:
            windows.install(win, menu_bar)

    def install_keys(self, win: Any) -> None:
        """Whatever app-wide keys every peer window of this app answers to."""

    def catalogue(self, now: float) -> Catalogue:
        from quill.core.lineups.sources import build_catalogue

        return build_catalogue(self.data_dir, now=now)

    def watched_files(self) -> Sequence[Path]:
        """Files whose change should refresh the rules (the stores sources read)."""
        base = self.data_dir
        return tuple(
            base / name
            for name in (
                "podcasts_library.json",
                "radio_favorites.json",
                "radio-station-tags.json",
                "radio-youtube-saved.json",
                "radio-youtube-channels.json",
                "radio-local-media.json",
                "radio-listens.json",
            )
        )

    def play(
        self, lineup: Lineup, refs: Sequence[ItemRef], start: int, facts: Sequence[ItemFacts | None]
    ) -> str:
        """Play *refs* from index *start*, carrying on through the rest.

        Returns what to say, or ``""`` when the player says it already.
        """
        return "This app cannot play lineups."

    def play_next(
        self, refs: Sequence[ItemRef], facts: Sequence[ItemFacts | None], *, at_end: bool
    ) -> str:
        """Play Next (after the current item) or, with *at_end*, Add to Up Next."""
        return "This app cannot queue lineup items."

    def step(self, delta: int) -> str:
        """Next or Previous item of what this app is playing from a Lineup."""
        return "Nothing from a lineup is playing."

    def pause(self) -> None:
        toggle = getattr(getattr(self.app, "_radio_controller", None), "toggle_play_pause", None)
        if callable(toggle):
            toggle()

    def stop_after_current(self) -> str:
        return "Stop after this item is not available here."

    def start_lineup_id(self) -> str:
        return ""

    def set_start_lineup_id(self, lineup_id: str) -> None:
        """Remember (or, with ``""``, forget) the Lineup this app opens in."""

    @staticmethod
    def now() -> float:
        return time.time()


__all__ = ["LineupsHost"]

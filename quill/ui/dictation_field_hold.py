"""Paused for its field: Resume, Resume in This Field, Discard Held Words.

The three commands a person has when dictation into another program pauses
because the focus moved (:mod:`quill.core.windows_dictation.target_hold`),
shared by QUILL Transcribe and Quill Inkwell's Dictate Anywhere (D-15,
2026-10-13) -- one copy, so the two say the same sentences and behave the same
way. Moved here from ``quill/apps/transcribe_dictation.py``, where they began.

**Arming.** From the app's own window or its tray menu, the app itself is in
front, and it never types into itself. So Resume in This Field there *arms*:
it waits for another program to come forward and resumes in the field that has
the focus there, after the same checks as a new start
(:mod:`quill.core.transcribe.arming`). QUILL Transcribe arms a start and an
Insert Again the same way, through :meth:`FieldHoldMixin._armed`.

A host supplies three things: ``_held_controller()`` (its controller, or
``None`` before the first start), ``_hold_refresh()`` (bring its menus and
window up to date) and ``_announce``.
"""

from __future__ import annotations

import os
from typing import Any

import wx

__all__ = ["FieldHoldMixin"]

_ARM_POLL_MS = 250


class FieldHoldMixin:
    """Resume, Resume in This Field and Discard Held Words, and arming."""

    frame: Any

    # -- the host's answers ------------------------------------------------------ #

    def _held_controller(self) -> Any:
        """The dictation controller, or ``None`` before the first start."""
        raise NotImplementedError

    def _hold_refresh(self) -> None:
        """Bring the menus, the window and the tray up to date."""
        raise NotImplementedError

    # -- what the host asks ------------------------------------------------------ #

    def dictation_paused(self) -> bool:
        controller = self._held_controller()
        return bool(controller is not None and controller.paused_for_target)

    # -- the three commands ------------------------------------------------------ #

    def resume_dictation(self) -> None:
        if not self.dictation_paused():
            self._announce("Dictation is not paused.")  # type: ignore[attr-defined]
            return
        self._held_controller().resume_held()

    def resume_in_this_field(self) -> None:
        if getattr(self, "_armed_for", "") == "resume":
            # The same command again cancels, as _arm promises.
            self._cancel_arming()
            return
        if not self.dictation_paused():
            self._announce("Dictation is not paused.")  # type: ignore[attr-defined]
            return
        if self._front_is_own_window():
            self._arm(here=True)
            return
        self._held_controller().resume_held(here=True)

    def discard_held_words(self) -> None:
        if not self.dictation_paused():
            self._announce("Dictation is not paused, so nothing is held.")  # type: ignore[attr-defined]
            return
        self._held_controller().discard_held()

    # -- arming: the tray and the window ----------------------------------------- #

    def _front_is_own_window(self) -> bool:
        try:
            from quill.platform.windows.foreground import foreground_window_info

            return int(foreground_window_info().process_id) == os.getpid()
        except Exception:  # noqa: BLE001 - not Windows: treat as our own
            return True

    def _arm(self, *, here: bool, insert: str = "") -> None:
        """Wait for another program to come forward, then start, resume, or
        (*insert*, Recent Phrases' Insert Again) type one phrase there."""
        from quill.core.transcribe.arming import ARM_SECONDS

        self._armed_for = "insert" if insert else ("resume" if here else "start")
        self._armed_text = insert
        self._armed_ticks = int(ARM_SECONDS * 1000 / _ARM_POLL_MS)
        timer = getattr(self, "_arm_timer", None)
        if timer is None:
            timer = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, self._on_arm_tick, timer)
            self._arm_timer = timer
        timer.Start(_ARM_POLL_MS)
        verb = "resumes" if here else "starts"
        self._announce(  # type: ignore[attr-defined]
            "Switch to the field you want. The phrase is typed there."
            if insert
            else f"Switch to the field you want. Dictation {verb} there. Choose the same "
            "command again to cancel."
        )
        self._hold_refresh()

    def _cancel_arming(self, *, say: bool = True, refresh: bool = True) -> bool:
        if not getattr(self, "_armed_for", ""):
            return False
        what, self._armed_for = self._armed_for, ""
        timer = getattr(self, "_arm_timer", None)
        if timer is not None:
            timer.Stop()
        if say:
            self._announce(  # type: ignore[attr-defined]
                {
                    "insert": "Cancelled; nothing was typed.",
                    "resume": "Cancelled; dictation is still paused and your words are held.",
                }.get(what, "Cancelled; dictation did not start.")
            )
        if refresh:
            self._hold_refresh()
        return True

    def dictation_armed(self) -> bool:
        """Waiting to start or resume dictation (not to type a recent phrase)."""
        return getattr(self, "_armed_for", "") in ("start", "resume")

    def _armed(self, what: str, text: str) -> None:
        """Another program came forward: do what was armed. QUILL Transcribe
        adds "start" and "insert"."""
        del text
        if what == "resume":
            controller = self._held_controller()
            if controller is not None:
                controller.resume_held(here=True)

    def _on_arm_tick(self, _event: Any) -> None:
        from quill.core.transcribe.arming import ready_to_start

        self._armed_ticks -= 1
        try:
            from quill.platform.windows.foreground import foreground_window_info

            window = foreground_window_info()
            ready = ready_to_start(
                hwnd=window.hwnd,
                process_id=window.process_id,
                window_class=window.window_class,
                own_process=os.getpid(),
            )
        except Exception:  # noqa: BLE001 - not Windows: nothing will come forward
            ready = False
        if ready:
            what, text = self._armed_for, getattr(self, "_armed_text", "")
            self._cancel_arming(say=False, refresh=False)  # what follows refreshes
            self._armed(what, text)
            return
        if self._armed_ticks <= 0:
            what = self._armed_for
            self._cancel_arming(say=False)
            self._announce(  # type: ignore[attr-defined]
                {
                    "insert": "No other program came forward, so nothing was typed.",
                    "resume": "No other program came forward; dictation is still paused.",
                }.get(what, "No other program came forward, so dictation did not start.")
            )

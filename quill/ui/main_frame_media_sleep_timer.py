"""Tools > Media > Sleep Timer... -- shared between Internet Radio and
Podcasts (it lives in the Media submenu because it touches both surfaces,
not either one alone). See ``quill/ui/media_sleep_timer.py`` for the
countdown/fade/restore logic itself; this mixin only wires it into
``MainFrame`` (menu, commands, dialog, announcements).
"""

from __future__ import annotations

from quill.ui.media_sleep_timer import SleepTimerController
from quill.ui.sleep_timer_dialog import SleepTimerDialog


class MediaSleepTimerMixin:
    """Adds the shared Radio/Podcasts sleep timer to ``MainFrame``."""

    def _init_media_sleep_timer(self) -> None:
        self._sleep_timer_controller = SleepTimerController(
            get_radio_controller=lambda: getattr(self, "_radio_controller", None),
            get_podcast_controller=lambda: getattr(self, "_podcast_controller", None),
            on_tick=self._on_sleep_timer_tick,
        )

    def _on_sleep_timer_tick(self, remaining_seconds: float) -> None:
        self._wx.CallAfter(self._apply_sleep_timer_tick, remaining_seconds)

    def _apply_sleep_timer_tick(self, remaining_seconds: float) -> None:
        if remaining_seconds <= 0:
            self._announce("Sleep timer: playback stopped, volume restored.")

    def open_sleep_timer_dialog(self) -> None:
        controller = self._sleep_timer_controller
        dialog = SleepTimerDialog(
            self.frame,
            is_active=controller.is_active,
            remaining_seconds=controller.remaining_seconds,
            announce_cb=self._announce,
        )
        minutes = dialog.show()
        if minutes is None:
            return
        if minutes <= 0:
            controller.cancel()
            self._announce("Sleep timer cancelled")
        else:
            controller.start(minutes)
            self._announce(f"Sleep timer set for {minutes} minutes")

    def cancel_sleep_timer(self) -> None:
        if not self._sleep_timer_controller.is_active:
            self._announce("No sleep timer is running.")
            return
        self._sleep_timer_controller.cancel()
        self._announce("Sleep timer cancelled")

    def _register_media_sleep_timer_commands(self) -> None:
        for command_id, title, handler in (
            ("media.sleep_timer", "Media: Sleep Timer...", self.open_sleep_timer_dialog),
            ("media.cancel_sleep_timer", "Media: Cancel Sleep Timer", self.cancel_sleep_timer),
        ):
            self.commands.try_register(
                command_id,
                title,
                handler,
                self._binding_for(command_id),
                feature_id="core.radio",
            )

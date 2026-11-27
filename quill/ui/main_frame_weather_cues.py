"""WeatherCuesMixin -- the alert cues of the Weather menu: Test Alert, the
system-tray toast, and the alert sound. Split from ``main_frame_weather`` (GATE-11)."""

from __future__ import annotations

from typing import Any

from quill.core.sound_events import SoundEvent


class WeatherCuesMixin:
    frame: Any
    _wx: Any

    def _announce(  # provided by host
        self, message: str, *, force: bool = False, sound: str = ""
    ) -> None: ...
    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        return 0

    @staticmethod
    def _weather_data_dir() -> Any: ...

    # -- test alert (preview the whole experience) --------------------------

    def weather_test_alert(self) -> None:
        """Weather > Test Alert: let the user preview exactly what a real alert
        does -- the spoken/shown text, the sound, a system-tray toast, and the
        alert dialog -- all clearly marked as a TEST and dismissable. Does not
        touch the network or the monitor's real state."""
        headline = "This is a TEST of Quill Weather alerts. No action is needed."
        # 1) The sound cue (honoring the user's enable + custom-file choice, so
        #    the test reflects what they have actually configured).
        self._play_weather_alert_sound()
        # 2) Spoken, forced so it interrupts like a real urgent alert would,
        #    led by the same earcon a real new alert posts (#1302) -- the
        #    point of the preview is that it sounds exactly like the real thing.
        self._announce(
            f"Test weather alert. {headline}", force=True, sound=SoundEvent.WEATHER_ALERT
        )
        # 3) A system-tray toast, marked as a test.
        self._show_weather_toast(
            "[TEST] Weather alert", "This is a test of Quill Weather alerts. No action is needed."
        )
        # 4) The alert dialog, dismissable.
        body = (
            "TEST WEATHER ALERT\n\n"
            f"{headline}\n\n"
            "Severity Severe, urgency Expected, certainty Observed. (Sample values.)\n"
            "Area: your area (test).\n\n"
            "Instructions: This is only a test. When a real alert is issued, its official "
            "instructions appear here -- follow them.\n\n"
            "This preview shows how a real National Weather Service alert would be announced, "
            "sounded, shown in the system tray, and displayed. Select OK to dismiss it."
        )
        self._show_message_box(body, "Test Weather Alert", self._wx.OK | self._wx.ICON_INFORMATION)

    def _show_weather_toast(self, title: str, body: str) -> None:
        """Show a Windows notification-area toast (screen readers announce it).
        Best-effort; a toast failure never disrupts the rest of the alert."""
        from quill.ui.toast import show_toast

        show_toast(title, body, parent=self.frame, icon=self._wx.ICON_WARNING)

    def _play_weather_alert_sound(self) -> None:
        """Play the alert cue for a newly-issued alert, honoring the user's
        enable toggle and custom-sound choice. Best-effort; never raises."""
        from quill.core.weather import settings as settings_mod

        try:
            settings = settings_mod.load_settings(self._weather_data_dir())
            if not settings.alert_sound_enabled:
                return
            from quill.platform import alert_sound

            alert_sound.play_alert_sound(settings.alert_sound_path, settings.alert_sound_repeat)
        except Exception:  # noqa: BLE001 - a sound must never disrupt the alert
            pass

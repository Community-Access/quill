"""Quill Radio's Preferences: the data that arrives after the dialog opens.

Split from ``quill/apps/radio_preferences.py`` under GATE-11 (extract, never
rebaseline). Two rows in Preferences depend on something slow to read: the
output device list (mpv enumerates devices by starting a process) and the
podcast check cadence (it lives in the shared podcast library on disk). The
dialog opens on what is cached or saved, and this module fills the real answer
in on a background task -- without overwriting a row the listener has already
changed, and without touching a dialog that has already closed.

Wiring only. The rows themselves are built in ``radio_preferences``; this
module only knows their indices -- and owns both ends of the shared cadence,
the read that fills the row and the write that saves it.
"""

from __future__ import annotations

from typing import Any

#: The half of the cadence help that is true whatever the cadence is.
_PODCAST_SCHEDULE_HELP_SUFFIX = (
    " QUILL Cast reads this same setting since 3.1.0, so "
    "turning it on here turns it on there; whichever app checks "
    "first, the other skips that round rather than asking the "
    "same feeds twice. A single podcast can say Manually only in "
    "its own settings while the rest keep this cadence."
)


def podcast_schedule_help(minutes: int, *, on_launch: bool) -> str:
    """The cadence row's help: what the schedule does, then what is shared."""
    from quill.core.podcasts import refresh_policy

    return (
        refresh_policy.describe_schedule(minutes, on_launch=on_launch)
        + _PODCAST_SCHEDULE_HELP_SUFFIX
    )


def _load_shared_check_minutes(fallback_minutes: int) -> int:
    """Read the shared cadence, falling back to Radio's saved value.

    The shared library is authoritative since 3.1.0; Radio's saved field is
    only the fallback for an install that has not been migrated yet.
    """
    from quill.core.podcasts import episode_alerts

    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.subscriptions import load_library

        shared = episode_alerts.interval_for_show(load_library(app_data_dir()).settings)
    except Exception:  # noqa: BLE001 - unreadable library: fall back
        shared = 0
    if shared > 0:
        return shared
    return fallback_minutes


def save_shared_check_minutes(minutes: int) -> None:
    """Write the cadence where QUILL Cast will see it. Best effort."""
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.subscriptions import load_library, save_library

        data_dir = app_data_dir()
        library = load_library(data_dir)
        library.settings.check_interval_minutes = int(minutes)
        save_library(data_dir, library)
    except Exception:  # noqa: BLE001 - losing the share beats losing the save
        return


class PreferencesDataLoad:
    """One background read for one open Preferences dialog.

    ``device_names`` is the caller's own list, updated in place, so the apply
    step after ``show()`` maps the chosen row to the device it now names.
    ``shared_check_minutes_loaded`` says whether the cadence row ever showed
    the shared value -- saving one that never did would replace it blind.
    """

    def __init__(
        self,
        app: Any,
        dialog: Any,
        *,
        cached_devices: list[tuple[str, str]] | None,
        mpv_present: bool,
        device_names: list[str],
        output_device_choice_index: int,
        podcast_schedule_choice_index: int,
        fallback_shared_check_minutes: int,
    ) -> None:
        self.app = app
        self.dialog = dialog
        self.history = app._radio_history
        self.cached_devices = cached_devices
        self.mpv_present = mpv_present
        self.device_names = device_names
        self.output_device_choice_index = output_device_choice_index
        self.podcast_schedule_choice_index = podcast_schedule_choice_index
        self.fallback_shared_check_minutes = fallback_shared_check_minutes
        self.shared_check_minutes_loaded = False

    def _read(self, **_task_kwargs: Any) -> tuple[list[tuple[str, str]], int]:
        from quill.ui.radio.mpv_radio_engine import list_audio_devices

        if self.cached_devices is not None:
            devices = list(self.cached_devices)
        elif self.mpv_present:
            devices = list_audio_devices()
        else:
            devices = []
        shared_minutes = _load_shared_check_minutes(self.fallback_shared_check_minutes)
        return devices, shared_minutes

    def _loaded(self, _operation_id: str, result: tuple[list[tuple[str, str]], int]) -> None:
        from quill.core.podcasts import refresh_policy
        from quill.ui.audio.output_routing import cache_output_devices
        from quill.ui.dialog_contract import dialog_alive
        from quill.ui.radio.mpv_radio_engine import output_device_choices

        dialog = self.dialog
        devices, shared_minutes = result
        self.shared_check_minutes_loaded = True
        if self.cached_devices is None and devices:
            cache_output_devices(devices)
        if not dialog_alive(dialog.dialog):
            return
        if self.cached_devices is None:
            if not devices:
                # WinRT retains DeviceInformation objects for the UI-thread
                # playback engine, so only its string list is requested here.
                from quill.ui.audio.winrt_engine import list_audio_devices as list_windows_devices

                devices = list_windows_devices()
                if devices:
                    cache_output_devices(devices)
            if devices:
                selected_index = dialog.choice_selection(self.output_device_choice_index)
                selected_device = (
                    self.device_names[selected_index]
                    if 0 <= selected_index < len(self.device_names)
                    else self.history.output_device
                )
                labels, names, index = output_device_choices(devices, selected_device)
                self.device_names[:] = names
                dialog.set_choice_options(self.output_device_choice_index, labels, index)
        if not dialog.choice_was_changed(self.podcast_schedule_choice_index):
            dialog.set_choice_selection(
                self.podcast_schedule_choice_index,
                refresh_policy.interval_index(shared_minutes),
            )
        dialog.set_choice_help_text(
            self.podcast_schedule_choice_index,
            podcast_schedule_help(shared_minutes, on_launch=self.history.podcast_refresh_on_launch),
        )

    def _report_failure(self) -> None:
        from quill.ui.dialog_contract import dialog_alive

        if dialog_alive(self.dialog.dialog):
            self.app._announce(
                "Radio could not refresh some Preferences data. "
                "The saved audio device and podcast interval are unchanged."
            )

    def _failed(self, _operation_id: str, _error: BaseException) -> None:
        self._report_failure()

    def _start(self) -> None:
        task_manager = getattr(self.app, "_task_manager", None)
        if task_manager is None:
            self._report_failure()
            return
        task_manager.submit(
            "radio-preferences-data",
            self._read,
            on_success=self._loaded,
            on_failure=self._failed,
        )

    def schedule(self) -> None:
        """Start the read once the dialog is up, or now when no wx app runs."""
        import wx

        call_after = getattr(wx, "CallAfter", None)
        get_app = getattr(wx, "GetApp", None)
        if callable(call_after) and callable(get_app) and get_app() is not None:
            call_after(self._start)
        else:
            self._start()

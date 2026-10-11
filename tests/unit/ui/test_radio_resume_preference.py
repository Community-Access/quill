"""Preferences > Interrupted recordings at launch (2026-09-25).

"Don't ask me again" on the Resume Recording dialog stores
``recording_resume_choice`` as always or never, and until this row existed
nothing in the app could set it back. These tests drive the real
``open_preferences`` with the dialog replaced, so they cover both the row the
listener sees and the value the answer writes.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest  # type: ignore[import-not-found]

from quill.apps import radio_preferences
from quill.core.radio.history import RadioHistory

_LABEL = "Interrup&ted recordings at launch:"


class _FakeDialog:
    """Records what Preferences offered; answers with *pick* on the resume row."""

    last: _FakeDialog | None = None
    pick: int | None = None
    startup_pick: bool | None = None
    choice_picks: dict[str, int] = {}

    def __init__(self, *_args, checkboxes, choices, texts, **_kwargs) -> None:
        self.checkboxes, self.choices, self.texts = checkboxes, choices, texts
        _FakeDialog.last = self

    def show(self):
        if _FakeDialog.pick is None:
            return None
        indices = [choice.selected_index for choice in self.choices]
        indices[[c.name for c in self.choices].index(_LABEL)] = _FakeDialog.pick
        for name, index in _FakeDialog.choice_picks.items():
            indices[[choice.name for choice in self.choices].index(name)] = index
        checkbox_values = [box.value for box in self.checkboxes]
        startup_index = [box.name for box in self.checkboxes].index(
            "Start Quill Radio with &Windows"
        )
        if _FakeDialog.startup_pick is not None:
            checkbox_values[startup_index] = _FakeDialog.startup_pick
        return (
            checkbox_values,
            indices,
            [text.value for text in self.texts],
        )

    def choice_was_changed(self, index: int) -> bool:
        return self.choices[index].name in _FakeDialog.choice_picks


@pytest.fixture
def app(monkeypatch):
    import quill.ui.app_preferences_dialog as dialog_module
    import quill.ui.radio.mpv_radio_engine as engine
    from quill.apps import radio_podcast_refresh
    from quill.core.radio import history as radio_history

    monkeypatch.setattr(dialog_module, "PreferencesDialog", _FakeDialog)
    monkeypatch.setattr(engine, "list_audio_devices", lambda: [])
    monkeypatch.setattr(radio_history, "save_history", lambda *_a, **_k: None)
    monkeypatch.setattr(radio_podcast_refresh, "reapply", lambda _app: "")
    _FakeDialog.last = None
    _FakeDialog.pick = None
    _FakeDialog.startup_pick = None
    _FakeDialog.choice_picks = {}
    host = MagicMock()
    host._radio_history = RadioHistory()
    return host


def _row(dialog: _FakeDialog):
    return next(choice for choice in dialog.choices if choice.name == _LABEL)


@pytest.mark.parametrize("stored", ["ask", "always", "never"])
def test_the_row_shows_what_is_stored(app, stored) -> None:
    app._radio_history.recording_resume_choice = stored
    radio_preferences.open_preferences(app)
    row = _row(_FakeDialog.last)
    assert radio_preferences.RESUME_CHOICES[row.selected_index][0] == stored


def test_dont_ask_again_can_be_undone(app) -> None:
    app._radio_history.recording_resume_choice = "never"
    _FakeDialog.pick = 0  # Ask each time
    radio_preferences.open_preferences(app)
    assert app._radio_history.recording_resume_choice == "ask"


def test_choosing_always_is_stored(app) -> None:
    _FakeDialog.pick = 1
    radio_preferences.open_preferences(app)
    assert app._radio_history.recording_resume_choice == "always"


def test_cancel_changes_nothing(app) -> None:
    app._radio_history.recording_resume_choice = "never"
    radio_preferences.open_preferences(app)
    assert app._radio_history.recording_resume_choice == "never"


def test_startup_preference_is_offered_and_applied(app, monkeypatch) -> None:
    from quill.platform.windows import radio_startup

    monkeypatch.setattr(radio_startup, "is_windows", lambda: True)
    monkeypatch.setattr(radio_startup, "running_portable", lambda: False)
    state = [False]
    writes: list[bool] = []

    def set_startup(value: bool) -> None:
        writes.append(value)
        state[0] = value

    monkeypatch.setattr(radio_startup, "is_launch_at_startup_enabled", lambda: state[0])
    monkeypatch.setattr(radio_startup, "set_launch_at_startup", set_startup)
    _FakeDialog.pick = 0
    _FakeDialog.startup_pick = True

    radio_preferences.open_preferences(app)

    checkbox = next(
        box for box in _FakeDialog.last.checkboxes if box.name == "Start Quill Radio with &Windows"
    )
    assert checkbox.value is False and checkbox.enabled is True
    assert writes == [True]
    assert app._announce.call_args[0][0].startswith(
        "Preferences saved. Quill Radio will start with Windows."
    )


def test_every_offered_value_survives_a_reload() -> None:
    # history_store keeps only these three; a fourth would read back as "ask".
    assert [value for value, _label in radio_preferences.RESUME_CHOICES] == [
        "ask",
        "always",
        "never",
    ]
    assert radio_preferences._resume_index("bogus") == 0


@pytest.mark.parametrize(
    ("user_device_index", "expected_device_index"),
    [(None, 2), (0, 0)],
)
@pytest.mark.parametrize(
    ("user_schedule_index", "expected_schedule_index"),
    [(None, 3), (0, 0), (1, 1)],
)
def test_preferences_data_loads_after_open_without_overwriting_edits(
    app,
    monkeypatch: pytest.MonkeyPatch,
    user_device_index: int | None,
    expected_device_index: int,
    user_schedule_index: int | None,
    expected_schedule_index: int,
) -> None:
    import wx

    import quill.ui.app_preferences_dialog as dialog_module
    from quill.ui.audio import output_routing
    from quill.ui.radio import mpv_radio_engine

    events: list[str] = []
    scheduled: list[tuple[object, tuple[object, ...], dict[str, object]]] = []
    devices = [("wasapi/{new}", "Speakers")]

    class _AliveDialog:
        def IsBeingDeleted(self) -> bool:
            return False

    class _PreferencesDialog:
        last = None

        def __init__(self, _parent, *, choices, **_kwargs) -> None:
            _PreferencesDialog.last = self
            self.choices = choices
            self.selections = [choice.selected_index for choice in choices]
            self.dialog = _AliveDialog()
            self.output_device_index = next(
                index
                for index, choice in enumerate(choices)
                if choice.name == "Radio &output device:"
            )
            self.schedule_index = next(
                index
                for index, choice in enumerate(choices)
                if choice.name == "Check subscribed podcast &feeds:"
            )
            self.changed_choices: set[int] = set()

        def choice_selection(self, index: int) -> int:
            return self.selections[index]

        def choice_was_changed(self, index: int) -> bool:
            return index in self.changed_choices

        def set_choice_options(self, index: int, options: list[str], selected_index: int) -> None:
            self.choices[index].options = options
            self.selections[index] = selected_index
            events.append("device options updated")

        def set_choice_selection(self, index: int, selected_index: int) -> None:
            self.selections[index] = selected_index
            events.append("schedule selection updated")

        def set_choice_help_text(self, index: int, help_text: str) -> None:
            self.choices[index].help_text = help_text
            events.append("schedule help updated")

        def show(self):
            events.append("shown")
            if user_device_index is not None:
                self.selections[self.output_device_index] = user_device_index
            if user_schedule_index is not None:
                self.selections[self.schedule_index] = user_schedule_index
                self.changed_choices.add(self.schedule_index)
            for callback, args, kwargs in scheduled:
                callback(*args, **kwargs)
            return None

    class _TaskManager:
        def submit(self, _name, worker, *, on_success, on_failure) -> None:
            events.append("submitted")
            result = worker(
                cancellation_token=None,
                operation_id="device-test",
                progress_callback=lambda *_args: None,
            )
            on_success("device-test", result)

    monkeypatch.setattr(dialog_module, "PreferencesDialog", _PreferencesDialog)
    monkeypatch.setattr(wx, "GetApp", lambda: object())
    monkeypatch.setattr(
        wx,
        "CallAfter",
        lambda callback, *args, **kwargs: scheduled.append((callback, args, kwargs)),
    )
    monkeypatch.setattr(output_routing, "cached_output_devices", lambda: None)
    monkeypatch.setattr(
        output_routing,
        "cache_output_devices",
        lambda _devices: events.append("cached"),
    )
    monkeypatch.setattr(
        radio_preferences,
        "_load_shared_check_minutes",
        lambda _fallback: events.append("cadence loaded") or 60,
    )
    monkeypatch.setattr(mpv_radio_engine, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(
        mpv_radio_engine,
        "list_audio_devices",
        lambda: events.append("enumerated") or devices,
    )
    app._task_manager = _TaskManager()
    app._radio_history.output_device = "wasapi/{old}"

    radio_preferences.open_preferences(app)

    assert events[0] == "shown"
    assert events.index("enumerated") > events.index("shown")
    assert "cadence loaded" in events
    offered_choice = next(
        choice
        for choice in _PreferencesDialog.last.choices
        if choice.name == "Radio &output device:"
    )
    assert offered_choice.options == (
        ["System default", "Speakers"]
        if user_device_index == 0
        else ["System default", "Speakers", "wasapi/{old} (not currently available)"]
    )
    assert (
        _PreferencesDialog.last.selections[_PreferencesDialog.last.output_device_index]
        == expected_device_index
    )
    assert (
        _PreferencesDialog.last.selections[_PreferencesDialog.last.schedule_index]
        == expected_schedule_index
    )


def test_saving_before_podcast_cadence_load_does_not_replace_shared_value(
    app, monkeypatch: pytest.MonkeyPatch
) -> None:
    writes: list[int] = []
    app._radio_history.podcast_refresh_minutes = 180
    monkeypatch.setattr(radio_preferences, "_save_shared_check_minutes", writes.append)
    _FakeDialog.pick = 0

    radio_preferences.open_preferences(app)

    assert writes == []
    assert app._radio_history.podcast_refresh_minutes == 180


def test_a_changed_podcast_cadence_is_saved_before_background_load_completes(
    app, monkeypatch: pytest.MonkeyPatch
) -> None:
    writes: list[int] = []
    app._radio_history.podcast_refresh_minutes = 60
    monkeypatch.setattr(radio_preferences, "_save_shared_check_minutes", writes.append)
    _FakeDialog.pick = 0
    _FakeDialog.choice_picks = {"Check subscribed podcast &feeds:": 1}

    radio_preferences.open_preferences(app)

    assert writes == [15]
    assert app._radio_history.podcast_refresh_minutes == 15

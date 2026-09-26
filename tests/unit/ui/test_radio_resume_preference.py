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

    def __init__(self, *_args, checkboxes, choices, texts, **_kwargs) -> None:
        self.checkboxes, self.choices, self.texts = checkboxes, choices, texts
        _FakeDialog.last = self

    def show(self):
        if _FakeDialog.pick is None:
            return None
        indices = [choice.selected_index for choice in self.choices]
        indices[[c.name for c in self.choices].index(_LABEL)] = _FakeDialog.pick
        return (
            [box.value for box in self.checkboxes],
            indices,
            [text.value for text in self.texts],
        )


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


def test_every_offered_value_survives_a_reload() -> None:
    # history_store keeps only these three; a fourth would read back as "ask".
    assert [value for value, _label in radio_preferences.RESUME_CHOICES] == [
        "ask",
        "always",
        "never",
    ]
    assert radio_preferences._resume_index("bogus") == 0

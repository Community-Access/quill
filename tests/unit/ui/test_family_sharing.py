from __future__ import annotations

from types import SimpleNamespace

from quill.core import family_preferences as family
from quill.ui import family_sharing


def test_radio_preferences_route_adopted_history_through_ui_save(monkeypatch, tmp_path) -> None:
    saved: list[bool] = []
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(family, "is_sharing", lambda *_args: False)
    monkeypatch.setattr(family, "set_sharing", lambda *_args: ["action_feedback"])
    host = SimpleNamespace(
        _save_radio_history=lambda: saved.append(True),
        _announce=lambda _message: None,
    )
    history = SimpleNamespace(share_family_prefs=True)

    family_sharing.after_preferences(host, "radio", history, {"share_family_prefs": True})

    assert saved == [True]

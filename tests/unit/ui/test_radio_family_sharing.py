"""Quill Radio and the shared family choices (qc.md X-05), end to end.

plan.md (shared desktop settings review):

* Radio's Preferences passed only ``share_family_prefs`` to the sharing
  helper, so changing *Announce dialog transitions* while already sharing was
  never published: Radio had True, the shared record kept False, and the next
  app to adopt took False.
* Radio's launch never adopted newer shared choices, as Cast does.

These use a temporary data folder, the real family record, the real
Preferences apply step and the real launch-task scheduler.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import family_preferences as family
from quill.ui import family_sharing


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    return tmp_path


def _history(**values):
    base = {"share_family_prefs": True, "announce_dialog_transitions": False}
    base.update(values)
    return SimpleNamespace(**base)


def _host(history):
    host = SimpleNamespace(said=[], saves=0, _radio_history=history)
    host._announce = host.said.append

    def save():
        host.saves += 1

    host._save_radio_history = save
    return host


def test_a_shared_choice_changed_in_radio_preferences_reaches_the_next_app(
    data_dir: Path,
) -> None:
    radio = _history()
    family.set_sharing(data_dir, "radio", True, radio)
    cast = _history()
    family.set_sharing(data_dir, "cast", True, cast)
    before = family_sharing.shared_values(radio)
    radio.announce_dialog_transitions = True  # the checkbox, as Preferences applies it
    family_sharing.after_preferences(
        _host(radio), "radio", radio, family_sharing.preference_changes(radio, before)
    )
    assert family._read(data_dir)["values"]["announce_dialog_transitions"] is True
    assert family.adopt(data_dir, "cast", cast) == ["announce_dialog_transitions"]
    assert cast.announce_dialog_transitions is True


def test_an_unchanged_shared_choice_is_not_republished(data_dir: Path) -> None:
    radio = _history()
    family.set_sharing(data_dir, "radio", True, radio)
    other = _history()
    family.set_sharing(data_dir, "cast", True, other)
    other.announce_dialog_transitions = True
    family.publish(data_dir, "cast", other)  # Cast changed it to True since
    before = family_sharing.shared_values(radio)
    changes = family_sharing.preference_changes(radio, before)
    assert changes == {"share_family_prefs": True}
    family_sharing.after_preferences(_host(radio), "radio", radio, changes)
    assert family._read(data_dir)["values"]["announce_dialog_transitions"] is True


def test_not_sharing_publishes_nothing(data_dir: Path) -> None:
    radio = _history(share_family_prefs=False)
    before = family_sharing.shared_values(radio)
    radio.announce_dialog_transitions = True
    family_sharing.after_preferences(
        _host(radio), "radio", radio, family_sharing.preference_changes(radio, before)
    )
    assert family._read(data_dir)["values"] == {}


def test_radio_preferences_passes_the_changed_shared_fields() -> None:
    """The Preferences apply step is too big to drive here; this pins the call."""
    import inspect

    from quill.apps import radio_preferences

    source = inspect.getsource(radio_preferences)
    assert '{"share_family_prefs": history.share_family_prefs}' not in source
    assert "family_sharing.preference_changes(history" in source


def _schedule_launch(monkeypatch: pytest.MonkeyPatch, host) -> list:
    """Run Radio's real launch scheduler; return what it deferred."""
    from quill.apps import radio_launch_tasks, radio_podcast_refresh
    from quill.ui.radio import calendar_wiring

    deferred: list = []
    fake_wx = SimpleNamespace(CallAfter=lambda fn, *a, **k: deferred.append((fn, a, k)))
    monkeypatch.setattr(calendar_wiring, "install_reminders", lambda *_a: None)
    monkeypatch.setattr(radio_podcast_refresh, "install", lambda *_a, **_k: None)
    monkeypatch.setattr("sys.argv", ["quill-radio"])
    radio_launch_tasks.schedule(host, fake_wx, safe_mode=True)
    return deferred


def test_radio_launch_adopts_a_newer_shared_choice_saves_and_says_so(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cast = _history(announce_dialog_transitions=True)
    family.set_sharing(data_dir, "cast", True, cast)
    radio = _history()
    family._write(
        data_dir,
        {"apps": {"cast": True, "radio": True}, "values": family._read(data_dir)["values"]},
    )
    host = _host(radio)
    deferred = _schedule_launch(monkeypatch, host)
    adopters = [item for item in deferred if item[0] is family_sharing.at_launch]
    assert adopters, "Radio's launch never adopts shared choices"
    for fn, args, kwargs in adopters:
        fn(*args, **kwargs)
    assert radio.announce_dialog_transitions is True
    assert host.saves == 1  # through Radio's own ordered writer
    assert host.said == ["Using your shared choice for announce dialog transitions."]


def test_radio_launch_without_sharing_changes_nothing(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cast = _history(announce_dialog_transitions=True)
    family.set_sharing(data_dir, "cast", True, cast)
    radio = _history(share_family_prefs=False)
    host = _host(radio)
    for fn, args, kwargs in _schedule_launch(monkeypatch, host):
        if fn is family_sharing.at_launch:
            fn(*args, **kwargs)
    assert radio.announce_dialog_transitions is False
    assert host.saves == 0 and host.said == []

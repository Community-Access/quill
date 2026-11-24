"""Background downloads on Beta and Dev (owner decision 11), through the UI helper.

Stable is unchanged: the silent check shows its dialog as before. Beta and Dev
fetch first, record it, say "downloaded" once, then offer -- and the offer's
Update goes straight to the install choices. A held download is recorded, and
in Quiet Hours or during a recording nothing is shown at all. Nothing here
installs anything; the task runner and the download are fakes.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.wx_session import patch_call_after

wx = pytest.importorskip("wx")

from quill.core.updater import history  # noqa: E402
from quill.core.updater.background import Conditions  # noqa: E402
from quill.core.updater.channels import ChannelState  # noqa: E402
from quill.ui.updates import background  # noqa: E402

URL = "https://github.com/Community-Access/quill/releases/download/quill-radio-v3.3.0-beta.2/Quill-Radio-Setup-Shared-3.3.0-beta.2.exe"


def _release() -> SimpleNamespace:
    return SimpleNamespace(
        version="3.3.0-beta.2",
        download_url=URL,
        download_digest="c" * 64,
        size=10,
        channels=("beta",),
    )


@pytest.fixture
def harness(monkeypatch, tmp_path: Path):
    log = tmp_path / "update-history.jsonl"
    real_record = history.record
    monkeypatch.setattr(history, "record", lambda *a, **k: real_record(*a, **{**k, "path": log}))
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    submitted: list[str] = []

    def submit(name, func, *, on_success=None, on_failure=None):
        submitted.append(name)
        try:
            result = func()
        except Exception as error:  # noqa: BLE001
            on_failure(name, error)
        else:
            on_success(name, result)

    monkeypatch.setattr(
        "quill.core.updater.download.download_verified",
        lambda url, dest, **_k: dest,
    )
    return SimpleNamespace(log=log, submit=submit, submitted=submitted)


def _run(harness, monkeypatch, state, conditions):
    monkeypatch.setattr(background, "read_conditions", lambda: conditions)
    spoken: list[str] = []
    ready: list[Path] = []
    handled = background.silent_found(
        app_key="radio",
        release=_release(),
        state=state,
        target_dir=Path("updates"),
        submit=harness.submit,
        announce=spoken.append,
        on_ready=ready.append,
    )
    return handled, spoken, ready


def test_stable_is_unchanged(harness, monkeypatch) -> None:
    handled, spoken, ready = _run(harness, monkeypatch, ChannelState(), Conditions())
    assert handled is False
    assert harness.submitted == [] and spoken == [] and ready == []


def test_beta_downloads_first_then_offers(harness, monkeypatch) -> None:
    handled, spoken, ready = _run(harness, monkeypatch, ChannelState(channel="beta"), Conditions())
    assert handled is True
    assert harness.submitted == ["app-update-background-download"]
    assert spoken == ["Update 3.3.0 Beta 2 downloaded"]
    assert ready and ready[0].name.endswith(".exe")
    kinds = [e.kind for e in history.read_events(path=harness.log)]
    assert kinds == ["downloaded"]


def test_metered_holds_but_still_offers(harness, monkeypatch) -> None:
    handled, _spoken, _ready = _run(
        harness, monkeypatch, ChannelState(channel="dev"), Conditions(metered=True)
    )
    assert handled is False
    event = history.read_events(path=harness.log)[0]
    assert event.kind == "held_back" and "metered" in event.detail


@pytest.mark.parametrize("conditions", [Conditions(quiet=True), Conditions(recording=True)])
def test_quiet_hours_and_recordings_hold_and_show_nothing(harness, monkeypatch, conditions) -> None:
    handled, spoken, ready = _run(harness, monkeypatch, ChannelState(channel="beta"), conditions)
    assert handled is True
    assert harness.submitted == [] and spoken == [] and ready == []
    assert history.read_events(path=harness.log)[0].kind == "held_back"


def test_a_failed_background_download_is_recorded_quietly(harness, monkeypatch) -> None:
    def boom(*_a, **_k):
        raise OSError("connection reset")

    monkeypatch.setattr("quill.core.updater.download.download_verified", boom)
    handled, spoken, ready = _run(harness, monkeypatch, ChannelState(channel="beta"), Conditions())
    assert handled is True and spoken == [] and ready == []
    assert history.read_events(path=harness.log)[0].kind == "failed"


def test_a_shell_app_writes_downloaded_and_offers_at_a_quiet_moment(
    harness, monkeypatch, tmp_path
) -> None:
    """FUX-15: Radio's Beta download says "downloaded" on the status bar, not
    over the station, and its offer waits while the station plays."""
    from quill.core import maintenance_moment
    from quill.ui import maintenance_moment_ui, update_notice
    from quill.ui.radio.playback_state import RadioPlayerState

    monkeypatch.setattr(background, "read_conditions", lambda: Conditions())
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    clock = SimpleNamespace(now=100.0)
    later: list = []
    maintenance_moment_ui.reset_for_tests()
    maintenance_moment_ui._MOMENTS["radio"] = maintenance_moment.MaintenanceMoment(
        clock=lambda: clock.now, launched=0.0
    )
    monkeypatch.setattr(maintenance_moment_ui, "_wx_later", lambda _ms, run: later.append(run))
    monkeypatch.setattr(maintenance_moment_ui, "window_in_front", lambda _w: True)
    monkeypatch.setattr(maintenance_moment_ui, "input_idle_seconds", lambda: None)
    offered: list[str] = []
    monkeypatch.setattr(
        update_notice,
        "show_update_available",
        lambda *_a, **kw: (offered.append(kw["release"].version), "close")[1],
    )
    said: list[str] = []
    status: list[str] = []
    shell = SimpleNamespace(
        frame=SimpleNamespace(Close=lambda: None),
        _task_manager=SimpleNamespace(submit=harness.submit),
        _announce=lambda message, **_k: said.append(message),
        _set_status=status.append,
        _update_app_name=lambda: "Quill Radio",
        _running_portable_build=lambda: False,
        _show_message_box=lambda *_a, **_k: None,
        _show_modal_dialog=lambda *_a, **_k: None,
        _radio_recorder=SimpleNamespace(is_recording=False),
        _radio_controller=SimpleNamespace(state=SimpleNamespace(state=RadioPlayerState.PLAYING)),
    )
    try:
        assert background.shell_found(shell, "radio", _release(), ChannelState("beta"), "3.2.0")
        assert said == []
        assert status[0] == "Update 3.3.0 Beta 2 downloaded"
        assert shell._maintenance_note.startswith("Update 3.3.0 Beta 2 waits until playback stops.")
        assert offered == []
        shell._radio_controller.state.state = RadioPlayerState.STOPPED
        clock.now = 130.0
        later.pop(0)()
        assert offered == ["3.3.0-beta.2"]
        assert shell._maintenance_note == ""
    finally:
        maintenance_moment_ui.reset_for_tests()

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
    monkeypatch.setattr(background.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
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

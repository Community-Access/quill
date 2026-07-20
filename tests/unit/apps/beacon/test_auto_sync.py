"""Headless tests for the auto-sync timer (PRD 45.10; off by default)."""

import tempfile

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon.model import Beacon, Resource
from quill.apps.beacon.sync_ui import SyncConfig


@pytest.fixture
def frame(monkeypatch):
    data_dir = tempfile.mkdtemp()
    monkeypatch.setenv("QUILLBEACON_DATA", data_dir)
    app = wx.App(False)
    from quill.apps.beacon.app import BeaconFrame

    f = BeaconFrame()
    yield f
    f.Destroy()
    try:
        app.Destroy()
    except Exception:
        pass


def test_auto_sync_timer_off_by_default(frame):
    # No config -> timer not running.
    assert frame.sync.config.auto_sync_seconds == 0
    assert not frame._sync_timer.IsRunning()


def test_auto_sync_timer_starts_when_configured(frame, tmp_path):
    frame.sync.save_config(
        SyncConfig(
            transport="folder", folder=str(tmp_path / "remote"), device="d", auto_sync_seconds=300
        )
    )
    frame.sync.setup_vault("pass")
    frame._apply_auto_sync_interval()
    assert frame._sync_timer.IsRunning()


def test_auto_sync_timer_off_when_unconfigured(frame, tmp_path):
    # Interval set but transport off -> timer must not run.
    frame.sync.save_config(SyncConfig(transport="off", auto_sync_seconds=300))
    frame._apply_auto_sync_interval()
    assert not frame._sync_timer.IsRunning()


def test_auto_sync_tick_runs_sync(frame, tmp_path):
    remote = tmp_path / "remote"
    frame.sync.save_config(
        SyncConfig(transport="folder", folder=str(remote), device="d", auto_sync_seconds=300)
    )
    frame.sync.setup_vault("pass")
    res = Resource(title="A", type="web", primary_uri="https://x/A")
    b = Beacon(resource_id=res.resource_id, title="A", in_inbox=False)
    frame.store.put_beacon(b, resource=res)
    # Tick before unlock -> no-op (quiet).
    frame._on_auto_sync_tick(None)
    frame.sync.unlock("pass")
    frame._on_auto_sync_tick(None)
    # The commit landed in the local log.
    assert frame.sync._has_local_commits()


def test_auto_sync_timer_stops_on_zero(frame, tmp_path):
    frame.sync.save_config(
        SyncConfig(
            transport="folder", folder=str(tmp_path / "r"), device="d", auto_sync_seconds=300
        )
    )
    frame.sync.setup_vault("pass")
    frame._apply_auto_sync_interval()
    assert frame._sync_timer.IsRunning()
    frame.sync.config.auto_sync_seconds = 0
    frame.sync.save_config(frame.sync.config)
    frame._apply_auto_sync_interval()
    assert not frame._sync_timer.IsRunning()

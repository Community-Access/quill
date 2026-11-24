"""Headless tests for the auto-sync timer (PRD 45.10; off by default)."""

import tempfile

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.apps.beacon.model import Beacon, Resource
from quill.apps.beacon.sync_ui import SyncConfig


@pytest.fixture
def frame(monkeypatch):
    data_dir = tempfile.mkdtemp()
    monkeypatch.setenv("QUILLBEACON_DATA", data_dir)
    app = shared_wx_app()
    from quill.apps.beacon.app import BeaconFrame

    f = BeaconFrame()
    yield f
    # Close the way the app closes, not ``f.Destroy()``: only ``_on_close`` stops
    # ``_sync_timer``, and a timer whose owner window has been deleted fires into
    # freed memory the next time anything pumps messages. With the 300 s interval
    # these tests configure, that was the full-suite crash of 2026-10-13: the
    # tick landed about five minutes later, in whichever test first ran a real
    # event loop (tests/unit/ui/podcasts/test_cast_list_actions_responsive.py),
    # looking like a cumulative native fault in wxPython on Python 3.14.
    # ``_on_close`` also stops the bridge threads and closes the store.
    f.Close()
    if f:
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


def _ready(frame, tmp_path):
    frame.sync.save_config(
        SyncConfig(
            transport="folder", folder=str(tmp_path / "remote"), device="d", auto_sync_seconds=300
        )
    )
    frame.sync.setup_vault("pass")
    frame.sync.unlock("pass")


def _record_said(said):
    """Stand-in for results_follow.say_with: what would be said, at once."""
    return lambda _frame, news, gone, **_kw: said.append(f"{news} {gone}".strip())


def test_a_routine_auto_sync_is_written_not_spoken(frame, tmp_path, monkeypatch):
    """FUX-15: a sync that changed nothing here never talks over reading."""
    _ready(frame, tmp_path)
    said, refreshed = [], []
    monkeypatch.setattr(frame.announcer, "say", lambda message, *a, **k: said.append(message))
    monkeypatch.setattr(frame, "_refresh_results", lambda *a, **k: refreshed.append(True))
    monkeypatch.setattr(frame.sync, "sync_now", lambda: {"pushed": 2, "pulled": 0})
    frame._on_auto_sync_tick(None)
    assert said == [] and refreshed == []
    assert frame.GetStatusBar().GetStatusText() == "Auto-synced. Pushed 2, pulled 0."


def test_an_auto_sync_that_brought_changes_says_so(frame, tmp_path, monkeypatch):
    _ready(frame, tmp_path)
    said, refreshed = [], []
    from quill.apps.beacon import results_follow

    monkeypatch.setattr(results_follow, "say_with", _record_said(said))
    monkeypatch.setattr(frame, "_refresh_results", lambda **k: refreshed.append(k) or "")
    monkeypatch.setattr(frame.sync, "sync_now", lambda: {"pushed": 0, "pulled": 3})
    frame._on_auto_sync_tick(None)
    # One sentence: the refresh itself says no count (FUX-06 keeps the reader's row).
    assert said == ["Auto-synced. Pushed 0, pulled 3."] and refreshed == [{}]


def test_a_sync_that_moved_nothing_leaves_the_status_bar_alone(frame, tmp_path, monkeypatch):
    _ready(frame, tmp_path)
    frame.SetStatusText("12 results")
    monkeypatch.setattr(frame.sync, "sync_now", lambda: {"pushed": 0, "pulled": 0})
    frame._on_auto_sync_tick(None)
    assert frame.GetStatusBar().GetStatusText() == "12 results"


def test_conflicts_are_said_even_when_nothing_was_pulled(frame, tmp_path, monkeypatch):
    _ready(frame, tmp_path)
    from quill.apps.beacon import results_follow

    said = []
    monkeypatch.setattr(results_follow, "say_with", _record_said(said))
    monkeypatch.setattr(
        frame.sync, "sync_now", lambda: {"pushed": 0, "pulled": 0, "conflicts": [1]}
    )
    frame._on_auto_sync_tick(None)
    assert said == ["Auto-synced. Pushed 0, pulled 0. 1 conflict(s) need review."]


def test_the_selected_bookmark_stays_selected_after_a_sync_refresh(frame, tmp_path):
    for title in ("B", "C"):
        res = Resource(title=title, type="web", primary_uri=f"https://x/{title}")
        frame.store.put_beacon(
            Beacon(resource_id=res.resource_id, title=title, in_inbox=False), resource=res
        )
    frame._refresh_results()
    titles = [b.title for b in frame._results_cache]
    chosen = titles.index("C")
    frame.results.Select(chosen)
    res = Resource(title="A", type="web", primary_uri="https://x/A")
    frame.store.put_beacon(
        Beacon(resource_id=res.resource_id, title="A", in_inbox=False), resource=res
    )
    frame._refresh_results()  # what a sync that brought something does
    assert frame._selected_beacon().title == "C"


def test_a_window_disabled_by_a_modal_holds_the_sync(frame):
    """Windows disables a modal's owner -- a system message box or file picker
    too, which wx.GetTopLevelWindows never lists."""
    import sys

    from quill.apps.beacon.auto_sync import modal_open

    assert modal_open(frame) is False
    frame.Disable()
    try:
        assert modal_open(frame) is (sys.platform == "win32")
    finally:
        frame.Enable()

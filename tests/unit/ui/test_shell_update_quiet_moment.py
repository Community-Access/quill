"""Radio, Cast and Studio: the launch check's update offer waits for quiet (FUX-15).

``app_shell.check_for_app_updates(silent_no_update=True)`` used to open the
update window the moment the check came back -- over the station Radio had
just resumed, a recording, a Studio live broadcast, or from the tray. Now it
waits (``quill.ui.updates.quiet``); Help > Check for Updates opens it at once.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core import maintenance_moment
from quill.ui import maintenance_moment_ui, maintenance_probes
from quill.ui.app_shell import AppShellFrame
from quill.ui.radio.playback_state import RadioPlayerState
from tests.wx_session import patch_call_after


class _Release(SimpleNamespace):
    def __init__(self, version: str) -> None:
        super().__init__(
            version=version,
            prerelease=False,
            notes="* What changed",
            published_at="",
            download_url=(
                "https://github.com/Community-Access/quill/releases/download/"
                f"quill-studio-v{version}/Quill-Studio-Setup-{version}.exe"
            ),
        )


@pytest.fixture
def moment(monkeypatch):
    state = SimpleNamespace(now=0.0, later=[], recorded=[])
    maintenance_moment_ui.reset_for_tests()
    for key in ("radio", "cast", "studio"):
        maintenance_moment_ui._MOMENTS[key] = maintenance_moment.MaintenanceMoment(
            clock=lambda: state.now
        )
    monkeypatch.setattr(
        maintenance_moment_ui, "_wx_later", lambda _ms, run: state.later.append(run)
    )
    monkeypatch.setattr(maintenance_moment_ui, "window_in_front", lambda _w: True)
    monkeypatch.setattr(maintenance_moment_ui, "input_idle_seconds", lambda: None)
    from quill.core.updater import history

    monkeypatch.setattr(
        history, "record", lambda *_a, detail="", **_k: state.recorded.append(detail)
    )
    yield state
    maintenance_moment_ui.reset_for_tests()


def _shell(monkeypatch, app_key: str, releases: list) -> SimpleNamespace:
    """A shell with the network, the task runner and the dialog replaced."""
    seen = SimpleNamespace(offered=[], status=[], said=[], boxes=[])
    shell = AppShellFrame.__new__(AppShellFrame)
    bar = SimpleNamespace(SetStatusText=seen.status.append)
    shell.frame = SimpleNamespace(GetTitle=lambda: f"Quill {app_key}", GetStatusBar=lambda: bar)
    shell._announce = lambda message, **_k: seen.said.append(message)
    shell._show_message_box = lambda message, *_a, **_k: seen.boxes.append(message)
    shell._running_portable_build = lambda: False

    def _submit(name, func, *, on_success=None, on_failure=None):
        on_success(name, func())

    shell._task_manager = SimpleNamespace(submit=_submit)
    import quill.core.updater.feed_fetch as feed_fetch
    import quill.ui.update_notice as update_notice

    monkeypatch.setattr(feed_fetch, "releases_for_check", lambda *_a, **_k: releases)
    monkeypatch.setattr("quill.core.updates.fetch_app_releases", lambda *_a, **_k: releases)
    monkeypatch.setattr(
        update_notice,
        "show_update_available",
        lambda *_a, **kw: (seen.offered.append(kw["release"].version), "close")[1],
    )
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    shell.seen = seen
    return shell


def _check(shell, app_key: str, *, silent: bool = True) -> None:
    shell.check_for_app_updates(
        repo_slug="Community-Access/quill",
        current_version="1.0.0",
        app_key=app_key,
        silent_no_update=silent,
        match_edition=False,
    )


def test_studio_waits_out_the_first_minute_and_says_so_unspoken(monkeypatch, moment) -> None:
    shell = _shell(monkeypatch, "studio", [_Release("9.0.0")])
    _check(shell, "studio")
    assert shell.seen.offered == []
    assert shell.seen.said == []
    assert shell.seen.status == [
        "Update 9.0.0 is ready and waits for a quiet moment. Help, Check for Updates offers it now."
    ]
    moment.now = 61.0
    moment.later.pop(0)()
    assert shell.seen.offered == ["9.0.0"]
    assert shell.seen.status[-1] == ""  # the "waits" line is cleared as it opens


def test_the_line_outlives_the_apps_own_status_until_the_offer_opens(monkeypatch, moment) -> None:
    """Radio and Cast rewrite the bar on every playback change."""
    shell = _shell(monkeypatch, "radio", [_Release("9.0.0")])
    shell._set_status("Radio: playing Jazz FM")
    _check(shell, "radio")
    shell._set_status("Radio: playing Jazz FM - Take Five")
    assert shell.seen.status[-1] == (
        "Radio: playing Jazz FM - Take Five  Update 9.0.0 is ready and waits for a "
        "quiet moment. Help, Check for Updates offers it now."
    )
    moment.now = 61.0
    moment.later.pop(0)()
    assert shell.seen.offered == ["9.0.0"]
    assert shell.seen.status[-1] == "Radio: playing Jazz FM - Take Five"


def test_studio_never_offers_over_a_live_broadcast(monkeypatch, moment) -> None:
    moment.now = 100.0
    shell = _shell(monkeypatch, "studio", [_Release("9.0.0")])
    shell._live = object()
    _check(shell, "studio")
    assert shell.seen.status[0].startswith("Update 9.0.0 waits until the live broadcast ends.")
    moment.later.pop(0)()
    assert shell.seen.offered == []
    shell._live = None
    moment.now = 130.0
    moment.later.pop(0)()
    assert shell.seen.offered == ["9.0.0"]


def test_check_for_updates_opens_a_waiting_offer_at_once(monkeypatch, moment) -> None:
    shell = _shell(monkeypatch, "studio", [_Release("9.0.0")])
    _check(shell, "studio")
    assert shell.seen.offered == []
    _check(shell, "studio", silent=False)
    assert shell.seen.offered == ["9.0.0"]
    assert shell.seen.said == []  # no second "Checking for updates"


def test_a_manual_check_with_nothing_waiting_is_unchanged(monkeypatch, moment) -> None:
    shell = _shell(monkeypatch, "studio", [_Release("9.0.0")])
    _check(shell, "studio", silent=False)
    assert shell.seen.offered == ["9.0.0"]


# -- the probes ----------------------------------------------------------------


def _phrase(app_key: str, host: object) -> list[str]:
    return [probe() for probe in maintenance_probes.probes_for(app_key, host)]


def test_radio_counts_a_recording_and_audible_playback() -> None:
    host = SimpleNamespace(
        _radio_recorder=SimpleNamespace(is_recording=True),
        _radio_controller=SimpleNamespace(state=SimpleNamespace(state=RadioPlayerState.BUFFERING)),
    )
    assert _phrase("radio", host) == ["the recording ends", "playback stops"]
    host._radio_recorder.is_recording = False
    host._radio_controller.state.state = RadioPlayerState.PAUSED
    assert _phrase("radio", host) == ["", ""]


def test_cast_counts_playback_and_loading() -> None:
    from quill.ui.podcasts.player_controller import PodcastPlayerState

    controller = SimpleNamespace(
        is_playing=lambda: False, state=SimpleNamespace(state=PodcastPlayerState.LOADING)
    )
    host = SimpleNamespace(_podcast_controller=controller)
    assert _phrase("cast", host) == ["playback stops"]
    controller.state.state = PodcastPlayerState.PAUSED
    assert _phrase("cast", host) == [""]
    controller.is_playing = lambda: True
    assert _phrase("cast", host) == ["playback stops"]
    host._podcast_controller = None
    assert _phrase("cast", host) == [""]


def test_studio_counts_broadcast_recording_jobs_and_playback() -> None:
    host = SimpleNamespace(
        _live=None,
        _live_starting=True,
        _demo=None,
        _demo_busy="A recording is starting",
        _capture_pending=False,
        _protected_background_jobs={1: "Export"},
        _active_player=SimpleNamespace(is_playing=lambda: True),
    )
    assert _phrase("studio", host) == [
        "the live broadcast ends",
        "the recording ends",
        "the work in progress finishes",
        "playback stops",
    ]
    idle = SimpleNamespace(_protected_background_jobs={})
    assert _phrase("studio", idle) == ["", "", "", ""]

"""QUILL Lite checks for its own updates (Help > Check for Updates, Ctrl+Alt+U).

It shipped with no update check at all: the one app most likely to be somebody's
only Quill product, and the one whose users are least likely to go looking on
GitHub, had no way to learn that a newer version existed.

The network call is replaced throughout -- what is under test is what QUILL Lite
does with each answer, including the three it is supposed to keep quiet about.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from quill.apps import lite_updates
from tests.wx_session import patch_call_after


class _Release(SimpleNamespace):
    def __init__(self, version: str, *, prerelease: bool = False) -> None:
        super().__init__(
            version=version,
            prerelease=prerelease,
            notes=f"* What changed in {version}",
            published_at="",
            download_url=(
                f"https://github.com/Community-Access/quill/releases/download/"
                f"quilllite-v{version}/QuillLite-Setup-Shared-{version}.exe"
            ),
        )


@pytest.fixture
def updates(monkeypatch):
    """Run the check synchronously, with the network and both dialogs replaced.

    ``thread_submit`` and ``wx.CallAfter`` become straight calls so a test reads
    top to bottom; everything else is the shipped code.
    """
    state = SimpleNamespace(
        releases=[],
        error=None,
        boxes=[],
        offered=[],
        answer="close",
        downloaded=[],
    )

    def _submit(name, func, *, on_success=None, on_failure=None):
        try:
            result = func()
        except BaseException as error:  # noqa: BLE001 - mirrors QuillTaskManager
            if on_failure is not None:
                on_failure(name, error)
            return
        if on_success is not None:
            on_success(name, result)

    def _fetch(_prefix, _url, **_kw):
        if state.error is not None:
            raise state.error
        return state.releases

    import quill.core.updates as core_updates
    import quill.ui.update_download as update_download
    import quill.ui.update_notice as update_notice

    monkeypatch.setattr(core_updates, "fetch_app_releases", _fetch)
    monkeypatch.setattr(update_download, "thread_submit", _submit)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        lite_updates,
        "show_message_box",
        lambda message, caption, style, parent=None: state.boxes.append(message),
    )
    monkeypatch.setattr(
        update_notice,
        "show_update_available",
        lambda *a, **kw: (state.offered.append(kw["release"].version), state.answer)[1],
    )
    monkeypatch.setattr(
        lite_updates, "_download", lambda _w, release, _a: state.downloaded.append(release.version)
    )
    monkeypatch.setattr(lite_updates, "_running_portable_build", lambda: False)
    return state


class _Window(SimpleNamespace):
    """A stand-in document window: the two things the check reaches for."""

    def __init__(self) -> None:
        super().__init__(said=[])

    def _announce(self, message: str) -> None:
        self.said.append(message)


# -- the throttle ---------------------------------------------------------


def test_a_profile_that_has_never_checked_is_due():
    assert lite_updates.update_check_due("") is True


def test_a_check_an_hour_ago_is_not_due_again():
    assert lite_updates.update_check_due(datetime.now(UTC).isoformat()) is False


def test_a_check_yesterday_is_due_again():
    old = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
    assert lite_updates.update_check_due(old) is True


def test_a_hand_edited_timestamp_does_not_silently_switch_checking_off():
    assert lite_updates.update_check_due("last Tuesday") is True


# -- what each answer does ------------------------------------------------


def test_a_newer_release_is_offered_with_its_notes(updates):
    updates.releases = [_Release("99.0.0")]
    lite_updates.check_for_updates(_Window())
    assert updates.offered == ["99.0.0"]


def test_saying_update_starts_the_download(updates):
    updates.releases = [_Release("99.0.0")]
    updates.answer = "update"
    lite_updates.check_for_updates(_Window())
    assert updates.downloaded == ["99.0.0"]


def test_saying_close_downloads_nothing(updates):
    updates.releases = [_Release("99.0.0")]
    updates.answer = "close"
    lite_updates.check_for_updates(_Window())
    assert updates.downloaded == []


def test_a_manual_check_that_finds_nothing_still_answers_in_a_dialog(updates):
    """Silence is indistinguishable from a key that is not bound."""
    updates.releases = [_Release("1.0.0")]
    lite_updates.check_for_updates(_Window())
    assert len(updates.boxes) == 1
    assert "up to date" in updates.boxes[0]


def test_a_prerelease_is_never_offered_to_the_stable_channel(updates):
    updates.releases = [_Release("9.9.9", prerelease=True)]
    lite_updates.check_for_updates(_Window())
    assert updates.offered == []
    assert "up to date" in updates.boxes[0]


def test_a_failed_manual_check_says_why(updates):
    updates.error = OSError("no network")
    lite_updates.check_for_updates(_Window())
    assert len(updates.boxes) == 1
    assert "no network" in updates.boxes[0]


# -- the launch check keeps quiet -----------------------------------------


def test_the_launch_check_says_nothing_when_there_is_nothing(updates):
    updates.releases = [_Release("1.0.0")]
    window = _Window()
    lite_updates.check_for_updates(window, silent_no_update=True)
    assert updates.boxes == []
    assert window.said == []


def test_the_launch_check_says_nothing_when_the_network_is_down(updates):
    updates.error = OSError("no network")
    window = _Window()
    lite_updates.check_for_updates(window, silent_no_update=True)
    assert updates.boxes == []
    assert window.said == []


class _Moment:
    """The launch check's quiet-moment rule (FUX-15) on a hand-turned clock."""

    def __init__(self, monkeypatch) -> None:
        from quill.core import maintenance_moment
        from quill.core.updater import history
        from quill.ui import maintenance_moment_ui, maintenance_probes

        self.now = 0.0
        self.later: list = []
        self.dictating = False
        self.recorded: list[str] = []
        maintenance_moment_ui.reset_for_tests()
        maintenance_moment_ui._MOMENTS["quilllite"] = maintenance_moment.MaintenanceMoment(
            clock=lambda: self.now
        )
        monkeypatch.setattr(
            maintenance_moment_ui, "_wx_later", lambda _ms, run: self.later.append(run)
        )
        monkeypatch.setattr(maintenance_moment_ui, "window_in_front", lambda _w: True)
        monkeypatch.setattr(maintenance_moment_ui, "input_idle_seconds", lambda: None)
        monkeypatch.setattr(
            maintenance_probes,
            "_windows_dictation",
            lambda: "dictation ends" if self.dictating else "",
        )
        monkeypatch.setattr(
            history, "record", lambda *_a, detail="", **_k: self.recorded.append(detail)
        )
        self._reset = maintenance_moment_ui.reset_for_tests

    def poll(self) -> None:
        self.later.pop(0)()


@pytest.fixture
def moment(monkeypatch):
    clock = _Moment(monkeypatch)
    yield clock
    clock._reset()


class _StatusWindow(_Window):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def _set_status_message(self, message: str) -> None:
        self.messages.append(message)


def test_the_launch_check_offers_a_real_update_after_the_first_minute(updates, moment):
    """Not on top of the window the screen reader is still reading (FUX-15)."""
    updates.releases = [_Release("99.0.0")]
    window = _StatusWindow()
    lite_updates.check_for_updates(window, silent_no_update=True)
    assert updates.offered == []
    assert window.said == []  # written, never spoken
    assert window.messages == [
        "Update 99.0.0 is ready and waits for a quiet moment. "
        "Help, Check for Updates (Ctrl+Alt+U) offers it now."
    ]
    assert moment.recorded == window.messages
    moment.now = 61.0
    moment.poll()
    assert updates.offered == ["99.0.0"]


def test_the_launch_check_never_opens_its_offer_while_dictating(updates, moment):
    updates.releases = [_Release("99.0.0")]
    moment.now = 120.0
    moment.dictating = True
    window = _StatusWindow()
    lite_updates.check_for_updates(window, silent_no_update=True)
    assert updates.offered == []
    assert window.messages[0].startswith("Update 99.0.0 waits until dictation ends.")
    moment.now = 400.0
    moment.poll()
    assert updates.offered == []
    moment.dictating = False
    moment.poll()  # just stopped: waits a little longer
    assert updates.offered == []
    moment.now = 430.0
    moment.poll()
    assert updates.offered == ["99.0.0"]


def test_check_for_updates_opens_a_waiting_offer_at_once(updates, moment):
    updates.releases = [_Release("99.0.0")]
    lite_updates.check_for_updates(_StatusWindow(), silent_no_update=True)
    assert updates.offered == []
    updates.releases = []  # asking again must not need the network
    lite_updates.check_for_updates(_StatusWindow())
    assert updates.offered == ["99.0.0"]
    assert updates.boxes == []


# -- the menu item --------------------------------------------------------


def test_queued_launch_check_does_not_start_during_shutdown(monkeypatch):
    checked = []
    app = SimpleNamespace(
        shutting_down=False,
        settings=SimpleNamespace(check_updates_on_launch=True, last_update_check=""),
        save_settings=lambda: None,
    )
    capture = patch_call_after(monkeypatch, lambda *_a, **_k: None)
    monkeypatch.setattr(
        lite_updates, "check_for_updates", lambda *args, **kwargs: checked.append(args)
    )
    lite_updates.check_at_launch(app)
    app.shutting_down = True
    # Only the check itself: with a wx.App alive in this worker, launch also
    # queues _confirm_update_started, and whether one is alive depends on which
    # files ran first -- so count the check, not every deferred call.
    scheduled = [
        fn for fn, _a, _k in capture.calls if fn is not lite_updates._confirm_update_started
    ]
    assert len(scheduled) == 1
    scheduled[0]()
    assert checked == []


def test_the_help_menu_command_runs_the_check_and_stamps_the_clock(lite_window, updates):
    win = lite_window("text")
    win.app.settings.last_update_check = ""
    updates.releases = [_Release("1.0.0")]

    win.cmd_check_updates()

    assert win.app.settings.last_update_check != ""
    assert win.app.queued_settings == 1
    assert "up to date" in updates.boxes[0]


def test_a_waiting_offer_opens_over_the_document_in_use_now(updates, moment, monkeypatch):
    """The document the check began in may be closed by the time it opens."""
    import quill.ui.update_notice as update_notice

    parents: list = []
    monkeypatch.setattr(
        update_notice,
        "show_update_available",
        lambda parent, **kw: (parents.append(parent), "close")[1],
    )
    updates.releases = [_Release("99.0.0")]
    later_doc = _StatusWindow()
    shell = SimpleNamespace(GetActiveChild=lambda: later_doc)
    first = _StatusWindow()
    first.GetTopLevelParent = lambda: shell
    lite_updates.check_for_updates(first, silent_no_update=True)
    moment.now = 61.0
    moment.poll()
    assert parents == [later_doc]

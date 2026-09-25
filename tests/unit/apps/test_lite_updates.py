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
    monkeypatch.setattr(lite_updates.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
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
    updates.releases = [_Release("2.0.0")]
    lite_updates.check_for_updates(_Window())
    assert updates.offered == ["2.0.0"]


def test_saying_update_starts_the_download(updates):
    updates.releases = [_Release("2.0.0")]
    updates.answer = "update"
    lite_updates.check_for_updates(_Window())
    assert updates.downloaded == ["2.0.0"]


def test_saying_close_downloads_nothing(updates):
    updates.releases = [_Release("2.0.0")]
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


def test_the_launch_check_still_offers_a_real_update(updates):
    """QUILL Lite has no notification centre to defer it to."""
    updates.releases = [_Release("2.0.0")]
    lite_updates.check_for_updates(_Window(), silent_no_update=True)
    assert updates.offered == ["2.0.0"]


# -- the menu item --------------------------------------------------------


def test_the_help_menu_command_runs_the_check_and_stamps_the_clock(lite_window, updates):
    win = lite_window("text")
    win.app.settings.last_update_check = ""
    updates.releases = [_Release("1.0.0")]

    win.cmd_check_updates()

    assert win.app.settings.last_update_check != ""
    assert win.app.saved_settings >= 1
    assert "up to date" in updates.boxes[0]

"""The guided half: what the checks answer, and that the window is reachable.

The checks are pure enough to test against a stand-in host -- which is the
point of their design: they read a handful of named attributes and answer
"cannot tell" for anything they cannot see, so a half-built app never makes a
lesson misbehave. The rest here are source-level wiring assertions, the same
shape as the other Radio wiring guards.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.ui import tutorial_checks
from quill.ui.radio.tutorial_checks import PROBE

_ROOT = Path(__file__).resolve().parents[4]


def evaluate(check, host, baseline):
    """Radio's checks, asked the way the window asks them."""
    return tutorial_checks.evaluate(check, host, baseline, PROBE)


def snapshot(host):
    return tutorial_checks.snapshot(host, PROBE)


def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


class _Windows:
    def __init__(self, titles: list[str]) -> None:
        self._titles = titles

    def open_titles(self) -> list[str]:
        return list(self._titles)


def _host(
    *,
    state: str = "STOPPED",
    volume: int = 70,
    muted: bool = False,
    favorites: int = 0,
    recordings: int = 0,
    titles: list[str] | None = None,
) -> SimpleNamespace:
    playback = SimpleNamespace(
        state=SimpleNamespace(name=state),
        volume_percent=volume,
        muted=muted,
    )
    return SimpleNamespace(
        _radio_controller=SimpleNamespace(state=playback),
        _radio_favorites=SimpleNamespace(favorites=list(range(favorites))),
        _radio_recorder=SimpleNamespace(active_count=recordings),
        _windows=_Windows(titles or []),
    )


def test_playing_is_answered_from_the_controller() -> None:
    host = _host(state="PLAYING")
    satisfied, sentence = evaluate("playing", host, {})
    assert satisfied
    assert sentence == "something is playing now"
    assert not evaluate("playing", _host(state="CONNECTING"), {})[0]


def test_volume_is_a_delta_not_a_level() -> None:
    """Somebody already at 70 has not done the step by standing still."""
    baseline = snapshot(_host(volume=70))
    assert not evaluate("volume-changed", _host(volume=70), baseline)[0]
    assert evaluate("volume-changed", _host(volume=60), baseline)[0]


def test_favorites_grow_rather_than_exist() -> None:
    """A listener with forty favorites has not already passed 'add one'."""
    baseline = snapshot(_host(favorites=40))
    assert not evaluate("favorite-added", _host(favorites=40), baseline)[0]
    assert evaluate("favorite-added", _host(favorites=41), baseline)[0]


def test_recording_started_and_finished_are_opposite_directions() -> None:
    idle = snapshot(_host(recordings=0))
    assert evaluate("recording-started", _host(recordings=1), idle)[0]
    running = snapshot(_host(recordings=1))
    assert evaluate("recording-finished", _host(recordings=0), running)[0]
    # Finishing something that never started is not a finish.
    assert not evaluate("recording-finished", _host(recordings=0), idle)[0]


def test_a_window_check_reads_the_open_peer_windows() -> None:
    host = _host(titles=["Quill Radio", "Browse Stations"])
    assert evaluate("window:Browse Stations", host, {})[0]
    assert not evaluate("window:Player", host, {})[0]


def test_an_app_it_cannot_read_answers_no_rather_than_raising() -> None:
    bare = SimpleNamespace()
    assert snapshot(bare)["volume"] is None
    for check in sorted(tutorial_checks.known_checks(PROBE)):
        assert evaluate(check, bare, {})[0] is False
    assert evaluate("no-such-check", _host(), {}) == (False, "")


def test_the_window_manager_can_list_what_is_open() -> None:
    """The lesson watcher needs the titles; the manager had no read-only door."""
    assert "def open_titles(self)" in _src("quill/ui/window_menu.py")


def test_help_menu_offers_tutorials_and_the_command_is_registered() -> None:
    app = _src("quill/apps/radio.py")
    menu = _src("quill/apps/radio_help_docs.py")
    assert 'host._menu_label("&Tutorials...", "radio.tutorials")' in menu
    assert "def open_radio_tutorials(self" in app
    assert "radio_help_docs.install_help_items(self, help_menu, wx)" in app
    assert '"radio.tutorials"' in _src("quill/ui/radio/palette_commands.py")


def test_tutorials_has_a_key_and_the_prd_moved_out_of_its_way() -> None:
    """Both halves of the swap, so neither can be undone on its own."""
    from quill.core.app_keymaps import APP_KEYMAPS

    assert APP_KEYMAPS["radio"]["radio.tutorials"] == "Ctrl+Alt+F1"
    assert "&Product Requirements...\\tAlt+Shift+F1" in _src("quill/apps/radio_help_docs.py")


def test_the_window_states_its_purpose_for_f1() -> None:
    from quill.core.radio.surface_help import PURPOSES
    from quill.ui.radio.tutorials import TITLE

    assert TITLE in PURPOSES


def test_the_window_watches_rather_than_grades() -> None:
    """Follow me is a courtesy: every step still has Next, and nothing blocks."""
    source = _src("quill/ui/tutorials_window.py")
    assert "Follow &me" in _src("quill/ui/tutorials_contents.py") or "Follow &me" in source
    assert "self._next_btn" in source
    # The watcher only ever moves forward, and only when the check says so.
    assert "self._step_by(1)" in source

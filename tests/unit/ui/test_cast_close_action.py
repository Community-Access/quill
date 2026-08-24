"""Closing means one thing in Cast and three in Radio -- until now (5.4).

Cast had one answer to closing the window (exit) and one narrow escape from it
(the Alt+F4-to-tray checkbox), so the titlebar X ended playback with no way to
say otherwise. Radio has carried Ask / Exit / Minimize to Tray for as long as
it has had a tray icon. Same window model, same audience, and one of them lost
an hour of listening to a reflex.

Three things are worth pinning, and they are the three that could quietly go
wrong:

* **The shipped default stays "exit".** An upgrade that starts asking a
  question is an upgrade that changed somebody's Alt+F4 under them.
* **A junk value reads as "exit", never "ask".** The failure mode of guessing
  wrong here is a dialog interrupting every deliberate close.
* **The stakes sentence is true.** It is the only thing telling somebody what
  Exit costs at the moment they are deciding.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.apps.podcasts_close import (
    _CLOSE_ACTION_LABELS,
    _CLOSE_ACTION_VALUES,
    _close_action_index,
    _close_action_value,
)
from quill.core.podcasts.history import PodcastHistory, load_history, save_history
from quill.ui.podcasts.close_confirm_dialog import stakes_line

# -- the setting ----------------------------------------------------------------


def test_the_shipped_answer_is_what_cast_has_always_done() -> None:
    assert PodcastHistory().close_action == "exit"


def test_the_setting_survives_a_save(tmp_path: Path) -> None:
    history = PodcastHistory()
    history.close_action = "minimize"
    save_history(tmp_path, history)

    assert load_history(tmp_path).close_action == "minimize"


def test_an_older_library_file_reads_as_exit(tmp_path: Path) -> None:
    """Nobody's close behaviour changes on upgrade."""
    save_history(tmp_path, PodcastHistory())
    store = tmp_path / "podcast_history.json"
    text = store.read_text(encoding="utf-8").replace('"close_action": "exit",', "")
    store.write_text(text, encoding="utf-8")

    assert load_history(tmp_path).close_action == "exit"


@pytest.mark.parametrize("junk", ["", "  ", "ASK ME", "tray", "0", "null"])
def test_a_junk_value_never_becomes_ask(tmp_path: Path, junk: str) -> None:
    """The asymmetry that matters: reading junk as "ask" would start
    interrupting every Alt+F4 with a question nobody chose."""
    save_history(tmp_path, PodcastHistory())
    store = tmp_path / "podcast_history.json"
    store.write_text(
        store.read_text(encoding="utf-8").replace(
            '"close_action": "exit"', f'"close_action": "{junk}"'
        ),
        encoding="utf-8",
    )

    assert load_history(tmp_path).close_action == "exit"


def test_a_stored_ask_is_honoured() -> None:
    """The other half: a real choice stands."""
    assert PodcastHistory.__dataclass_fields__["close_action"].default == "exit"
    history = PodcastHistory()
    history.close_action = "ask"
    assert history.close_action == "ask"


# -- the Preferences combo ------------------------------------------------------


def test_the_three_answers_read_the_same_as_radios() -> None:
    """Two apps that behave the same on close should read the same in
    Preferences, in the same order -- otherwise the shared behaviour is
    something the listener has to rediscover per app."""
    radio = Path(__file__).resolve().parents[3] / "quill" / "apps" / "radio.py"
    source = radio.read_text(encoding="utf-8")

    assert '_CLOSE_ACTION_LABELS = ("Ask every time", "Exit", "Minimize to Tray")' in source
    assert _CLOSE_ACTION_LABELS == ("Ask every time", "Exit", "Minimize to Tray")


def test_every_row_round_trips() -> None:
    for index, value in enumerate(_CLOSE_ACTION_VALUES):
        assert _close_action_index(value) == index
        assert _close_action_value(index) == value


def test_an_unreadable_row_or_value_lands_on_exit() -> None:
    for junk in ("", "TRAY", None, "ask me"):
        assert _close_action_value(_close_action_index(junk)) in {"exit", "ask"}
    assert _close_action_index("nonsense") == 1
    assert _close_action_value(-1) == "exit"
    assert _close_action_value(99) == "exit"


# -- the sentence a listener actually hears -------------------------------------


def test_nothing_at_stake_says_nothing() -> None:
    """A dialog that opens with a warning about nothing teaches people to
    ignore the warning."""
    assert stakes_line(playing=False, downloads=0) == ""


def test_playback_is_named() -> None:
    said = stakes_line(playing=True, downloads=0)

    assert said == "An episode is playing -- exiting now stops it."


def test_one_download_is_singular_and_several_are_counted() -> None:
    """Read aloud, "1 downloads" is the kind of thing that makes somebody stop
    trusting the rest of the sentence."""
    assert (
        stakes_line(playing=False, downloads=1)
        == "a download is in progress -- exiting now stops it."
    )
    assert "3 downloads are in progress" in stakes_line(playing=False, downloads=3)


def test_both_at_once_read_as_one_sentence() -> None:
    said = stakes_line(playing=True, downloads=2)

    assert said == "An episode is playing and 2 downloads are in progress -- exiting now stops it."


# -- the wiring -----------------------------------------------------------------


def test_the_close_flow_asks_the_history_rather_than_hard_coding_exit() -> None:
    source = (
        Path(__file__).resolve().parents[3] / "quill" / "apps" / "podcasts_close.py"
    ).read_text(encoding="utf-8")

    assert 'getattr(self._podcast_history, "close_action", "exit")' in source
    assert "confirm=self._run_cast_close_confirm" in source


def test_the_confirm_is_never_shown_from_inside_the_close_handler() -> None:
    """ShowModal from an EVT_CLOSE handler on wxMSW can return without ever
    displaying, and the close is then silently vetoed -- the Quill Radio
    "Alt+F4 does nothing while a station plays" bug. The shared flow vetoes
    and re-runs the confirm deferred; this is the assertion that Cast uses
    that flow rather than opening the dialog itself.
    """
    source = (
        Path(__file__).resolve().parents[3] / "quill" / "apps" / "podcasts_close.py"
    ).read_text(encoding="utf-8")

    handler = source[
        source.index("def _on_cast_app_close") : source.index("def _cast_close_is_protected")
    ]

    assert "CastCloseConfirmDialog" not in handler
    assert "self.handle_app_close(" in handler


def test_a_probe_that_raises_does_not_stop_the_window_closing() -> None:
    """This runs on the way out. A close handler that raises is a window that
    cannot be closed, which is worse than any wrong answer it could give."""
    from quill.apps.podcasts_close import CastCloseMixin

    class Boom(CastCloseMixin):
        @property
        def _podcast_controller(self):  # noqa: ANN202 - a deliberate detonation
            raise RuntimeError("no controller")

    assert Boom()._cast_close_stakes() == (False, 0)
    assert Boom()._cast_close_is_protected() is False

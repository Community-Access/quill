"""The dial tuning policy, driven by a fake clock (idea from BlindRadio by serrebidev, MIT)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.radio import dial_tuning as dial
from quill.core.radio.models import RadioStation


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _row(name: str, **kw: object) -> dial.DialRow:
    station_kw = {k: kw.pop(k) for k in ("stream_url", "is_recording") if k in kw}
    station = RadioStation(
        name=name,
        stream_url=str(station_kw.get("stream_url", f"http://x/{name}")),
        is_recording=bool(station_kw.get("is_recording", False)),
    )
    return dial.DialRow(key=station.stream_url, station=station, **kw)  # type: ignore[arg-type]


ON = dial.DialSettings(enabled=True)


def _tuner(settings: dial.DialSettings = ON, metered: bool = False):
    clock = Clock()
    return dial.DialTuner(settings, clock=clock, is_metered=lambda: metered), clock


# -- settings -------------------------------------------------------------


def test_ships_off_and_every_default_matches_the_design():
    s = dial.DialSettings()
    assert s.enabled is False
    assert s.wait_ms == 350
    assert s.keep_neighbours is True
    assert s.metered_stop is True
    assert s.hiss is True and s.hiss_level == "low"
    assert s.remember_volume is False


def test_from_history_reads_fields_and_repairs_nonsense():
    history = SimpleNamespace(
        dial_tuning=True, dial_wait_ms=999, dial_hiss_level="loud", dial_keep_neighbours=False
    )
    s = dial.DialSettings.from_history(history)
    assert s.enabled and not s.keep_neighbours
    assert s.wait_ms == dial.DEFAULT_WAIT_MS
    assert s.hiss_level == "low"
    assert dial.DialSettings.from_history(object()) == dial.DialSettings()


def test_choice_indices_round_trip():
    for index, (ms, _label) in enumerate(dial.WAIT_CHOICES):
        assert dial.wait_index(ms) == index
    assert dial.WAIT_CHOICES[dial.wait_index(12345)][0] == 350
    assert dial.hiss_level_index("medium") == 1
    assert dial.hiss_level_index("nope") == 0


# -- which rows tune ------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(dial.LIVE_LISTS))
def test_live_lists_tune(kind):
    assert dial.row_tunes(_row("A", list_kind=kind))


@pytest.mark.parametrize(
    "row",
    [
        None,
        dial.DialRow(key="folder"),
        _row("Episode", is_recording=True),
        _row("Video", stream_url="https://www.youtube.com/watch?v=abc"),
        _row("Spotify", stream_url="spotify:playlist:1"),
        _row("Lazy", list_kind=dial.BROWSE, needs_resolve=True),
        _row("Pod", list_kind=dial.BROWSE, source="apple"),
        _row("Book", list_kind=dial.BROWSE, source="librivox"),
        _row("Elsewhere", list_kind="podcasts"),
    ],
)
def test_on_demand_and_folder_rows_never_tune(row):
    assert not dial.row_tunes(row)


# -- the settle timer -----------------------------------------------------


def test_off_does_nothing():
    tuner, clock = _tuner(dial.DialSettings())
    assert tuner.focus(_row("A")) == []
    clock.advance(5)
    assert tuner.poll() == []
    assert tuner.next_due() is None


def test_settling_plays_after_the_wait_and_not_before():
    tuner, clock = _tuner()
    a = _row("A")
    tuner.focus(a)
    assert tuner.next_due() == pytest.approx(0.35)
    clock.advance(0.3)
    assert tuner.poll() == []
    clock.advance(0.06)
    actions = tuner.poll()
    assert dial.Tune(a) in actions
    assert dial.Warm(()) in actions
    assert tuner.current_key == a.key
    assert tuner.passing_through(a.key)


def test_holding_an_arrow_plays_nothing_until_it_stops_even_when_instant():
    # Instant plays a tap at once. Repeats of a held key arrive closer together
    # than HOLD_GAP_S, and play nothing until the key comes up.
    tuner, clock = _tuner(dial.DialSettings(enabled=True, wait_ms=0))
    rows = [_row(f"S{i}") for i in range(10)]
    tuner.focus(rows[0])
    assert [a for a in tuner.poll() if isinstance(a, dial.Tune)] == [dial.Tune(rows[0])]
    clock.advance(0.03)
    for row in rows[1:]:
        tuner.focus(row)
        assert not [a for a in tuner.poll() if isinstance(a, dial.Tune)]
        clock.advance(0.03)  # key repeat
    clock.advance(dial.HOLD_GAP_S)
    tunes = [a for a in tuner.poll() if isinstance(a, dial.Tune)]
    assert tunes == [dial.Tune(rows[-1])]


def test_holding_an_arrow_with_a_wait_plays_only_where_it_stops():
    tuner, clock = _tuner()
    rows = [_row(f"S{i}") for i in range(10)]
    for row in rows:
        tuner.focus(row)
        assert not [a for a in tuner.poll() if isinstance(a, dial.Tune)]
        clock.advance(0.03)
    clock.advance(0.35)
    assert [a for a in tuner.poll() if isinstance(a, dial.Tune)] == [dial.Tune(rows[-1])]


def test_instant_tap_plays_at_once():
    tuner, _clock = _tuner(dial.DialSettings(enabled=True, wait_ms=0))
    tuner.focus(_row("A"))
    assert tuner.next_due() == 0
    assert any(isinstance(a, dial.Tune) for a in tuner.poll())


def test_a_folder_row_cancels_the_pending_tune():
    tuner, clock = _tuner()
    tuner.focus(_row("A"))
    tuner.focus(dial.DialRow(key="folder"))
    clock.advance(2)
    assert tuner.poll() == []


def test_back_on_the_playing_station_does_not_retune():
    tuner, clock = _tuner()
    a = _row("A")
    tuner.focus(a)
    clock.advance(1)
    tuner.poll()
    clock.advance(1)
    tuner.focus(a)
    clock.advance(1)
    assert tuner.poll() == []


def test_leaving_the_list_cancels_pending_and_lets_neighbours_go():
    tuner, clock = _tuner()
    tuner.focus(_row("A"))
    assert tuner.left_list() == [dial.Warm(())]
    clock.advance(1)
    assert tuner.poll() == []


# -- neighbours ------------------------------------------------------------


def test_neighbours_warm_once_connected_after_first():
    tuner, clock = _tuner()
    before, a, after = _row("B"), _row("A"), _row("C")
    tuner.focus(a, before, after)
    clock.advance(1)
    tuner.poll()
    assert tuner.connected(a.key) == [dial.Warm((after, before))]
    assert not tuner.hiss_wanted


def test_neighbours_respect_settings_and_metered():
    a, b, c = _row("A"), _row("B"), _row("C")
    off = dial.DialSettings(enabled=True, keep_neighbours=False)
    assert dial.warm_candidates(a, b, c, settings=off, metered=False) == ()
    assert dial.warm_candidates(a, b, c, settings=ON, metered=True) == ()
    allow = dial.DialSettings(enabled=True, metered_stop=False)
    assert dial.warm_candidates(a, b, c, settings=allow, metered=True) == (c, b)


def test_neighbours_skip_untunable_and_duplicates_and_cap_at_two():
    a = _row("A")
    episode = _row("E", is_recording=True)
    assert dial.warm_candidates(a, episode, a, settings=ON, metered=False) == ()
    b = _row("B")
    assert dial.warm_candidates(a, b, b, settings=ON, metered=False) == (b,)
    assert dial.MAX_WARM == 2 and dial.MAX_PLAYERS == 3


def test_metered_tuner_never_warms():
    tuner, clock = _tuner(metered=True)
    a = _row("A")
    tuner.focus(a, _row("B"), _row("C"))
    clock.advance(1)
    tuner.poll()
    assert tuner.connected(a.key) == [dial.Warm(())]


def test_a_broken_metered_probe_means_not_metered():
    clock = Clock()

    def boom() -> bool:
        raise RuntimeError

    tuner = dial.DialTuner(ON, clock=clock, is_metered=boom)
    a, c = _row("A"), _row("C")
    tuner.focus(a, None, c)
    clock.advance(1)
    tuner.poll()
    assert tuner.connected(a.key) == [dial.Warm((c,))]


def test_turning_off_lets_everything_go():
    tuner, clock = _tuner()
    tuner.focus(_row("A"))
    clock.advance(1)
    tuner.poll()
    assert tuner.update_settings(dial.DialSettings()) == [dial.Warm(())]
    assert not tuner.hiss_wanted
    assert tuner.poll() == []


# -- the hiss and a dead station -------------------------------------------


def test_hiss_plays_while_connecting_and_stops_on_air():
    tuner, clock = _tuner()
    a = _row("A")
    tuner.focus(a)
    clock.advance(1)
    tuner.poll()
    assert tuner.hiss_wanted
    tuner.connected(a.key)
    assert not tuner.hiss_wanted


def test_no_hiss_when_switched_off():
    tuner, clock = _tuner(dial.DialSettings(enabled=True, hiss=False))
    tuner.focus(_row("A"))
    clock.advance(1)
    tuner.poll()
    assert not tuner.hiss_wanted


def test_dead_station_hiss_stops_then_said_once():
    tuner, clock = _tuner()
    a = _row("Dead FM")
    tuner.focus(a)
    clock.advance(1)
    tuner.poll()
    clock.advance(dial.SILENT_AFTER_S)
    assert tuner.poll() == []
    assert not tuner.hiss_wanted
    clock.advance(dial.SAY_AFTER_S)
    assert tuner.poll() == [dial.Say("Dead FM is not answering.")]
    clock.advance(10)
    assert tuner.poll() == []
    assert tuner.next_due() is None


def test_failed_connection_stops_hiss_at_once_and_says_later():
    tuner, clock = _tuner()
    a = _row("Gone")
    tuner.focus(a)
    clock.advance(1)
    tuner.poll()
    tuner.failed(a.key)
    assert not tuner.hiss_wanted
    assert tuner.next_due() == pytest.approx(dial.SAY_AFTER_S)
    clock.advance(dial.SAY_AFTER_S)
    assert tuner.poll() == [dial.Say("Gone is not answering.")]


def test_reports_about_another_station_are_ignored():
    tuner, clock = _tuner()
    tuner.focus(_row("A"))
    clock.advance(1)
    tuner.poll()
    assert tuner.connected("other") == []
    assert tuner.failed("other") == []
    assert tuner.hiss_wanted


# -- commit ------------------------------------------------------------------


def test_enter_commits_once_and_ends_passing_through():
    tuner, clock = _tuner()
    a = _row("A")
    tuner.focus(a)
    clock.advance(1)
    tuner.poll()
    tuner.connected(a.key)
    assert tuner.commit(a.key) is True
    assert not tuner.passing_through(a.key)
    assert tuner.hiss_wanted  # the reload connects again
    assert tuner.commit(a.key) is False
    assert tuner.commit("never tuned") is False


def test_a_committed_failure_is_the_players_to_report():
    tuner, clock = _tuner()
    a = _row("A")
    tuner.focus(a)
    clock.advance(1)
    tuner.poll()
    tuner.commit(a.key)
    tuner.failed(a.key)
    clock.advance(30)
    assert tuner.poll() == []
    assert tuner.next_due() is None


def test_forget_drops_the_current_station():
    tuner, clock = _tuner()
    a = _row("A")
    tuner.focus(a)
    clock.advance(1)
    tuner.poll()
    tuner.forget()
    assert tuner.current_key == ""
    assert not tuner.passing_through(a.key)


# -- recording -----------------------------------------------------------------


def test_recording_pauses_tuning_and_says_so_once():
    tuner, clock = _tuner()
    assert tuner.focus(_row("A"), recording=True) == [dial.Say(dial.RECORDING_PAUSED)]
    assert tuner.focus(_row("B"), recording=True) == []
    clock.advance(2)
    assert tuner.poll() == []
    # Recording over: moving tunes again, and the next recording says it again.
    tuner.focus(_row("C"))
    clock.advance(1)
    assert any(isinstance(a, dial.Tune) for a in tuner.poll())
    assert tuner.focus(_row("D"), recording=True) == [dial.Say(dial.RECORDING_PAUSED)]


def test_state_word_names_the_new_state():
    assert dial.state_word(True).endswith("on.")
    assert dial.state_word(False).endswith("off.")
